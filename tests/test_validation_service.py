import pandas as pd
import pytest

from src.schemas.analysis_output_schema import AnalysisOutput
from src.schemas.recommendation_output_schema import (
    ExpectedImpact,
    MeasurementPlan,
    RecommendationActionStep,
    RecommendationCard,
    RecommendationOutput,
)
from src.validation import CampaignValidationService, ReportValidationService


def _valid_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "campaign_name": "Launch",
                "date": "2026-03-01",
                "channel": "Email",
                "impressions": 100,
                "clicks": 10,
                "conversions": 2,
                "spend": 50.0,
                "revenue": 200.0,
            }
        ]
    )


def _recommendation_output() -> RecommendationOutput:
    recommendation = RecommendationCard(
        id="REC-01",
        title="Improve onboarding follow-up",
        category="Retention",
        priority="High",
        effort="Medium",
        time_to_see_impact="2 weeks",
        confidence="High",
        whats_happening="Early churn is elevated.",
        evidence=["Week-one churn is above target."],
        what_you_should_do=[
            RecommendationActionStep(
                step="Launch follow-up emails",
                where="CRM",
                how="Send a targeted follow-up sequence to at-risk customers.",
                guardrails=["Avoid spamming inactive users."],
            )
        ],
        why_this_matters="It improves customer retention.",
        expected_impact=ExpectedImpact(
            primary_kpi="Retention rate",
            direction="Increase",
            explanation="At-risk customers receive timely intervention.",
        ),
        dependency_or_risk=["Needs CRM team support."],
        measurement_plan=MeasurementPlan(
            how_to_measure="Compare retention before and after the sequence.",
            success_criteria="Retention improves by 5%.",
            check_timing="2 weeks",
            notes="Review by segment.",
        ),
        owner_suggestion="Lifecycle team",
    )

    return RecommendationOutput(recommendations=[recommendation] * 5)


def test_campaign_validation_detects_explicit_failure_scenarios():
    dataframe = _valid_dataframe()
    dataframe.loc[0, "clicks"] = 120

    result = CampaignValidationService().validate_dataframe(dataframe)

    assert result.is_valid is False
    assert any(issue.code == "clicks_exceed_impressions" for issue in result.errors)


def test_campaign_validation_reports_missing_required_columns():
    dataframe = _valid_dataframe().drop(columns=["revenue"])

    result = CampaignValidationService().validate_dataframe(dataframe)

    assert result.is_valid is False
    assert any(issue.code == "missing_required_column" and issue.field_name == "revenue" for issue in result.errors)


def test_validation_result_raise_for_errors_contains_codes():
    dataframe = _valid_dataframe()
    dataframe.loc[0, "conversions"] = 20

    result = CampaignValidationService().validate_dataframe(dataframe)

    with pytest.raises(ValueError, match="conversions_exceed_clicks"):
        result.raise_for_errors()


def test_report_validation_service_accepts_model_inputs():
    report_validator = ReportValidationService()

    analysis = report_validator.validate_analysis(
        AnalysisOutput(
            analysis="Revenue is stable.",
            key_signals=["Revenue is flat."],
            detected_issues=["Growth stalled."],
            root_cause_hypothesis="The campaign mix is saturated.",
            business_risks=["Pipeline softness."],
            confidence_score=0.75,
        )
    )
    recommendations = report_validator.validate_recommendations(_recommendation_output())

    assert analysis.confidence_score == 75.0
    assert len(recommendations.recommendations) == 5
