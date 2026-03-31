import json

from src.evaluation import (
    EvaluationStatus,
    RecommendationBenchmarkCandidate,
    RecommendationBenchmarkRepository,
    RecommendationBenchmarkRunner,
)
from src.reporting import MarketingReport
from src.schemas.analysis_output_schema import AnalysisOutput
from src.schemas.recommendation_output_schema import (
    ExpectedImpact,
    MeasurementPlan,
    RecommendationActionStep,
    RecommendationCard,
)


def _recommendation_card(title: str) -> RecommendationCard:
    return RecommendationCard(
        id=title.upper().replace(" ", "-"),
        title=title,
        category="Customer Retention",
        priority="High",
        effort="Medium",
        time_to_see_impact="2 weeks",
        confidence="High",
        whats_happening="Customer retention is weakening and churn is rising.",
        evidence=["Churn rate increased and retention rate declined."],
        what_you_should_do=[
            RecommendationActionStep(
                step="Launch a segmented follow-up campaign",
                where="CRM",
                how="Target churn-risk customers with a win-back and onboarding sequence.",
                guardrails=["Avoid spamming recent purchasers."],
            )
        ],
        why_this_matters="It protects repeat revenue.",
        expected_impact=ExpectedImpact(
            primary_kpi="Retention rate",
            direction="Increase",
            explanation="At-risk customers receive timely intervention.",
        ),
        dependency_or_risk=["Needs lifecycle operations support."],
        measurement_plan=MeasurementPlan(
            how_to_measure="Compare retention before and after the campaign.",
            success_criteria="Retention rate improves by 5%.",
            check_timing="2 weeks",
            notes="Monitor by segment.",
        ),
        owner_suggestion="Lifecycle team",
    )


def _report(*titles: str) -> MarketingReport:
    return MarketingReport(
        category="Customer Retention",
        analysis=AnalysisOutput(
            analysis="Retention has softened and churn is rising.",
            key_signals=["Retention rate fell week over week."],
            detected_issues=["Churn increased among newer customers."],
            root_cause_hypothesis="The onboarding and follow-up journey is not engaging customers quickly enough.",
            business_risks=["Repeat revenue may decline."],
            confidence_score=80.0,
        ),
        recommendations=tuple(_recommendation_card(title) for title in titles),
    )


def test_benchmark_repository_loads_cases(tmp_path):
    benchmark_file = tmp_path / "cases.json"
    benchmark_file.write_text(
        json.dumps(
            [
                {
                    "case_id": "retention-1",
                    "category": "Customer Retention",
                    "description": "Retention case",
                    "expected_problem_terms": ["retention", "churn"],
                    "expected_evidence_terms": ["churn"],
                    "preferred_primary_kpis": ["retention rate"],
                }
            ]
        ),
        encoding="utf-8",
    )

    repository = RecommendationBenchmarkRepository(benchmark_file=benchmark_file)
    cases = repository.load_cases()

    assert len(cases) == 1
    assert cases[0].case_id == "retention-1"


def test_benchmark_runner_ranks_stronger_candidate_higher():
    case = RecommendationBenchmarkRepository().load_cases()[1]
    runner = RecommendationBenchmarkRunner()

    stronger = RecommendationBenchmarkCandidate(
        candidate_id="stronger",
        report=_report(
            "Launch segmented follow-up campaign",
            "Improve onboarding win-back flow",
            "Refine churn-risk segment targeting",
            "Test retention offer timing",
            "Strengthen post-purchase follow-up",
        ),
        parameter_settings={"temperature": 0.2},
    )
    weaker = RecommendationBenchmarkCandidate(
        candidate_id="weaker",
        report=_report(
            "General campaign refresh",
            "General campaign refresh",
            "General campaign refresh",
            "General campaign refresh",
            "General campaign refresh",
        ),
        parameter_settings={"temperature": 0.7},
    )

    result = runner.run_case(case, [weaker, stronger])

    assert result.ranked_results[0].candidate_id == "stronger"
    assert result.ranked_results[0].overall_status in {EvaluationStatus.PASS, EvaluationStatus.BORDERLINE}
    assert result.sensitivity_summary is not None
    assert result.sensitivity_summary.sample_count == 2
