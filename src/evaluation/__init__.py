"""Recommendation evaluation contracts and helpers."""

from .benchmarks import (
    RecommendationBenchmarkCandidate,
    RecommendationBenchmarkCase,
    RecommendationBenchmarkCaseResult,
    RecommendationBenchmarkRepository,
    RecommendationBenchmarkRunner,
    RecommendationBenchmarkSuiteResult,
)
from .recommendation_framework import (
    CriterionDefinition,
    CriterionScore,
    EvaluationStatus,
    ParameterSensitivitySummary,
    RecommendationEvaluationFramework,
    RecommendationEvaluationResult,
)
from .report_loader import (
    build_candidate_from_report_file,
    load_marketing_report,
    load_report_payload,
    marketing_report_from_payload,
    select_benchmark_cases,
)

__all__ = [
    "build_candidate_from_report_file",
    "CriterionDefinition",
    "CriterionScore",
    "EvaluationStatus",
    "load_marketing_report",
    "load_report_payload",
    "marketing_report_from_payload",
    "ParameterSensitivitySummary",
    "RecommendationBenchmarkCandidate",
    "RecommendationBenchmarkCase",
    "RecommendationBenchmarkCaseResult",
    "RecommendationBenchmarkRepository",
    "RecommendationBenchmarkRunner",
    "RecommendationBenchmarkSuiteResult",
    "RecommendationEvaluationFramework",
    "RecommendationEvaluationResult",
    "select_benchmark_cases",
]
