"""Optional OpenAI implementations of the stable intelligence ports."""

from __future__ import annotations

import json
import os
from typing import Sequence, TypeVar

from pydantic import BaseModel

from src_2.contracts import (
    BudgetScenario,
    CampaignAssessment,
    CampaignEvidencePack,
    CampaignInsight,
    PortfolioInsight,
    StakeholderReport,
)

from .prompt_registry import load_prompt

OutputModel = TypeVar("OutputModel", bound=BaseModel)


class _StructuredOpenAI:
    def __init__(self, model: str | None = None) -> None:
        from openai import OpenAI

        self.client = OpenAI()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5-mini")

    def parse(self, prompt_name: str, payload: dict, model: type[OutputModel]) -> OutputModel:
        response = self.client.responses.parse(
            model=self.model,
            instructions=load_prompt(prompt_name),
            input=json.dumps(payload, ensure_ascii=True, default=str),
            text_format=model,
        )
        if response.output_parsed is None:
            raise RuntimeError("The model did not return a validated structured response")
        return response.output_parsed


class OpenAICampaignAnalyst(_StructuredOpenAI):
    def analyze(self, evidence: CampaignEvidencePack) -> CampaignInsight:
        return self.parse(
            "campaign_analysis", evidence.model_dump(mode="json"), CampaignInsight
        )


class OpenAIPortfolioSynthesizer(_StructuredOpenAI):
    def synthesize(
        self,
        assessments: Sequence[CampaignAssessment],
        insights: Sequence[CampaignInsight],
    ) -> PortfolioInsight:
        cycle_id = assessments[0].cycle_id if assessments else "unknown"
        return self.parse(
            "portfolio_synthesis",
            {
                "cycle_id": cycle_id,
                "assessments": [item.model_dump(mode="json") for item in assessments],
                "insights": [item.model_dump(mode="json") for item in insights],
            },
            PortfolioInsight,
        )


class OpenAIReportNarrator(_StructuredOpenAI):
    def narrate(
        self, portfolio: PortfolioInsight, budget: BudgetScenario
    ) -> StakeholderReport:
        return self.parse(
            "recommendation_narrator",
            {
                "portfolio": portfolio.model_dump(mode="json"),
                "budget": budget.model_dump(mode="json"),
            },
            StakeholderReport,
        )
