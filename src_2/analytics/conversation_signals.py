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
        next_step_assessable = signals.next_step_agreed.agreed is not None
        observed_order = bool(outcome.get("has_order")) if outcome is not None else False
        barrier_resolutions = {item.resolution.value for item in signals.barriers}
        ad_match_level = record.ad_message_match.level.value
        purchase_intent = signals.purchase_intent.level.value
        specificity = signals.specificity.level.value
        urgency = signals.urgency.level.value
        price_sensitivity = signals.price_sensitivity.level.value
        deal_seeking = signals.deal_seeking.level.value
        financing = signals.financing.level.value
        delivery_intent = signals.delivery_intent.level.value
        sales_agreement = signals.sales_agreement.level.value
        agent_helpfulness = signals.agent_evaluation.helpfulness.value
        agent_tone_quality = signals.agent_tone.quality.value
        commercial_traits = [item.trait.value for item in signals.commercial_traits]
        rows.append(
            {
                "entity_id": entity_id,
                "conversation_id": record.conversation_id,
                "purpose": signals.conversation_purpose.value,
                "purchase_intent": purchase_intent,
                "assessable_purchase_intent": purchase_intent != "unknown",
                "has_barrier": bool(signals.barriers),
                "barriers": [item.barrier_type.value for item in signals.barriers],
                "products": [item.product_reference for item in signals.mentioned_products],
                "assessable_agent_helpfulness": agent_helpfulness
                != "not_assessable",
                "agent_helpful": agent_helpfulness in {"good", "strong"},
                "assessable_specificity": specificity != "unknown",
                "specific_customer_need": specificity in {"medium", "high"},
                "high_specificity": specificity == "high",
                "assessable_urgency": urgency != "unknown",
                "urgency_present": urgency in {"low", "medium", "high"},
                "high_urgency": urgency == "high",
                "urgency_elicited_by_agent": (
                    urgency in {"low", "medium", "high"}
                    and signals.urgency.elicited_by_agent is True
                ),
                "assessable_price_sensitivity": price_sensitivity != "unknown",
                "price_sensitive": price_sensitivity in {"sensitive", "blocking"},
                "price_blocking": price_sensitivity == "blocking",
                "assessable_deal_seeking": deal_seeking != "unknown",
                "deal_seeking": deal_seeking in {"interested", "required"},
                "deal_required": deal_seeking == "required",
                "assessable_financing": financing != "unknown",
                "financing_discussed": financing
                in {"inquiry", "consideration", "strong"},
                "strong_financing": financing == "strong",
                "assessable_delivery_intent": delivery_intent != "unknown",
                "delivery_present": delivery_intent
                in {"question", "readiness", "checkout_details"},
                "delivery_ready": delivery_intent
                in {"readiness", "checkout_details"},
                "delivery_elicited_by_agent": (
                    delivery_intent in {"question", "readiness", "checkout_details"}
                    and signals.delivery_intent.elicited_by_agent is True
                ),
                "assessable_sales_agreement": sales_agreement != "unknown",
                "sales_agreement": sales_agreement in {"partial", "complete"},
                "blocking_barrier": any(
                    item.severity.value == "blocking" for item in signals.barriers
                ),
                "assessable_barrier_resolution": bool(
                    barrier_resolutions.intersection({"resolved", "unresolved"})
                ),
                "barrier_resolved": "resolved" in barrier_resolutions,
                "competitor_mentioned": signals.competitor_mention.mentioned,
                "value_drivers": [item.driver.value for item in signals.value_drivers],
                "commercial_traits": commercial_traits,
                "brand_preference": "brand_preference" in commercial_traits,
                "feature_priority": "feature_priority" in commercial_traits,
                "bulk_purchase_interest": "bulk_purchase_interest"
                in commercial_traits,
                "customization_interest": "customization_interest"
                in commercial_traits,
                "stated_exit_reason": signals.stated_exit_reason.reason.value,
                "assessable_agent_tone": agent_tone_quality != "not_assessable",
                "positive_agent_tone": agent_tone_quality == "positive",
                "mixed_agent_tone": agent_tone_quality == "mixed",
                "negative_agent_tone": agent_tone_quality == "negative",
                "agent_tone_labels": [
                    item.value for item in signals.agent_tone.labels
                ],
                "assessable_next_step_agreement": next_step_assessable,
                "next_step_agreed": next_step_agreed,
                "next_step_order_progression": next_step_agreed and observed_order,
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
        assessable_purchase_intent_conversations=(
            "assessable_purchase_intent",
            "sum",
        ),
        high_purchase_intent_conversations=(
            "purchase_intent",
            lambda values: values.eq("high").sum(),
        ),
        barrier_conversations=("has_barrier", "sum"),
        assessable_agent_helpfulness_conversations=(
            "assessable_agent_helpfulness",
            "sum",
        ),
        agent_helpful_conversations=("agent_helpful", "sum"),
        assessable_specificity_conversations=("assessable_specificity", "sum"),
        specific_customer_need_conversations=("specific_customer_need", "sum"),
        high_specificity_conversations=("high_specificity", "sum"),
        assessable_urgency_conversations=("assessable_urgency", "sum"),
        urgency_present_conversations=("urgency_present", "sum"),
        high_urgency_conversations=("high_urgency", "sum"),
        urgency_elicited_by_agent_conversations=(
            "urgency_elicited_by_agent",
            "sum",
        ),
        assessable_price_sensitivity_conversations=(
            "assessable_price_sensitivity",
            "sum",
        ),
        price_sensitive_conversations=("price_sensitive", "sum"),
        price_blocking_conversations=("price_blocking", "sum"),
        assessable_deal_seeking_conversations=("assessable_deal_seeking", "sum"),
        deal_seeking_conversations=("deal_seeking", "sum"),
        deal_required_conversations=("deal_required", "sum"),
        assessable_financing_conversations=("assessable_financing", "sum"),
        financing_discussion_conversations=("financing_discussed", "sum"),
        strong_financing_conversations=("strong_financing", "sum"),
        assessable_delivery_intent_conversations=(
            "assessable_delivery_intent",
            "sum",
        ),
        delivery_present_conversations=("delivery_present", "sum"),
        delivery_ready_conversations=("delivery_ready", "sum"),
        delivery_elicited_by_agent_conversations=(
            "delivery_elicited_by_agent",
            "sum",
        ),
        assessable_sales_agreement_conversations=(
            "assessable_sales_agreement",
            "sum",
        ),
        sales_agreement_conversations=("sales_agreement", "sum"),
        blocking_barrier_conversations=("blocking_barrier", "sum"),
        assessable_barrier_conversations=("assessable_barrier_resolution", "sum"),
        resolved_barrier_conversations=("barrier_resolved", "sum"),
        competitor_mention_conversations=("competitor_mentioned", "sum"),
        brand_preference_conversations=("brand_preference", "sum"),
        feature_priority_conversations=("feature_priority", "sum"),
        bulk_purchase_interest_conversations=("bulk_purchase_interest", "sum"),
        customization_interest_conversations=("customization_interest", "sum"),
        assessable_agent_tone_conversations=("assessable_agent_tone", "sum"),
        positive_agent_tone_conversations=("positive_agent_tone", "sum"),
        mixed_agent_tone_conversations=("mixed_agent_tone", "sum"),
        negative_agent_tone_conversations=("negative_agent_tone", "sum"),
        assessable_next_step_agreement_conversations=(
            "assessable_next_step_agreement",
            "sum",
        ),
        next_step_agreed_conversations=("next_step_agreed", "sum"),
        next_step_order_progression_conversations=(
            "next_step_order_progression",
            "sum",
        ),
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
                "top_commercial_trait": _top_value(
                    item
                    for values in group["commercial_traits"]
                    for item in values
                ),
                "top_agent_tone": _top_value(
                    item
                    for values in group["agent_tone_labels"]
                    for item in values
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
        result["high_purchase_intent_conversations"]
        / result["assessable_purchase_intent_conversations"].replace(0, pd.NA)
    )
    result["barrier_conversation_rate"] = result["barrier_conversations"] / denominator
    result["agent_helpful_rate"] = (
        result["agent_helpful_conversations"]
        / result["assessable_agent_helpfulness_conversations"].replace(0, pd.NA)
    )
    for count_column, assessable_column, rate_column in (
        (
            "specific_customer_need_conversations",
            "assessable_specificity_conversations",
            "specific_customer_need_rate",
        ),
        (
            "high_specificity_conversations",
            "assessable_specificity_conversations",
            "high_specificity_rate",
        ),
        (
            "high_urgency_conversations",
            "assessable_urgency_conversations",
            "high_urgency_rate",
        ),
        (
            "urgency_elicited_by_agent_conversations",
            "urgency_present_conversations",
            "urgency_elicited_by_agent_rate",
        ),
        (
            "price_sensitive_conversations",
            "assessable_price_sensitivity_conversations",
            "price_sensitive_rate",
        ),
        (
            "price_blocking_conversations",
            "assessable_price_sensitivity_conversations",
            "price_blocking_rate",
        ),
        (
            "deal_seeking_conversations",
            "assessable_deal_seeking_conversations",
            "deal_seeking_rate",
        ),
        (
            "deal_required_conversations",
            "assessable_deal_seeking_conversations",
            "deal_required_rate",
        ),
        (
            "financing_discussion_conversations",
            "assessable_financing_conversations",
            "financing_discussion_rate",
        ),
        (
            "strong_financing_conversations",
            "assessable_financing_conversations",
            "strong_financing_rate",
        ),
        (
            "delivery_ready_conversations",
            "assessable_delivery_intent_conversations",
            "delivery_ready_rate",
        ),
        (
            "delivery_elicited_by_agent_conversations",
            "delivery_present_conversations",
            "delivery_elicited_by_agent_rate",
        ),
        (
            "sales_agreement_conversations",
            "assessable_sales_agreement_conversations",
            "sales_agreement_rate",
        ),
        (
            "positive_agent_tone_conversations",
            "assessable_agent_tone_conversations",
            "positive_agent_tone_rate",
        ),
        (
            "mixed_agent_tone_conversations",
            "assessable_agent_tone_conversations",
            "mixed_agent_tone_rate",
        ),
        (
            "negative_agent_tone_conversations",
            "assessable_agent_tone_conversations",
            "negative_agent_tone_rate",
        ),
        (
            "next_step_agreed_conversations",
            "assessable_next_step_agreement_conversations",
            "next_step_agreement_rate",
        ),
    ):
        result[rate_column] = result[count_column] / result[
            assessable_column
        ].replace(0, pd.NA)
    for count_column, rate_column in (
        ("blocking_barrier_conversations", "blocking_barrier_rate"),
        ("competitor_mention_conversations", "competitor_mention_rate"),
        ("brand_preference_conversations", "brand_preference_rate"),
        ("feature_priority_conversations", "feature_priority_rate"),
        ("bulk_purchase_interest_conversations", "bulk_purchase_interest_rate"),
        ("customization_interest_conversations", "customization_interest_rate"),
    ):
        result[rate_column] = result[count_column] / denominator
    result["barrier_resolution_rate"] = result["resolved_barrier_conversations"] / result[
        "assessable_barrier_conversations"
    ].replace(0, pd.NA)
    result["next_step_order_progression_rate"] = result[
        "next_step_order_progression_conversations"
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
