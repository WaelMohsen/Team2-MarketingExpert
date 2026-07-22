"""Replaceable deterministic and model-backed intelligence adapters."""

from .deterministic import (
    DeterministicCampaignAnalyst,
    DeterministicPortfolioSynthesizer,
    DeterministicReportNarrator,
)
from .openai_adapters import (
    OpenAICampaignAnalyst,
    OpenAIPortfolioSynthesizer,
    OpenAIReportNarrator,
)
from .prompt_registry import load_prompt

__all__ = [
    "DeterministicCampaignAnalyst",
    "DeterministicPortfolioSynthesizer",
    "DeterministicReportNarrator",
    "OpenAICampaignAnalyst",
    "OpenAIPortfolioSynthesizer",
    "OpenAIReportNarrator",
    "load_prompt",
]
