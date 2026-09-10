"""Objective-only empirical-Bayes scoring and deterministic actions."""

from dataclasses import dataclass
from hashlib import sha256
from math import isclose
from random import Random
from statistics import variance
from typing import Dict, Iterable, List, Optional

import pandas as pd

from .config import ObjectiveRegistry
from .contracts import (
    BenchmarkQuality,
    BenchmarkScope,
    EfficiencyComparison,
    EvidenceStatus,
    NextCycleAction,
    StatisticalDecision,
)


@dataclass(frozen=True)
class EmpiricalPrior:
    alpha: float
    beta: float
    peer_count: int

    @property
    def strength(self) -> float:
        return self.alpha + self.beta

    @property
    def mean(self) -> float:
        return self.alpha / self.strength


def _quantile(values: List[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def fit_beta_prior(
    successes: Iterable[float], trials: Iterable[float]
) -> EmpiricalPrior:
    pairs = [
        (float(success), float(trial))
        for success, trial in zip(successes, trials)
        if float(trial) > 0 and 0 <= float(success) <= float(trial)
    ]
    if not pairs:
        raise ValueError("At least one valid peer is required")
    total_successes = sum(success for success, _ in pairs)
    total_trials = sum(trial for _, trial in pairs)
    peer_count = len(pairs)
    mean = (total_successes + 0.5) / (total_trials + 1.0)
    strength = total_trials / peer_count
    rates = [success / trial for success, trial in pairs]
    if len(rates) > 1:
        observed_variance = variance(rates)
        if observed_variance > 0:
            implied_strength = mean * (1 - mean) / observed_variance - 1
            strength = min(strength, implied_strength) if implied_strength > 0 else 1.0
    strength = max(float(strength), 1.0)
    return EmpiricalPrior(
        alpha=max(mean * strength, 1e-9),
        beta=max((1 - mean) * strength, 1e-9),
        peer_count=peer_count,
    )


def _seed(level: str, entity_id: str, metric: str) -> int:
    digest = sha256(f"{level}|{entity_id}|{metric}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _score(
    successes: float,
    trials: float,
    prior: EmpiricalPrior,
    direction: str,
    seed: int,
    samples: int = 5000,
) -> Dict[str, float]:
    posterior_alpha = prior.alpha + successes
    posterior_beta = prior.beta + trials - successes
    rng = Random(seed)
    entity_draws = [
        rng.betavariate(posterior_alpha, posterior_beta) for _ in range(samples)
    ]
    benchmark_draws = [
        rng.betavariate(prior.alpha, prior.beta) for _ in range(samples)
    ]
    if direction == "higher":
        lift_draws = [
            entity - benchmark
            for entity, benchmark in zip(entity_draws, benchmark_draws)
        ]
    else:
        lift_draws = [
            benchmark - entity
            for entity, benchmark in zip(entity_draws, benchmark_draws)
        ]
    lift_low = _quantile(lift_draws, 0.025)
    lift_high = _quantile(lift_draws, 0.975)
    if lift_low > 0:
        decision = StatisticalDecision.SCALE
    elif lift_high < 0:
        decision = StatisticalDecision.KILL
    else:
        decision = StatisticalDecision.HOLD
    return {
        "raw_rate": successes / trials,
        "corrected_rate": posterior_alpha / (posterior_alpha + posterior_beta),
        "range_low": _quantile(entity_draws, 0.025),
        "range_high": _quantile(entity_draws, 0.975),
        "benchmark": prior.mean,
        "expected_lift": sum(lift_draws) / len(lift_draws),
        "lift_low": lift_low,
        "lift_high": lift_high,
        "probability_better": sum(lift > 0 for lift in lift_draws) / len(lift_draws),
        "statistical_decision": decision.value,
    }


def _evidence_status(trials: float, minimum_trials: int) -> EvidenceStatus:
    if trials <= 0:
        return EvidenceStatus.NONE
    if trials < minimum_trials:
        return EvidenceStatus.LIMITED
    return EvidenceStatus.SUFFICIENT


def _valid_peers(
    frame: pd.DataFrame,
    row: pd.Series,
    numerator: str,
    denominator: str,
    objectives: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    mask = frame["entity_id"].ne(row["entity_id"])
    if objectives is not None:
        mask &= frame["objective"].isin(list(objectives))
    peers = frame.loc[mask].copy()
    peers["_successes"] = pd.to_numeric(peers[numerator], errors="coerce")
    peers["_trials"] = pd.to_numeric(peers[denominator], errors="coerce")
    return peers[
        peers["_trials"].gt(0)
        & peers["_successes"].ge(0)
        & peers["_successes"].le(peers["_trials"])
    ]


def _adjusted_pooled_rate(peers: pd.DataFrame) -> Optional[float]:
    if peers.empty:
        return None
    return float(
        (peers["_successes"].sum() + 0.5) / (peers["_trials"].sum() + 1.0)
    )


def _fallback_objectives(
    registry: ObjectiveRegistry, objective: str
) -> List[str]:
    contract = registry.objectives[objective]
    group = contract.fallback_benchmark_group
    if not group:
        return []
    return [
        name
        for name, candidate in registry.objectives.items()
        if candidate.fallback_benchmark_group == group
        and candidate.primary_metric == contract.primary_metric
        and candidate.primary_numerator == contract.primary_numerator
        and candidate.primary_denominator == contract.primary_denominator
        and candidate.primary_direction == contract.primary_direction
    ]


def _efficiency(
    frame: pd.DataFrame, row: pd.Series, metric: str, direction: str
) -> Dict[str, object]:
    peers = frame[
        frame["objective"].eq(row["objective"])
        & frame["entity_id"].ne(row["entity_id"])
    ].copy()
    values = pd.to_numeric(peers[metric], errors="coerce").dropna()
    actual = pd.to_numeric(pd.Series([row.get(metric)]), errors="coerce").iloc[0]
    if pd.isna(actual) or values.empty:
        return {
            "efficiency_value": None if pd.isna(actual) else float(actual),
            "efficiency_benchmark": None,
            "efficiency_peer_count": int(len(values)),
            "efficiency_comparison": EfficiencyComparison.UNAVAILABLE.value,
        }
    benchmark = float(values.median())
    actual_value = float(actual)
    if isclose(actual_value, benchmark, rel_tol=1e-9, abs_tol=1e-12):
        comparison = EfficiencyComparison.EQUAL
    elif (direction == "higher" and actual_value > benchmark) or (
        direction == "lower" and actual_value < benchmark
    ):
        comparison = EfficiencyComparison.BETTER
    else:
        comparison = EfficiencyComparison.WORSE
    return {
        "efficiency_value": actual_value,
        "efficiency_benchmark": benchmark,
        "efficiency_peer_count": int(len(values)),
        "efficiency_comparison": comparison.value,
    }


def _action(
    decision: StatisticalDecision,
    evidence: EvidenceStatus,
    efficiency: EfficiencyComparison,
    benchmark_quality: BenchmarkQuality,
) -> tuple[NextCycleAction, List[str]]:
    if evidence is not EvidenceStatus.SUFFICIENT or decision is StatisticalDecision.INSUFFICIENT_EVIDENCE:
        return NextCycleAction.INSUFFICIENT_EVIDENCE, ["INSUFFICIENT_PRIMARY_EVIDENCE"]
    if decision is StatisticalDecision.SCALE:
        statistical_reason = "PRIMARY_LIFT_RANGE_POSITIVE"
    elif decision is StatisticalDecision.KILL:
        statistical_reason = "PRIMARY_LIFT_RANGE_NEGATIVE"
    else:
        statistical_reason = "PRIMARY_LIFT_RANGE_CROSSES_ZERO"
    if benchmark_quality is BenchmarkQuality.PROVISIONAL:
        return NextCycleAction.KEEP_AS_TEST, [
            statistical_reason,
            "SAME_OBJECTIVE_PEERS_INSUFFICIENT",
            "FALLBACK_TO_SHARED_PRIMARY_KPI_GROUP",
            "FALLBACK_ACTION_CAPPED_AT_TEST",
        ]
    if decision is StatisticalDecision.KILL:
        return NextCycleAction.DO_NOT_FUND, [statistical_reason]
    if decision is StatisticalDecision.HOLD:
        return NextCycleAction.KEEP_AS_TEST, [statistical_reason]
    if efficiency in {EfficiencyComparison.BETTER, EfficiencyComparison.EQUAL}:
        return NextCycleAction.SCALE, [
            "PRIMARY_LIFT_RANGE_POSITIVE",
            "EFFICIENCY_ACCEPTABLE_VS_PEER",
        ]
    if efficiency is EfficiencyComparison.WORSE:
        return NextCycleAction.KEEP_AS_TEST, [
            "PRIMARY_LIFT_RANGE_POSITIVE",
            "EFFICIENCY_WORSE_THAN_PEER",
        ]
    return NextCycleAction.KEEP_AS_TEST, [
        "PRIMARY_LIFT_RANGE_POSITIVE",
        "EFFICIENCY_BENCHMARK_UNAVAILABLE",
    ]


def score_level(
    frame: pd.DataFrame, level: str, registry: ObjectiveRegistry
) -> pd.DataFrame:
    output = frame.copy()
    scored: List[Dict[str, object]] = []
    for _, row in output.iterrows():
        objective = str(row["objective"])
        if objective not in registry.objectives:
            raise ValueError(f"No objective contract configured for {objective}")
        contract = registry.objectives[objective]
        successes = float(row.get(contract.primary_numerator, 0) or 0)
        trials = float(row.get(contract.primary_denominator, 0) or 0)
        evidence = _evidence_status(trials, contract.minimum_trials)
        same_objective_peers = _valid_peers(
            output,
            row,
            contract.primary_numerator,
            contract.primary_denominator,
            [objective],
        )
        peers = same_objective_peers
        benchmark_scope = BenchmarkScope.UNAVAILABLE
        benchmark_quality = BenchmarkQuality.UNAVAILABLE
        if len(same_objective_peers) >= contract.minimum_peer_entities:
            benchmark_scope = BenchmarkScope.SAME_OBJECTIVE
            benchmark_quality = BenchmarkQuality.DECISION_GRADE
        else:
            fallback_objectives = _fallback_objectives(registry, objective)
            if fallback_objectives:
                fallback_peers = _valid_peers(
                    output,
                    row,
                    contract.primary_numerator,
                    contract.primary_denominator,
                    fallback_objectives,
                )
                if len(fallback_peers) >= contract.minimum_peer_entities:
                    peers = fallback_peers
                    benchmark_scope = BenchmarkScope.SHARED_PRIMARY_KPI_GROUP
                    benchmark_quality = BenchmarkQuality.PROVISIONAL
        portfolio_peers = _valid_peers(
            output,
            row,
            contract.primary_numerator,
            contract.primary_denominator,
        )
        values: Dict[str, object] = {
            "entity_id": row["entity_id"],
            "score_metric": contract.primary_metric,
            "score_numerator": contract.primary_numerator,
            "score_denominator": contract.primary_denominator,
            "score_direction": contract.primary_direction,
            "score_successes": successes,
            "score_trials": trials,
            "raw_rate": successes / trials if trials else None,
            "corrected_rate": None,
            "range_low": None,
            "range_high": None,
            "benchmark": None,
            "benchmark_peer_count": int(len(peers)),
            "same_objective_peer_count": int(len(same_objective_peers)),
            "benchmark_scope": benchmark_scope.value,
            "benchmark_quality": benchmark_quality.value,
            "portfolio_context_benchmark": _adjusted_pooled_rate(portfolio_peers),
            "portfolio_context_peer_count": int(len(portfolio_peers)),
            "expected_lift": None,
            "lift_low": None,
            "lift_high": None,
            "probability_better": None,
            "statistical_decision": StatisticalDecision.INSUFFICIENT_EVIDENCE.value,
            "evidence_status": evidence.value,
            "efficiency_metric": contract.efficiency_metric,
            "efficiency_direction": contract.efficiency_direction,
        }
        if (
            trials > 0
            and benchmark_quality is not BenchmarkQuality.UNAVAILABLE
            and len(peers) >= contract.minimum_peer_entities
        ):
            prior = fit_beta_prior(peers["_successes"], peers["_trials"])
            values.update(
                _score(
                    successes,
                    trials,
                    prior,
                    contract.primary_direction,
                    _seed(level, str(row["entity_id"]), contract.primary_metric),
                )
            )
        efficiency_values = _efficiency(
            output, row, contract.efficiency_metric, contract.efficiency_direction
        )
        values.update(efficiency_values)
        decision = StatisticalDecision(str(values["statistical_decision"]))
        comparison = EfficiencyComparison(str(values["efficiency_comparison"]))
        action, reasons = _action(
            decision, evidence, comparison, benchmark_quality
        )
        values["recommended_action"] = action.value
        values["reason_codes"] = reasons
        scored.append(values)
    return output.merge(pd.DataFrame(scored), on="entity_id", how="left")


def score_all_levels(
    scorecards: Dict[str, pd.DataFrame], registry: ObjectiveRegistry
) -> Dict[str, pd.DataFrame]:
    return {
        level: score_level(frame, level, registry)
        for level, frame in scorecards.items()
    }
