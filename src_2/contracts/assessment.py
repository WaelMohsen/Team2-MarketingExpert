"""Deterministic campaign assessment contract."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src_2.domain.assessment_rules import NextCycleAction, TargetStatus
from src_2.domain.models import CampaignType, EvidenceStatus


class MetricAssessment(BaseModel):
    metric: str
    actual: float | None
    benchmark: float | None
    passed: bool | None
    reason: str


class CampaignAssessment(BaseModel):
    cycle_id: str
    campaign_id: str
    campaign_name: str
    campaign_type: CampaignType
    target_status: TargetStatus
    next_cycle_action: NextCycleAction
    evidence_status: EvidenceStatus
    primary_results: list[MetricAssessment]
    guardrail_results: list[MetricAssessment]
    reason_codes: list[str] = Field(default_factory=list)
