"""Deterministic aggregation, KPI, benchmark, and allocation services."""

from .aggregations import CycleScorecards, build_level_scorecard, build_scorecards
from .allocation import DeterministicBudgetAllocator, build_budget_scenario
from .conversation_signals import aggregate_conversation_signals
from .empirical_bayes import (
    EmpiricalPrior,
    add_empirical_bayes_scores,
    fit_beta_prior,
    score_beta_binomial,
    score_level,
)
from .assessment_engine import (
    AssessmentBundle,
    DeterministicCampaignAssessor,
    build_assessment_bundle,
    build_evidence_packs,
    enrich_scorecards,
    metric_direction,
    metric_label,
    resolve_benchmark,
)

__all__ = [
    "CycleScorecards",
    "AssessmentBundle",
    "aggregate_conversation_signals",
    "add_empirical_bayes_scores",
    "DeterministicBudgetAllocator",
    "DeterministicCampaignAssessor",
    "build_assessment_bundle",
    "build_budget_scenario",
    "build_evidence_packs",
    "build_level_scorecard",
    "build_scorecards",
    "enrich_scorecards",
    "metric_direction",
    "metric_label",
    "resolve_benchmark",
    "EmpiricalPrior",
    "fit_beta_prior",
    "score_beta_binomial",
    "score_level",
]
