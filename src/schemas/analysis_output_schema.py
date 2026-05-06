import json
import math
import warnings
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, field_validator, model_validator

from .validators import assert_ascii


# ─────────────────────────────────────────────
# 1. SUB-MODELS
# ─────────────────────────────────────────────


class KeySignal(BaseModel):
    observation: str
    metric_name: str
    actual_value: str
    benchmark_value: str
    channel: Optional[str] = None
    is_positive: bool

    @field_validator("observation", "metric_name", "actual_value", "benchmark_value")
    @classmethod
    def must_be_english(cls, v: str) -> str:
        return assert_ascii(v)


class DetectedIssue(BaseModel):
    issue: str
    affected_channel: str
    metric_impacted: str
    business_impact: str
    severity: Literal["High", "Medium", "Low"]

    @field_validator("issue", "affected_channel", "metric_impacted", "business_impact")
    @classmethod
    def must_be_english(cls, v: str) -> str:
        return assert_ascii(v)


class BusinessRisk(BaseModel):
    risk: str
    financial_impact: str
    likelihood: str        # "High" | "Medium" | "Low"
    time_horizon: str      # "immediate" | "short-term" | "long-term"

    @field_validator("risk", "financial_impact", "time_horizon")
    @classmethod
    def must_be_english(cls, v: str) -> str:
        return assert_ascii(v)


class RootCauseHypothesis(BaseModel):
    hypothesis: str
    bottleneck_type: Literal["Pre-Click", "Post-Click", "Budget", "None"]
    supporting_signals: List[str]
    confidence_rationale: str

    @field_validator("hypothesis", "confidence_rationale")
    @classmethod
    def must_be_english(cls, v: str) -> str:
        return assert_ascii(v)


# ─────────────────────────────────────────────
# 2. MAIN SCHEMA
# ─────────────────────────────────────────────


class AnalysisOutput(BaseModel):
    analysis: str
    key_signals: List[KeySignal]
    detected_issues: List[DetectedIssue]
    root_cause_hypothesis: RootCauseHypothesis
    business_risks: List[BusinessRisk]
    confidence_score: float

    @field_validator("analysis")
    @classmethod
    def must_be_english(cls, v: str) -> str:
        return assert_ascii(v)

    @model_validator(mode="after")
    def validate_structure(self) -> "AnalysisOutput":
        if not self.analysis.strip():
            raise ValueError("analysis field is empty")
        if not self.root_cause_hypothesis.hypothesis.strip():
            raise ValueError("root_cause_hypothesis is empty")
        if len(self.key_signals) < 2:
            raise ValueError("at least 2 key_signals required")
        channels = {i.affected_channel for i in self.detected_issues}
        if self.detected_issues and len(channels) < 2:
            warnings.warn(
                "detected_issues reference fewer than 2 channels",
                UserWarning,
                stacklevel=2,
            )
        return self


# ─────────────────────────────────────────────
# 3. TARGET-SPECIFIC SUBCLASSES
# ─────────────────────────────────────────────


class AcquisitionAnalysisOutput(AnalysisOutput):
    bottleneck_type: Literal["Pre-Click", "Post-Click", "None"]
    cvr_vs_benchmark: Literal["above", "below", "within"]
    recommended_action_type: str  # "Fix landing page" | "Fix creatives" | "Scale"


class RetentionAnalysisOutput(AnalysisOutput):
    leaky_bucket_detected: bool
    highest_churn_channel: str
    revenue_at_risk: float

    @field_validator("revenue_at_risk")
    @classmethod
    def must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("revenue_at_risk must be positive")
        return v


class RevenueAnalysisOutput(AnalysisOutput):
    roas_status: Literal["healthy", "warning", "critical"]
    highest_roas_channel: str
    ltv_cac_ratio: float


class SatisfactionAnalysisOutput(AnalysisOutput):
    engagement_status: Literal["high", "medium", "low"]
    highest_bounce_channel: str
    ad_fatigue_risk: bool


# ─────────────────────────────────────────────
# 4. REGISTRY + UTILITIES
# ─────────────────────────────────────────────


ANALYSIS_SCHEMA_REGISTRY = {
    "Customer Acquisition":  AcquisitionAnalysisOutput,
    "Customer Retention":    RetentionAnalysisOutput,
    "Revenue Growth":        RevenueAnalysisOutput,
    "Customer Satisfaction": SatisfactionAnalysisOutput,
}


def get_analysis_schema(target: str) -> type[AnalysisOutput]:
    return ANALYSIS_SCHEMA_REGISTRY.get(target, AnalysisOutput)


def _clean_nans(value: Any) -> Any:
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {k: _clean_nans(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean_nans(v) for v in value]
    return value


def validate_analysis_output(
    text: str,
    target: str = "Customer Acquisition"
) -> AnalysisOutput:

    data = _clean_nans(json.loads(text))
    model = get_analysis_schema(target)(**data)

    score = float(model.confidence_score or 0)
    if 0.0 <= score <= 1.0:
        score *= 100.0
    model.confidence_score = round(max(0.0, min(100.0, score)), 2)

    return model