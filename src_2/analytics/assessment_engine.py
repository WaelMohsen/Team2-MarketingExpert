"""Benchmark evidence and assign transparent target and funding decisions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite
from typing import Any, Literal

import pandas as pd

from src_2.contracts import (
    CampaignAssessment,
    CampaignEvidencePack,
    DataQualityReport,
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
from src_2.domain.models import CampaignType, EntityLevel, EvidenceStatus

from .aggregations import CycleScorecards

Direction = Literal["higher", "lower", "range"]

METRIC_METADATA: dict[str, tuple[str, Direction]] = {
    "reach": ("Reach", "higher"),
    "impressions": ("Impressions", "higher"),
    "frequency": ("Frequency", "range"),
    "link_ctr_pct": ("Link click-through rate", "higher"),
    "cpm": ("Cost per 1,000 impressions", "lower"),
    "cpc": ("Cost per link click", "lower"),
    "meta_conversation_starts": ("Meta-attributed conversation starts", "higher"),
    "observed_conversations": ("Observed WhatsApp conversations", "higher"),
    "observed_conversations_per_day": ("Observed conversations per active day", "higher"),
    "orders_created": ("Orders created", "higher"),
    "delivered_orders": ("Delivered orders", "higher"),
    "repeat_delivered_orders": ("Repeat delivered orders", "higher"),
    "repeat_conversation_rate": ("Repeat conversation rate", "higher"),
    "repeat_order_rate": ("Repeat delivered-order rate", "higher"),
    "order_creation_rate": ("Order creation rate", "higher"),
    "delivered_rate": ("Delivered-order rate", "higher"),
    "negative_outcome_rate": ("Negative-outcome rate", "lower"),
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
}

OUTCOME_METRICS = {
    "observed_conversations",
    "observed_conversations_per_day",
    "orders_created",
    "delivered_orders",
    "repeat_delivered_orders",
    "repeat_conversation_rate",
    "repeat_order_rate",
    "order_creation_rate",
    "delivered_rate",
    "negative_outcome_rate",
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
    resolved_direction = direction or metric_direction(metric)
    benchmark, source = resolve_benchmark(frame, row, metric, strategy)
    return MetricEvidence(
        metric=metric,
        label=metric_label(metric),
        actual=actual,
        benchmark=benchmark,
        benchmark_source=source,
        direction=resolved_direction,
        passed=_compare(actual, benchmark, resolved_direction),
        evidence_count=int(row.get("observed_conversations", 0) or 0),
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
        passed = _compare(actual, benchmark, direction)

    return MetricEvidence(
        metric=guardrail.metric,
        label=metric_label(guardrail.metric),
        actual=actual,
        benchmark=benchmark,
        benchmark_source=source,
        direction=direction,
        passed=passed,
        evidence_count=int(row.get("observed_conversations", 0) or 0),
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
    requires_outcomes = bool(required_metrics.intersection(OUTCOME_METRICS))
    if requires_outcomes and int(row.get("observed_conversations", 0) or 0) < 10:
        return EvidenceStatus.INSUFFICIENT
    return quality.status


def _entity_evidence(
    frame: pd.DataFrame, row: pd.Series, level: EntityLevel
) -> EntityEvidence:
    metrics = [
        "spend",
        "link_ctr_pct",
        "observed_conversations",
        "delivered_orders",
        "net_revenue",
        "net_roas",
        "cost_per_delivered_order",
        "negative_outcome_rate",
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
        )
        if key in row.index and pd.notna(row.get(key))
    }
    return EntityEvidence(
        entity_level=level,
        entity_id=str(row["entity_id"]),
        entity_name=str(row["entity_name"]),
        metrics=evidence,
        dimensions=dimensions,
    )


def _assessment_reason(metric: MetricEvidence) -> str:
    if metric.benchmark is None:
        return "No compatible benchmark was available."
    relation = "met" if metric.passed else "did not meet"
    return (
        f"Actual {metric.actual:,.2f} {relation} benchmark "
        f"{metric.benchmark:,.2f} ({metric.benchmark_source})."
    )


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
        "Benchmarks are current-cycle peer medians unless an explicit target is configured; they are POC references, not approved business targets."
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

        target_status = classify_target(
            primary_kpis_passed=primary_passed,
            critical_guardrails_passed=all(item.passed is True for item in target_guards),
            evidence_status=evidence.evidence_status,
        )
        action = classify_next_cycle_action(
            allocation_metric_passed=allocation_passed,
            critical_guardrails_passed=all(item.passed is True for item in allocation_guards),
            delivered_orders=delivered,
            spend=spend,
            evidence_status=evidence.evidence_status,
        )

        reasons: list[str] = []
        if evidence.evidence_status is not EvidenceStatus.READY:
            reasons.append(evidence.evidence_status.value)
        reasons.extend(
            f"primary:{item.metric}:{'pass' if item.passed else 'fail'}"
            for item in evidence.primary_kpis
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
            evidence_status=evidence.evidence_status,
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
        metric = config.allocation_metric.metric
        direction = config.allocation_metric.direction
        peers = frame[frame["campaign_id"].eq(row["campaign_id"])]
        benchmark, source = resolve_benchmark(peers, row, metric, "portfolio_median")
        actual = _number(row.get(metric))
        passed = _compare(actual, benchmark, direction)
        observations = int(row.get("observed_conversations", 0) or 0)

        if parent.next_cycle_action in {
            NextCycleAction.DO_NOT_FUND,
            NextCycleAction.DATA_NOT_READY,
        }:
            action = parent.next_cycle_action
            reason = "Parent campaign is blocked."
        elif observations < MINIMUM_EVIDENCE[level]:
            action = NextCycleAction.INSUFFICIENT_EVIDENCE
            reason = f"Only {observations} observed conversations; minimum is {MINIMUM_EVIDENCE[level]}."
        elif float(row.get("spend", 0) or 0) > 0 and int(
            row.get("delivered_orders", 0) or 0
        ) == 0:
            action = NextCycleAction.DO_NOT_FUND
            reason = "Spend was recorded without a delivered order in the observed outcomes."
        elif passed is True:
            action = (
                NextCycleAction.SCALE
                if quality.status is EvidenceStatus.READY
                else NextCycleAction.KEEP_AS_TEST
            )
            reason = f"{metric_label(metric)} met its within-campaign peer benchmark."
        else:
            action = NextCycleAction.DO_NOT_FUND
            reason = f"{metric_label(metric)} did not meet its within-campaign peer benchmark."
        rows.append(
            {
                "entity_id": row["entity_id"],
                "next_cycle_action": action.value,
                "evidence_status": (
                    EvidenceStatus.INSUFFICIENT.value
                    if observations < MINIMUM_EVIDENCE[level]
                    else quality.status.value
                ),
                "allocation_metric": metric,
                "allocation_metric_value": actual,
                "allocation_benchmark": benchmark,
                "allocation_benchmark_source": source,
                "allocation_metric_passed": passed,
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
