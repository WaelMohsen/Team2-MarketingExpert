"""Normalize one completed cycle into privacy-safe canonical fact tables."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pandas as pd

from .loaders import RawCyclePayload

META_CONVERSATION_ACTION = "onsite_conversion.messaging_conversation_started_7d"
NEGATIVE_OUTCOMES = {"ghosted", "cancelled", "refunded", "adversarial"}
OPEN_OUTCOMES = {"active", "stuck_pending"}


@dataclass(frozen=True)
class CanonicalCycleData:
    """Dimensions and facts at their natural grain.

    Raw message text, phone numbers, and customer names are deliberately omitted.
    """

    campaigns: pd.DataFrame
    adsets: pd.DataFrame
    ads: pd.DataFrame
    creatives: pd.DataFrame
    media_daily: pd.DataFrame
    conversations: pd.DataFrame
    order_lines: pd.DataFrame
    products: pd.DataFrame
    source_directory: str

    @property
    def cycle_start(self) -> pd.Timestamp | None:
        if self.media_daily.empty:
            return None
        return self.media_daily["date_start"].min()

    @property
    def cycle_end(self) -> pd.Timestamp | None:
        if self.media_daily.empty:
            return None
        return self.media_daily["date_stop"].max()


def _require_list(payload: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"meta_data.json must contain a list named {key!r}")
    return value


def _optional_id(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(value)


def _normalize_dimensions(
    meta: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    campaigns = pd.json_normalize(_require_list(meta, "campaigns"))
    adsets = pd.json_normalize(_require_list(meta, "adsets"))
    ads = pd.json_normalize(_require_list(meta, "ads"))
    creatives = pd.json_normalize(_require_list(meta, "creatives"))

    for frame, label in (
        (campaigns, "campaigns"),
        (adsets, "adsets"),
        (ads, "ads"),
        (creatives, "creatives"),
    ):
        if frame.empty or "id" not in frame:
            raise ValueError(f"{label} must contain at least one record with an id")
        frame.drop_duplicates("id", keep="last", inplace=True)
        frame["id"] = frame["id"].astype(str)

    campaigns = campaigns.rename(columns={"id": "campaign_id", "name": "campaign_name"})
    adsets = adsets.rename(columns={"id": "adset_id", "name": "adset_name"})
    ads = ads.rename(
        columns={"id": "ad_id", "name": "ad_name", "creative.id": "creative_id"}
    )
    creatives = creatives.rename(
        columns={"id": "creative_id", "name": "creative_name"}
    )

    for frame, columns in (
        (campaigns, ("campaign_id",)),
        (adsets, ("adset_id", "campaign_id")),
        (ads, ("ad_id", "adset_id", "campaign_id", "creative_id")),
        (creatives, ("creative_id",)),
    ):
        for column in columns:
            if column in frame:
                frame[column] = frame[column].map(_optional_id)

    for frame in (campaigns, ads):
        for column in ("start_date", "end_date"):
            if column in frame:
                frame[column] = pd.to_datetime(frame[column], errors="coerce")

    if "daily_budget" in adsets:
        adsets["daily_budget_raw"] = pd.to_numeric(
            adsets["daily_budget"], errors="coerce"
        )

    return campaigns, adsets, ads, creatives


def _extract_action_value(actions: Any, action_type: str) -> float:
    if not isinstance(actions, list):
        return 0.0
    return sum(
        float(item.get("value", 0) or 0)
        for item in actions
        if item.get("action_type") == action_type
    )


def _normalize_media(
    meta: Mapping[str, Any], ads: pd.DataFrame, adsets: pd.DataFrame
) -> pd.DataFrame:
    media = pd.json_normalize(_require_list(meta, "insights"))
    required = {"ad_id", "adset_id", "campaign_id", "date_start", "date_stop"}
    missing = required.difference(media.columns)
    if missing:
        raise ValueError(f"insights are missing required fields: {sorted(missing)}")

    for column in ("ad_id", "adset_id", "campaign_id"):
        media[column] = media[column].map(_optional_id)
    for column in ("date_start", "date_stop"):
        media[column] = pd.to_datetime(media[column], errors="coerce")
    for column in (
        "impressions",
        "reach",
        "frequency",
        "clicks",
        "link_clicks",
        "ctr",
        "spend",
        "cpm",
    ):
        if column not in media:
            media[column] = 0.0
        media[column] = pd.to_numeric(media[column], errors="coerce").fillna(0.0)

    media["meta_conversation_starts"] = media.get(
        "actions", pd.Series([[]] * len(media), index=media.index)
    ).map(lambda value: _extract_action_value(value, META_CONVERSATION_ACTION))
    media = media.drop_duplicates(["ad_id", "date_start"], keep="last")

    media = media.merge(
        ads[["ad_id", "creative_id"]].drop_duplicates("ad_id"),
        on="ad_id",
        how="left",
    )
    media = media.merge(
        adsets[["adset_id", "audience_type"]].drop_duplicates("adset_id"),
        on="adset_id",
        how="left",
    )
    return media


def _normalize_conversations(
    raw: list[dict[str, Any]], ads: pd.DataFrame, adsets: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ad_lookup = ads.set_index("ad_id").to_dict("index")
    audience_lookup = adsets.set_index("adset_id")["audience_type"].to_dict()
    conversation_rows: list[dict[str, Any]] = []
    line_rows: list[dict[str, Any]] = []

    for item in raw:
        source = item.get("source") or {}
        customer = item.get("customer") or {}
        outcome = item.get("outcome") or {}
        messages = item.get("messages") or []

        ad_id = _optional_id(source.get("ad_id"))
        ad_record = ad_lookup.get(ad_id, {}) if ad_id else {}
        adset_id = _optional_id(ad_record.get("adset_id"))
        campaign_id = _optional_id(source.get("campaign_id"))
        campaign_id = campaign_id or _optional_id(ad_record.get("campaign_id"))
        creative_id = _optional_id(source.get("creative_id"))
        creative_id = creative_id or _optional_id(ad_record.get("creative_id"))
        audience_type = audience_lookup.get(adset_id)

        outcome_type = str(outcome.get("type") or "unknown").lower()
        total = float(outcome.get("total", 0) or 0)
        refunded_amount = float(outcome.get("refunded_amount", 0) or 0)
        cycle_number = int(item.get("cycle") or 0)
        started_at = pd.to_datetime(item.get("started_at"), errors="coerce", utc=True)
        last_message_at = pd.to_datetime(
            item.get("last_message_at"), errors="coerce", utc=True
        )
        duration_minutes = None
        if pd.notna(started_at) and pd.notna(last_message_at):
            duration_minutes = (last_message_at - started_at).total_seconds() / 60

        has_order = bool(outcome.get("order_id"))
        delivered_revenue = total if outcome_type == "delivered" else 0.0
        if outcome_type == "delivered":
            net_revenue = total
        elif outcome_type == "refunded":
            net_revenue = max(total - refunded_amount, 0.0)
        else:
            net_revenue = 0.0

        row = {
            "conversation_id": _optional_id(item.get("id")),
            "campaign_id": campaign_id,
            "adset_id": adset_id,
            "ad_id": ad_id,
            "creative_id": creative_id,
            "audience_type": audience_type,
            "source_platform": source.get("platform"),
            "customer_id": _optional_id(customer.get("id")),
            "language": item.get("language"),
            "cycle_number": cycle_number,
            "started_at": started_at,
            "last_message_at": last_message_at,
            "conversation_minutes": duration_minutes,
            "message_count": len(messages),
            "inbound_messages": sum(
                message.get("direction") == "inbound" for message in messages
            ),
            "outbound_messages": sum(
                message.get("direction") == "outbound" for message in messages
            ),
            "outcome_type": outcome_type,
            "order_id": _optional_id(outcome.get("order_id")),
            "has_order": has_order,
            "is_delivered": outcome_type == "delivered",
            "is_refunded": outcome_type == "refunded",
            "is_cancelled": outcome_type == "cancelled",
            "is_ghosted": outcome_type == "ghosted",
            "is_negative": outcome_type in NEGATIVE_OUTCOMES,
            "is_open_or_pending": outcome_type in OPEN_OUTCOMES,
            "is_repeat_cycle": cycle_number > 1,
            "is_repeat_delivered": cycle_number > 1 and outcome_type == "delivered",
            "gross_order_value": total if has_order else 0.0,
            "delivered_revenue": delivered_revenue,
            "net_revenue": net_revenue,
            "refunded_amount": refunded_amount,
            "cancelled_value": total if outcome_type == "cancelled" else 0.0,
            "pending_value": total if outcome_type == "stuck_pending" else 0.0,
        }
        conversation_rows.append(row)

        for line in outcome.get("line_items") or []:
            quantity = float(line.get("quantity", 0) or 0)
            unit_price = float(line.get("unit_price", 0) or 0)
            line_rows.append(
                {
                    "conversation_id": row["conversation_id"],
                    "campaign_id": campaign_id,
                    "adset_id": adset_id,
                    "ad_id": ad_id,
                    "creative_id": creative_id,
                    "audience_type": audience_type,
                    "outcome_type": outcome_type,
                    "order_id": row["order_id"],
                    "product_id": _optional_id(line.get("product_id")),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_value": quantity * unit_price,
                }
            )

    conversations = pd.DataFrame(conversation_rows)
    if not conversations.empty:
        conversations = conversations.drop_duplicates("conversation_id", keep="last")
    return conversations, pd.DataFrame(line_rows)


def normalize_cycle(payload: RawCyclePayload) -> CanonicalCycleData:
    campaigns, adsets, ads, creatives = _normalize_dimensions(payload.meta)
    media = _normalize_media(payload.meta, ads, adsets)
    conversations, order_lines = _normalize_conversations(
        payload.conversations, ads, adsets
    )

    products = pd.json_normalize(payload.products)
    if not products.empty and "id" in products:
        products = products.rename(columns={"id": "product_id"})
        products["product_id"] = products["product_id"].map(_optional_id)
        products = products.drop_duplicates("product_id", keep="last")
    if not order_lines.empty and not products.empty:
        order_lines = order_lines.merge(products, on="product_id", how="left")

    return CanonicalCycleData(
        campaigns=campaigns,
        adsets=adsets,
        ads=ads,
        creatives=creatives,
        media_daily=media,
        conversations=conversations,
        order_lines=order_lines,
        products=products,
        source_directory=str(payload.source_directory),
    )
