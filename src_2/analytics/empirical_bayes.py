"""Small-sample corrected scores learned from compatible peer entities."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from random import Random
from statistics import variance
from typing import Iterable

import pandas as pd

from src_2.contracts import EmpiricalBayesScore
from src_2.domain.config import CampaignTypeRegistry, ScoreMetricConfig
from src_2.domain.models import CampaignType, FundingDecision

from .aggregations import CycleScorecards


@dataclass(frozen=True)
class EmpiricalPrior:
    alpha: float
    beta: float
    peer_count: int
    source: str

    @property
    def strength(self) -> float:
        return self.alpha + self.beta

    @property
    def mean(self) -> float:
        return self.alpha / self.strength


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("Cannot calculate a quantile from no values")
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def fit_beta_prior(
    successes: Iterable[float],
    trials: Iterable[float],
    *,
    source: str,
) -> EmpiricalPrior:
    """Fit a transparent empirical beta prior from peer sufficient statistics.

    The prior mean is the pooled peer rate. Its strength is no greater than the
    average peer sample size and is reduced when peer rates are heterogeneous.
    """

    pairs = [
        (float(k), float(n))
        for k, n in zip(successes, trials)
        if isfinite(float(k))
        and isfinite(float(n))
        and float(n) > 0
        and 0 <= float(k) <= float(n)
    ]
    if not pairs:
        raise ValueError("At least one valid peer is required to fit an empirical prior")
    total_successes = sum(item[0] for item in pairs)
    total_trials = sum(item[1] for item in pairs)
    peer_count = len(pairs)

    # A half-observation continuity adjustment keeps all-success/all-failure
    # peer groups from producing a degenerate prior at exactly zero or one.
    mean = (total_successes + 0.5) / (total_trials + 1.0)
    average_trials = total_trials / peer_count
    strength = average_trials
    rates = [k / n for k, n in pairs]
    if len(rates) > 1:
        observed_variance = variance(rates)
        if observed_variance > 0:
            implied_strength = mean * (1 - mean) / observed_variance - 1
            if implied_strength > 0:
                strength = min(strength, implied_strength)
            else:
                strength = 1.0
    strength = max(float(strength), 1.0)
    return EmpiricalPrior(
        alpha=max(mean * strength, 1e-9),
        beta=max((1 - mean) * strength, 1e-9),
        peer_count=peer_count,
        source=source,
    )


def score_beta_binomial(
    *,
    metric: str,
    numerator: str,
    denominator: str,
    direction: str,
    successes: float,
    trials: float,
    prior: EmpiricalPrior,
    practical_lift_threshold: float = 0.0,
    seed: int = 0,
    samples: int = 5000,
) -> EmpiricalBayesScore:
    """Return a corrected score and the posterior distribution of peer lift."""

    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError(
            f"Invalid binomial sufficient statistics for {metric}: "
            f"successes={successes}, trials={trials}"
        )
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
        lift_draws = [actual - benchmark for actual, benchmark in zip(entity_draws, benchmark_draws)]
    else:
        lift_draws = [benchmark - actual for actual, benchmark in zip(entity_draws, benchmark_draws)]

    lift_low = _quantile(lift_draws, 0.025)
    lift_high = _quantile(lift_draws, 0.975)
    if trials <= 0:
        decision = FundingDecision.HOLD
    elif lift_low > practical_lift_threshold:
        decision = FundingDecision.SCALE
    elif lift_high < -practical_lift_threshold:
        decision = FundingDecision.KILL
    else:
        decision = FundingDecision.HOLD

    return EmpiricalBayesScore(
        metric=metric,
        numerator=numerator,
        denominator=denominator,
        direction=direction,
        successes=successes,
        trials=trials,
        raw_score=successes / trials if trials else None,
        corrected_score=posterior_alpha / (posterior_alpha + posterior_beta),
        corrected_score_low=_quantile(entity_draws, 0.025),
        corrected_score_high=_quantile(entity_draws, 0.975),
        benchmark_score=prior.mean,
        benchmark_low=_quantile(benchmark_draws, 0.025),
        benchmark_high=_quantile(benchmark_draws, 0.975),
        benchmark_source=prior.source,
        benchmark_peer_count=prior.peer_count,
        prior_alpha=prior.alpha,
        prior_beta=prior.beta,
        prior_strength=prior.strength,
        expected_lift=sum(lift_draws) / len(lift_draws),
        lift_low=lift_low,
        lift_high=lift_high,
        probability_better=sum(value > 0 for value in lift_draws) / len(lift_draws),
        practical_lift_threshold=practical_lift_threshold,
        decision=decision,
        interval_method=(
            "95% empirical-Bayes posterior simulation conditional on a peer-fitted beta prior"
        ),
    )


def _valid_peers(
    frame: pd.DataFrame,
    row: pd.Series,
    spec: ScoreMetricConfig,
) -> pd.DataFrame:
    peers = frame[frame["entity_id"].ne(row["entity_id"])].copy()
    peers["_successes"] = pd.to_numeric(peers[spec.numerator], errors="coerce")
    peers["_trials"] = pd.to_numeric(peers[spec.denominator], errors="coerce")
    return peers[
        peers["_trials"].gt(0)
        & peers["_successes"].ge(0)
        & peers["_successes"].le(peers["_trials"])
    ]


def _valid_historical_peers(
    frame: pd.DataFrame | None,
    spec: ScoreMetricConfig,
) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    peers = frame.copy()
    peers["_successes"] = pd.to_numeric(peers[spec.numerator], errors="coerce")
    peers["_trials"] = pd.to_numeric(peers[spec.denominator], errors="coerce")
    return peers[
        peers["_trials"].gt(0)
        & peers["_successes"].ge(0)
        & peers["_successes"].le(peers["_trials"])
    ]


def _resolve_prior(
    frame: pd.DataFrame,
    row: pd.Series,
    spec: ScoreMetricConfig,
    level: str,
    historical_frame: pd.DataFrame | None = None,
) -> EmpiricalPrior | None:
    historical = _valid_historical_peers(historical_frame, spec)
    if not historical.empty:
        for mask, source in (
            (
                historical["campaign_type"].eq(row["campaign_type"]),
                "historical same-type empirical prior",
            ),
            (
                historical["objective"].eq(row["objective"]),
                "historical same-objective empirical prior",
            ),
            (
                pd.Series(True, index=historical.index),
                "historical compatible-portfolio empirical prior",
            ),
        ):
            candidates = historical[mask]
            if len(candidates) >= 2:
                return fit_beta_prior(
                    candidates["_successes"], candidates["_trials"], source=source
                )
    peers = _valid_peers(frame, row, spec)
    scopes: list[tuple[pd.Series, str]] = []
    if level != "campaign":
        scopes.append(
            (
                peers["campaign_id"].eq(row["campaign_id"]),
                "current-cycle same-campaign empirical prior",
            )
        )
    scopes.extend(
        [
            (
                peers["campaign_type"].eq(row["campaign_type"]),
                "current-cycle same-type empirical prior",
            ),
            (
                peers["objective"].eq(row["objective"]),
                "current-cycle same-objective empirical prior",
            ),
            (
                pd.Series(True, index=peers.index),
                "current-cycle compatible-portfolio empirical prior",
            ),
        ]
    )
    fallback: tuple[pd.DataFrame, str] | None = None
    for mask, source in scopes:
        candidates = peers[mask]
        if not candidates.empty:
            fallback = (candidates, source)
        if len(candidates) >= 2:
            return fit_beta_prior(
                candidates["_successes"], candidates["_trials"], source=source
            )
    if fallback is None:
        return None
    candidates, source = fallback
    return fit_beta_prior(candidates["_successes"], candidates["_trials"], source=source)


def _seed(level: str, entity_id: str, metric: str) -> int:
    digest = sha256(f"{level}|{entity_id}|{metric}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def score_level(
    frame: pd.DataFrame,
    level: str,
    registry: CampaignTypeRegistry,
    historical_frame: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Attach the same empirical-Bayes score contract to one entity-level table."""

    result = frame.copy()
    scored_rows: list[dict[str, object]] = []
    for _, row in result.iterrows():
        spec = registry.campaign_types[CampaignType(row["campaign_type"])].score_metric
        successes = float(row.get(spec.numerator, 0) or 0)
        trials = float(row.get(spec.denominator, 0) or 0)
        prior = _resolve_prior(result, row, spec, level, historical_frame)
        score = None
        error = None
        if prior is None:
            error = "No compatible peer outcomes were available to fit an empirical prior."
        else:
            try:
                score = score_beta_binomial(
                    metric=spec.metric,
                    numerator=spec.numerator,
                    denominator=spec.denominator,
                    direction=spec.direction,
                    successes=successes,
                    trials=trials,
                    prior=prior,
                    practical_lift_threshold=spec.practical_lift_threshold,
                    seed=_seed(level, str(row["entity_id"]), spec.metric),
                )
            except ValueError as exc:
                error = str(exc)
        payload: dict[str, object] = {
            "entity_id": row["entity_id"],
            "score_metric": spec.metric,
            "score_numerator": spec.numerator,
            "score_denominator": spec.denominator,
            "score_direction": spec.direction,
            "score_successes": successes,
            "score_trials": trials,
            "raw_score": None,
            "corrected_score": None,
            "corrected_score_low": None,
            "corrected_score_high": None,
            "benchmark_score": None,
            "benchmark_low": None,
            "benchmark_high": None,
            "benchmark_source": None,
            "benchmark_peer_count": 0,
            "prior_alpha": None,
            "prior_beta": None,
            "prior_strength": None,
            "expected_lift": None,
            "lift_low": None,
            "lift_high": None,
            "probability_better": None,
            "practical_lift_threshold": spec.practical_lift_threshold,
            "statistical_decision": FundingDecision.HOLD.value,
            "score_interval_method": None,
            "score_error": error,
        }
        if score is not None:
            values = score.model_dump(mode="json")
            payload.update(
                {
                    "raw_score": values["raw_score"],
                    "corrected_score": values["corrected_score"],
                    "corrected_score_low": values["corrected_score_low"],
                    "corrected_score_high": values["corrected_score_high"],
                    "benchmark_score": values["benchmark_score"],
                    "benchmark_low": values["benchmark_low"],
                    "benchmark_high": values["benchmark_high"],
                    "benchmark_source": values["benchmark_source"],
                    "benchmark_peer_count": values["benchmark_peer_count"],
                    "prior_alpha": values["prior_alpha"],
                    "prior_beta": values["prior_beta"],
                    "prior_strength": values["prior_strength"],
                    "expected_lift": values["expected_lift"],
                    "lift_low": values["lift_low"],
                    "lift_high": values["lift_high"],
                    "probability_better": values["probability_better"],
                    "statistical_decision": values["decision"],
                    "score_interval_method": values["interval_method"],
                    "score_error": None,
                }
            )
        scored_rows.append(payload)
    return result.merge(pd.DataFrame(scored_rows), on="entity_id", how="left")


def add_empirical_bayes_scores(
    scorecards: CycleScorecards,
    registry: CampaignTypeRegistry,
    historical_scorecards: CycleScorecards | None = None,
) -> CycleScorecards:
    """Add objective-aligned corrected scores to every scorecard level."""

    return CycleScorecards(
        campaign=score_level(
            scorecards.campaign,
            "campaign",
            registry,
            historical_scorecards.campaign if historical_scorecards else None,
        ),
        adset=score_level(
            scorecards.adset,
            "adset",
            registry,
            historical_scorecards.adset if historical_scorecards else None,
        ),
        ad=score_level(
            scorecards.ad,
            "ad",
            registry,
            historical_scorecards.ad if historical_scorecards else None,
        ),
        creative=score_level(
            scorecards.creative,
            "creative",
            registry,
            historical_scorecards.creative if historical_scorecards else None,
        ),
        audience=score_level(
            scorecards.audience,
            "audience",
            registry,
            historical_scorecards.audience if historical_scorecards else None,
        ),
    )
