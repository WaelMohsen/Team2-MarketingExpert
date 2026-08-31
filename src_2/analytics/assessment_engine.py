"""Benchmark evidence and assign transparent target and funding decisions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite, sqrt
from statistics import NormalDist
from typing import Any, Literal

import pandas as pd

from src_2.contracts import (
    CampaignAssessment,
    CampaignEvidencePack,
    DataQualityReport,
    EmpiricalBayesScore,
    EntityEvidence,
    MetricAssessment,
    MetricEvidence,
)
from src_2.domain.assessment_rules import (
    NextCycleAction,
    classify_next_cycle_action,
    classify_target,
)
from src_2.domain.config import CampaignTypeConfig, CampaignTypeRegistry, GuardrailConfig
from src_2.domain.models import (
    CampaignType,
    EntityLevel,
    EvidenceStatus,
    FundingDecision,
)

from .aggregations import CycleScorecards

Direction = Literal["higher", "lower", "range"]

METRIC_METADATA: dict[str, tuple[str, Direction]] = {
    "reach": ("Summed daily reach proxy", "higher"),
    "avg_daily_reach": ("Average valid daily reach", "higher"),
    "peak_daily_reach": ("Peak valid daily reach", "higher"),
    "impressions": ("Impressions", "higher"),
    "frequency": ("Frequency", "range"),
    "link_ctr_pct": ("Link click-through rate", "higher"),
    "link_ctr": ("Link click-through rate", "higher"),
    "cpm": ("Cost per 1,000 impressions", "lower"),
    "cpc": ("Cost per link click", "lower"),
    "meta_conversation_starts": ("Meta-attributed conversation starts", "higher"),
    "observed_conversations": ("Observed WhatsApp conversations", "higher"),
    "mature_conversations": ("Mature outcome conversations", "higher"),
    "mature_unique_customers": ("Customers with mature outcomes", "higher"),
    "observed_conversations_per_day": ("Observed conversations per active day", "higher"),
    "orders_created": ("Orders created", "higher"),
    "delivered_orders": ("Delivered orders", "higher"),
    "repeat_delivered_orders": ("Repeat delivered orders", "higher"),
    "repeat_conversation_rate": ("Repeat conversation rate", "higher"),
    "repeat_order_rate": ("Repeat delivered-order rate", "higher"),
    "order_creation_rate": ("Order creation rate", "higher"),
    "delivered_rate": ("Delivered-order rate", "higher"),
    "customer_delivered_rate": ("Customer delivered-order rate", "higher"),
    "negative_outcome_rate": ("Negative-outcome rate", "lower"),
    "customer_negative_outcome_rate": ("Customer negative-outcome rate", "lower"),
    "retention_delivery_rate": ("Returning-customer delivery rate", "higher"),
    "unresolved_outcome_rate": ("Unresolved-outcome rate", "lower"),
    "refund_rate": ("Refund rate", "lower"),
    "cost_per_observed_conversation": ("Cost per observed conversation", "lower"),
    "cost_per_delivered_order": ("Cost per delivered order", "lower"),
    "net_revenue": ("Net revenue", "higher"),
    "net_revenue_per_day": ("Net revenue per active day", "higher"),
    "net_roas": ("Net return on ad spend", "higher"),
    "aov": ("Average order value", "higher"),
    "unique_products_ordered": ("Unique products ordered", "higher"),
    "units_ordered": ("Units ordered", "higher"),
    "unique_creatives": ("Unique creatives", "higher"),
    "ad_count": ("Ads tested", "higher"),
    "spend": ("Spend", "higher"),
    "semantic_conversations": ("Semantically assessed conversations", "higher"),
    "high_purchase_intent_rate": ("High purchase-intent rate", "higher"),
    "barrier_conversation_rate": ("Conversation barrier rate", "lower"),
    "agent_helpful_rate": ("Helpful agent-conversation rate", "higher"),
    "semantic_coverage_rate": ("Conversation-signal coverage rate", "higher"),
    "high_urgency_rate": ("High-urgency conversation rate", "higher"),
    "price_sensitive_rate": ("Price-sensitive conversation rate", "lower"),
    "price_blocking_rate": ("Price-blocking conversation rate", "lower"),
    "deal_seeking_rate": ("Deal-seeking conversation rate", "lower"),
    "delivery_ready_rate": ("Delivery-ready conversation rate", "higher"),
    "sales_agreement_rate": ("Sales-agreement conversation rate", "higher"),
    "blocking_barrier_rate": ("Blocking-barrier conversation rate", "lower"),
    "barrier_resolution_rate": ("Barrier-resolution rate", "higher"),
    "competitor_mention_rate": ("Competitor-mention rate", "lower"),
    "next_step_agreement_rate": ("Next-step agreement rate", "higher"),
    "next_step_completion_rate": ("Agreed next-step completion rate", "higher"),
}

RATE_COMPONENTS: dict[str, tuple[str, str]] = {
    "link_ctr": ("link_clicks", "impressions"),
    "order_creation_rate": ("mature_orders_created", "mature_conversations"),
    "delivered_rate": ("delivered_orders", "mature_conversations"),
    "negative_outcome_rate": ("negative_outcomes", "mature_conversations"),
    "customer_delivered_rate": ("delivered_customers", "mature_unique_customers"),
    "customer_negative_outcome_rate": (
        "negative_outcome_customers",
        "mature_unique_customers",
    ),
    "retention_delivery_rate": (
        "returning_delivered_customers",
        "mature_returning_unique_customers",
    ),
    "high_purchase_intent_rate": (
        "high_purchase_intent_conversations",
        "semantic_conversations",
    ),
    "barrier_conversation_rate": ("barrier_conversations", "semantic_conversations"),
    "agent_helpful_rate": ("agent_helpful_conversations", "semantic_conversations"),
    "high_urgency_rate": ("high_urgency_conversations", "semantic_conversations"),
    "price_sensitive_rate": ("price_sensitive_conversations", "semantic_conversations"),
    "price_blocking_rate": ("price_blocking_conversations", "semantic_conversations"),
    "deal_seeking_rate": ("deal_seeking_conversations", "semantic_conversations"),
    "delivery_ready_rate": ("delivery_ready_conversations", "semantic_conversations"),
    "sales_agreement_rate": ("sales_agreement_conversations", "semantic_conversations"),
    "blocking_barrier_rate": ("blocking_barrier_conversations", "semantic_conversations"),
    "barrier_resolution_rate": (
        "resolved_barrier_conversations",
        "assessable_barrier_conversations",
    ),
    "competitor_mention_rate": (
        "competitor_mention_conversations",
        "semantic_conversations",
    ),
    "next_step_agreement_rate": (
        "next_step_agreed_conversations",
        "semantic_conversations",
    ),
    "next_step_completion_rate": (
        "next_step_observed_conversations",
        "next_step_agreed_conversations",
    ),
}

SEMANTIC_METRICS = {
    "high_purchase_intent_rate",
    "barrier_conversation_rate",
    "agent_helpful_rate",
    "high_urgency_rate",
    "price_sensitive_rate",
    "price_blocking_rate",
    "deal_seeking_rate",
    "delivery_ready_rate",
    "sales_agreement_rate",
    "blocking_barrier_rate",
    "barrier_resolution_rate",
    "competitor_mention_rate",
    "next_step_agreement_rate",
    "next_step_completion_rate",
}

OUTCOME_METRICS = {
    "observed_conversations",
    "mature_conversations",
    "mature_unique_customers",
    "observed_conversations_per_day",
    "orders_created",
    "delivered_orders",
    "repeat_delivered_orders",
    "repeat_conversation_rate",
    "repeat_order_rate",
    "order_creation_rate",
    "delivered_rate",
    "customer_delivered_rate",
    "negative_outcome_rate",
    "customer_negative_outcome_rate",
    "retention_delivery_rate",
    "unresolved_outcome_rate",
    "refund_rate",
    "cost_per_observed_conversation",
    "cost_per_delivered_order",
    "net_revenue",
    "net_revenue_per_day",
    "net_roas",
    "aov",
    "unique_products_ordered",
    "units_ordered",
}

MINIMUM_EVIDENCE = {
    "campaign": 10,
    "adset": 5,
    "ad": 3,
    "creative": 3,
    "audience": 5,
}


@dataclass(frozen=True)
class AssessmentBundle:
    assessments: list[CampaignAssessment]
    evidence_packs: list[CampaignEvidencePack]
    scorecards: CycleScorecards


def metric_label(metric: str) -> str:
    return METRIC_METADATA.get(metric, (metric.replace("_", " ").title(), "higher"))[0]


def metric_direction(metric: str) -> Direction:
    return METRIC_METADATA.get(metric, (metric, "higher"))[1]


def _number(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if isfinite(parsed) else None


def _empirical_bayes_score_from_row(row: pd.Series) -> EmpiricalBayesScore | None:
    if "score_metric" not in row.index or pd.isna(row.get("benchmark_score")):
        return None
    return EmpiricalBayesScore(
        metric=str(row["score_metric"]),
        numerator=str(row["score_numerator"]),
        denominator=str(row["score_denominator"]),
        direction=str(row["score_direction"]),
        successes=float(row.get("score_successes", 0) or 0),
        trials=float(row.get("score_trials", 0) or 0),
        raw_score=_number(row.get("raw_score")),
        corrected_score=_number(row.get("corrected_score")),
        corrected_score_low=_number(row.get("corrected_score_low")),
        corrected_score_high=_number(row.get("corrected_score_high")),
        benchmark_score=_number(row.get("benchmark_score")),
        benchmark_low=_number(row.get("benchmark_low")),
        benchmark_high=_number(row.get("benchmark_high")),
        benchmark_source=str(row.get("benchmark_source")),
        benchmark_peer_count=int(row.get("benchmark_peer_count", 0) or 0),
        prior_alpha=_number(row.get("prior_alpha")),
        prior_beta=_number(row.get("prior_beta")),
        prior_strength=_number(row.get("prior_strength")),
        expected_lift=_number(row.get("expected_lift")),
        lift_low=_number(row.get("lift_low")),
        lift_high=_number(row.get("lift_high")),
        probability_better=_number(row.get("probability_better")),
        practical_lift_threshold=float(row.get("practical_lift_threshold", 0) or 0),
        decision=FundingDecision(str(row.get("statistical_decision", "hold"))),
        interval_method=(
            str(row.get("score_interval_method"))
            if pd.notna(row.get("score_interval_method"))
            else None
        ),
    )


def _compare(
    actual: float | None,
    benchmark: float | None,
    direction: Direction,
    maximum: float | None = None,
) -> bool | None:
    if actual is None or benchmark is None:
        return None
    if direction == "higher":
        return actual >= benchmark
    if direction == "lower":
        return actual <= benchmark
    if maximum is None:
        return None
    return benchmark <= actual <= maximum


def _wilson_interval(
    successes: float, trials: float, comparisons: int
) -> tuple[float | None, float | None]:
    if trials <= 0:
        return None, None
    adjusted_alpha = 0.05 / max(comparisons, 1)
    z = NormalDist().inv_cdf(1 - adjusted_alpha / 2)
    proportion = successes / trials
    z2 = z * z
    denominator = 1 + z2 / trials
    centre = (proportion + z2 / (2 * trials)) / denominator
    margin = (
        z
        * sqrt(proportion * (1 - proportion) / trials + z2 / (4 * trials * trials))
        / denominator
    )
    return max(0.0, centre - margin), min(1.0, centre + margin)


def _metric_interval(
    frame: pd.DataFrame, row: pd.Series, metric: str
) -> tuple[float | None, float | None, str | None]:
    components = RATE_COMPONENTS.get(metric)
    if components is None:
        return None, None, None
    successes = _number(row.get(components[0]))
    trials = _number(row.get(components[1]))
    if successes is None or trials is None:
        return None, None, None
    low, high = _wilson_interval(successes, trials, len(frame))
    method = f"95% family-wise Wilson interval across {max(len(frame), 1)} comparisons"
    return low, high, method


def _compare_interval(
    actual: float | None,
    benchmark: float | None,
    direction: Direction,
    low: float | None,
    high: float | None,
    maximum: float | None = None,
) -> bool | None:
    if low is None or high is None:
        return _compare(actual, benchmark, direction, maximum)
    if benchmark is None:
        return None
    if direction == "higher":
        if low >= benchmark:
            return True
        if high < benchmark:
            return False
        return None
    if direction == "lower":
        if high <= benchmark:
            return True
        if low > benchmark:
            return False
        return None
    if maximum is None:
        return None
    if low >= benchmark and high <= maximum:
        return True
    if high < benchmark or low > maximum:
        return False
    return None


def _valid_values(frame: pd.DataFrame, metric: str) -> pd.Series:
    if metric not in frame:
        return pd.Series(dtype=float)
    return (
        pd.to_numeric(frame[metric], errors="coerce")
        .replace([float("inf"), float("-inf")], pd.NA)
        .dropna()
    )


def resolve_benchmark(
    frame: pd.DataFrame,
    row: pd.Series,
    metric: str,
    strategy: str | None = None,
) -> tuple[float | None, str | None]:
    """Resolve a reviewable POC benchmark, excluding the current entity."""

    peers = frame[frame["entity_id"].ne(row["entity_id"])]
    if metric in OUTCOME_METRICS and "mature_conversations" in peers:
        peers = peers[peers["mature_conversations"].ge(10)]
    if strategy in {None, "same_type_median", "historical_same_type"}:
        same_type = peers[peers["campaign_type"].eq(row["campaign_type"])]
        values = _valid_values(same_type, metric)
        if not values.empty:
            prefix = (
                "current-cycle same-type median (historical fallback)"
                if strategy == "historical_same_type"
                else "current-cycle same-type median"
            )
            return float(values.median()), prefix
    values = _valid_values(peers, metric)
    if not values.empty:
        return float(values.median()), "current-cycle portfolio median"
    return None, None


def _metric_evidence(
    frame: pd.DataFrame,
    row: pd.Series,
    metric: str,
    *,
    strategy: str | None = None,
    direction: Direction | None = None,
) -> MetricEvidence:
    actual = _number(row.get(metric))
    if metric in {"reach", "frequency"} and int(
        row.get("invalid_reach_rows", 0) or 0
    ):
        actual = None
    resolved_direction = direction or metric_direction(metric)
    benchmark, source = resolve_benchmark(frame, row, metric, strategy)
    low, high, interval_method = _metric_interval(frame, row, metric)
    passed = _compare(actual, benchmark, resolved_direction)
    interval_comparison = _compare_interval(
        actual, benchmark, resolved_direction, low, high
    )
    if metric in {"customer_delivered_rate", "customer_negative_outcome_rate"}:
        evidence_count_field = "mature_unique_customers"
    elif metric in OUTCOME_METRICS:
        evidence_count_field = "mature_conversations"
    elif metric in SEMANTIC_METRICS:
        evidence_count_field = "semantic_conversations"
    else:
        evidence_count_field = "observed_conversations"
    return MetricEvidence(
        metric=metric,
        label=metric_label(metric),
        actual=actual,
        benchmark=benchmark,
        benchmark_source=source,
        direction=resolved_direction,
        passed=passed,
        evidence_count=int(row.get(evidence_count_field, 0) or 0),
        confidence_interval_low=low,
        confidence_interval_high=high,
        interval_method=interval_method,
        comparison_conclusive=(
            interval_comparison is not None
            if interval_method is not None
            else passed is not None
        ),
    )


def _guardrail_evidence(
    frame: pd.DataFrame, row: pd.Series, guardrail: GuardrailConfig
) -> MetricEvidence:
    actual = _number(row.get(guardrail.metric))
    benchmark: float | None = None
    maximum: float | None = None
    source: str | None = None
    direction: Direction = metric_direction(guardrail.metric)

    if guardrail.operator == "greater_than":
        benchmark = guardrail.value
        direction = "higher"
        passed = actual is not None and benchmark is not None and actual > benchmark
        source = "configured threshold"
    elif guardrail.operator == "greater_than_or_equal":
        benchmark = guardrail.value
        direction = "higher"
        passed = _compare(actual, benchmark, direction)
        source = "configured threshold"
    elif guardrail.operator == "less_than_or_equal":
        benchmark = guardrail.value
        direction = "lower"
        passed = _compare(actual, benchmark, direction)
        source = "configured threshold"
    elif guardrail.operator == "within":
        benchmark = guardrail.minimum
        maximum = guardrail.maximum
        direction = "range"
        passed = _compare(actual, benchmark, direction, maximum)
        source = (
            f"configured range to {maximum:g}" if maximum is not None else "configured range"
        )
    else:
        benchmark, source = resolve_benchmark(
            frame, row, guardrail.metric, guardrail.benchmark_strategy
        )
        low, high, interval_method = _metric_interval(
            frame, row, guardrail.metric
        )
        passed = _compare(actual, benchmark, direction)

    if guardrail.operator != "benchmark":
        low, high, interval_method = _metric_interval(frame, row, guardrail.metric)
    interval_comparison = _compare_interval(
        actual, benchmark, direction, low, high, maximum
    )
    if guardrail.metric in {
        "customer_delivered_rate",
        "customer_negative_outcome_rate",
    }:
        evidence_count_field = "mature_unique_customers"
    elif guardrail.metric in OUTCOME_METRICS:
        evidence_count_field = "mature_conversations"
    else:
        evidence_count_field = "observed_conversations"

    return MetricEvidence(
        metric=guardrail.metric,
        label=metric_label(guardrail.metric),
        actual=actual,
        benchmark=benchmark,
        benchmark_source=source,
        direction=direction,
        passed=passed,
        evidence_count=int(row.get(evidence_count_field, 0) or 0),
        confidence_interval_low=low,
        confidence_interval_high=high,
        interval_method=interval_method,
        comparison_conclusive=(
            interval_comparison is not None
            if interval_method is not None
            else passed is not None
        ),
    )


def _campaign_evidence_status(
    row: pd.Series, config: CampaignTypeConfig, quality: DataQualityReport
) -> EvidenceStatus:
    if quality.status is EvidenceStatus.DATA_NOT_READY:
        return EvidenceStatus.DATA_NOT_READY
    required_metrics = {
        *config.primary_kpis,
        config.allocation_metric.metric,
        *(guardrail.metric for guardrail in config.guardrails),
    }
    if required_metrics.intersection({"reach", "frequency"}) and (
        quality.daily_reach_is_non_additive
        or int(row.get("invalid_reach_rows", 0) or 0) > 0
    ):
        return EvidenceStatus.DATA_NOT_READY
    requires_outcomes = bool(required_metrics.intersection(OUTCOME_METRICS))
    if requires_outcomes and int(row.get("mature_conversations", 0) or 0) < 10:
        return EvidenceStatus.INSUFFICIENT
    return quality.status


def _entity_evidence(
    frame: pd.DataFrame, row: pd.Series, level: EntityLevel
) -> EntityEvidence:
    metrics = [
        "spend",
        "link_ctr_pct",
        "observed_conversations",
        "mature_conversations",
        "mature_unique_customers",
        "delivered_orders",
        "customer_delivered_rate",
        "unresolved_outcome_rate",
        "net_revenue",
        "net_roas",
        "cost_per_delivered_order",
        "negative_outcome_rate",
        "semantic_conversations",
        "high_purchase_intent_rate",
        "barrier_conversation_rate",
        "agent_helpful_rate",
        "semantic_coverage_rate",
        "high_urgency_rate",
        "price_sensitive_rate",
        "price_blocking_rate",
        "deal_seeking_rate",
        "delivery_ready_rate",
        "sales_agreement_rate",
        "blocking_barrier_rate",
        "barrier_resolution_rate",
        "competitor_mention_rate",
        "next_step_agreement_rate",
        "next_step_completion_rate",
    ]
    evidence = [
        _metric_evidence(frame, row, metric)
        for metric in metrics
        if metric in row.index
    ]
    dimensions = {
        key: row.get(key)
        for key in (
            "campaign_id",
            "adset_id",
            "creative_id",
            "audience_type",
            "theme",
            "angle",
            "top_conversation_purpose",
            "top_barrier",
            "top_mentioned_product",
            "top_value_driver",
            "top_stated_exit_reason",
        )
        if key in row.index and pd.notna(row.get(key))
    }
    return EntityEvidence(
        entity_level=level,
        entity_id=str(row["entity_id"]),
        entity_name=str(row["entity_name"]),
        metrics=evidence,
        dimensions=dimensions,
        decision_score=_empirical_bayes_score_from_row(row),
    )


def _assessment_reason(metric: MetricEvidence) -> str:
    if metric.actual is None:
        return "The metric is unavailable or failed a data-quality rule."
    if metric.benchmark is None:
        return "No compatible benchmark was available."
    if metric.passed is None:
        if (
            metric.confidence_interval_low is not None
            and metric.confidence_interval_high is not None
        ):
            return (
                f"Actual {metric.actual:,.2f}; uncertainty interval "
                f"[{metric.confidence_interval_low:,.2f}, "
                f"{metric.confidence_interval_high:,.2f}] overlaps benchmark "
                f"{metric.benchmark:,.2f}."
            )
        return "The available evidence does not support a conclusive comparison."
    relation = "met" if metric.passed else "did not meet"
    reason = (
        f"Actual {metric.actual:,.2f} {relation} benchmark "
        f"{metric.benchmark:,.2f} ({metric.benchmark_source})."
    )
    if metric.comparison_conclusive is False:
        reason += " The simultaneous uncertainty interval overlaps the benchmark."
    return reason


def _build_campaign_pack(
    cycle_id: str,
    row: pd.Series,
    scorecards: CycleScorecards,
    registry: CampaignTypeRegistry,
    quality: DataQualityReport,
) -> CampaignEvidencePack:
    """Deterministic measurement for one campaign — evidence only, no decision."""
    campaign_type = CampaignType(row["campaign_type"])
    config = registry.campaign_types[campaign_type]
    campaign_frame = scorecards.campaign
    evidence_status = _campaign_evidence_status(row, config, quality)

    primary = [
        _metric_evidence(campaign_frame, row, metric)
        for metric in config.primary_kpis
    ]
    supporting = [
        _metric_evidence(campaign_frame, row, metric)
        for metric in config.supporting_kpis
    ]
    guards = [
        _guardrail_evidence(campaign_frame, row, guardrail)
        for guardrail in config.guardrails
    ]
    allocation = _metric_evidence(
        campaign_frame,
        row,
        config.allocation_metric.metric,
        direction=config.allocation_metric.direction,
    )

    limitations = list(quality.warnings)
    limitations.append(
        "Empirical-Bayes priors are learned from compatible current-cycle peers because no separate historical-cycle store was supplied; they are POC references, not approved business targets."
    )
    limitations.append(
        "The practical lift threshold is zero for the POC and must be replaced by an approved minimum worthwhile business effect."
    )
    semantic_count = int(row.get("semantic_conversations", 0) or 0)
    if semantic_count:
        limitations.append(
            f"Semantic summaries cover {semantic_count} validated LLM classifications and are diagnostic only; they do not determine funding."
        )
    else:
        limitations.append(
            "No validated conversation-signal artifact was supplied; semantic diagnostic fields are unavailable."
        )
    campaign_entity = _entity_evidence(campaign_frame, row, EntityLevel.CAMPAIGN)
    child_frames = {
        EntityLevel.ADSET: scorecards.adset,
        EntityLevel.AD: scorecards.ad,
        EntityLevel.CREATIVE: scorecards.creative,
        EntityLevel.AUDIENCE: scorecards.audience,
    }
    children: dict[EntityLevel, list[EntityEvidence]] = {}
    for level, frame in child_frames.items():
        subset = frame[frame["campaign_id"].eq(row["campaign_id"])]
        children[level] = [
            _entity_evidence(subset, child, level) for _, child in subset.iterrows()
        ]

    return CampaignEvidencePack(
        cycle_id=cycle_id,
        campaign_id=str(row["campaign_id"]),
        campaign_name=str(row["campaign_name"]),
        campaign_type=campaign_type,
        business_job=config.business_job,
        success_question=config.success_question,
        evidence_status=evidence_status,
        primary_kpis=primary,
        supporting_kpis=supporting,
        guardrails=guards,
        allocation_kpi=allocation,
        campaign=campaign_entity,
        adsets=children[EntityLevel.ADSET],
        ads=children[EntityLevel.AD],
        creatives=children[EntityLevel.CREATIVE],
        audiences=children[EntityLevel.AUDIENCE],
        limitations=limitations,
        decision_score=_empirical_bayes_score_from_row(row),
    )


def build_evidence_packs(
    cycle_id: str,
    scorecards: CycleScorecards,
    registry: CampaignTypeRegistry,
    quality: DataQualityReport,
) -> list[CampaignEvidencePack]:
    """Deterministic evidence for every campaign — the input to a CampaignAssessor."""
    return [
        _build_campaign_pack(cycle_id, row, scorecards, registry, quality)
        for _, row in scorecards.campaign.iterrows()
    ]


def _entity_metric_actual(entity: EntityEvidence, metric: str) -> float | None:
    return next((m.actual for m in entity.metrics if m.metric == metric), None)


class DeterministicCampaignAssessor:
    """Default `CampaignAssessor`: transparent, rule-based funding decisions.

    Reproduces the decision from the evidence pack + campaign-type config alone
    (which is why the pack carries ``allocation_kpi``).
    """

    def assess(
        self, evidence: CampaignEvidencePack, config: CampaignTypeConfig
    ) -> CampaignAssessment:
        target_guards = [
            item
            for item, guardrail in zip(evidence.guardrails, config.guardrails)
            if "target" in guardrail.required_for
        ]
        allocation_guards = [
            item
            for item, guardrail in zip(evidence.guardrails, config.guardrails)
            if "allocation" in guardrail.required_for
        ]
        primary_passed = bool(evidence.primary_kpis) and all(
            item.passed is True for item in evidence.primary_kpis
        )
        allocation_passed = (
            evidence.allocation_kpi is not None
            and evidence.allocation_kpi.passed is True
        )
        delivered = int(_entity_metric_actual(evidence.campaign, "delivered_orders") or 0)
        spend = float(_entity_metric_actual(evidence.campaign, "spend") or 0.0)
        required_evidence = [
            *evidence.primary_kpis,
            *target_guards,
            *allocation_guards,
        ]
        if evidence.allocation_kpi is not None:
            required_evidence.append(evidence.allocation_kpi)
        decision_evidence_status = evidence.evidence_status
        if (
            decision_evidence_status is not EvidenceStatus.DATA_NOT_READY
            and any(item.passed is None for item in required_evidence)
        ):
            decision_evidence_status = EvidenceStatus.INSUFFICIENT

        target_status = classify_target(
            primary_kpis_passed=primary_passed,
            critical_guardrails_passed=all(item.passed is True for item in target_guards),
            evidence_status=decision_evidence_status,
        )
        guards_passed = all(item.passed is True for item in allocation_guards)
        if evidence.decision_score is None:
            action = classify_next_cycle_action(
                allocation_metric_passed=allocation_passed,
                critical_guardrails_passed=guards_passed,
                delivered_orders=delivered,
                spend=spend,
                evidence_status=decision_evidence_status,
            )
        elif decision_evidence_status is EvidenceStatus.DATA_NOT_READY:
            action = NextCycleAction.DATA_NOT_READY
        elif decision_evidence_status is EvidenceStatus.INSUFFICIENT:
            action = NextCycleAction.INSUFFICIENT_EVIDENCE
        elif evidence.decision_score.decision is FundingDecision.KILL:
            action = NextCycleAction.DO_NOT_FUND
        elif evidence.decision_score.decision is FundingDecision.HOLD:
            action = NextCycleAction.KEEP_AS_TEST
        elif guards_passed:
            action = (
                NextCycleAction.SCALE
                if decision_evidence_status is EvidenceStatus.READY
                else NextCycleAction.KEEP_AS_TEST
            )
        else:
            action = NextCycleAction.KEEP_AS_TEST

        reasons: list[str] = []
        if decision_evidence_status is not EvidenceStatus.READY:
            reasons.append(decision_evidence_status.value)
        reasons.extend(
            f"primary:{item.metric}:"
            f"{'pass' if item.passed is True else 'fail' if item.passed is False else 'inconclusive'}"
            for item in evidence.primary_kpis
        )
        if evidence.decision_score is not None:
            reasons.append(
                f"empirical_bayes:{evidence.decision_score.metric}:"
                f"{evidence.decision_score.decision.value}"
            )
        reasons.extend(
            f"guardrail:{item.metric}:fail"
            for item in allocation_guards
            if item.passed is not True
        )
        _mk = lambda item: MetricAssessment(
            metric=item.metric,
            actual=item.actual,
            benchmark=item.benchmark,
            passed=item.passed,
            reason=_assessment_reason(item),
        )
        return CampaignAssessment(
            cycle_id=evidence.cycle_id,
            campaign_id=evidence.campaign_id,
            campaign_name=evidence.campaign_name,
            campaign_type=evidence.campaign_type,
            target_status=target_status,
            next_cycle_action=action,
            evidence_status=decision_evidence_status,
            primary_results=[_mk(item) for item in evidence.primary_kpis],
            guardrail_results=[_mk(item) for item in evidence.guardrails],
            reason_codes=reasons,
        )


def _add_campaign_decisions(
    frame: pd.DataFrame,
    assessments: list[CampaignAssessment],
    registry: CampaignTypeRegistry,
) -> pd.DataFrame:
    result = frame.copy()
    decisions = pd.DataFrame(
        [
            {
                "campaign_id": item.campaign_id,
                "target_status": item.target_status.value,
                "next_cycle_action": item.next_cycle_action.value,
                "evidence_status": item.evidence_status.value,
            }
            for item in assessments
        ]
    )
    result = result.merge(decisions, on="campaign_id", how="left")
    result["primary_kpi"] = result["campaign_type"].map(
        lambda value: registry.campaign_types[CampaignType(value)].primary_kpis[0]
    )
    result["allocation_metric"] = result["campaign_type"].map(
        lambda value: registry.campaign_types[CampaignType(value)].allocation_metric.metric
    )
    result["funding_decision"] = result["statistical_decision"]
    result["decision_score"] = result["corrected_score"]
    return result


def _add_child_decisions(
    frame: pd.DataFrame,
    level: str,
    campaign_assessments: dict[str, CampaignAssessment],
    registry: CampaignTypeRegistry,
    quality: DataQualityReport,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        parent = campaign_assessments[str(row["campaign_id"])]
        config = registry.campaign_types[CampaignType(row["campaign_type"])]
        metric = str(row.get("score_metric") or config.score_metric.metric)
        observations = int(row.get("score_trials", 0) or 0)
        own_decision = FundingDecision(str(row.get("statistical_decision", "hold")))
        lift_low = _number(row.get("lift_low"))
        lift_high = _number(row.get("lift_high"))
        corrected = _number(row.get("corrected_score"))
        benchmark = _number(row.get("benchmark_score"))
        source = row.get("benchmark_source")

        if parent.next_cycle_action in {
            NextCycleAction.DO_NOT_FUND,
            NextCycleAction.DATA_NOT_READY,
        }:
            action = parent.next_cycle_action
            reason = "Parent campaign is blocked; the entity score is retained for learning."
        elif observations <= 0 or benchmark is None:
            action = NextCycleAction.INSUFFICIENT_EVIDENCE
            reason = str(
                row.get("score_error")
                or "No eligible observations were available for the corrected score."
            )
        elif own_decision is FundingDecision.KILL:
            action = NextCycleAction.DO_NOT_FUND
            reason = (
                f"The full 95% favorable-lift range [{lift_low:.1%}, {lift_high:.1%}] "
                "is below the POC threshold."
            )
        elif own_decision is FundingDecision.SCALE:
            action = (
                NextCycleAction.SCALE
                if quality.status is EvidenceStatus.READY
                else NextCycleAction.KEEP_AS_TEST
            )
            reason = (
                f"The full 95% favorable-lift range [{lift_low:.1%}, {lift_high:.1%}] "
                "is above the POC threshold."
            )
        else:
            action = NextCycleAction.KEEP_AS_TEST
            reason = (
                f"The 95% favorable-lift range [{lift_low:.1%}, {lift_high:.1%}] "
                "crosses zero; retain only as a named test."
            )
        rows.append(
            {
                "entity_id": row["entity_id"],
                "next_cycle_action": action.value,
                "evidence_status": (
                    EvidenceStatus.INSUFFICIENT.value
                    if observations <= 0 or benchmark is None
                    else quality.status.value
                ),
                "allocation_metric": config.allocation_metric.metric,
                "allocation_metric_value": _number(
                    row.get(config.allocation_metric.metric)
                ),
                "allocation_benchmark": benchmark,
                "allocation_benchmark_source": source,
                "allocation_metric_passed": (
                    True
                    if own_decision is FundingDecision.SCALE
                    else False
                    if own_decision is FundingDecision.KILL
                    else None
                ),
                "allocation_confidence_interval_low": _number(
                    row.get("corrected_score_low")
                ),
                "allocation_confidence_interval_high": _number(
                    row.get("corrected_score_high")
                ),
                "funding_decision": own_decision.value,
                "decision_score": corrected,
                "decision_reason": reason,
            }
        )
    return frame.merge(pd.DataFrame(rows), on="entity_id", how="left")


def enrich_scorecards(
    scorecards: CycleScorecards,
    assessments: list[CampaignAssessment],
    registry: CampaignTypeRegistry,
    quality: DataQualityReport,
) -> CycleScorecards:
    """Attach campaign and child decisions (incl. parent→child propagation) onto the scorecards."""
    assessment_lookup = {item.campaign_id: item for item in assessments}
    return CycleScorecards(
        campaign=_add_campaign_decisions(scorecards.campaign, assessments, registry),
        adset=_add_child_decisions(
            scorecards.adset, "adset", assessment_lookup, registry, quality
        ),
        ad=_add_child_decisions(
            scorecards.ad, "ad", assessment_lookup, registry, quality
        ),
        creative=_add_child_decisions(
            scorecards.creative, "creative", assessment_lookup, registry, quality
        ),
        audience=_add_child_decisions(
            scorecards.audience, "audience", assessment_lookup, registry, quality
        ),
    )


def build_assessment_bundle(
    cycle_id: str,
    scorecards: CycleScorecards,
    registry: CampaignTypeRegistry,
    quality: DataQualityReport,
) -> AssessmentBundle:
    """Evidence + deterministic decisions (the default assessor path)."""
    packs = build_evidence_packs(cycle_id, scorecards, registry, quality)
    assessor = DeterministicCampaignAssessor()
    assessments = [
        assessor.assess(pack, registry.campaign_types[pack.campaign_type])
        for pack in packs
    ]
    enriched = enrich_scorecards(scorecards, assessments, registry, quality)
    return AssessmentBundle(
        assessments=assessments, evidence_packs=packs, scorecards=enriched
    )
