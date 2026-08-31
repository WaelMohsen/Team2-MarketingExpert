"""Evidence supplied to prompts or future agents."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src_2.domain.models import (
    CampaignType,
    EntityLevel,
    EvidenceStatus,
    FundingDecision,
)


class EmpiricalBayesScore(BaseModel):
    """Reviewable small-sample score and comparison to its learned peer prior."""

    metric: str
    numerator: str
    denominator: str
    direction: Literal["higher", "lower"]
    successes: float = Field(ge=0)
    trials: float = Field(ge=0)
    raw_score: float | None = Field(default=None, ge=0, le=1)
    corrected_score: float | None = Field(default=None, ge=0, le=1)
    corrected_score_low: float | None = Field(default=None, ge=0, le=1)
    corrected_score_high: float | None = Field(default=None, ge=0, le=1)
    benchmark_score: float | None = Field(default=None, ge=0, le=1)
    benchmark_low: float | None = Field(default=None, ge=0, le=1)
    benchmark_high: float | None = Field(default=None, ge=0, le=1)
    benchmark_source: str | None = None
    benchmark_peer_count: int = Field(default=0, ge=0)
    prior_alpha: float | None = Field(default=None, gt=0)
    prior_beta: float | None = Field(default=None, gt=0)
    prior_strength: float | None = Field(default=None, gt=0)
    expected_lift: float | None = None
    lift_low: float | None = None
    lift_high: float | None = None
    probability_better: float | None = Field(default=None, ge=0, le=1)
    practical_lift_threshold: float = Field(default=0, ge=0, le=1)
    decision: FundingDecision
    interval_method: str | None = None


class MetricEvidence(BaseModel):
    metric: str
    label: str
    actual: float | None
    benchmark: float | None
    benchmark_source: str | None
    direction: Literal["higher", "lower", "range"]
    passed: bool | None
    evidence_count: int | None = Field(default=None, ge=0)
    confidence_interval_low: float | None = None
    confidence_interval_high: float | None = None
    interval_method: str | None = None
    comparison_conclusive: bool | None = None


class EntityEvidence(BaseModel):
    entity_level: EntityLevel
    entity_id: str
    entity_name: str
    metrics: list[MetricEvidence]
    dimensions: dict[str, Any] = Field(default_factory=dict)
    decision_score: EmpiricalBayesScore | None = None


class CampaignEvidencePack(BaseModel):
    cycle_id: str
    campaign_id: str
    campaign_name: str
    campaign_type: CampaignType
    business_job: str
    success_question: str
    evidence_status: EvidenceStatus
    primary_kpis: list[MetricEvidence]
    supporting_kpis: list[MetricEvidence]
    guardrails: list[MetricEvidence]
    campaign: EntityEvidence
    adsets: list[EntityEvidence] = Field(default_factory=list)
    ads: list[EntityEvidence] = Field(default_factory=list)
    creatives: list[EntityEvidence] = Field(default_factory=list)
    audiences: list[EntityEvidence] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    # Decision-grade allocation-KPI evidence (benchmark + direction-correct pass/fail),
    # so a CampaignAssessor can reproduce the funding decision from the pack alone.
    allocation_kpi: MetricEvidence | None = None
    decision_score: EmpiricalBayesScore | None = None
