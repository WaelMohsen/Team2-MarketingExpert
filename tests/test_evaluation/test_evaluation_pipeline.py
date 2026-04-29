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
    mock_rec_evaluator = MagicMock()
    mock_rec_evaluator.evaluate.return_value = rec_result or {
        "category": "acquisition",
        "campaign_id": "Spring Launch",
        "target": "customer_acquisition",
        "final_score": 0.8,
    }

    mock_analysis_evaluator = MagicMock()
    mock_analysis_model = MagicMock()
    mock_analysis_model.model_dump.return_value = analysis_result or {
        "overall_score": 4,
        "overall_status": "pass",
        "criteria_scores": [],
        "summary": "Good analysis.",
        "improvement_suggestions": [],
    }
    mock_analysis_evaluator.evaluate.return_value = mock_analysis_model
    mock_ground_truth_loader = MagicMock()
    mock_ground_truth_loader.load_ground_truth.return_value = []

    pipeline = EvaluationPipeline(
        recommendation_evaluator=mock_rec_evaluator,
        ground_truth_loader=mock_ground_truth_loader,
        analysis_evaluator=mock_analysis_evaluator,
    )
    return (
        pipeline,
        mock_rec_evaluator,
        mock_analysis_evaluator,
        mock_ground_truth_loader,
    )


def test_run_recommendation_passes_campaign_metadata():
    pipeline, mock_rec, _, mock_ground_truth_loader = _make_pipeline()
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
    mock_ground_truth_loader.load_ground_truth.assert_called_once_with(
        "Spring Launch", "customer_acquisition"
    )
    assert call_args["campaign_id"] == "Spring Launch"
    assert call_args["target"] == "customer_acquisition"
    assert call_args["category"] == "acquisition"


def test_run_analysis_attaches_campaign_metadata():
    pipeline, _, mock_analysis, _ = _make_pipeline()
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


def test_run_analysis_accepts_dict_input():
    pipeline, _, mock_analysis, _ = _make_pipeline()
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


def test_run_all_merges_metadata_into_analysis_result():
    pipeline, mock_rec, mock_analysis, _ = _make_pipeline()
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
    """EvaluationPipeline.__init__ must not call analysis factory eagerly."""
    mock_rec_evaluator = MagicMock()
    mock_ground_truth_loader = MagicMock()
    analysis_factory = MagicMock(return_value=MagicMock())

    pipeline = EvaluationPipeline(
        recommendation_evaluator=mock_rec_evaluator,
        ground_truth_loader=mock_ground_truth_loader,
        analysis_evaluator_factory=analysis_factory,
    )
    analysis_factory.assert_not_called()

    _ = pipeline.analysis_evaluator
    analysis_factory.assert_called_once()


def test_injected_analysis_evaluator_used_directly():
    """An injected analysis_evaluator is used as-is without instantiating a new one."""
    mock_rec_evaluator = MagicMock()
    mock_ground_truth_loader = MagicMock()
    custom_evaluator = MagicMock()
    analysis_factory = MagicMock()

    pipeline = EvaluationPipeline(
        recommendation_evaluator=mock_rec_evaluator,
        ground_truth_loader=mock_ground_truth_loader,
        analysis_evaluator=custom_evaluator,
        analysis_evaluator_factory=analysis_factory,
    )
    _ = pipeline.analysis_evaluator
    analysis_factory.assert_not_called()

    assert pipeline.analysis_evaluator is custom_evaluator
