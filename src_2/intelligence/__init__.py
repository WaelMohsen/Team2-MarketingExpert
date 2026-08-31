"""Model-backed intelligence adapters."""

from .openai_adapters import (
    OpenAICampaignAnalyst,
    OpenAIPortfolioSynthesizer,
    OpenAIReportNarrator,
)
from .prompt_registry import load_prompt
from .conversation_signals import (
    OpenAIAdMessageMatchEvaluator,
    OpenAIConversationSignalExtractor,
    build_semantic_input,
    build_signal_record,
)

__all__ = [
    "OpenAIAdMessageMatchEvaluator",
    "OpenAICampaignAnalyst",
    "OpenAIPortfolioSynthesizer",
    "OpenAIReportNarrator",
    "OpenAIConversationSignalExtractor",
    "build_semantic_input",
    "build_signal_record",
    "load_prompt",
]
