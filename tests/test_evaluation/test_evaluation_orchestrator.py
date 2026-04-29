from unittest.mock import MagicMock, patch

from src.evaluation.contracts import EvaluationRequest, EvaluationResult
from src.evaluation.orchestrator import EvaluationOrchestrator
from src.schemas.analysis_output_schema import AnalysisOutput


def _sample_analysis() -> AnalysisOutput:
    return AnalysisOutput(
        analysis="Campaign performance is declining.",
        key_signals=["Revenue dropped 15%"],
        detected_issues=["Audience fatigue"],
        root_cause_hypothesis="Creative message is stale.",
        business_risks=["Lower growth and wasted spend"],
        confidence_score=72.0,
    )


def _request() -> EvaluationRequest:
    return EvaluationRequest(
        campaign_id="Spring Launch",
        target="Customer Acquisition",
        category="Customer Acquisition",
        campaign_context='[{"spend": 1000}]',
        analysis_output=_sample_analysis(),
        recommendation_output=[{"title": "Refresh creative"}],
        kpis=["revenue"],
    )


def test_run_request_returns_evaluation_result():
    analysis_evaluator = MagicMock()
    recommendation_evaluator = MagicMock()
    analysis_evaluator.evaluate.return_value = {"score": 0.81, "flags": []}
    recommendation_evaluator.evaluate.return_value = {"final_score": 0.77}

    orchestrator = EvaluationOrchestrator(
        llm_callable=MagicMock(),
        embedding_callable=MagicMock(),
        analysis_evaluator=analysis_evaluator,
        recommendation_evaluator=recommendation_evaluator,
    )

    with patch.object(orchestrator, "load_ground_truth", return_value=[]):
        result = orchestrator.run_request(_request())

    assert isinstance(result, EvaluationResult)
    assert result.campaign_id == "Spring Launch"
    assert result.target == "Customer Acquisition"
    assert result.category == "Customer Acquisition"
    assert result.analysis_result["campaign_id"] == "Spring Launch"
    assert result.analysis_result["target"] == "Customer Acquisition"
    assert result.recommendation_result["final_score"] == 0.77


def test_run_all_returns_legacy_dict_shape():
    analysis_evaluator = MagicMock()
    recommendation_evaluator = MagicMock()
    analysis_evaluator.evaluate.return_value = {"score": 0.81, "flags": []}
    recommendation_evaluator.evaluate.return_value = {"final_score": 0.77}

    orchestrator = EvaluationOrchestrator(
        llm_callable=MagicMock(),
        embedding_callable=MagicMock(),
        analysis_evaluator=analysis_evaluator,
        recommendation_evaluator=recommendation_evaluator,
    )

    req = _request()
    with patch.object(orchestrator, "load_ground_truth", return_value=[]):
        result = orchestrator.run_all(
            campaign_id=req.campaign_id,
            target=req.target,
            analysis_output=req.analysis_output,
            recommendation_output=req.recommendation_output,
            kpis=req.kpis,
            campaign_context=req.campaign_context,
            category=req.category,
        )

    assert "analysis_evaluation" in result
    assert "recommendation_evaluation" in result
    assert result["campaign_id"] == "Spring Launch"
    assert result["target"] == "Customer Acquisition"


def test_run_request_can_skip_analysis():
    analysis_evaluator = MagicMock()
    recommendation_evaluator = MagicMock()
    recommendation_evaluator.evaluate.return_value = {"final_score": 0.77}

    orchestrator = EvaluationOrchestrator(
        llm_callable=MagicMock(),
        embedding_callable=MagicMock(),
        analysis_evaluator=analysis_evaluator,
        recommendation_evaluator=recommendation_evaluator,
    )

    with patch.object(orchestrator, "load_ground_truth", return_value=[]):
        result = orchestrator.run_request(_request(), include_analysis=False)

    assert result.analysis_result is None
    assert result.recommendation_result["final_score"] == 0.77
    analysis_evaluator.evaluate.assert_not_called()
