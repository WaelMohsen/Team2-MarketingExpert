"""Benchmark fixtures and automated runners for recommendation evaluation."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ..config import AppSettings
from ..core.observability import get_correlation_id
from ..reporting import MarketingReport
from .recommendation_framework import (
    ParameterSensitivitySummary,
    RecommendationEvaluationFramework,
    RecommendationEvaluationResult,
)

logger = logging.getLogger(__name__)
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class RecommendationBenchmarkCase:
    """A benchmark case describing what strong recommendations should contain."""

    case_id: str
    category: str
    description: str
    expected_problem_terms: tuple[str, ...]
    expected_evidence_terms: tuple[str, ...]
    preferred_primary_kpis: tuple[str, ...]
    required_action_terms: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()
    min_recommendations: int = 5

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RecommendationBenchmarkCase":
        return cls(
            case_id=str(payload["case_id"]),
            category=str(payload["category"]),
            description=str(payload["description"]),
            expected_problem_terms=tuple(payload.get("expected_problem_terms", ())),
            expected_evidence_terms=tuple(payload.get("expected_evidence_terms", ())),
            preferred_primary_kpis=tuple(payload.get("preferred_primary_kpis", ())),
            required_action_terms=tuple(payload.get("required_action_terms", ())),
            forbidden_terms=tuple(payload.get("forbidden_terms", ())),
            min_recommendations=int(payload.get("min_recommendations", 5)),
        )


@dataclass(frozen=True)
class RecommendationBenchmarkCandidate:
    """A report candidate being evaluated against a benchmark case."""

    candidate_id: str
    report: MarketingReport
    parameter_settings: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RecommendationBenchmarkCaseResult:
    """Ranked results for a single benchmark case."""

    case: RecommendationBenchmarkCase
    ranked_results: tuple[RecommendationEvaluationResult, ...]
    sensitivity_summary: ParameterSensitivitySummary | None = None

    def to_dict(self) -> dict[str, Any]:
        sensitivity_summary = None
        if self.sensitivity_summary is not None:
            sensitivity_summary = {
                "parameter_name": self.sensitivity_summary.parameter_name,
                "sample_count": self.sensitivity_summary.sample_count,
                "min_score": self.sensitivity_summary.min_score,
                "max_score": self.sensitivity_summary.max_score,
                "score_range": self.sensitivity_summary.score_range,
                "stable": self.sensitivity_summary.stable,
                "status_changed": self.sensitivity_summary.status_changed,
            }

        return {
            "case_id": self.case.case_id,
            "category": self.case.category,
            "ranked_results": [result.to_dict() for result in self.ranked_results],
            "sensitivity_summary": sensitivity_summary,
        }


@dataclass(frozen=True)
class RecommendationBenchmarkSuiteResult:
    """Combined results for multiple benchmark cases."""

    case_results: tuple[RecommendationBenchmarkCaseResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"case_results": [case_result.to_dict() for case_result in self.case_results]}


class RecommendationBenchmarkRepository:
    """Loads benchmark cases from a JSON fixture file."""

    def __init__(self, benchmark_file: str | Path | None = None, settings: AppSettings | None = None) -> None:
        self._settings = settings or AppSettings.default()
        self._benchmark_file = Path(benchmark_file) if benchmark_file else self._settings.paths.benchmark_file

    def load_cases(self) -> tuple[RecommendationBenchmarkCase, ...]:
        with self._benchmark_file.open("r", encoding="utf-8") as fixture_file:
            payload = json.load(fixture_file)

        cases = tuple(RecommendationBenchmarkCase.from_dict(item) for item in payload)
        logger.info("Loaded %s recommendation benchmark cases from %s", len(cases), self._benchmark_file)
        return cases


class RecommendationBenchmarkRunner:
    """Evaluates recommendation outputs against benchmark cases."""

    def __init__(self, framework: RecommendationEvaluationFramework | None = None) -> None:
        self._framework = framework or RecommendationEvaluationFramework()

    def evaluate_candidate(
        self,
        case: RecommendationBenchmarkCase,
        candidate: RecommendationBenchmarkCandidate,
    ) -> RecommendationEvaluationResult:
        logger.info(
            "Evaluating candidate %s against benchmark case %s",
            candidate.candidate_id,
            case.case_id,
        )

        criterion_scores = (
            self._score_problem_relevance(case, candidate.report),
            self._score_evidence_grounding(case, candidate.report),
            self._score_actionability(case, candidate.report),
            self._score_expected_impact(case, candidate.report),
            self._score_feasibility(case, candidate.report),
            self._score_measurability(case, candidate.report),
            self._score_clarity(case, candidate.report),
            self._score_non_duplication(candidate.report),
        )

        trace = {
            "benchmark_case_id": case.case_id,
            "benchmark_category": case.category,
            "correlation_id": get_correlation_id(),
        }
        return self._framework.evaluate_candidate(
            candidate_id=candidate.candidate_id,
            criterion_scores=criterion_scores,
            parameter_settings=candidate.parameter_settings,
            trace=trace,
        )

    def run_case(
        self,
        case: RecommendationBenchmarkCase,
        candidates: Sequence[RecommendationBenchmarkCandidate],
    ) -> RecommendationBenchmarkCaseResult:
        results = [self.evaluate_candidate(case, candidate) for candidate in candidates]
        ranked_results = tuple(self._framework.compare_results(results))
        sensitivity_summary = None
        if len(ranked_results) > 1:
            sensitivity_summary = self._framework.summarize_parameter_sensitivity(ranked_results)

        logger.info("Completed benchmark case %s with %s candidates", case.case_id, len(ranked_results))
        return RecommendationBenchmarkCaseResult(
            case=case,
            ranked_results=ranked_results,
            sensitivity_summary=sensitivity_summary,
        )

    def run_suite(
        self,
        cases: Sequence[RecommendationBenchmarkCase],
        candidates_by_case: Mapping[str, Sequence[RecommendationBenchmarkCandidate]],
    ) -> RecommendationBenchmarkSuiteResult:
        case_results = []
        for case in cases:
            case_candidates = candidates_by_case.get(case.case_id, ())
            if not case_candidates:
                continue
            case_results.append(self.run_case(case, case_candidates))

        logger.info("Completed benchmark suite with %s cases", len(case_results))
        return RecommendationBenchmarkSuiteResult(case_results=tuple(case_results))

    def _score_problem_relevance(
        self,
        case: RecommendationBenchmarkCase,
        report: MarketingReport,
    ):
        aggregate_text = self._aggregate_report_text(report)
        coverage = self._term_coverage(aggregate_text, case.expected_problem_terms)
        forbidden_hits = self._matching_terms(aggregate_text, case.forbidden_terms)
        score = 5.0 if coverage >= 0.75 else 4.0 if coverage >= 0.5 else 3.0 if coverage >= 0.25 else 2.0
        if report.category != case.category:
            score = min(score, 2.0)
        if forbidden_hits:
            score = max(1.0, score - 1.0)

        return self._framework.score_criterion(
            name="problem_relevance",
            score=score,
            rationale=(
                f"Problem-term coverage={coverage:.2f}; forbidden_hits={len(forbidden_hits)}; "
                f"report_category={report.category}"
            ),
            evidence=self._matching_terms(aggregate_text, case.expected_problem_terms),
        )

    def _score_evidence_grounding(
        self,
        case: RecommendationBenchmarkCase,
        report: MarketingReport,
    ):
        evidence_lists = [recommendation.evidence for recommendation in report.recommendations]
        evidence_ratio = self._ratio(bool(evidence) for evidence in evidence_lists)
        evidence_text = " ".join(item for evidence in evidence_lists for item in evidence).lower()
        coverage = self._term_coverage(evidence_text, case.expected_evidence_terms)
        score = round(min(5.0, 2.0 + (evidence_ratio * 2.0) + (coverage * 1.5)), 2)

        return self._framework.score_criterion(
            name="evidence_grounding",
            score=score,
            rationale=f"Evidence ratio={evidence_ratio:.2f}; expected evidence term coverage={coverage:.2f}",
            evidence=self._matching_terms(evidence_text, case.expected_evidence_terms),
        )

    def _score_actionability(
        self,
        case: RecommendationBenchmarkCase,
        report: MarketingReport,
    ):
        complete_action_steps = 0
        action_text_parts: list[str] = []
        for recommendation in report.recommendations:
            if recommendation.what_you_should_do:
                action_text_parts.extend(
                    f"{step.step} {step.where} {step.how}" for step in recommendation.what_you_should_do
                )
                if all(step.step and step.where and step.how for step in recommendation.what_you_should_do):
                    complete_action_steps += 1

        completeness_ratio = complete_action_steps / len(report.recommendations) if report.recommendations else 0.0
        action_text = " ".join(action_text_parts).lower()
        action_term_coverage = self._term_coverage(action_text, case.required_action_terms)
        score = round(min(5.0, 2.0 + (completeness_ratio * 2.0) + (action_term_coverage * 1.0)), 2)

        return self._framework.score_criterion(
            name="actionability",
            score=score,
            rationale=f"Complete action ratio={completeness_ratio:.2f}; action-term coverage={action_term_coverage:.2f}",
            evidence=self._matching_terms(action_text, case.required_action_terms),
        )

    def _score_expected_impact(
        self,
        case: RecommendationBenchmarkCase,
        report: MarketingReport,
    ):
        impact_ratio = self._ratio(bool(recommendation.expected_impact.primary_kpi) for recommendation in report.recommendations)
        impact_text = " ".join(
            f"{recommendation.expected_impact.primary_kpi} {recommendation.expected_impact.direction} {recommendation.expected_impact.explanation}"
            for recommendation in report.recommendations
        ).lower()
        kpi_coverage = self._term_coverage(impact_text, case.preferred_primary_kpis)
        score = round(min(5.0, 2.0 + (impact_ratio * 2.0) + (kpi_coverage * 1.0)), 2)

        return self._framework.score_criterion(
            name="expected_impact",
            score=score,
            rationale=f"Impact ratio={impact_ratio:.2f}; KPI coverage={kpi_coverage:.2f}",
            evidence=self._matching_terms(impact_text, case.preferred_primary_kpis),
        )

    def _score_feasibility(
        self,
        case: RecommendationBenchmarkCase,
        report: MarketingReport,
    ):
        feasible_count = 0
        for recommendation in report.recommendations:
            if recommendation.dependency_or_risk and recommendation.owner_suggestion:
                feasible_count += 1
        ratio = feasible_count / len(report.recommendations) if report.recommendations else 0.0
        score = round(min(5.0, 2.0 + (ratio * 3.0)), 2)

        return self._framework.score_criterion(
            name="feasibility_and_risk",
            score=score,
            rationale=f"Recommendations with owner and risk/dependency={ratio:.2f}",
            evidence=tuple(recommendation.owner_suggestion for recommendation in report.recommendations if recommendation.owner_suggestion),
        )

    def _score_measurability(
        self,
        case: RecommendationBenchmarkCase,
        report: MarketingReport,
    ):
        measurable_count = 0
        for recommendation in report.recommendations:
            measurement_plan = recommendation.measurement_plan
            if (
                measurement_plan.how_to_measure
                and measurement_plan.success_criteria
                and measurement_plan.check_timing
            ):
                measurable_count += 1
        ratio = measurable_count / len(report.recommendations) if report.recommendations else 0.0
        score = round(min(5.0, 2.0 + (ratio * 3.0)), 2)

        return self._framework.score_criterion(
            name="measurability",
            score=score,
            rationale=f"Recommendations with complete measurement plans={ratio:.2f}",
            evidence=tuple(
                recommendation.measurement_plan.success_criteria
                for recommendation in report.recommendations
                if recommendation.measurement_plan.success_criteria
            ),
        )

    def _score_clarity(
        self,
        case: RecommendationBenchmarkCase,
        report: MarketingReport,
    ):
        aggregate_text = self._aggregate_report_text(report)
        abbreviation_hits = self._matching_terms(aggregate_text, ("ctr", "roas", "cpa", "cac", "ltv", "mer"))
        average_title_length = (
            sum(len(recommendation.title.split()) for recommendation in report.recommendations) / len(report.recommendations)
            if report.recommendations
            else 0.0
        )
        score = 5.0
        if abbreviation_hits:
            score -= 1.0
        if average_title_length > 10:
            score -= 0.5

        return self._framework.score_criterion(
            name="clarity",
            score=max(1.0, score),
            rationale=f"Average title length={average_title_length:.2f}; abbreviation hits={len(abbreviation_hits)}",
            evidence=abbreviation_hits,
        )

    def _score_non_duplication(self, report: MarketingReport):
        titles = [self._normalize_text(recommendation.title) for recommendation in report.recommendations]
        unique_ratio = len(set(titles)) / len(titles) if titles else 0.0
        score = round(min(5.0, 2.0 + (unique_ratio * 3.0)), 2)

        return self._framework.score_criterion(
            name="non_duplication",
            score=score,
            rationale=f"Unique normalized title ratio={unique_ratio:.2f}",
            evidence=tuple(set(titles)),
        )

    @staticmethod
    def _aggregate_report_text(report: MarketingReport) -> str:
        recommendation_text = " ".join(
            " ".join(
                [
                    recommendation.title,
                    recommendation.whats_happening,
                    recommendation.why_this_matters or "",
                    " ".join(recommendation.evidence),
                    " ".join(f"{step.step} {step.where} {step.how}" for step in recommendation.what_you_should_do),
                    " ".join(recommendation.dependency_or_risk),
                ]
            )
            for recommendation in report.recommendations
        )
        return f"{report.category} {report.analysis.analysis} {report.analysis.root_cause_hypothesis} {recommendation_text}".lower()

    @staticmethod
    def _normalize_text(text: str) -> str:
        return _WHITESPACE_RE.sub(" ", text.strip().lower())

    @classmethod
    def _matching_terms(cls, text: str, terms: Iterable[str]) -> tuple[str, ...]:
        normalized_text = cls._normalize_text(text)
        return tuple(term for term in terms if term.lower() in normalized_text)

    @classmethod
    def _term_coverage(cls, text: str, terms: Sequence[str]) -> float:
        if not terms:
            return 1.0
        matching_terms = cls._matching_terms(text, terms)
        return len(matching_terms) / len(terms)

    @staticmethod
    def _ratio(values: Iterable[bool]) -> float:
        values = tuple(values)
        if not values:
            return 0.0
        return sum(1 for value in values if value) / len(values)
