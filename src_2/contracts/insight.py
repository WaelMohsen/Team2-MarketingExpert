"""Structured output contracts for prompt and future agent analysis."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src_2.domain.models import CampaignType, EntityLevel, EvidenceStatus


class EvidenceReference(BaseModel):
    entity_level: EntityLevel
    entity_id: str
    metric: str
    actual: float | None
    benchmark: float | None = None


class CampaignInsight(BaseModel):
    campaign_id: str
    target_assessment: str
    supporting_evidence: list[EvidenceReference]
    performance_drivers: list[str] = Field(default_factory=list)
    audience_findings: list[str] = Field(default_factory=list)
    creative_findings: list[str] = Field(default_factory=list)
    risks_and_confounders: list[str] = Field(default_factory=list)
    strategic_lesson: str
    next_controlled_test: str | None = None
    evidence_status: EvidenceStatus


class CampaignTypeLesson(BaseModel):
    """Lessons for one known campaign type.

    A list of typed records is used instead of a dictionary with dynamic keys so
    the contract is compatible with OpenAI Structured Outputs.
    """

    campaign_type: CampaignType
    lessons: list[str] = Field(default_factory=list)


class PortfolioInsight(BaseModel):
    cycle_id: str
    repeated_patterns: list[str] = Field(default_factory=list)
    conflicting_results: list[str] = Field(default_factory=list)
    campaign_type_lessons: list[CampaignTypeLesson] = Field(default_factory=list)
    portfolio_risks: list[str] = Field(default_factory=list)
    tests_to_prioritize: list[str] = Field(default_factory=list)
