"""Allocate every objective envelope using primary and conversation evidence."""

from typing import Dict, List, Tuple

import pandas as pd

from .config import BudgetPolicy, ObjectiveRegistry
from .contracts import BudgetAllocation, ExplorationTest, NextCycleAction


ALLOCATION_BASIS = "primary_probability_x_semantic_lower_bound"


def _weights(rows: pd.DataFrame, column: str) -> Dict[str, float]:
    if rows.empty:
        return {}
    values = pd.to_numeric(rows[column], errors="coerce").fillna(0).clip(lower=0)
    if float(values.sum()) <= 0:
        values = pd.Series(1.0, index=rows.index)
    values = values / float(values.sum())
    return dict(zip(rows["campaign_id"].astype(str), values.astype(float)))


def _score_weights(rows: pd.DataFrame) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Return normalized products and raw products for rows with both components."""
    priorities: Dict[str, float] = {}
    for _, row in rows.iterrows():
        primary = pd.to_numeric(row.get("probability_better"), errors="coerce")
        semantic = pd.to_numeric(
            (row.get("semantic_score") or {}).get("range_low"), errors="coerce"
        )
        if pd.isna(primary) or pd.isna(semantic):
            continue
        priorities[str(row["campaign_id"])] = max(float(primary), 0.0) * max(
            float(semantic), 0.0
        )
    total = sum(priorities.values())
    weights = {
        campaign_id: priority / total
        for campaign_id, priority in priorities.items()
    } if total > 0 else {}
    return weights, priorities


def _named_test(
    row: pd.Series, contract, units: float
) -> ExplorationTest:
    metric = contract.semantic.metric.replace("_", " ")
    barrier = row.get("top_barrier")
    test_change = (
        f"Clarify the offer and address the observed {barrier} barrier"
        if isinstance(barrier, str) and barrier
        else "Clarify the offer and intended customer need"
    )
    return ExplorationTest(
        campaign_id=str(row["campaign_id"]),
        campaign_name=str(row["campaign_name"]),
        objective=str(row["objective"]),
        assigned_budget_units=units,
        hypothesis=(
            f"{test_change} in a named variant against the current message. "
            f"Hypothesis: this increases {metric} and improves "
            f"{contract.primary_metric.replace('_', ' ')} in the next cycle. "
            "The observed association is a hypothesis, not an established cause."
        ),
        primary_metric=contract.primary_metric,
        success_rule=(
            "At cycle end, check the primary favorable-lift range, efficiency, and the "
            "separate semantic range. A provisional Link CTR benchmark remains capped "
            "at KEEP_AS_TEST."
        ),
        failure_rule=(
            "At cycle end, DO_NOT_FUND requires a decision-grade primary lift upper "
            "bound below zero with sufficient evidence. Semantic quality alone does "
            "not determine the final action."
        ),
        stop_rule=(
            "Stop when the assigned budget is spent or the next cycle ends, whichever "
            "comes first; wait for outcomes to mature before scoring."
        ),
    )


def allocate_budget(
    campaign_scorecard: pd.DataFrame,
    registry: ObjectiveRegistry,
    policy: BudgetPolicy,
) -> Tuple[List[BudgetAllocation], List[ExplorationTest], float]:
    if policy.allocation_mode != "score_based":
        raise ValueError(f"Unknown allocation mode: {policy.allocation_mode}")
    if policy.campaign_weight != ALLOCATION_BASIS:
        raise ValueError(f"Unknown campaign weight: {policy.campaign_weight}")

    frame = campaign_scorecard.copy()
    objective_spend = frame.groupby("objective")["spend"].sum()
    if float(objective_spend.sum()) > 0:
        objective_shares = objective_spend / float(objective_spend.sum())
    else:
        objectives = sorted(frame["objective"].dropna().unique())
        objective_shares = pd.Series(1 / len(objectives), index=objectives)

    state: Dict[str, Dict[str, object]] = {}
    unallocated = 0.0
    tests: List[ExplorationTest] = []
    for objective, share in objective_shares.items():
        rows = frame[frame["objective"].eq(objective)].copy()
        envelope = policy.budget_units * float(share)
        score_weights, priorities = _score_weights(rows)
        spend_weights = _weights(rows, "spend")
        if not score_weights:
            unallocated += envelope

        for _, row in rows.iterrows():
            campaign_id = str(row["campaign_id"])
            semantic = row.get("semantic_score") or {}
            primary_component = pd.to_numeric(
                row.get("probability_better"), errors="coerce"
            )
            semantic_component = pd.to_numeric(
                semantic.get("range_low"), errors="coerce"
            )
            weight = float(score_weights.get(campaign_id, 0.0))
            units = envelope * weight
            has_components = campaign_id in priorities
            reasons = list(row["reason_codes"])
            reasons.append(
                "BUDGET_WEIGHTED_BY_PRIMARY_PROBABILITY_X_SEMANTIC_LOWER_BOUND"
                if has_components
                else "BUDGET_COMPONENT_UNAVAILABLE_ZERO_ALLOCATION"
            )
            state[campaign_id] = {
                "envelope": envelope,
                "weight": weight,
                "units": units,
                "baseline_units": envelope * spend_weights[campaign_id],
                "primary": None if pd.isna(primary_component) else float(primary_component),
                "semantic": None if pd.isna(semantic_component) else float(semantic_component),
                "priority": priorities.get(campaign_id),
                "reasons": reasons,
            }
            if (
                units > 0
                and str(row["recommended_action"]) == NextCycleAction.KEEP_AS_TEST.value
            ):
                tests.append(
                    _named_test(row, registry.objectives[str(objective)], units)
                )

    allocations: List[BudgetAllocation] = []
    for _, row in frame.iterrows():
        campaign_id = str(row["campaign_id"])
        item = state[campaign_id]
        units = float(item["units"])
        allocations.append(
            BudgetAllocation(
                campaign_id=campaign_id,
                campaign_name=str(row["campaign_name"]),
                objective=str(row["objective"]),
                action=NextCycleAction(str(row["recommended_action"])),
                budget_pool="score_based" if item["priority"] is not None else "unallocated",
                objective_envelope_units=float(item["envelope"]),
                allocation_weight=float(item["weight"]),
                recommended_budget_units=units,
                recommended_budget_share=units / policy.budget_units,
                allocation_basis=ALLOCATION_BASIS,
                primary_probability_component=item["primary"],
                semantic_priority=item["semantic"],
                allocation_priority=item["priority"],
                previous_spend_budget_units=float(item["baseline_units"]),
                reason_codes=list(item["reasons"]),
            )
        )
    return allocations, tests, unallocated
