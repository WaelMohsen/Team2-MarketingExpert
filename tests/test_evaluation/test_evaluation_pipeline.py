"""Tests for EvaluationPipeline: metadata propagation, lazy evaluator init, dict/model input."""

from unittest.mock import MagicMock, patch

import pytest

from src.evaluation.evaluation_pipeline import EvaluationPipeline
from src.schemas.analysis_output_schema import AnalysisOutput


def _sample_analysis_output():
    return AnalysisOutput(
        analysis="Campaign shows declining returns.",
        key_signals=["Revenue down 15%"],
        detected_issues=["High churn rate"],
        root_cause_hypothesis="Audience fatigue.",
        business_risks=["Revenue loss"],
        confidence_score=72.0,
    )


def _make_pipeline(rec_result=None, analysis_result=None):
    mock_llm = MagicMock()
    mock_embed = MagicMock()

    mock_rec_evaluator = MagicMock()
    mock_rec_evaluator.evaluate.return_value = rec_result or {
        "category": "acquisition",
        "campaign_id": "Spring Launch",
        "target": "customer_acquisition",
        "final_score": 0.8,
    }

    mock_analysis_evaluator = MagicMock()
    mock_analysis_evaluator.evaluate.return_value = analysis_result or {
        "category": "acquisition",
        "score": 0.75,
        "flags": [],
    }

    pipeline = EvaluationPipeline(
        mock_llm, mock_embed, analysis_evaluator=mock_analysis_evaluator
    )
    pipeline.recommendation_evaluator = mock_rec_evaluator
    return pipeline, mock_rec_evaluator, mock_analysis_evaluator


@patch(
    "src.evaluation.evaluation_pipeline.EvaluationPipeline.load_ground_truth",
    return_value=[],
)
def test_run_recommendation_passes_campaign_metadata(mock_gt):
    pipeline, mock_rec, _ = _make_pipeline()
    analysis = _sample_analysis_output()

    pipeline.run_recommendation(
        campaign_id="Spring Launch",
        target="customer_acquisition",
        analysis_output=analysis,
        recommendation_output=[{"action": "x"}],
        kpis=["revenue"],
        category="acquisition",
    )

    call_args = mock_rec.evaluate.call_args[0][0]
    assert call_args["campaign_id"] == "Spring Launch"
    assert call_args["target"] == "customer_acquisition"
    assert call_args["category"] == "acquisition"


@patch(
    "src.evaluation.evaluation_pipeline.EvaluationPipeline.load_ground_truth",
    return_value=[],
)
def test_run_analysis_attaches_campaign_metadata(mock_gt):
    pipeline, _, mock_analysis = _make_pipeline()
    analysis = _sample_analysis_output()

    result = pipeline.run_analysis(
        analysis_output=analysis,
        campaign_context="Some context",
        category="acquisition",
        campaign_id="Spring Launch",
        target="customer_acquisition",
    )

    assert result["campaign_id"] == "Spring Launch"
    assert result["target"] == "customer_acquisition"


@patch(
    "src.evaluation.evaluation_pipeline.EvaluationPipeline.load_ground_truth",
    return_value=[],
)
def test_run_analysis_accepts_dict_input(mock_gt):
    pipeline, _, mock_analysis = _make_pipeline()
    analysis_dict = {
        "analysis": "Revenue is dropping.",
        "key_signals": ["Revenue down"],
        "detected_issues": ["Churn"],
        "root_cause_hypothesis": "Fatigue",
        "business_risks": ["Loss"],
        "confidence_score": 60.0,
    }

    result = pipeline.run_analysis(
        analysis_output=analysis_dict,
        category="retention",
        campaign_id="Q1",
        target="customer_retention",
    )

    assert result["campaign_id"] == "Q1"
    mock_analysis.evaluate.assert_called_once()


@patch(
    "src.evaluation.evaluation_pipeline.EvaluationPipeline.load_ground_truth",
    return_value=[],
)
def test_run_all_merges_metadata_into_analysis_result(mock_gt):
    pipeline, mock_rec, mock_analysis = _make_pipeline()
    analysis = _sample_analysis_output()

    result = pipeline.run_all(
        campaign_id="Spring Launch",
        target="customer_acquisition",
        analysis_output=analysis,
        recommendation_output=[],
        kpis=[],
        category="acquisition",
    )

    assert "recommendation_evaluation" in result
    assert "analysis_evaluation" in result
    assert result["analysis_evaluation"]["campaign_id"] == "Spring Launch"
    assert result["analysis_evaluation"]["target"] == "customer_acquisition"


def test_analysis_evaluator_not_instantiated_on_init():
    """EvaluationPipeline.__init__ must not call AnalysisQualityEvaluator eagerly."""
    mock_llm = MagicMock()
    mock_embed = MagicMock()

    with patch(
        "src.evaluation.evaluation_pipeline.AnalysisQualityEvaluator"
    ) as mock_cls:
        pipeline = EvaluationPipeline(mock_llm, mock_embed)
        mock_cls.assert_not_called()

        # Accessing the property triggers lazy creation
        _ = pipeline.analysis_evaluator
        mock_cls.assert_called_once()


def test_injected_analysis_evaluator_used_directly():
    """An injected analysis_evaluator is used as-is without instantiating a new one."""
    mock_llm = MagicMock()
    mock_embed = MagicMock()
    custom_evaluator = MagicMock()

    with patch(
        "src.evaluation.evaluation_pipeline.AnalysisQualityEvaluator"
    ) as mock_cls:
        pipeline = EvaluationPipeline(
            mock_llm, mock_embed, analysis_evaluator=custom_evaluator
        )
        _ = pipeline.analysis_evaluator
        mock_cls.assert_not_called()

    assert pipeline.analysis_evaluator is custom_evaluator
