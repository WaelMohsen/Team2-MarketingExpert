"""Evidence supplied to prompts or future agents."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src_2.domain.models import CampaignType, EntityLevel, EvidenceStatus


class MetricEvidence(BaseModel):
    metric: str
    label: str
    actual: float | None
    benchmark: float | None
    benchmark_source: str | None
    direction: Literal["higher", "lower", "range"]
    passed: bool | None
    evidence_count: int | None = Field(default=None, ge=0)


class EntityEvidence(BaseModel):
    entity_level: EntityLevel
    entity_id: str
    entity_name: str
    metrics: list[MetricEvidence]
    dimensions: dict[str, Any] = Field(default_factory=dict)


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
