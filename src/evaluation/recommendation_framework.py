"""Practical recommendation evaluation contracts and scoring helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class EvaluationStatus(str, Enum):
    """Normalized evaluation states used across the application."""

    PASS = "pass"
    BORDERLINE = "borderline"
    FAIL = "fail"


@dataclass(frozen=True)
class CriterionDefinition:
    """Configuration for a recommendation evaluation criterion."""

    name: str
    description: str
    weight: float
    pass_threshold: float
    borderline_threshold: float
    hard_fail_threshold: float


@dataclass(frozen=True)
class CriterionScore:
    """Score and rationale for a single recommendation criterion."""

    name: str
    score: float
    status: EvaluationStatus
    rationale: str
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the criterion score for logs or downstream systems."""

        return {
            "name": self.name,
            "score": self.score,
            "status": self.status.value,
            "rationale": self.rationale,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class RecommendationEvaluationResult:
    """Evaluation result for one recommendation candidate output."""

    candidate_id: str
    criteria: tuple[CriterionScore, ...]
    overall_score: float
    overall_status: EvaluationStatus
    parameter_settings: dict[str, Any] = field(default_factory=dict)
    trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the evaluation result with traceability metadata."""

        return {
            "candidate_id": self.candidate_id,
            "overall_score": self.overall_score,
            "overall_status": self.overall_status.value,
            "parameter_settings": dict(self.parameter_settings),
            "criteria": [criterion.to_dict() for criterion in self.criteria],
            "trace": dict(self.trace),
        }


@dataclass(frozen=True)
class ParameterSensitivitySummary:
    """Summary of stability when one model parameter changes across runs."""

    parameter_name: str
    sample_count: int
    min_score: float
    max_score: float
    score_range: float
    stable: bool
    status_changed: bool


DEFAULT_CRITERIA: tuple[CriterionDefinition, ...] = (
    CriterionDefinition(
        name="problem_relevance",
        description="Recommendation addresses the business problem raised by the input metrics.",
        weight=0.20,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
    ),
    CriterionDefinition(
        name="evidence_grounding",
        description="Claims are supported by metrics, signals, or explicit observations.",
        weight=0.20,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
    ),
    CriterionDefinition(
        name="actionability",
        description="Recommendation includes concrete next steps that a team can execute.",
        weight=0.15,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
    ),
    CriterionDefinition(
        name="expected_impact",
        description="Recommendation states an expected business outcome and why it should happen.",
        weight=0.15,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
    ),
    CriterionDefinition(
        name="feasibility_and_risk",
        description="Recommendation is realistic and acknowledges constraints, dependencies, or risks.",
        weight=0.10,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
    ),
    CriterionDefinition(
        name="measurability",
        description="Recommendation can be evaluated with a concrete measurement plan.",
        weight=0.10,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
    ),
    CriterionDefinition(
        name="clarity",
        description="Recommendation is easy for a non-specialist stakeholder to understand.",
        weight=0.05,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
    ),
    CriterionDefinition(
        name="non_duplication",
        description="Recommendation set avoids repeating the same action in different wording.",
        weight=0.05,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
    ),
)


class RecommendationEvaluationFramework:
    """Builds consistent recommendation scores, thresholds, and comparisons."""

    def __init__(self, criteria: Sequence[CriterionDefinition] | None = None) -> None:
        self._criteria = tuple(criteria or DEFAULT_CRITERIA)
        self._criteria_by_name = {criterion.name: criterion for criterion in self._criteria}

    @property
    def criteria(self) -> tuple[CriterionDefinition, ...]:
        """Return the configured evaluation criteria."""

        return self._criteria

    def score_criterion(
        self,
        name: str,
        score: float,
        rationale: str,
        evidence: Sequence[str] | None = None,
    ) -> CriterionScore:
        """Create a normalized criterion score using configured thresholds."""

        definition = self._criteria_by_name[name]
        normalized_score = round(max(0.0, min(5.0, float(score))), 2)
        status = self._status_for_score(definition, normalized_score)
        return CriterionScore(
            name=name,
            score=normalized_score,
            status=status,
            rationale=rationale,
            evidence=tuple(evidence or ()),
        )

    def evaluate_candidate(
        self,
        candidate_id: str,
        criterion_scores: Sequence[CriterionScore],
        parameter_settings: Mapping[str, Any] | None = None,
        trace: Mapping[str, Any] | None = None,
    ) -> RecommendationEvaluationResult:
        """Aggregate criterion scores into one weighted evaluation result."""

        scores_by_name = {criterion.name: criterion for criterion in criterion_scores}
        missing_criteria = [criterion.name for criterion in self._criteria if criterion.name not in scores_by_name]
        if missing_criteria:
            raise ValueError(f"Missing criterion scores: {', '.join(missing_criteria)}")

        weighted_total = 0.0
        hard_failures = False
        has_borderline = False

        for definition in self._criteria:
            criterion_score = scores_by_name[definition.name]
            weighted_total += criterion_score.score * definition.weight
            hard_failures = hard_failures or criterion_score.score < definition.hard_fail_threshold
            has_borderline = has_borderline or criterion_score.status == EvaluationStatus.BORDERLINE

        overall_score = round(weighted_total, 2)

        if hard_failures or overall_score < 3.0:
            overall_status = EvaluationStatus.FAIL
        elif has_borderline or overall_score < 4.0:
            overall_status = EvaluationStatus.BORDERLINE
        else:
            overall_status = EvaluationStatus.PASS

        result_trace = dict(trace or {})
        result_trace["hard_failures_present"] = hard_failures
        result_trace["missing_criteria"] = missing_criteria

        return RecommendationEvaluationResult(
            candidate_id=candidate_id,
            criteria=tuple(scores_by_name[criterion.name] for criterion in self._criteria),
            overall_score=overall_score,
            overall_status=overall_status,
            parameter_settings=dict(parameter_settings or {}),
            trace=result_trace,
        )

    def compare_results(
        self,
        results: Sequence[RecommendationEvaluationResult],
    ) -> list[RecommendationEvaluationResult]:
        """Return results sorted from best to worst using stable comparison rules."""

        status_order = {
            EvaluationStatus.PASS: 2,
            EvaluationStatus.BORDERLINE: 1,
            EvaluationStatus.FAIL: 0,
        }

        return sorted(
            results,
            key=lambda result: (
                status_order[result.overall_status],
                result.overall_score,
                self._criterion_score(result, "evidence_grounding"),
                self._criterion_score(result, "problem_relevance"),
            ),
            reverse=True,
        )

    def summarize_parameter_sensitivity(
        self,
        results: Sequence[RecommendationEvaluationResult],
        parameter_name: str = "temperature",
        stable_range: float = 0.5,
    ) -> ParameterSensitivitySummary:
        """Summarize score stability when a parameter changes across runs."""

        if not results:
            raise ValueError("At least one evaluation result is required.")

        scores = [result.overall_score for result in results]
        statuses = {result.overall_status for result in results}
        min_score = min(scores)
        max_score = max(scores)
        score_range = round(max_score - min_score, 2)

        return ParameterSensitivitySummary(
            parameter_name=parameter_name,
            sample_count=len(results),
            min_score=min_score,
            max_score=max_score,
            score_range=score_range,
            stable=score_range <= stable_range,
            status_changed=len(statuses) > 1,
        )

    @staticmethod
    def _status_for_score(definition: CriterionDefinition, score: float) -> EvaluationStatus:
        if score >= definition.pass_threshold:
            return EvaluationStatus.PASS
        if score >= definition.borderline_threshold:
            return EvaluationStatus.BORDERLINE
        return EvaluationStatus.FAIL

    @staticmethod
    def _criterion_score(result: RecommendationEvaluationResult, criterion_name: str) -> float:
        for criterion in result.criteria:
            if criterion.name == criterion_name:
                return criterion.score
        return 0.0
