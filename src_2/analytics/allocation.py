"""Create an illustrative next-cycle budget scenario from deterministic decisions."""

from __future__ import annotations

from math import isfinite

import pandas as pd

from src_2.contracts import BudgetAllocation, BudgetScenario, CampaignAssessment, DataQualityReport
from src_2.domain.assessment_rules import NextCycleAction
from src_2.domain.config import BudgetPolicy, CampaignTypeRegistry
from src_2.domain.models import BudgetPool, CampaignType, EntityLevel, EvidenceStatus


def _allocation_weights(
    rows: pd.DataFrame, metric: str, direction: str
) -> dict[str, float]:
    values = pd.to_numeric(rows[metric], errors="coerce")
    valid = values.map(lambda value: isfinite(value) and value > 0 if pd.notna(value) else False)
    eligible = rows[valid].copy()
    if eligible.empty:
        return {}
    numeric = pd.to_numeric(eligible[metric], errors="coerce").astype(float)
    raw = numeric if direction == "higher" else 1.0 / numeric
    total = float(raw.sum())
    if total <= 0:
        return {}
    return dict(zip(eligible["campaign_id"], raw / total))


def build_budget_scenario(
    cycle_id: str,
    campaign_scorecard: pd.DataFrame,
    assessments: list[CampaignAssessment],
    registry: CampaignTypeRegistry,
    policy: BudgetPolicy,
    quality: DataQualityReport,
) -> BudgetScenario:
    """Allocate historical type envelopes using one allocation KPI within each type."""

    assessment_by_id = {item.campaign_id: item for item in assessments}
    spend_by_type = campaign_scorecard.groupby("campaign_type")["spend"].sum()
    total_spend = float(spend_by_type.sum())
    type_shares = (
        spend_by_type / total_spend if total_spend > 0 else spend_by_type * 0
    )
    allocations_by_id: dict[str, float] = {}
    reasons: dict[str, str] = {}
    unallocated = 0.0

    for campaign_type_value, type_rows in campaign_scorecard.groupby("campaign_type"):
        campaign_type = CampaignType(campaign_type_value)
        config = registry.campaign_types[campaign_type]
        pool = config.budget_pool
        pool_key = pool.value
        allowed_actions = set(policy.action_eligibility.get(pool_key, []))
        envelope = policy.budget_units * float(type_shares.get(campaign_type_value, 0))
        eligible_ids = [
            campaign_id
            for campaign_id in type_rows["campaign_id"]
            if assessment_by_id[str(campaign_id)].next_cycle_action.value
            in allowed_actions
        ]
        eligible = type_rows[type_rows["campaign_id"].isin(eligible_ids)]
        metric = config.allocation_metric.metric
        weights = _allocation_weights(
            eligible, metric, config.allocation_metric.direction
        )
        allocated_in_type = 0.0
        for campaign_id, weight in weights.items():
            units = envelope * weight
            allocations_by_id[str(campaign_id)] = units
            allocated_in_type += units
            reasons[str(campaign_id)] = (
                f"Receives {weight:.1%} of the {campaign_type.value} envelope using "
                f"{metric.replace('_', ' ')} ({config.allocation_metric.direction} is better)."
            )
        unallocated += max(envelope - allocated_in_type, 0.0)

    allocations: list[BudgetAllocation] = []
    for _, row in campaign_scorecard.iterrows():
        campaign_id = str(row["campaign_id"])
        assessment = assessment_by_id[campaign_id]
        units = float(allocations_by_id.get(campaign_id, 0.0))
        reason = reasons.get(
            campaign_id,
            f"No units assigned because the deterministic action is {assessment.next_cycle_action.value}.",
        )
        allocations.append(
            BudgetAllocation(
                entity_level=EntityLevel.CAMPAIGN,
                entity_id=campaign_id,
                entity_name=str(row["campaign_name"]),
                action=assessment.next_cycle_action,
                budget_units=units,
                budget_share_pct=units / policy.budget_units * 100,
                reason=reason,
            )
        )

    operational = (
        quality.status is EvidenceStatus.READY
        and quality.event_definitions_reconciled
    )
    experimental_share = float(type_shares.get(CampaignType.EXPERIMENTAL.value, 0))
    assumptions = [
        "The scenario uses 100 normalized units, not an approved currency budget.",
        "Campaign-type envelopes follow the previous cycle's observed spend share.",
        f"The experimental test envelope is {experimental_share:.2%}, derived from experimental campaign spend.",
        "Each campaign type uses one configured allocation KPI; no weighted composite score is used.",
        "There is no maximum campaign concentration cap in this POC.",
        "Funds blocked by deterministic eligibility rules remain unallocated.",
    ]
    if not operational:
        assumptions.append(
            "Because Meta and WhatsApp event populations are not reconciled, this is an illustrative scenario and must not be executed automatically."
        )
    return BudgetScenario(
        cycle_id=cycle_id,
        scenario_name="POC normalized next-cycle allocation",
        total_budget_units=policy.budget_units,
        evidence_status=quality.status,
        operational=operational,
        assumptions=assumptions,
        allocations=allocations,
        unallocated_units=unallocated,
    )


class DeterministicBudgetAllocator:
    """Default `BudgetAllocator`: historical-envelope allocation with one KPI per type."""

    def allocate(
        self,
        cycle_id: str,
        campaign_scorecard: pd.DataFrame,
        assessments: list[CampaignAssessment],
        registry: CampaignTypeRegistry,
        policy: BudgetPolicy,
        quality: DataQualityReport,
    ) -> BudgetScenario:
        return build_budget_scenario(
            cycle_id, campaign_scorecard, assessments, registry, policy, quality
        )
