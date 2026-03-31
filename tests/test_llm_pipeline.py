from pathlib import Path

import pandas as pd

from src.config import AppSettings, LLMSettings
from src.llm.pipeline import LLMReportService
from src.schemas.analysis_output_schema import AnalysisOutput
from src.schemas.recommendation_output_schema import (
    ExpectedImpact,
    MeasurementPlan,
    RecommendationActionStep,
    RecommendationCard,
    RecommendationOutput,
)


class _FakeMessage:
    def __init__(self, parsed):
        self.parsed = parsed


class _FakeChoice:
    def __init__(self, parsed):
        self.message = _FakeMessage(parsed)


class _FakeResponse:
    def __init__(self, parsed):
        self.choices = [_FakeChoice(parsed)]


class RecordingOutputWriter:
    def __init__(self) -> None:
        self.saved_output = None

    def save(self, output):
        self.saved_output = output
        return Path("output_log/fake.json")


def _recommendation_card(index: int) -> RecommendationCard:
    return RecommendationCard(
        id=f"RET-{index}",
        title=f"Improve retention outreach {index}",
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


def test_generate_report_persists_parameter_settings(monkeypatch):
    responses = [
        AnalysisOutput(
            analysis="Retention has softened and churn is rising.",
            key_signals=["Retention rate fell week over week."],
            detected_issues=["Churn increased among newer customers."],
            root_cause_hypothesis="Lifecycle follow-up is not engaging at-risk customers quickly enough.",
            business_risks=["Repeat revenue may decline."],
            confidence_score=82.0,
        ),
        RecommendationOutput(recommendations=[_recommendation_card(index) for index in range(1, 6)]),
    ]

    def fake_chat_completion(client, system_text, user_text, response_format, model, temperature):
        return _FakeResponse(responses.pop(0))

    monkeypatch.setattr("src.llm.pipeline.chat_completion", fake_chat_completion)

    writer = RecordingOutputWriter()
    default_settings = AppSettings.default()
    settings = AppSettings(
        paths=default_settings.paths,
        llm=LLMSettings(
            analysis_model="analysis-test-model",
            recommendation_model="recommendation-test-model",
            analysis_temperature=0.1,
            recommendation_temperature=0.6,
        ),
    )
    service = LLMReportService(
        settings=settings,
        client_factory=lambda: object(),
        output_writer=writer,
    )

    dataframe = pd.DataFrame(
        [
            {
                "campaign_name": "Retention Campaign",
                "date": "2026-03-31",
                "channel": "Email",
                "impressions": 1000,
                "clicks": 100,
                "conversions": 10,
                "spend": 250.0,
                "revenue": 1200.0,
            }
        ]
    )
    metrics = {
        "overall": {"Campaign Name": "Retention Campaign", "Total Revenue": 1200.0},
        "per_channel": {"Email": {"Campaign Name": "Retention Campaign", "Total Revenue": 1200.0}},
    }

    service.generate_report(dataframe, "Customer Retention", metrics)

    assert writer.saved_output is not None
    parameter_settings = writer.saved_output["parameter_settings"]
    assert parameter_settings["analysis_model"] == "analysis-test-model"
    assert parameter_settings["recommendation_model"] == "recommendation-test-model"
    assert parameter_settings["analysis_temperature"] == 0.1
    assert parameter_settings["recommendation_temperature"] == 0.6
    assert parameter_settings["category_prompt_path"] == "prompts/customer_retention.md"
    assert parameter_settings["analysis_system_prompt_path"] == "prompts/system_analysis_prompt.md"
    assert parameter_settings["recommendation_system_prompt_path"] == "prompts/recommendation_system_prompt.md"
    assert len(parameter_settings["category_prompt_sha256"]) == 64
    assert len(parameter_settings["analysis_system_prompt_sha256"]) == 64
    assert len(parameter_settings["recommendation_system_prompt_sha256"]) == 64
    assert len(parameter_settings["analysis_system_prompt_rendered_sha256"]) == 64
    assert len(parameter_settings["recommendation_system_prompt_rendered_sha256"]) == 64
