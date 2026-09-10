"""Convert scored tables into the compact recommendation input contract."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from .config import BudgetPolicy, ObjectiveRegistry
from .contracts import (
    BenchmarkQuality,
    BenchmarkScope,
    BudgetAllocation,
    BusinessOutcomes,
    CampaignPackage,
    ChildEfficiency,
    ChildEntityScore,
    ChildEvidence,
    ChildPrimaryScore,
    ConversationDiagnostics,
    CycleSummary,
    DataScope,
    DecisionPolicy,
    DeliverySummary,
    EfficiencyComparison,
    EfficiencyEvidence,
    EntityLevel,
    EntityScore,
    EvidenceStatus,
    EvidenceSummary,
    ExplorationTest,
    NextCycleAction,
    PrimaryScore,
    RecommendationInput,
    StatisticalDecision,
    SemanticScore,
)
from .data import CanonicalData


def _optional_float(value: Any) -> Optional[float]:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return None if pd.isna(numeric) else float(numeric)


def _integer(value: Any) -> int:
    numeric = _optional_float(value)
    return int(numeric or 0)


def _optional_text(value: Any) -> Optional[str]:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _iso_date(value: Any) -> Optional[str]:
    timestamp = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(timestamp) else timestamp.date().isoformat()


def _attributes(row: pd.Series) -> Dict[str, Any]:
    names = (
        "adset_id",
        "adset_name",
        "ad_id",
        "creative_id",
        "creative_name",
        "audience_type",
        "theme",
        "angle",
    )
    return {
        name: value
        for name in names
        if name in row and (value := _optional_text(row.get(name))) is not None
    }


def entity_from_row(row: pd.Series) -> EntityScore:
    return EntityScore(
        entity_level=EntityLevel(str(row["entity_level"])),
        entity_id=str(row["entity_id"]),
        entity_name=str(row["entity_name"]),
        campaign_id=str(row["campaign_id"]),
        parent_entity_id=_optional_text(row.get("parent_entity_id")),
        objective=str(row["objective"]),
        attributes=_attributes(row),
        semantic_score=SemanticScore.model_validate(row["semantic_score"]),
        delivery=DeliverySummary(
            status=_optional_text(row.get("entity_status")),
            start_date=_iso_date(row.get("media_start")),
            end_date=_iso_date(row.get("media_end")),
            running_days=_integer(row.get("running_days")),
            active_days=_integer(row.get("active_days")),
            impressions=float(_optional_float(row.get("impressions")) or 0),
            link_clicks=float(_optional_float(row.get("link_clicks")) or 0),
        ),
        evidence=EvidenceSummary(
            successes=float(_optional_float(row.get("score_successes")) or 0),
            trials=float(_optional_float(row.get("score_trials")) or 0),
            observed_conversations=_integer(row.get("observed_conversations")),
            mature_conversations=_integer(row.get("mature_conversations")),
            unresolved_conversations=_integer(row.get("unresolved_conversations")),
            unique_customers=_integer(row.get("unique_customers")),
            mature_unique_customers=_integer(row.get("mature_unique_customers")),
            evidence_status=EvidenceStatus(str(row["evidence_status"])),
        ),
        primary_score=PrimaryScore(
            metric=str(row["score_metric"]),
            numerator=str(row["score_numerator"]),
            denominator=str(row["score_denominator"]),
            direction=str(row["score_direction"]),
            raw_rate=_optional_float(row.get("raw_rate")),
            corrected_rate=_optional_float(row.get("corrected_rate")),
            range_low=_optional_float(row.get("range_low")),
            range_high=_optional_float(row.get("range_high")),
            benchmark=_optional_float(row.get("benchmark")),
            benchmark_peer_count=_integer(row.get("benchmark_peer_count")),
            same_objective_peer_count=_integer(
                row.get("same_objective_peer_count")
            ),
            benchmark_scope=BenchmarkScope(str(row["benchmark_scope"])),
            benchmark_quality=BenchmarkQuality(str(row["benchmark_quality"])),
            portfolio_context_benchmark=_optional_float(
                row.get("portfolio_context_benchmark")
            ),
            portfolio_context_peer_count=_integer(
                row.get("portfolio_context_peer_count")
            ),
            expected_lift=_optional_float(row.get("expected_lift")),
            lift_low=_optional_float(row.get("lift_low")),
            lift_high=_optional_float(row.get("lift_high")),
            probability_better=_optional_float(row.get("probability_better")),
            statistical_decision=StatisticalDecision(
                str(row["statistical_decision"])
            ),
        ),
        efficiency=EfficiencyEvidence(
            metric=str(row["efficiency_metric"]),
            direction=str(row["efficiency_direction"]),
            value=_optional_float(row.get("efficiency_value")),
            benchmark=_optional_float(row.get("efficiency_benchmark")),
            benchmark_peer_count=_integer(row.get("efficiency_peer_count")),
            comparison=EfficiencyComparison(str(row["efficiency_comparison"])),
        ),
        business_outcomes=BusinessOutcomes(
            spend=float(_optional_float(row.get("spend")) or 0),
            created_orders=_integer(row.get("mature_orders_created")),
            delivered_orders=_integer(row.get("delivered_orders")),
            net_revenue=float(_optional_float(row.get("net_revenue")) or 0),
        ),
        diagnostics=ConversationDiagnostics(
            semantic_conversations=_integer(row.get("semantic_conversations")),
            semantic_coverage_rate=_optional_float(row.get("semantic_coverage_rate")),
            high_purchase_intent_rate=_optional_float(
                row.get("high_purchase_intent_rate")
            ),
            price_blocking_rate=_optional_float(row.get("price_blocking_rate")),
            barrier_resolution_rate=_optional_float(
                row.get("barrier_resolution_rate")
            ),
            ad_alignment_rate=_optional_float(row.get("ad_alignment_rate")),
            agent_helpful_rate=_optional_float(row.get("agent_helpful_rate")),
            next_step_agreement_rate=_optional_float(
                row.get("next_step_agreement_rate")
            ),
            next_step_order_progression_rate=_optional_float(
                row.get("next_step_order_progression_rate")
            ),
            top_customer_need=_optional_text(row.get("top_customer_need")),
            top_barrier=_optional_text(row.get("top_barrier")),
            top_value_driver=_optional_text(row.get("top_value_driver")),
        ),
        recommended_action=NextCycleAction(str(row["recommended_action"])),
        reason_codes=list(row["reason_codes"]),
    )


def child_from_entity(entity: EntityScore) -> ChildEntityScore:
    return ChildEntityScore(
        entity_level=entity.entity_level,
        entity_id=entity.entity_id,
        entity_name=entity.entity_name,
        parent_entity_id=entity.parent_entity_id,
        attributes=entity.attributes,
        evidence=ChildEvidence(
            successes=entity.evidence.successes,
            trials=entity.evidence.trials,
            evidence_status=entity.evidence.evidence_status,
        ),
        primary_score=ChildPrimaryScore(
            raw_rate=entity.primary_score.raw_rate,
            corrected_rate=entity.primary_score.corrected_rate,
            range_low=entity.primary_score.range_low,
            range_high=entity.primary_score.range_high,
            benchmark=entity.primary_score.benchmark,
            benchmark_peer_count=entity.primary_score.benchmark_peer_count,
            same_objective_peer_count=entity.primary_score.same_objective_peer_count,
            benchmark_scope=entity.primary_score.benchmark_scope,
            benchmark_quality=entity.primary_score.benchmark_quality,
            portfolio_context_benchmark=entity.primary_score.portfolio_context_benchmark,
            portfolio_context_peer_count=entity.primary_score.portfolio_context_peer_count,
            lift_low=entity.primary_score.lift_low,
            lift_high=entity.primary_score.lift_high,
            probability_better=entity.primary_score.probability_better,
            statistical_decision=entity.primary_score.statistical_decision,
        ),
        efficiency=ChildEfficiency(
            value=entity.efficiency.value,
            benchmark=entity.efficiency.benchmark,
            comparison=entity.efficiency.comparison,
        ),
        spend=entity.business_outcomes.spend,
        diagnostics=entity.diagnostics,
        semantic_score=entity.semantic_score,
        recommended_action=entity.recommended_action,
        reason_codes=entity.reason_codes,
    )


def build_recommendation_input(
    data: CanonicalData,
    scored: Dict[str, pd.DataFrame],
    signals: List[Dict[str, Any]],
    registry: ObjectiveRegistry,
    policy: BudgetPolicy,
    allocations: List[BudgetAllocation],
    tests: List[ExplorationTest],
    unallocated: float,
) -> RecommendationInput:
    allocation_by_id = {item.campaign_id: item for item in allocations}
    entity_scores = {
        level: [entity_from_row(row) for _, row in frame.iterrows()]
        for level, frame in scored.items()
    }
    children_by_campaign: Dict[str, List[ChildEntityScore]] = {}
    for level, entities in entity_scores.items():
        if level == "campaign":
            continue
        for entity in entities:
            children_by_campaign.setdefault(entity.campaign_id, []).append(
                child_from_entity(entity)
            )
    campaign_packages = [
        CampaignPackage(
            campaign=campaign,
            allocation=allocation_by_id[campaign.campaign_id],
            child_entities=children_by_campaign.get(campaign.campaign_id, []),
        )
        for campaign in entity_scores["campaign"]
    ]

    prompt_versions = sorted(
        {
            str(record.get("prompt_version"))
            for record in signals
            if record.get("prompt_version")
        }
    )
    ad_prompt_versions = sorted(
        {
            str(record.get("ad_match_prompt_version"))
            for record in signals
            if record.get("ad_match_prompt_version")
        }
    )
    paid_count = int(data.conversations["conversation_id"].nunique())
    semantic_count = len(
        {
            str(record.get("conversation_id"))
            for record in signals
            if str(record.get("conversation_id"))
            in set(data.conversations["conversation_id"].astype(str))
        }
    )
    start = data.cycle_start
    end = data.cycle_end
    cycle_id = (
        f"cycle_{start.date().isoformat()}_{end.date().isoformat()}"
        if start is not None and end is not None
        else "cycle_unknown"
    )
    return RecommendationInput(
        schema_version="recommendation-input-v3",
        generated_at=datetime.now(timezone.utc),
        cycle=CycleSummary(
            cycle_id=cycle_id,
            start_date=start.date().isoformat() if start is not None else None,
            end_date=end.date().isoformat() if end is not None else None,
            currency=policy.currency,
            budget_mode="normalized_units"
            if policy.currency == "units"
            else "currency",
            next_budget_amount=policy.budget_units,
        ),
        decision_policy=DecisionPolicy(
            allocation_mode="score_based",
            objective_envelope_basis="previous_cycle_spend_share",
            campaign_weight="primary_probability_x_semantic_lower_bound",
            missing_component_rule="zero_allocation",
            concentration_cap=policy.concentration_cap,
            scale_rule="SCALE when the 95% favorable-lift lower bound is above zero.",
            kill_rule="KILL when the 95% favorable-lift upper bound is below zero.",
            hold_rule="HOLD when the 95% favorable-lift range crosses zero.",
        ),
        data_scope=DataScope(
            paid_attributed_conversations=paid_count,
            semantic_conversations=semantic_count,
            semantic_coverage_rate=(semantic_count / paid_count if paid_count else None),
            outcome_data_assumption="complete_for_cycle",
            financial_metrics_reliability="accepted_for_mvp",
            conversation_prompt_version=", ".join(prompt_versions) or None,
            ad_match_prompt_version=", ".join(ad_prompt_versions) or None,
        ),
        objective_contracts=list(registry.objectives.values()),
        campaigns=campaign_packages,
        exploration_tests=tests,
        unallocated_budget_units=unallocated,
    )
