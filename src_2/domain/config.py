"""Pydantic contracts for human-editable YAML policy."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import BudgetPool, CampaignType


class GuardrailConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    operator: Literal[
        "greater_than",
        "greater_than_or_equal",
        "less_than_or_equal",
        "within",
        "benchmark",
    ]
    value: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    benchmark_strategy: str | None = None
    required_for: list[str] = Field(default_factory=list)


class AllocationMetricConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    direction: Literal["higher", "lower"]


class ScoreMetricConfig(BaseModel):
    """Sufficient-statistic definition for a small-sample corrected score."""

    model_config = ConfigDict(extra="forbid")

    metric: str
    numerator: str
    denominator: str
    direction: Literal["higher", "lower"]
    model: Literal["beta_binomial"] = "beta_binomial"
    practical_lift_threshold: float = Field(default=0.0, ge=0, le=1)


class CampaignTypeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_job: str
    success_question: str
    primary_kpis: list[str] = Field(min_length=1)
    supporting_kpis: list[str] = Field(default_factory=list)
    guardrails: list[GuardrailConfig] = Field(default_factory=list)
    allocation_metric: AllocationMetricConfig
    score_metric: ScoreMetricConfig
    budget_pool: BudgetPool = BudgetPool.CORE
    analysis_guidance: list[str] = Field(default_factory=list)


class CampaignTypeRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    benchmark_fallback_order: list[str] = Field(min_length=1)
    campaign_types: dict[CampaignType, CampaignTypeConfig]

    @model_validator(mode="after")
    def require_all_campaign_types(self) -> "CampaignTypeRegistry":
        missing = set(CampaignType) - set(self.campaign_types)
        if missing:
            names = ", ".join(sorted(item.value for item in missing))
            raise ValueError(f"Missing campaign type configuration: {names}")
        return self


class EnvelopeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str
    campaign_type: CampaignType | None = None


class BudgetPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    budget_units: float = Field(gt=0)
    exploit_share: float = Field(default=0.7, ge=0, le=1)
    explore_share: float = Field(default=0.3, ge=0, le=1)
    campaign_type_envelopes: EnvelopeConfig
    test_envelope: EnvelopeConfig
    maximum_campaign_concentration: float | None = Field(default=None, gt=0, le=1)
    allow_unallocated_budget: bool = True
    allow_limited_evidence_scenarios: bool = True
    action_eligibility: dict[str, list[str]]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_complete_split(self) -> "BudgetPolicy":
        if abs(self.exploit_share + self.explore_share - 1.0) > 1e-9:
            raise ValueError("exploit_share and explore_share must sum to 1")
        return self
