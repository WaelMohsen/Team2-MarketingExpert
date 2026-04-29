from unittest.mock import MagicMock

import pytest

from src.evaluation.analysis.evaluator import AnalysisQualityEvaluator
from src.schemas.analysis_output_schema import AnalysisOutput


def _sample_analysis() -> AnalysisOutput:
    return AnalysisOutput(
        analysis=("Campaign performance is declining due to weak audience relevance."),
        key_signals=["Clicks dropped from 12000 to 4500"],
        detected_issues=["High bounce rate and low conversion"],
        root_cause_hypothesis=(
            "Audience targeting is misaligned with landing page message."
        ),
        business_risks=["Continued spend inefficiency and revenue loss"],
        confidence_score=78.0,
    )


def _verdict(scores: dict, explanations: dict):
    response = MagicMock()
    parsed = MagicMock()
    parsed.scores.dict.return_value = scores
    parsed.explanations.dict.return_value = explanations
    response.choices = [MagicMock(message=MagicMock(parsed=parsed))]
    return response


def _mock_logger(path: str = "evaluation_logs/analysis/eval_1.json"):
    logger = MagicMock()
    logger.log.return_value = path
    return logger


def test_analysis_quality_evaluator_returns_weighted_score_and_no_flags(
    monkeypatch,
):
    scores = {
        "clarity": 0.8,
        "data_grounding": 0.9,
        "logic_coherence": 0.8,
        "business_focus": 0.7,
        "confidence_calibration": 0.8,
        "no_recommendation": 0.95,
    }
    explanations = dict.fromkeys(scores, "ok")

    module_path = "src.evaluation.analysis.evaluator.chat_completion"
    monkeypatch.setattr(module_path, lambda **kwargs: _verdict(scores, explanations))

    logger = _mock_logger()
    evaluator = AnalysisQualityEvaluator(client=object(), logger=logger)
    result = evaluator.evaluate(_sample_analysis(), "campaign context")

    expected = (
        0.8 * 0.18 + 0.9 * 0.20 + 0.8 * 0.20 + 0.7 * 0.15 + 0.8 * 0.12 + 0.95 * 0.15
    )

    assert result["score"] == round(expected, 3)
    assert result["flags"] == []
    assert result["dimensions"]["no_recommendation"] == pytest.approx(0.95)
    assert result["log_file"] == "evaluation_logs/analysis/eval_1.json"
    logger.log.assert_called_once()


def test_analysis_quality_evaluator_flags_recommendation_language(monkeypatch):
    scores = {
        "clarity": 0.7,
        "data_grounding": 0.75,
        "logic_coherence": 0.7,
        "business_focus": 0.7,
        "confidence_calibration": 0.7,
        "no_recommendation": 0.4,
    }
    explanations = dict.fromkeys(scores, "ok")

    module_path = "src.evaluation.analysis.evaluator.chat_completion"
    monkeypatch.setattr(module_path, lambda **kwargs: _verdict(scores, explanations))

    logger = _mock_logger()
    evaluator = AnalysisQualityEvaluator(client=object(), logger=logger)
    result = evaluator.evaluate(_sample_analysis(), "campaign context")

    assert "low_no_recommendation" in result["flags"]
    assert "analysis_contains_recommendations" in result["flags"]
    assert result["log_file"] == "evaluation_logs/analysis/eval_1.json"
    logger.log.assert_called_once()


def test_analysis_quality_evaluator_llm_failure_fallback(monkeypatch):
    module_path = "src.evaluation.analysis.evaluator.chat_completion"

    def _raise(**kwargs):
        raise RuntimeError("model down")

    monkeypatch.setattr(module_path, _raise)

    logger = _mock_logger()
    evaluator = AnalysisQualityEvaluator(client=object(), logger=logger)
    result = evaluator.evaluate(_sample_analysis(), "campaign context")

    assert result["score"] == 0
    assert result["error"] == "llm_failed"
    assert result["flags"] == ["llm_failed"]
    assert result["log_file"] == "evaluation_logs/analysis/eval_1.json"
    logger.log.assert_called_once()
