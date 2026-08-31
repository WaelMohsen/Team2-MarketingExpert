"""Privacy boundary and OpenAI adapter for conversation semantics."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime
from typing import Any

import pandas as pd

from src_2.contracts.conversation import (
    AdMessageContext,
    AdMessageMatchSignal,
    ConversationAttribution,
    ConversationSignalRecord,
    ConversationSignals,
    MessageRole,
    SemanticConversationInput,
    SemanticMessage,
)

from .prompt_registry import load_prompt

PROMPT_NAME = "conversation_signals"
PROMPT_VERSION = "conversation-signals-v2"
AD_MATCH_PROMPT_NAME = "ad_message_match"
AD_MATCH_PROMPT_VERSION = "ad-message-match-v1"

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
_LONG_NUMBER = re.compile(r"(?<!\w)\d{7,}(?!\w)")
_ADDRESS_CUES = (
    "address",
    "street",
    "road",
    "district",
    "building",
    "apartment",
    "العنوان",
    "عنوان",
    "شارع",
    "عمارة",
    "شقة",
)


def _contains_address_cue(text: str) -> bool:
    lowered = text.casefold()
    return any(cue in lowered for cue in _ADDRESS_CUES)


def _redact_text(
    text: str, conversation: dict[str, Any], *, address_sensitive: bool
) -> str:
    customer = conversation.get("customer") or {}
    redacted = str(text or "")
    for key in ("first_name", "last_name", "phone"):
        value = str(customer.get(key) or "").strip()
        if value:
            redacted = re.sub(re.escape(value), f"[REDACTED_{key.upper()}]", redacted, flags=re.IGNORECASE)
    redacted = _EMAIL.sub("[REDACTED_EMAIL]", redacted)
    redacted = _PHONE.sub("[REDACTED_PHONE]", redacted)
    redacted = _LONG_NUMBER.sub("[REDACTED_NUMBER]", redacted)
    if address_sensitive or _contains_address_cue(redacted):
        return "[REDACTED_ADDRESS_MESSAGE]"
    return redacted


def build_semantic_input(conversation: dict[str, Any]) -> SemanticConversationInput:
    """Project a raw record to message-only, redacted model input."""

    started_at = pd.to_datetime(conversation.get("started_at"), errors="coerce", utc=True)
    messages: list[SemanticMessage] = []
    agent_requested_address = False
    for index, message in enumerate(conversation.get("messages") or []):
        inbound = message.get("direction") == "inbound"
        role = MessageRole.CUSTOMER if inbound else MessageRole.AGENT
        raw_text = str(message.get("text") or "")
        sent_at = pd.to_datetime(message.get("sent_at"), errors="coerce", utc=True)
        relative_minute = None
        if pd.notna(started_at) and pd.notna(sent_at):
            relative_minute = (sent_at - started_at).total_seconds() / 60
        messages.append(
            SemanticMessage(
                message_index=index,
                role=role,
                relative_minute=relative_minute,
                redacted_text=_redact_text(
                    raw_text,
                    conversation,
                    address_sensitive=inbound and agent_requested_address,
                ),
                product_references=[str(item) for item in message.get("products") or []],
            )
        )
        if inbound:
            agent_requested_address = False
        else:
            agent_requested_address = _contains_address_cue(raw_text)
    return SemanticConversationInput(
        language=conversation.get("language"),
        messages=messages,
    )


class OpenAIConversationSignalExtractor:
    """Extract validated semantic signals; never receives outcomes or customer records."""

    def __init__(
        self,
        model: str | None = None,
        *,
        client: Any | None = None,
        max_attempts: int = 3,
    ) -> None:
        if client is None:
            from openai import OpenAI

            client = OpenAI()
        self.client = client
        self.model = model or os.getenv(
            "OPENAI_CONVERSATION_MODEL", os.getenv("OPENAI_MODEL", "gpt-5-mini")
        )
        self.max_attempts = max_attempts
        self.prompt = load_prompt(PROMPT_NAME)
        self.prompt_version = PROMPT_VERSION
        self.prompt_sha256 = hashlib.sha256(self.prompt.encode("utf-8")).hexdigest()

    def extract(self, model_input: SemanticConversationInput) -> ConversationSignals:
        error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.client.responses.parse(
                    model=self.model,
                    instructions=self.prompt,
                    input=json.dumps(model_input.model_dump(mode="json"), ensure_ascii=False),
                    text_format=ConversationSignals,
                )
                if response.output_parsed is None:
                    raise RuntimeError("The model returned no validated conversation signals")
                return response.output_parsed
            except Exception as exc:  # API errors vary by SDK version.
                error = exc
                if attempt < self.max_attempts:
                    time.sleep(2 ** (attempt - 1))
        detail = (
            f"{type(error).__name__}: {error}" if error is not None else "unknown error"
        )
        raise RuntimeError(
            f"Conversation signal extraction failed after {self.max_attempts} attempts. "
            f"Last error: {detail}"
        ) from error


class OpenAIAdMessageMatchEvaluator:
    """Evaluate message match separately so transcript semantics stay outcome-blind."""

    def __init__(
        self,
        model: str | None = None,
        *,
        client: Any | None = None,
        max_attempts: int = 3,
    ) -> None:
        if client is None:
            from openai import OpenAI

            client = OpenAI()
        self.client = client
        self.model = model or os.getenv(
            "OPENAI_CONVERSATION_MODEL", os.getenv("OPENAI_MODEL", "gpt-5-mini")
        )
        self.max_attempts = max_attempts
        self.prompt = load_prompt(AD_MATCH_PROMPT_NAME)
        self.prompt_version = AD_MATCH_PROMPT_VERSION
        self.prompt_sha256 = hashlib.sha256(self.prompt.encode("utf-8")).hexdigest()

    def evaluate(
        self, ad_context: AdMessageContext, signals: ConversationSignals
    ) -> AdMessageMatchSignal:
        payload = {
            "ad_context": ad_context.model_dump(mode="json"),
            "conversation_signals": {
                "conversation_purpose": signals.conversation_purpose.value,
                "customer_need": signals.customer_need,
                "purchase_intent": signals.purchase_intent.model_dump(mode="json"),
                "mentioned_products": [
                    item.model_dump(mode="json") for item in signals.mentioned_products
                ],
                "urgency": signals.urgency.model_dump(mode="json"),
                "price_sensitivity": signals.price_sensitivity.model_dump(mode="json"),
                "deal_seeking": signals.deal_seeking.model_dump(mode="json"),
                "delivery_intent": signals.delivery_intent.model_dump(mode="json"),
                "value_drivers": [
                    item.model_dump(mode="json") for item in signals.value_drivers
                ],
            },
        }
        error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.client.responses.parse(
                    model=self.model,
                    instructions=self.prompt,
                    input=json.dumps(payload, ensure_ascii=False),
                    text_format=AdMessageMatchSignal,
                )
                if response.output_parsed is None:
                    raise RuntimeError("The model returned no validated ad-message match")
                return response.output_parsed
            except Exception as exc:
                error = exc
                if attempt < self.max_attempts:
                    time.sleep(2 ** (attempt - 1))
        detail = f"{type(error).__name__}: {error}" if error else "unknown error"
        raise RuntimeError(
            f"Ad-message match evaluation failed after {self.max_attempts} attempts. "
            f"Last error: {detail}"
        ) from error


def build_signal_record(
    *,
    conversation_id: str,
    attribution: ConversationAttribution,
    signals: ConversationSignals,
    extractor: OpenAIConversationSignalExtractor,
    ad_message_match: AdMessageMatchSignal | None = None,
    ad_match_evaluator: OpenAIAdMessageMatchEvaluator | None = None,
) -> ConversationSignalRecord:
    return ConversationSignalRecord(
        conversation_id=conversation_id,
        attribution=attribution,
        prompt_version=extractor.prompt_version,
        prompt_sha256=extractor.prompt_sha256,
        model=extractor.model,
        extracted_at=datetime.now().astimezone(),
        signals=signals,
        signal_schema_version=2,
        ad_message_match=ad_message_match or AdMessageMatchSignal(
            level="unknown", rationale=None, evidence_message_indexes=[]
        ),
        ad_match_prompt_version=(
            ad_match_evaluator.prompt_version if ad_match_evaluator else None
        ),
        ad_match_prompt_sha256=(
            ad_match_evaluator.prompt_sha256 if ad_match_evaluator else None
        ),
        ad_match_model=ad_match_evaluator.model if ad_match_evaluator else None,
    )
