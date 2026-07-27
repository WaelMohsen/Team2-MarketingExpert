"""Model-backed intelligence adapters."""

from .openai_adapters import (
    OpenAICampaignAnalyst,
    OpenAIPortfolioSynthesizer,
    OpenAIReportNarrator,
)
from .prompt_registry import load_prompt

__all__ = [
    "OpenAICampaignAnalyst",
    "OpenAIPortfolioSynthesizer",
    "OpenAIReportNarrator",
    "load_prompt",
]
