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
    merge_token_usage,
    response_token_usage,
    validate_evidence_message_indexes,
    validate_semantic_evidence_rules,
)

__all__ = [
    "OpenAIAdMessageMatchEvaluator",
    "OpenAICampaignAnalyst",
    "OpenAIPortfolioSynthesizer",
    "OpenAIReportNarrator",
    "OpenAIConversationSignalExtractor",
    "build_semantic_input",
    "build_signal_record",
    "merge_token_usage",
    "response_token_usage",
    "validate_evidence_message_indexes",
    "validate_semantic_evidence_rules",
    "load_prompt",
]
