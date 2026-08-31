import pytest

from src_2.analytics import (
    EmpiricalPrior,
    add_empirical_bayes_scores,
    build_scorecards,
    score_beta_binomial,
)
from src_2.domain.models import FundingDecision
from src_2.infrastructure.configuration import load_campaign_type_registry
from src_2.ingestion import load_sample2, normalize_cycle


def _score(successes, trials):
    return score_beta_binomial(
        metric="customer_delivered_rate",
        numerator="delivered_customers",
        denominator="mature_unique_customers",
        direction="higher",
        successes=successes,
        trials=trials,
        prior=EmpiricalPrior(alpha=8, beta=12, peer_count=5, source="test peers"),
        seed=17,
        samples=20_000,
    )


def test_small_samples_shrink_more_than_large_samples_with_the_same_raw_rate():
    small = _score(3, 4)
    large = _score(60, 80)

    assert small.raw_score == large.raw_score == pytest.approx(0.75)
    assert small.corrected_score == pytest.approx(11 / 24)
    assert large.corrected_score == pytest.approx(68 / 100)
    assert abs(small.corrected_score - 0.4) < abs(large.corrected_score - 0.4)
    assert small.decision is FundingDecision.HOLD
    assert large.decision is FundingDecision.SCALE


def test_small_failure_is_held_but_repeated_failure_is_killed():
    assert _score(0, 4).decision is FundingDecision.HOLD
    assert _score(0, 80).decision is FundingDecision.KILL


def test_all_five_scorecards_expose_the_same_empirical_bayes_contract():
    data = normalize_cycle(load_sample2())
    registry = load_campaign_type_registry()
    scorecards = add_empirical_bayes_scores(build_scorecards(data), registry)
    required = {
        "raw_score",
        "corrected_score",
        "corrected_score_low",
        "corrected_score_high",
        "benchmark_score",
        "benchmark_source",
        "benchmark_peer_count",
        "expected_lift",
        "lift_low",
        "lift_high",
        "probability_better",
        "statistical_decision",
    }

    for level in ("campaign", "adset", "ad", "creative", "audience"):
        frame = scorecards.by_level(level)
        assert required.issubset(frame.columns)
        assert frame["benchmark_peer_count"].ge(1).all()
        assert frame["corrected_score"].between(0, 1).all()
        assert set(frame["statistical_decision"]).issubset({"scale", "hold", "kill"})


def test_order_creation_score_uses_only_mature_outcomes():
    data = normalize_cycle(load_sample2())
    scorecards = add_empirical_bayes_scores(
        build_scorecards(data), load_campaign_type_registry()
    )
    experimental = scorecards.campaign[
        scorecards.campaign["campaign_type"].eq("experimental")
    ]

    assert experimental["score_successes"].le(experimental["score_trials"]).all()
    assert (
        experimental["score_successes"] == experimental["mature_orders_created"]
    ).all()
