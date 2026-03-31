import pandas as pd

from src.metrics import MetricsBundle
from src.preprocessing import PreprocessingResult
from src.pipelines import MarketingPipeline
from src.reporting import MarketingReport
from src.schemas.analysis_output_schema import AnalysisOutput
from src.schemas.recommendation_output_schema import (
    ExpectedImpact,
    MeasurementPlan,
    RecommendationActionStep,
    RecommendationCard,
)
from src.validation import ValidationResult


def _recommendation_card() -> RecommendationCard:
    return RecommendationCard(
        id="REC-01",
        title="Improve retention outreach",
        category="Retention",
        priority="High",
        effort="Medium",
        time_to_see_impact="2 weeks",
        confidence="High",
        whats_happening="Retention is slipping.",
        evidence=["Churn is increasing on one channel."],
        what_you_should_do=[
            RecommendationActionStep(
                step="Launch a follow-up campaign",
                where="CRM",
                how="Segment recent churn-risk users and send a tailored offer.",
                guardrails=["Do not over-discount loyal customers."],
            )
        ],
        why_this_matters="It protects recurring revenue.",
        expected_impact=ExpectedImpact(
            primary_kpi="Retention rate",
            direction="Increase",
            explanation="More at-risk users receive timely follow-up.",
        ),
        dependency_or_risk=["Needs CRM operations support."],
        measurement_plan=MeasurementPlan(
            how_to_measure="Compare retention rates before and after launch.",
            success_criteria="Retention improves by 5%.",
            check_timing="2 weeks",
            notes="Segment by channel.",
        ),
        owner_suggestion="Marketing Ops",
    )


class FakeDataService:
    def __init__(self, dataframe: pd.DataFrame) -> None:
        self.dataframe = dataframe
        self.requested_filepath = None
        self.validated_datasets = []

    def load_raw_dataframe(self, filepath=None) -> pd.DataFrame:
        self.requested_filepath = filepath
        return self.dataframe

    @staticmethod
    def validate_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
        return dataframe


class FakeMetricsService:
    def __init__(self, metrics: MetricsBundle) -> None:
        self.metrics = metrics
        self.calls = []

    def calculate_full(self, dataframe: pd.DataFrame, category: str) -> MetricsBundle:
        self.calls.append((dataframe, category))
        return self.metrics


class FakeReportService:
    def __init__(self, report: MarketingReport) -> None:
        self.report = report
        self.calls = []

    def generate_report(self, dataframe: pd.DataFrame, category: str, metrics: MetricsBundle) -> MarketingReport:
        self.calls.append((dataframe, category, metrics))
        return self.report


class FakePreprocessingService:
    def __init__(self, dataframe: pd.DataFrame) -> None:
        self.dataframe = dataframe
        self.calls = []

    def preprocess(self, raw_dataframe: pd.DataFrame) -> PreprocessingResult:
        self.calls.append(raw_dataframe)
        return PreprocessingResult(
            dataframe=self.dataframe,
            applied_steps=("normalize_strings",),
            row_count_before=len(raw_dataframe),
            row_count_after=len(self.dataframe),
        )


class FakeValidationService:
    def __init__(self) -> None:
        self.calls = []

    def validate_dataframe(self, dataframe: pd.DataFrame) -> ValidationResult:
        self.calls.append(dataframe)
        return ValidationResult()


def test_marketing_pipeline_coordinates_all_services():
    dataframe = pd.DataFrame([{"campaign_name": "Launch"}])
    metrics = MetricsBundle(
        overall={"Campaign Name": "Launch", "Total Revenue": 1000.0},
        per_channel={"Email": {"Campaign Name": "Launch", "Total Revenue": 1000.0}},
    )
    report = MarketingReport(
        category="Revenue Growth",
        analysis=AnalysisOutput(
            analysis="Revenue is growing.",
            key_signals=["Revenue increased week over week."],
            detected_issues=["Growth is concentrated in one channel."],
            root_cause_hypothesis="Email is driving most of the lift.",
            business_risks=["Channel concentration risk."],
            confidence_score=78.0,
        ),
        recommendations=(_recommendation_card(),),
    )

    data_service = FakeDataService(dataframe)
    metrics_service = FakeMetricsService(metrics)
    report_service = FakeReportService(report)
    preprocessing_service = FakePreprocessingService(dataframe)
    validation_service = FakeValidationService()
    pipeline = MarketingPipeline(
        data_service=data_service,
        metrics_service=metrics_service,
        report_service=report_service,
        preprocessing_service=preprocessing_service,
        validation_service=validation_service,
    )

    result = pipeline.run("Revenue Growth", filepath="data/custom.csv")

    assert data_service.requested_filepath == "data/custom.csv"
    assert preprocessing_service.calls[0].equals(dataframe)
    assert validation_service.calls[0].equals(dataframe)
    assert metrics_service.calls[0][1] == "Revenue Growth"
    assert report_service.calls[0][2] == metrics
    assert isinstance(result.correlation_id, str)
    assert len(result.correlation_id) == 12
    assert result.raw_dataset.equals(dataframe)
    assert result.dataset.equals(dataframe)
    assert result.metrics == metrics
    assert result.report == report
    assert result.preprocessing.applied_steps == ("normalize_strings",)
    assert result.input_validation.is_valid is True
