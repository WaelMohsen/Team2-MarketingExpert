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
    LLMTokenUsage,
    MessageRole,
    SemanticConversationInput,
    SemanticMessage,
)

from .prompt_registry import load_prompt

PROMPT_NAME = "conversation_signals"
PROMPT_VERSION = "conversation-signals-v3.2"
SEMANTIC_INPUT_VERSION = "semantic-input-v3"
AD_MATCH_PROMPT_NAME = "ad_message_match"
AD_MATCH_PROMPT_VERSION = "ad-message-match-v1"

_PRICING_AS_OF = "2026-09-04"
_MODEL_PRICING_USD_PER_MILLION = {
    "gpt-5-mini": (0.25, 0.025, 2.00),
}

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
_LONG_NUMBER = re.compile(r"(?<!\w)\d{7,}(?!\w)")
_GREETING_NAME = re.compile(
    r"(?i)((?:\b(?:hi|hello|hey|dear|thanks|thank\s+you)\b|"
    r"(?:أهلاً|أهلا|اهلا|مرحبا|شكراً|شكرا))[\s,:-]+)"
    r"([^\s,.!?،؛:]+)"
)
_GENERIC_GREETING_WORDS = {"there", "again", "everyone", "all", "وسهلا"}
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


def _value(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _model_pricing(model: str) -> tuple[float, float, float, str] | None:
    override_names = (
        "OPENAI_CONVERSATION_INPUT_USD_PER_MILLION",
        "OPENAI_CONVERSATION_CACHED_INPUT_USD_PER_MILLION",
        "OPENAI_CONVERSATION_OUTPUT_USD_PER_MILLION",
    )
    overrides = [os.getenv(name) for name in override_names]
    if all(value not in (None, "") for value in overrides):
        try:
            return (
                float(overrides[0]),
                float(overrides[1]),
                float(overrides[2]),
                os.getenv(
                    "OPENAI_CONVERSATION_PRICING_AS_OF", "environment-override"
                ),
            )
        except (TypeError, ValueError):
            return None
    for model_name, rates in _MODEL_PRICING_USD_PER_MILLION.items():
        if model == model_name or model.startswith(f"{model_name}-"):
            return (*rates, _PRICING_AS_OF)
    return None


def response_token_usage(response: Any, model: str) -> LLMTokenUsage:
    """Read usage from an OpenAI response and attach the active price snapshot."""

    usage = _value(response, "usage")
    pricing = _model_pricing(model)
    pricing_fields = (
        {
            "input_usd_per_million": pricing[0],
            "cached_input_usd_per_million": pricing[1],
            "output_usd_per_million": pricing[2],
            "pricing_as_of": pricing[3],
        }
        if pricing
        else {}
    )
    if usage is None:
        return LLMTokenUsage(request_count=1, model=model, **pricing_fields)

    input_tokens = int(_value(usage, "input_tokens", 0) or 0)
    output_tokens = int(_value(usage, "output_tokens", 0) or 0)
    input_details = _value(usage, "input_tokens_details", {}) or {}
    output_details = _value(usage, "output_tokens_details", {}) or {}
    cached_tokens = int(_value(input_details, "cached_tokens", 0) or 0)
    reasoning_tokens = int(_value(output_details, "reasoning_tokens", 0) or 0)
    total_tokens = int(
        _value(usage, "total_tokens", input_tokens + output_tokens)
        or input_tokens + output_tokens
    )
    estimated_cost = None
    if pricing:
        uncached_tokens = max(input_tokens - cached_tokens, 0)
        estimated_cost = (
            uncached_tokens * pricing[0]
            + cached_tokens * pricing[1]
            + output_tokens * pricing[2]
        ) / 1_000_000
    return LLMTokenUsage(
        request_count=1,
        input_tokens=input_tokens,
        cached_input_tokens=cached_tokens,
        output_tokens=output_tokens,
        reasoning_output_tokens=reasoning_tokens,
        total_tokens=total_tokens,
        model=model,
        estimated_cost_usd=estimated_cost,
        **pricing_fields,
    )


def merge_token_usage(*items: LLMTokenUsage) -> LLMTokenUsage:
    """Combine calls and retries without losing unknown-cost information."""

    active = [
        item
        for item in items
        if item.request_count or item.input_tokens or item.output_tokens
    ]
    if not active:
        return LLMTokenUsage()

    def common(name: str) -> Any:
        values = {getattr(item, name) for item in active}
        return next(iter(values)) if len(values) == 1 else None

    estimated_cost = (
        None
        if any(item.estimated_cost_usd is None for item in active)
        else sum(item.estimated_cost_usd or 0 for item in active)
    )
    return LLMTokenUsage(
        request_count=sum(item.request_count for item in active),
        input_tokens=sum(item.input_tokens for item in active),
        cached_input_tokens=sum(item.cached_input_tokens for item in active),
        output_tokens=sum(item.output_tokens for item in active),
        reasoning_output_tokens=sum(
            item.reasoning_output_tokens for item in active
        ),
        total_tokens=sum(item.total_tokens for item in active),
        model=common("model"),
        input_usd_per_million=common("input_usd_per_million"),
        cached_input_usd_per_million=common(
            "cached_input_usd_per_million"
        ),
        output_usd_per_million=common("output_usd_per_million"),
        pricing_as_of=common("pricing_as_of"),
        estimated_cost_usd=estimated_cost,
    )


def validate_evidence_message_indexes(
    value: Any,
    valid_indexes: set[int],
    *,
    context: str,
) -> None:
    """Reject model evidence references that are absent from the supplied input."""

    payload = value.model_dump(mode="python") if hasattr(value, "model_dump") else value
    invalid: list[int] = []

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if key == "evidence_message_indexes":
                    invalid.extend(
                        index for index in child if index not in valid_indexes
                    )
                else:
                    visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(payload)
    if invalid:
        raise ValueError(
            f"{context} cited unavailable message indexes: {sorted(set(invalid))}"
        )


def validate_semantic_evidence_rules(
    signals: ConversationSignals,
    model_input: SemanticConversationInput,
) -> None:
    """Enforce evidence rules that cannot be expressed in the JSON schema."""

    roles = {
        message.message_index: message.role for message in model_input.messages
    }

    def require_role(
        indexes: list[int],
        role: MessageRole,
        *,
        context: str,
        required: bool = False,
    ) -> None:
        if required and not indexes:
            raise ValueError(f"{context} requires evidence message indexes")
        invalid_roles = [index for index in indexes if roles.get(index) is not role]
        if invalid_roles:
            raise ValueError(
                f"{context} must cite only {role.value} messages; "
                f"invalid indexes: {invalid_roles}"
            )

    def validate_elicited_customer_signal(
        indexes: list[int],
        elicited_by_agent: bool | None,
        *,
        context: str,
        required: bool,
    ) -> None:
        if required and not indexes:
            raise ValueError(f"{context} requires evidence message indexes")
        if not indexes:
            return
        customer_indexes = [
            index for index in indexes if roles.get(index) is MessageRole.CUSTOMER
        ]
        agent_indexes = [
            index for index in indexes if roles.get(index) is MessageRole.AGENT
        ]
        if not customer_indexes:
            raise ValueError(f"{context} requires customer evidence")
        if elicited_by_agent is True:
            if not any(
                agent_index < customer_index
                for agent_index in agent_indexes
                for customer_index in customer_indexes
            ):
                raise ValueError(
                    f"{context} marked elicited_by_agent requires a preceding "
                    "agent message in its evidence"
                )
        elif agent_indexes:
            raise ValueError(
                f"{context} not marked elicited_by_agent must cite only customer messages"
            )

    validate_elicited_customer_signal(
        signals.purchase_intent.evidence_message_indexes,
        signals.purchase_intent.elicited_by_agent,
        context="Purchase intent",
        required=signals.purchase_intent.level.value != "unknown",
    )
    require_role(
        signals.specificity.evidence_message_indexes,
        MessageRole.CUSTOMER,
        context="Specificity",
        required=signals.specificity.level.value not in {"none", "unknown"},
    )
    validate_elicited_customer_signal(
        signals.urgency.evidence_message_indexes,
        signals.urgency.elicited_by_agent,
        context="Urgency",
        required=signals.urgency.level.value not in {"none", "unknown"},
    )
    validate_elicited_customer_signal(
        signals.delivery_intent.evidence_message_indexes,
        signals.delivery_intent.elicited_by_agent,
        context="Delivery intent",
        required=signals.delivery_intent.level.value not in {"none", "unknown"},
    )
    for context, level, elicited_by_agent in (
        ("Urgency", signals.urgency.level.value, signals.urgency.elicited_by_agent),
        (
            "Delivery intent",
            signals.delivery_intent.level.value,
            signals.delivery_intent.elicited_by_agent,
        ),
    ):
        if level not in {"none", "unknown"} and elicited_by_agent is None:
            raise ValueError(
                f"{context} must set elicited_by_agent to true or false when assessable"
            )
    for context, level, indexes in (
        (
            "Price sensitivity",
            signals.price_sensitivity.level.value,
            signals.price_sensitivity.evidence_message_indexes,
        ),
        (
            "Deal seeking",
            signals.deal_seeking.level.value,
            signals.deal_seeking.evidence_message_indexes,
        ),
        (
            "Financing",
            signals.financing.level.value,
            signals.financing.evidence_message_indexes,
        ),
    ):
        require_role(
            indexes,
            MessageRole.CUSTOMER,
            context=context,
            required=level not in {"none", "unknown"},
        )
    require_role(
        signals.sales_agreement.evidence_message_indexes,
        MessageRole.CUSTOMER,
        context="Sales agreement",
        required=signals.sales_agreement.level.value in {"partial", "complete"},
    )
    for product in signals.mentioned_products:
        if not any(
            roles.get(index) is MessageRole.CUSTOMER
            for index in product.evidence_message_indexes
        ):
            raise ValueError("Mentioned product requires customer evidence")
    for value_driver in signals.value_drivers:
        require_role(
            value_driver.evidence_message_indexes,
            MessageRole.CUSTOMER,
            context="Value driver",
            required=True,
        )
    for trait in signals.commercial_traits:
        require_role(
            trait.evidence_message_indexes,
            MessageRole.CUSTOMER,
            context=f"Commercial trait {trait.trait.value}",
            required=True,
        )
    if signals.competitor_mention.mentioned:
        require_role(
            signals.competitor_mention.evidence_message_indexes,
            MessageRole.CUSTOMER,
            context="Competitor mention",
            required=True,
        )
    if signals.stated_exit_reason.reason.value not in {"unknown", "not_stated"}:
        require_role(
            signals.stated_exit_reason.evidence_message_indexes,
            MessageRole.CUSTOMER,
            context="Stated exit reason",
            required=True,
        )
    if signals.next_step_agreed.agreed is True:
        require_role(
            signals.next_step_agreed.evidence_message_indexes,
            MessageRole.CUSTOMER,
            context="Agreed next step",
            required=True,
        )

    for barrier in signals.barriers:
        customer_indexes = sorted(
            index
            for index in barrier.evidence_message_indexes
            if roles.get(index) is MessageRole.CUSTOMER
        )
        if not customer_indexes:
            raise ValueError("A sales barrier requires customer evidence")
        if barrier.resolution.value != "resolved":
            require_role(
                barrier.evidence_message_indexes,
                MessageRole.CUSTOMER,
                context="Unresolved sales barrier",
            )
            continue
        agent_indexes = sorted(
            index
            for index in barrier.evidence_message_indexes
            if roles.get(index) is MessageRole.AGENT
        )
        resolution_sequence_exists = any(
            barrier_index < agent_index < progression_index
            for barrier_index in customer_indexes
            for agent_index in agent_indexes
            for progression_index in customer_indexes
        )
        if not resolution_sequence_exists:
            raise ValueError(
                "A resolved sales barrier requires customer barrier evidence, an "
                "agent response, and a later customer message that accepts the "
                "answer or continues toward checkout"
            )

    require_role(
        signals.agent_evaluation.evidence_message_indexes,
        MessageRole.AGENT,
        context="Agent evaluation",
        required=any(
            rating.value != "not_assessable"
            for rating in (
                signals.agent_evaluation.helpfulness,
                signals.agent_evaluation.needs_discovery,
                signals.agent_evaluation.objection_handling,
                signals.agent_evaluation.progression,
                signals.agent_evaluation.tone,
            )
        ),
    )
    require_role(
        signals.agent_tone.evidence_message_indexes,
        MessageRole.AGENT,
        context="Agent tone",
        required=signals.agent_tone.quality.value != "not_assessable",
    )


def _contains_address_cue(text: str) -> bool:
    lowered = text.casefold()
    return any(cue in lowered for cue in _ADDRESS_CUES)


def _redact_agent_address_segments(text: str) -> str:
    """Keep non-address context while masking an agent's address segment."""

    parts = re.split(r"([.!?؟\n]+)", text)
    redacted_parts: list[str] = []
    for position in range(0, len(parts), 2):
        segment = parts[position]
        delimiter = parts[position + 1] if position + 1 < len(parts) else ""
        if _contains_address_cue(segment):
            marker = (
                "[ADDRESS_REQUEST]"
                if "?" in delimiter or "؟" in delimiter
                else "[REDACTED_ADDRESS_SEGMENT]"
            )
            redacted_parts.append(marker)
            redacted_parts.append(delimiter)
        else:
            redacted_parts.append(segment)
            redacted_parts.append(delimiter)
    return "".join(redacted_parts)


def _redact_text(
    text: str,
    conversation: dict[str, Any],
    *,
    address_sensitive: bool,
    redact_greeting_name: bool,
    customer_message: bool,
) -> str:
    customer = conversation.get("customer") or {}
    redacted = str(text or "")
    if address_sensitive or (customer_message and _contains_address_cue(redacted)):
        return "[REDACTED_ADDRESS_MESSAGE]"
    if not customer_message and _contains_address_cue(redacted):
        redacted = _redact_agent_address_segments(redacted)
    redacted = _EMAIL.sub("[REDACTED_EMAIL]", redacted)
    redacted = _PHONE.sub("[REDACTED_PHONE]", redacted)
    redacted = _LONG_NUMBER.sub("[REDACTED_NUMBER]", redacted)
    for key in ("first_name", "last_name"):
        value = str(customer.get(key) or "").strip()
        if value:
            redacted = re.sub(
                rf"(?<!\w){re.escape(value)}(?!\w)",
                f"[REDACTED_{key.upper()}]",
                redacted,
                flags=re.IGNORECASE,
            )
    if redact_greeting_name:
        def replace_greeting(match: re.Match[str]) -> str:
            candidate = match.group(2)
            if candidate.casefold() in _GENERIC_GREETING_WORDS:
                return match.group(0)
            return f"{match.group(1)}[REDACTED_GREETING_NAME]"

        redacted = _GREETING_NAME.sub(replace_greeting, redacted)
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
                    redact_greeting_name=not inbound,
                    customer_message=inbound,
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
        self.last_usage = LLMTokenUsage()

    def extract(self, model_input: SemanticConversationInput) -> ConversationSignals:
        self.last_usage = LLMTokenUsage()
        error: Exception | None = None
        validation_feedback: str | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                request_input = json.dumps(
                    model_input.model_dump(mode="json"), ensure_ascii=False
                )
                if validation_feedback:
                    request_input += (
                        "\n\nThe previous structured output was rejected by local "
                        f"validation. Correct this issue: {validation_feedback}"
                    )
                response = self.client.responses.parse(
                    model=self.model,
                    instructions=self.prompt,
                    input=request_input,
                    text_format=ConversationSignals,
                )
                try:
                    call_usage = response_token_usage(response, self.model)
                except (TypeError, ValueError):
                    call_usage = LLMTokenUsage(request_count=1, model=self.model)
                self.last_usage = merge_token_usage(
                    self.last_usage, call_usage
                )
                if response.output_parsed is None:
                    raise RuntimeError("The model returned no validated conversation signals")
                validate_evidence_message_indexes(
                    response.output_parsed,
                    set(range(len(model_input.messages))),
                    context="Conversation signals",
                )
                validate_semantic_evidence_rules(
                    response.output_parsed,
                    model_input,
                )
                return response.output_parsed
            except Exception as exc:  # API errors vary by SDK version.
                error = exc
                if isinstance(exc, ValueError):
                    validation_feedback = str(exc)
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
        self.last_usage = LLMTokenUsage()

    def evaluate(
        self, ad_context: AdMessageContext, signals: ConversationSignals
    ) -> AdMessageMatchSignal:
        self.last_usage = LLMTokenUsage()
        payload = {
            "ad_context": ad_context.model_dump(mode="json"),
            "conversation_signals": {
                "conversation_purpose": signals.conversation_purpose.value,
                "customer_need": signals.customer_need,
                "purchase_intent": signals.purchase_intent.model_dump(mode="json"),
                "specificity": signals.specificity.model_dump(mode="json"),
                "mentioned_products": [
                    item.model_dump(mode="json") for item in signals.mentioned_products
                ],
                "urgency": signals.urgency.model_dump(mode="json"),
                "price_sensitivity": signals.price_sensitivity.model_dump(mode="json"),
                "deal_seeking": signals.deal_seeking.model_dump(mode="json"),
                "financing": signals.financing.model_dump(mode="json"),
                "delivery_intent": signals.delivery_intent.model_dump(mode="json"),
                "value_drivers": [
                    item.model_dump(mode="json") for item in signals.value_drivers
                ],
                "commercial_traits": [
                    item.model_dump(mode="json") for item in signals.commercial_traits
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
                try:
                    call_usage = response_token_usage(response, self.model)
                except (TypeError, ValueError):
                    call_usage = LLMTokenUsage(request_count=1, model=self.model)
                self.last_usage = merge_token_usage(
                    self.last_usage, call_usage
                )
                if response.output_parsed is None:
                    raise RuntimeError("The model returned no validated ad-message match")
                supplied_indexes: set[int] = set()

                def collect_indexes(value: Any) -> None:
                    if isinstance(value, dict):
                        for key, child in value.items():
                            if key == "evidence_message_indexes":
                                supplied_indexes.update(child)
                            else:
                                collect_indexes(child)
                    elif isinstance(value, list):
                        for child in value:
                            collect_indexes(child)

                collect_indexes(signals.model_dump(mode="python"))
                validate_evidence_message_indexes(
                    response.output_parsed,
                    supplied_indexes,
                    context="Ad-message match",
                )
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
    semantic_usage: LLMTokenUsage | None = None,
    ad_match_usage: LLMTokenUsage | None = None,
) -> ConversationSignalRecord:
    return ConversationSignalRecord(
        conversation_id=conversation_id,
        attribution=attribution,
        input_projection_version=SEMANTIC_INPUT_VERSION,
        prompt_version=extractor.prompt_version,
        prompt_sha256=extractor.prompt_sha256,
        model=extractor.model,
        extracted_at=datetime.now().astimezone(),
        signals=signals,
        signal_schema_version=3,
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
        semantic_usage=(
            semantic_usage
            if semantic_usage is not None
            else getattr(extractor, "last_usage", LLMTokenUsage())
        ),
        ad_match_usage=(
            ad_match_usage
            if ad_match_usage is not None
            else getattr(ad_match_evaluator, "last_usage", LLMTokenUsage())
        ),
    )
