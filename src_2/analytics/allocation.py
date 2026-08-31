"""Create an illustrative next-cycle budget scenario from deterministic decisions."""

from __future__ import annotations

import pandas as pd

from src_2.contracts import (
    BudgetAllocation,
    BudgetScenario,
    CampaignAssessment,
    DataQualityReport,
    ExplorationTest,
)
from src_2.domain.assessment_rules import NextCycleAction
from src_2.domain.config import BudgetPolicy, CampaignTypeRegistry
from src_2.domain.models import EntityLevel, EvidenceStatus, FundingDecision


def _weights(rows: pd.DataFrame, column: str, *, equal_fallback: bool = True) -> dict[str, float]:
    if rows.empty:
        return {}
    source = rows[column] if column in rows else pd.Series(0.0, index=rows.index)
    values = pd.to_numeric(source, errors="coerce").fillna(0).clip(lower=0)
    total = float(values.sum())
    if total <= 0:
        if not equal_fallback:
            return {}
        values = pd.Series(1.0, index=rows.index)
        total = float(len(rows))
    return dict(zip(rows["campaign_id"].astype(str), values / total))


def build_budget_scenario(
    cycle_id: str,
    campaign_scorecard: pd.DataFrame,
    assessments: list[CampaignAssessment],
    registry: CampaignTypeRegistry,
    policy: BudgetPolicy,
    quality: DataQualityReport,
) -> BudgetScenario:
    """Allocate 70/30 exploit/explore envelopes without mixing entity levels."""

    assessment_by_id = {item.campaign_id: item for item in assessments}
    spend_by_type = campaign_scorecard.groupby("campaign_type")["spend"].sum()
    total_spend = float(spend_by_type.sum())
    type_shares = (
        spend_by_type / total_spend if total_spend > 0 else spend_by_type * 0
    )
    allocations_by_id = {str(value): 0.0 for value in campaign_scorecard["campaign_id"]}
    reasons: dict[str, list[str]] = {key: [] for key in allocations_by_id}
    unallocated = 0.0
    working = campaign_scorecard.copy()
    if "statistical_decision" not in working:
        action_map = {
            "scale": FundingDecision.SCALE.value,
            "do_not_fund": FundingDecision.KILL.value,
        }
        working["statistical_decision"] = working["campaign_id"].map(
            lambda value: action_map.get(
                assessment_by_id[str(value)].next_cycle_action.value,
                FundingDecision.HOLD.value,
            )
        )

    pools = (
        (
            "exploit",
            policy.budget_units * policy.exploit_share,
            FundingDecision.SCALE.value,
            "probability_better",
        ),
        (
            "explore",
            policy.budget_units * policy.explore_share,
            FundingDecision.HOLD.value,
            "spend",
        ),
    )
    for pool_name, pool_units, decision, weight_column in pools:
        eligible = working[working["statistical_decision"].eq(decision)].copy()
        eligible = eligible[
            eligible["campaign_id"].map(
                lambda value: assessment_by_id[str(value)].next_cycle_action
                not in {NextCycleAction.DATA_NOT_READY, NextCycleAction.DO_NOT_FUND}
            )
        ]
        if pool_name == "exploit" and not eligible.empty:
            eligible["_pool_weight"] = 0.0
            for campaign_type_value, type_rows in eligible.groupby("campaign_type"):
                within_type = _weights(type_rows, weight_column)
                type_share = float(type_shares.get(campaign_type_value, 0))
                for campaign_id, weight in within_type.items():
                    eligible.loc[
                        eligible["campaign_id"].astype(str).eq(campaign_id),
                        "_pool_weight",
                    ] = type_share * weight
            weights = _weights(eligible, "_pool_weight")
        else:
            weights = _weights(eligible, weight_column)
        if not weights:
            unallocated += pool_units
            continue
        for campaign_id, weight in weights.items():
            units = pool_units * weight
            allocations_by_id[campaign_id] += units
            if pool_name == "exploit":
                reasons[campaign_id].append(
                    f"Exploit: {weight:.1%} of the exploit pool, preserving eligible campaign-type mix and weighting by probability of beating the peer benchmark."
                )
            else:
                metric = str(
                    eligible.loc[
                        eligible["campaign_id"].astype(str).eq(campaign_id),
                        "score_metric",
                    ].iloc[0]
                )
                reasons[campaign_id].append(
                    f"Explore: named test of whether {metric.replace('_', ' ')} can beat its peer benchmark; scale when the full lift range is positive, kill when fully negative, otherwise stop at the end of the next completed cycle."
                )

    allocations: list[BudgetAllocation] = []
    exploration_tests: list[ExplorationTest] = []
    for _, row in campaign_scorecard.iterrows():
        campaign_id = str(row["campaign_id"])
        assessment = assessment_by_id[campaign_id]
        units = float(allocations_by_id.get(campaign_id, 0.0))
        reason = " ".join(reasons.get(campaign_id, [])) or (
            f"No units assigned because the statistical decision is "
            f"{row.get('statistical_decision', 'unavailable')}."
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
        if units > 0 and row.get("statistical_decision") == FundingDecision.HOLD.value:
            metric = str(row.get("score_metric", "primary KPI"))
            benchmark = pd.to_numeric(
                pd.Series([row.get("benchmark_score")]), errors="coerce"
            ).iloc[0]
            exploration_tests.append(
                ExplorationTest(
                    entity_id=campaign_id,
                    entity_name=str(row["campaign_name"]),
                    test_name=(
                        f"Retest {row['campaign_name']}: "
                        f"{metric.replace('_', ' ').title()}"
                    ),
                    hypothesis=(
                        f"The next-cycle {metric.replace('_', ' ')} will be better "
                        "than the compatible peer benchmark."
                    ),
                    primary_metric=metric,
                    assigned_budget_units=units,
                    benchmark_score=float(benchmark) if pd.notna(benchmark) else None,
                    success_rule=(
                        "SCALE only when the 95% favorable-lift lower bound is above zero."
                    ),
                    failure_rule=(
                        "KILL only when the 95% favorable-lift upper bound is below zero."
                    ),
                    stop_rule=(
                        "Stop data collection when the assigned explore budget is spent "
                        "or the next cycle ends, whichever comes first; wait for the "
                        "outcome maturity window before applying the decision rule."
                    ),
                )
            )

    operational = (
        quality.status is EvidenceStatus.READY
        and quality.event_definitions_reconciled
    )
    assumptions = [
        "The scenario uses 100 normalized units, not an approved currency budget.",
        f"Exploit is fixed at {policy.exploit_share:.0%} and only statistical scale decisions are eligible.",
        f"Explore is fixed at {policy.explore_share:.0%} and funds named tests for statistical hold decisions.",
        "Within both pools, campaign-type envelopes preserve the previous cycle's spend mix.",
        "Exploit weighting uses probability of beating the learned benchmark; explore weighting preserves historical spend within type.",
        "Budget is allocated only at campaign level, so adset, ad, creative, and audience recommendations are not double-counted.",
        "There is no maximum campaign concentration cap in this POC.",
        "Unused exploit or explore envelopes remain unallocated.",
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
        exploration_tests=exploration_tests,
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
