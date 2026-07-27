"""Completed-cycle reporting use case."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src_2.analytics import (
    CycleScorecards,
    DeterministicBudgetAllocator,
    DeterministicCampaignAssessor,
    build_evidence_packs,
    build_scorecards,
    enrich_scorecards,
)
from src_2.application.ports import (
    BudgetAllocator,
    CampaignAnalyst,
    CampaignAssessor,
    PortfolioSynthesizer,
    ReportNarrator,
)
from src_2.contracts import (
    BudgetScenario,
    CampaignAssessment,
    CampaignEvidencePack,
    CampaignInsight,
    CycleManifest,
    DataQualityReport,
    PortfolioInsight,
    StakeholderReport,
)
from src_2.infrastructure.configuration import (
    load_budget_policy,
    load_campaign_type_registry,
)
from src_2.ingestion import (
    CanonicalCycleData,
    build_data_quality_report,
    load_sample2,
    normalize_cycle,
)
from src_2.intelligence import (
    OpenAICampaignAnalyst,
    OpenAIPortfolioSynthesizer,
    OpenAIReportNarrator,
)


def _records(frame: pd.DataFrame) -> list[dict]:
    return json.loads(frame.to_json(orient="records", date_format="iso"))


@dataclass(frozen=True)
class CompletedCycleReport:
    manifest: CycleManifest
    data_quality: DataQualityReport
    canonical_data: CanonicalCycleData
    scorecards: CycleScorecards
    evidence_packs: list[CampaignEvidencePack]
    assessments: list[CampaignAssessment]
    insights: list[CampaignInsight]
    portfolio_insight: PortfolioInsight
    budget_scenario: BudgetScenario
    stakeholder_report: StakeholderReport

    def campaign_evidence(self, campaign_id: str) -> CampaignEvidencePack:
        return next(
            item for item in self.evidence_packs if item.campaign_id == campaign_id
        )

    def campaign_insight(self, campaign_id: str) -> CampaignInsight:
        return next(item for item in self.insights if item.campaign_id == campaign_id)

    def to_export_dict(self) -> dict:
        return {
            "manifest": self.manifest.model_dump(mode="json"),
            "data_quality": self.data_quality.model_dump(mode="json"),
            "assessments": [item.model_dump(mode="json") for item in self.assessments],
            "insights": [item.model_dump(mode="json") for item in self.insights],
            "portfolio_insight": self.portfolio_insight.model_dump(mode="json"),
            "budget_scenario": self.budget_scenario.model_dump(mode="json"),
            "stakeholder_report": self.stakeholder_report.model_dump(mode="json"),
            "scorecards": {
                level: _records(self.scorecards.by_level(level))
                for level in ("campaign", "adset", "ad", "creative", "audience")
            },
        }


def _manifest(data: CanonicalCycleData) -> CycleManifest:
    start = data.cycle_start
    end = data.cycle_end
    if start is None or end is None:
        raise ValueError("A completed cycle requires at least one dated insight row")
    cycle_id = f"cycle_{start.date().isoformat()}_{end.date().isoformat()}"
    return CycleManifest(
        cycle_id=cycle_id,
        extracted_at=datetime.now(timezone.utc),
        reporting_start=start.date(),
        reporting_end=end.date(),
        currency="EGP",
        timezone="Africa/Cairo",
        input_directory=data.source_directory,
    )


def run_completed_cycle(
    input_directory: str | Path | None = None,
    *,
    campaign_assessor: CampaignAssessor | None = None,
    budget_allocator: BudgetAllocator | None = None,
    campaign_analyst: CampaignAnalyst | None = None,
    portfolio_synthesizer: PortfolioSynthesizer | None = None,
    report_narrator: ReportNarrator | None = None,
) -> CompletedCycleReport:
    """Run the pipeline: deterministic measurement → decisions → LLM narrative.

    Stages sit behind ports:
      * ``campaign_assessor`` / ``budget_allocator`` — the funding decisions.
        These default to the deterministic rule-based implementations (money
        decisions are safe-by-default; opt in to an LLM by injecting one).
      * ``campaign_analyst`` / ``portfolio_synthesizer`` / ``report_narrator`` —
        the narrative, which defaults to the OpenAI adapters (needs
        ``OPENAI_API_KEY`` unless a caller injects its own).

    KPIs, benchmarks, and the evidence packs are always computed deterministically
    and handed to the decision/narrative ports as input.
    """

    canonical = normalize_cycle(load_sample2(input_directory))
    manifest = _manifest(canonical)
    quality = build_data_quality_report(canonical)
    registry = load_campaign_type_registry()
    policy = load_budget_policy()
    raw_scorecards = build_scorecards(canonical)

    # Deterministic evidence in → decision ports → enriched scorecards + budget.
    evidence_packs = build_evidence_packs(manifest.cycle_id, raw_scorecards, registry, quality)
    assessor = campaign_assessor or DeterministicCampaignAssessor()
    assessments = [
        assessor.assess(pack, registry.campaign_types[pack.campaign_type])
        for pack in evidence_packs
    ]
    scorecards = enrich_scorecards(raw_scorecards, assessments, registry, quality)
    allocator = budget_allocator or DeterministicBudgetAllocator()
    budget = allocator.allocate(
        manifest.cycle_id, scorecards.campaign, assessments, registry, policy, quality
    )

    analyst = campaign_analyst or OpenAICampaignAnalyst()
    insights = [analyst.analyze(pack) for pack in evidence_packs]
    synthesizer = portfolio_synthesizer or OpenAIPortfolioSynthesizer()
    portfolio = synthesizer.synthesize(assessments, insights)
    narrator = report_narrator or OpenAIReportNarrator()
    stakeholder_report = narrator.narrate(portfolio, budget)

    report = CompletedCycleReport(
        manifest=manifest,
        data_quality=quality,
        canonical_data=canonical,
        scorecards=scorecards,
        evidence_packs=evidence_packs,
        assessments=assessments,
        insights=insights,
        portfolio_insight=portfolio,
        budget_scenario=budget,
        stakeholder_report=stakeholder_report,
    )
    return report
