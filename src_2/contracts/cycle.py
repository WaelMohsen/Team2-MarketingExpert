"""Cycle-level input and data-quality contracts."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from src_2.domain.models import EvidenceStatus


class CycleManifest(BaseModel):
    cycle_id: str
    extracted_at: datetime
    reporting_start: date
    reporting_end: date
    currency: str
    timezone: str
    input_directory: str


class DataQualityReport(BaseModel):
    status: EvidenceStatus
    meta_conversation_starts: int = Field(ge=0)
    observed_meta_whatsapp_conversations: int = Field(ge=0)
    reconciliation_ratio: float | None = Field(default=None, ge=0)
    event_definitions_reconciled: bool = False
    unmatched_campaigns: int = Field(default=0, ge=0)
    unmatched_adsets: int = Field(default=0, ge=0)
    unmatched_ads: int = Field(default=0, ge=0)
    open_or_pending_conversations: int = Field(default=0, ge=0)
    repeated_customers: int = Field(default=0, ge=0)
    organic_direct_conversations: int = Field(default=0, ge=0)
    reach_exceeds_impressions_rows: int = Field(default=0, ge=0)
    daily_reach_is_non_additive: bool = True
    warnings: list[str] = Field(default_factory=list)
