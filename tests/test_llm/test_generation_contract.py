from types import SimpleNamespace

import pytest

from src.evaluation.run_config import (
    EvaluationConfig,
    GenerationConfig,
    RunConfig,
    RuntimeConfig,
)
from src.llm.client import llm_callable
from src.llm.pipeline import generate_response


def _run_config() -> RunConfig:
    return RunConfig(
        runtime=RuntimeConfig(
            campaign_id="Spring Launch", category=None, context_rows=10
        ),
        generation=GenerationConfig(
            analysis_model="analysis-default",
            analysis_temp=0.2,
            recommendation_model="recommendation-default",
            recommendation_temp=0.3,
        ),
        evaluation=EvaluationConfig(
            analysis_judge_model="judge-analysis",
            analysis_judge_temp=0.1,
            recommendation_judge_model="judge-recommendation",
            recommendation_judge_temp=0.1,
        ),
    )


def test_llm_callable_uses_config_defaults(monkeypatch):
    captured = {}

    class _FakeCompletions:
        def create(self, model, messages, temperature):
            captured["model"] = model
            captured["messages"] = messages
            captured["temperature"] = temperature
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions()))

    monkeypatch.setattr("src.llm.client.load_run_config", _run_config)
    monkeypatch.setattr("src.llm.client.get_client", lambda: fake_client)

    result = llm_callable("hello")

    assert result == "ok"
    assert captured["model"] == "recommendation-default"
    assert captured["temperature"] == 0.3


def test_generate_response_uses_config_defaults(monkeypatch):
    analysis_parsed = SimpleNamespace(
        model_dump=lambda: {
            "analysis": "A",
            "key_signals": ["K"],
            "detected_issues": ["I"],
            "root_cause_hypothesis": "R",
            "business_risks": ["B"],
            "confidence_score": 85.0,
        }
    )
    recommendation_card = SimpleNamespace(model_dump=lambda: {"title": "Rec 1"})
    recommendation_parsed = SimpleNamespace(
        model_dump=lambda: {"recommendations": [{"title": "Rec 1"}]},
        recommendations=[recommendation_card],
    )
    responses = [
        SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(parsed=analysis_parsed))]
        ),
        SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(parsed=recommendation_parsed))
            ]
        ),
    ]
    captured = []

    monkeypatch.setattr("src.llm.pipeline.load_run_config", _run_config)
    monkeypatch.setattr("src.llm.pipeline.get_client", lambda: object())
    monkeypatch.setattr(
        "src.llm.pipeline.chat_completion",
        lambda client, system_text, user_text, response_format, model, temp: (
            captured.append((model, temp)) or responses.pop(0)
        ),
    )
    monkeypatch.setattr(
        "src.llm.pipeline.analysis_system_prompt", lambda *args: "sys-a"
    )
    monkeypatch.setattr(
        "src.llm.pipeline.build_analysis_user_prompt", lambda context: "user-a"
    )
    monkeypatch.setattr(
        "src.llm.pipeline.recommendation_system_prompt", lambda *args: "sys-r"
    )
    monkeypatch.setattr(
        "src.llm.pipeline.build_recommendation_user_prompt",
        lambda context_block, analysis_input: "user-r",
    )
    monkeypatch.setattr(
        "src.llm.pipeline.build_context_block", lambda category, df, metrics: "ctx"
    )
    monkeypatch.setattr(
        "src.llm.pipeline.validate_analysis_output", lambda payload: analysis_parsed
    )
    monkeypatch.setattr(
        "src.llm.pipeline.validate_recommendation_output",
        lambda payload: recommendation_parsed,
    )
    monkeypatch.setattr("src.llm.pipeline.save_output", lambda output: None)

    result = generate_response(
        df="df", category="Customer Acquisition", metrics={"overall": {"CTR": 1}}
    )

    assert result["analysis"]["analysis"] == "A"
    assert result["recommendations"] == [{"title": "Rec 1"}]
    assert captured == [
        ("analysis-default", 0.2),
        ("recommendation-default", 0.3),
    ]


def test_generate_response_raises_instead_of_returning_error_string(monkeypatch):
    monkeypatch.setattr("src.llm.pipeline.load_run_config", _run_config)
    monkeypatch.setattr(
        "src.llm.pipeline.get_client",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(RuntimeError, match="boom"):
        generate_response(df="df", category="Customer Acquisition", metrics={})
