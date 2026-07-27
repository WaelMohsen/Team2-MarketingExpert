"""Contracts for narrative quality evaluation and its historical record.

These are versioned so historical runs remain comparable over time. The
deterministic consistency layer populates ``consistency_checks``; the (optional,
future) LLM judge layer populates ``criterion_scores`` / ``overall_score``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

EVALUATION_SCHEMA_VERSION = 1


class ConsistencyCheck(BaseModel):
    """One deterministic check of a narrative against its evidence."""

    name: str
    passed: bool
    severity: str = Field(description="'hard' fails the campaign; 'warn' is advisory")
    detail: str = ""


class CriterionScore(BaseModel):
    """One LLM-judge criterion result (populated once the judge is added)."""

    name: str
    score: int = Field(ge=1, le=5)
    weight: float = Field(ge=0, le=1)
    rationale: str = ""


class CampaignEvaluation(BaseModel):
    campaign_id: str
    campaign_name: str
    # Snapshots of what was judged, so the run is self-contained for the
    # historical input/output view even after the live report is gone.
    evidence_summary: dict = Field(default_factory=dict)
    narrative: dict = Field(default_factory=dict)
    consistency_checks: list[ConsistencyCheck] = Field(default_factory=list)
    consistency_passed: bool = True
    criterion_scores: list[CriterionScore] = Field(default_factory=list)
    overall_score: float | None = None


class EvaluationReport(BaseModel):
    schema_version: int = EVALUATION_SCHEMA_VERSION
    run_id: str
    run_timestamp: str
    cycle_id: str
    # Attribution: needed to explain why a trend moved.
    model: str
    prompt_version: str
    generator: str = "openai_narrative"
    judge: str = "deterministic_consistency"
    # Aggregates for the history/trend view.
    campaigns_evaluated: int = 0
    consistency_pass_rate: float = 0.0
    mean_overall_score: float | None = None
    campaign_evaluations: list[CampaignEvaluation] = Field(default_factory=list)
