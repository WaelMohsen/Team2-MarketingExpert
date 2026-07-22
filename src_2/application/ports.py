"""Replaceable intelligence and storage interfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence

from src_2.contracts import (
    BudgetScenario,
    CampaignAssessment,
    CampaignEvidencePack,
    CampaignInsight,
    PortfolioInsight,
    StakeholderReport,
)


class CampaignAnalyst(Protocol):
    def analyze(self, evidence: CampaignEvidencePack) -> CampaignInsight: ...


class PortfolioSynthesizer(Protocol):
    def synthesize(
        self,
        assessments: Sequence[CampaignAssessment],
        insights: Sequence[CampaignInsight],
    ) -> PortfolioInsight: ...


class ReportNarrator(Protocol):
    def narrate(
        self, portfolio: PortfolioInsight, budget: BudgetScenario
    ) -> StakeholderReport: ...


class ArtifactStore(Protocol):
    def save_json(self, cycle_id: str, name: str, payload: dict) -> Path: ...
