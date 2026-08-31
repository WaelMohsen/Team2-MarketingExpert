"""Replaceable intelligence and storage interfaces."""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from src_2.contracts import (
    AdMessageContext,
    AdMessageMatchSignal,
    BudgetScenario,
    CampaignAssessment,
    CampaignEvidencePack,
    CampaignInsight,
    ConversationSignals,
    DataQualityReport,
    PortfolioInsight,
    StakeholderReport,
    SemanticConversationInput,
)
from src_2.domain.config import BudgetPolicy, CampaignTypeConfig, CampaignTypeRegistry


class CampaignAssessor(Protocol):
    """Turns one campaign's evidence + type config into a funding decision."""

    def assess(
        self, evidence: CampaignEvidencePack, config: CampaignTypeConfig
    ) -> CampaignAssessment: ...


class BudgetAllocator(Protocol):
    """Turns the assessed campaigns into an illustrative budget scenario."""

    def allocate(
        self,
        cycle_id: str,
        campaign_scorecard: Any,  # pandas DataFrame of the enriched campaign scorecard
        assessments: Sequence[CampaignAssessment],
        registry: CampaignTypeRegistry,
        policy: BudgetPolicy,
        quality: DataQualityReport,
    ) -> BudgetScenario: ...


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


class ConversationSignalExtractor(Protocol):
    """Classifies redacted messages into validated diagnostic signals."""

    model: str
    prompt_version: str
    prompt_sha256: str

    def extract(
        self, model_input: SemanticConversationInput
    ) -> ConversationSignals: ...


class AdMessageMatchEvaluator(Protocol):
    """Compares an ad promise with already-validated customer signals."""

    model: str
    prompt_version: str
    prompt_sha256: str

    def evaluate(
        self, ad_context: AdMessageContext, signals: ConversationSignals
    ) -> AdMessageMatchSignal: ...
