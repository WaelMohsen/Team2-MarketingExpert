import json
import math
import re
from typing import Any, Dict, List, Optional

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
    severity: str  # "High" | "Medium" | "Low"

    @field_validator("issue", "affected_channel", "metric_impacted", "business_impact")
    @classmethod
    def must_be_english(cls, v: str) -> str:
        return assert_ascii(v)

    @field_validator("severity")
    @classmethod
    def severity_must_be_valid(cls, v: str) -> str:
        if v not in ("High", "Medium", "Low"):
            raise ValueError("severity must be High, Medium, or Low")
        return v


class BusinessRisk(BaseModel):
    risk: str
    financial_impact: str  # must contain a number
    likelihood: str        # "High" | "Medium" | "Low"
    time_horizon: str      # "immediate" | "short-term" | "long-term"

    @field_validator("risk", "financial_impact", "time_horizon")
    @classmethod
    def must_be_english(cls, v: str) -> str:
        return assert_ascii(v)

    @field_validator("financial_impact")
    @classmethod
    def must_have_number(cls, v: str) -> str:
        if not re.search(r"\d", v):
            raise ValueError("financial_impact must contain a numeric figure")
        return v


class RootCauseHypothesis(BaseModel):
    hypothesis: str
    bottleneck_type: str        # "Pre-Click" | "Post-Click" | "Budget" | "None"
    supporting_signals: List[str]
    confidence_rationale: str

    @field_validator("hypothesis", "confidence_rationale")
    @classmethod
    def must_be_english(cls, v: str) -> str:
        return assert_ascii(v)

    @field_validator("bottleneck_type")
    @classmethod
    def must_be_valid(cls, v: str) -> str:
        if v not in ("Pre-Click", "Post-Click", "Budget", "None"):
            raise ValueError("Invalid bottleneck_type")
        return v


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
            raise ValueError("detected_issues must reference at least 2 channels")
        return self


# ─────────────────────────────────────────────
# 3. TARGET-SPECIFIC SUBCLASSES
# ─────────────────────────────────────────────


class AcquisitionAnalysisOutput(AnalysisOutput):
    bottleneck_type: str          # "Pre-Click" | "Post-Click" | "None"
    cvr_vs_benchmark: str         # "above" | "below" | "within"
    recommended_action_type: str  # "Fix landing page" | "Fix creatives" | "Scale"

    @field_validator("bottleneck_type")
    @classmethod
    def bottleneck_valid(cls, v: str) -> str:
        if v not in ("Pre-Click", "Post-Click", "None"):
            raise ValueError("Invalid bottleneck_type")
        return v

    @field_validator("cvr_vs_benchmark")
    @classmethod
    def cvr_valid(cls, v: str) -> str:
        if v not in ("above", "below", "within"):
            raise ValueError("Invalid cvr_vs_benchmark")
        return v


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
    roas_status: str          # "healthy" | "warning" | "critical"
    highest_roas_channel: str
    ltv_cac_ratio: float

    @field_validator("roas_status")
    @classmethod
    def roas_valid(cls, v: str) -> str:
        if v not in ("healthy", "warning", "critical"):
            raise ValueError("Invalid roas_status")
        return v


class SatisfactionAnalysisOutput(AnalysisOutput):
    engagement_status: str     # "high" | "medium" | "low"
    highest_bounce_channel: str
    ad_fatigue_risk: bool

    @field_validator("engagement_status")
    @classmethod
    def engagement_valid(cls, v: str) -> str:
        if v not in ("high", "medium", "low"):
            raise ValueError("Invalid engagement_status")
        return v


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