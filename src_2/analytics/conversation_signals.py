"""Aggregate validated semantic records as diagnostic scorecard evidence."""

from __future__ import annotations

from collections import Counter
from typing import Iterable

import pandas as pd

from src_2.contracts import ConversationSignalRecord
from src_2.ingestion.normalizer import CanonicalCycleData


def _entity_ids(frame: pd.DataFrame, level: str) -> pd.Series:
    if level == "campaign":
        return frame["campaign_id"]
    if level == "adset":
        return frame["adset_id"]
    if level == "ad":
        return frame["ad_id"]
    if level == "creative":
        return frame["campaign_id"] + "::creative::" + frame["creative_id"]
    if level == "audience":
        return (
            frame["campaign_id"]
            + "::audience::"
            + frame["audience_type"].fillna("unknown").astype(str)
        )
    raise ValueError(f"Unsupported scorecard level: {level}")


def _top_value(values: Iterable[str]) -> str | None:
    counter = Counter(value for value in values if value)
    if not counter:
        return None
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _flatten_records(
    data: CanonicalCycleData, records: Iterable[ConversationSignalRecord], level: str
) -> pd.DataFrame:
    attribution = data.conversations[
        [
            "conversation_id",
            "campaign_id",
            "adset_id",
            "ad_id",
            "creative_id",
            "audience_type",
        ]
    ].copy()
    attribution["entity_id"] = _entity_ids(attribution, level)
    entity_by_conversation = attribution.set_index("conversation_id")["entity_id"].to_dict()
    outcomes = data.conversations.set_index("conversation_id")
    rows: list[dict] = []
    for record in records:
        entity_id = entity_by_conversation.get(record.conversation_id)
        if not entity_id or pd.isna(entity_id):
            continue
        signals = record.signals
        outcome = outcomes.loc[record.conversation_id] if record.conversation_id in outcomes.index else None
        next_step_agreed = signals.next_step_agreed.agreed is True
        next_step_observed = bool(outcome.get("has_order")) if outcome is not None else False
        barrier_resolutions = {item.resolution.value for item in signals.barriers}
        ad_match_level = record.ad_message_match.level.value
        rows.append(
            {
                "entity_id": entity_id,
                "conversation_id": record.conversation_id,
                "purpose": signals.conversation_purpose.value,
                "purchase_intent": signals.purchase_intent.level.value,
                "has_barrier": bool(signals.barriers),
                "barriers": [item.barrier_type.value for item in signals.barriers],
                "products": [item.product_reference for item in signals.mentioned_products],
                "agent_helpful": signals.agent_evaluation.helpfulness.value
                in {"good", "strong"},
                "high_urgency": signals.urgency.level.value == "high",
                "price_sensitive": signals.price_sensitivity.level.value
                in {"sensitive", "blocking"},
                "price_blocking": signals.price_sensitivity.level.value == "blocking",
                "deal_seeking": signals.deal_seeking.level.value
                in {"interested", "required"},
                "deal_required": signals.deal_seeking.level.value == "required",
                "delivery_ready": signals.delivery_intent.level.value
                in {"readiness", "checkout_details"},
                "sales_agreement": signals.sales_agreement.level.value
                in {"partial", "complete"},
                "blocking_barrier": any(
                    item.severity.value == "blocking" for item in signals.barriers
                ),
                "assessable_barrier_resolution": bool(
                    barrier_resolutions.intersection({"resolved", "unresolved"})
                ),
                "barrier_resolved": "resolved" in barrier_resolutions,
                "competitor_mentioned": signals.competitor_mention.mentioned,
                "value_drivers": [item.driver.value for item in signals.value_drivers],
                "stated_exit_reason": signals.stated_exit_reason.reason.value,
                "next_step_agreed": next_step_agreed,
                "next_step_observed": next_step_agreed and next_step_observed,
                "assessable_ad_message_match": ad_match_level != "unknown",
                "ad_message_aligned": ad_match_level == "aligned",
                "ad_message_partial": ad_match_level == "partial",
                "ad_message_mismatch": ad_match_level == "mismatch",
            }
        )
    return pd.DataFrame(rows)


def aggregate_conversation_signals(
    data: CanonicalCycleData,
    records: Iterable[ConversationSignalRecord],
    level: str,
) -> pd.DataFrame:
    frame = _flatten_records(data, records, level)
    if frame.empty:
        return pd.DataFrame(columns=["entity_id"])
    base = frame.groupby("entity_id", as_index=False).agg(
        semantic_conversations=("conversation_id", "nunique"),
        high_purchase_intent_conversations=(
            "purchase_intent",
            lambda values: values.eq("high").sum(),
        ),
        barrier_conversations=("has_barrier", "sum"),
        agent_helpful_conversations=("agent_helpful", "sum"),
        high_urgency_conversations=("high_urgency", "sum"),
        price_sensitive_conversations=("price_sensitive", "sum"),
        price_blocking_conversations=("price_blocking", "sum"),
        deal_seeking_conversations=("deal_seeking", "sum"),
        deal_required_conversations=("deal_required", "sum"),
        delivery_ready_conversations=("delivery_ready", "sum"),
        sales_agreement_conversations=("sales_agreement", "sum"),
        blocking_barrier_conversations=("blocking_barrier", "sum"),
        assessable_barrier_conversations=("assessable_barrier_resolution", "sum"),
        resolved_barrier_conversations=("barrier_resolved", "sum"),
        competitor_mention_conversations=("competitor_mentioned", "sum"),
        next_step_agreed_conversations=("next_step_agreed", "sum"),
        next_step_observed_conversations=("next_step_observed", "sum"),
        assessable_ad_message_match_conversations=(
            "assessable_ad_message_match",
            "sum",
        ),
        ad_message_aligned_conversations=("ad_message_aligned", "sum"),
        ad_message_partial_conversations=("ad_message_partial", "sum"),
        ad_message_mismatch_conversations=("ad_message_mismatch", "sum"),
    )
    categories: list[dict] = []
    for entity_id, group in frame.groupby("entity_id"):
        categories.append(
            {
                "entity_id": entity_id,
                "top_conversation_purpose": _top_value(group["purpose"]),
                "top_barrier": _top_value(
                    item for values in group["barriers"] for item in values
                ),
                "top_mentioned_product": _top_value(
                    item for values in group["products"] for item in values
                ),
                "top_value_driver": _top_value(
                    item for values in group["value_drivers"] for item in values
                ),
                "top_stated_exit_reason": _top_value(
                    value
                    for value in group["stated_exit_reason"]
                    if value not in {"unknown", "not_stated"}
                ),
            }
        )
    result = base.merge(pd.DataFrame(categories), on="entity_id", how="left")
    denominator = result["semantic_conversations"].replace(0, pd.NA)
    result["high_purchase_intent_rate"] = (
        result["high_purchase_intent_conversations"] / denominator
    )
    result["barrier_conversation_rate"] = result["barrier_conversations"] / denominator
    result["agent_helpful_rate"] = (
        result["agent_helpful_conversations"] / denominator
    )
    for count_column, rate_column in (
        ("high_urgency_conversations", "high_urgency_rate"),
        ("price_sensitive_conversations", "price_sensitive_rate"),
        ("price_blocking_conversations", "price_blocking_rate"),
        ("deal_seeking_conversations", "deal_seeking_rate"),
        ("deal_required_conversations", "deal_required_rate"),
        ("delivery_ready_conversations", "delivery_ready_rate"),
        ("sales_agreement_conversations", "sales_agreement_rate"),
        ("blocking_barrier_conversations", "blocking_barrier_rate"),
        ("competitor_mention_conversations", "competitor_mention_rate"),
        ("next_step_agreed_conversations", "next_step_agreement_rate"),
    ):
        result[rate_column] = result[count_column] / denominator
    result["barrier_resolution_rate"] = result["resolved_barrier_conversations"] / result[
        "assessable_barrier_conversations"
    ].replace(0, pd.NA)
    result["next_step_completion_rate"] = result[
        "next_step_observed_conversations"
    ] / result["next_step_agreed_conversations"].replace(0, pd.NA)
    assessable_match = result["assessable_ad_message_match_conversations"].replace(
        0, pd.NA
    )
    result["ad_message_alignment_rate"] = (
        result["ad_message_aligned_conversations"] / assessable_match
    )
    result["ad_message_partial_rate"] = (
        result["ad_message_partial_conversations"] / assessable_match
    )
    result["ad_message_mismatch_rate"] = (
        result["ad_message_mismatch_conversations"] / assessable_match
    )
    return result
