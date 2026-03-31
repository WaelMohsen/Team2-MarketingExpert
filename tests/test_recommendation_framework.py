from src.evaluation import EvaluationStatus, RecommendationEvaluationFramework


def _criterion_scores(framework: RecommendationEvaluationFramework, overrides=None):
    base_scores = {criterion.name: 4.0 for criterion in framework.criteria}
    if overrides:
        base_scores.update(overrides)

    return [
        framework.score_criterion(
            name=criterion.name,
            score=base_scores[criterion.name],
            rationale=f"{criterion.name} rationale",
            evidence=[f"{criterion.name} evidence"],
        )
        for criterion in framework.criteria
    ]


def test_evaluate_candidate_fails_when_hard_failure_is_present():
    framework = RecommendationEvaluationFramework()

    result = framework.evaluate_candidate(
        "candidate-a",
        _criterion_scores(framework, {"evidence_grounding": 1.5}),
        parameter_settings={"temperature": 0.2},
    )

    assert result.overall_status == EvaluationStatus.FAIL
    assert result.trace["hard_failures_present"] is True


def test_compare_results_orders_by_status_then_score():
    framework = RecommendationEvaluationFramework()

    passing_result = framework.evaluate_candidate(
        "candidate-pass",
        _criterion_scores(framework, {"clarity": 4.5}),
    )
    borderline_result = framework.evaluate_candidate(
        "candidate-borderline",
        _criterion_scores(framework, {"clarity": 3.0, "expected_impact": 3.0}),
    )

    ranked = framework.compare_results([borderline_result, passing_result])

    assert [result.candidate_id for result in ranked] == ["candidate-pass", "candidate-borderline"]


def test_parameter_sensitivity_summary_detects_instability():
    framework = RecommendationEvaluationFramework()

    stable_candidate = framework.evaluate_candidate(
        "temp-0.0",
        _criterion_scores(framework),
        parameter_settings={"temperature": 0.0},
    )
    unstable_candidate = framework.evaluate_candidate(
        "temp-0.7",
        _criterion_scores(framework, {"problem_relevance": 2.5, "evidence_grounding": 2.5}),
        parameter_settings={"temperature": 0.7},
    )

    summary = framework.summarize_parameter_sensitivity(
        [stable_candidate, unstable_candidate],
        parameter_name="temperature",
        stable_range=0.5,
    )

    assert summary.parameter_name == "temperature"
    assert summary.sample_count == 2
    assert summary.score_range > 0.5
    assert summary.stable is False
    assert summary.status_changed is True
