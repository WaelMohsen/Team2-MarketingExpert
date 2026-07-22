"""Load and normalize one completed marketing-results cycle from Sample 2 JSON."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import pandas as pd

META_CONVERSATION_ACTION = "onsite_conversion.messaging_conversation_started_7d"
NEGATIVE_OUTCOMES = {"ghosted", "cancelled", "refunded", "adversarial"}
OPEN_OUTCOMES = {"active", "stuck_pending"}


@dataclass
class CycleData:
    campaigns: pd.DataFrame
    adsets: pd.DataFrame
    ads: pd.DataFrame
    creatives: pd.DataFrame
    insights: pd.DataFrame
    conversations: pd.DataFrame
    line_items: pd.DataFrame
    products: pd.DataFrame
    source_dir: Optional[str] = None

    @property
    def cycle_start(self):
        if self.insights.empty:
            return None
        return self.insights["date_start"].min()

    @property
    def cycle_end(self):
        if self.insights.empty:
            return None
        return self.insights["date_stop"].max()


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _require_list(payload: Mapping[str, Any], key: str) -> List[dict]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"meta_data.json must contain a list named {key!r}")
    return value


def _normalize_dimensions(meta_data: Mapping[str, Any]):
    campaigns = pd.json_normalize(_require_list(meta_data, "campaigns"))
    adsets = pd.json_normalize(_require_list(meta_data, "adsets"))
    creatives = pd.json_normalize(_require_list(meta_data, "creatives"))
    ads = pd.json_normalize(_require_list(meta_data, "ads"))

    for frame, label in (
        (campaigns, "campaigns"),
        (adsets, "adsets"),
        (creatives, "creatives"),
        (ads, "ads"),
    ):
        if frame.empty or "id" not in frame:
            raise ValueError(f"{label} must contain at least one record with an id")
        frame.drop_duplicates("id", keep="last", inplace=True)
        frame["id"] = frame["id"].astype(str)

    campaigns = campaigns.rename(columns={"id": "campaign_id", "name": "campaign_name"})
    adsets = adsets.rename(columns={"id": "adset_id", "name": "adset_name"})
    creatives = creatives.rename(columns={"id": "creative_id", "name": "creative_name"})
    ads = ads.rename(
        columns={
            "id": "ad_id",
            "name": "ad_name",
            "creative.id": "creative_id",
        }
    )

    for frame, columns in (
        (campaigns, ("campaign_id",)),
        (adsets, ("adset_id", "campaign_id")),
        (ads, ("ad_id", "adset_id", "campaign_id", "creative_id")),
        (creatives, ("creative_id",)),
    ):
        for column in columns:
            if column in frame:
                frame[column] = frame[column].astype(str)

    for frame in (campaigns, ads):
        for column in ("start_date", "end_date"):
            if column in frame:
                frame[column] = pd.to_datetime(frame[column], errors="coerce")

    if "daily_budget" in adsets:
        adsets["daily_budget_raw"] = pd.to_numeric(
            adsets["daily_budget"], errors="coerce"
        )

    return campaigns, adsets, ads, creatives


def _extract_action_value(actions, action_type: str) -> float:
    if not isinstance(actions, list):
        return 0.0
    return sum(
        float(action.get("value", 0) or 0)
        for action in actions
        if action.get("action_type") == action_type
    )


def _normalize_insights(meta_data: Mapping[str, Any]) -> pd.DataFrame:
    insights = pd.json_normalize(_require_list(meta_data, "insights"))
    required = {"ad_id", "adset_id", "campaign_id", "date_start", "date_stop"}
    missing = required.difference(insights.columns)
    if missing:
        raise ValueError(f"insights are missing required fields: {sorted(missing)}")

    for column in ("ad_id", "adset_id", "campaign_id"):
        insights[column] = insights[column].astype(str)
    for column in ("date_start", "date_stop"):
        insights[column] = pd.to_datetime(insights[column], errors="coerce")
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
        if column in insights:
            insights[column] = pd.to_numeric(insights[column], errors="coerce").fillna(
                0
            )
        else:
            insights[column] = 0.0

    insights["meta_conversation_starts"] = insights.get(
        "actions", pd.Series([[]] * len(insights), index=insights.index)
    ).apply(lambda value: _extract_action_value(value, META_CONVERSATION_ACTION))

    # A fresh export can restate attributed actions for a previous day. Keep the
    # latest record for each ad/day instead of double-counting the restatement.
    insights = insights.drop_duplicates(["ad_id", "date_start"], keep="last")
    return insights


def _normalize_conversations(
    conversations_raw: List[dict], ads: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ad_to_adset = ads.set_index("ad_id")["adset_id"].to_dict()
    records = []
    line_items = []

    for conversation in conversations_raw:
        source = conversation.get("source") or {}
        customer = conversation.get("customer") or {}
        outcome = conversation.get("outcome") or {}
        messages = conversation.get("messages") or []

        outcome_type = str(outcome.get("type") or "unknown").lower()
        total = float(outcome.get("total", 0) or 0)
        refunded_amount = float(outcome.get("refunded_amount", 0) or 0)
        cycle = int(conversation.get("cycle") or 0)
        ad_id = source.get("ad_id")
        ad_id = str(ad_id) if ad_id is not None else None
        started_at = pd.to_datetime(conversation.get("started_at"), errors="coerce")
        last_message_at = pd.to_datetime(
            conversation.get("last_message_at"), errors="coerce"
        )
        duration_minutes = None
        if pd.notna(started_at) and pd.notna(last_message_at):
            duration_minutes = (last_message_at - started_at).total_seconds() / 60

        has_order = bool(outcome.get("order_id"))
        delivered_revenue = total if outcome_type == "delivered" else 0.0
        net_revenue = 0.0
        if outcome_type == "delivered":
            net_revenue = total
        elif outcome_type == "refunded":
            net_revenue = max(total - refunded_amount, 0.0)

        record = {
            "conversation_id": conversation.get("id"),
            "campaign_id": source.get("campaign_id"),
            "adset_id": ad_to_adset.get(ad_id),
            "ad_id": ad_id,
            "creative_id": source.get("creative_id"),
            "source_platform": source.get("platform"),
            "customer_id": customer.get("id"),
            "language": conversation.get("language"),
            "cycle": cycle,
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
            "order_id": outcome.get("order_id"),
            "has_order": has_order,
            "is_delivered": outcome_type == "delivered",
            "is_refunded": outcome_type == "refunded",
            "is_cancelled": outcome_type == "cancelled",
            "is_ghosted": outcome_type == "ghosted",
            "is_negative": outcome_type in NEGATIVE_OUTCOMES,
            "is_open_or_pending": outcome_type in OPEN_OUTCOMES,
            "is_repeat_cycle": cycle > 1,
            "is_repeat_delivered": cycle > 1 and outcome_type == "delivered",
            "gross_order_value": total if has_order else 0.0,
            "delivered_revenue": delivered_revenue,
            "net_revenue": net_revenue,
            "refunded_amount": refunded_amount,
            "cancelled_value": total if outcome_type == "cancelled" else 0.0,
            "pending_value": total if outcome_type == "stuck_pending" else 0.0,
        }
        records.append(record)

        for item in outcome.get("line_items") or []:
            quantity = float(item.get("quantity", 0) or 0)
            unit_price = float(item.get("unit_price", 0) or 0)
            line_items.append(
                {
                    "conversation_id": conversation.get("id"),
                    "campaign_id": source.get("campaign_id"),
                    "adset_id": ad_to_adset.get(ad_id),
                    "ad_id": ad_id,
                    "creative_id": source.get("creative_id"),
                    "outcome_type": outcome_type,
                    "order_id": outcome.get("order_id"),
                    "product_id": item.get("product_id"),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_value": quantity * unit_price,
                }
            )

    conversations = pd.DataFrame(records)
    if not conversations.empty:
        conversations = conversations.drop_duplicates("conversation_id", keep="last")
        for column in ("campaign_id", "adset_id", "ad_id", "creative_id"):
            conversations[column] = conversations[column].apply(
                lambda value: (
                    str(value) if pd.notna(value) and value is not None else None
                )
            )
    return conversations, pd.DataFrame(line_items)


def build_cycle_data(
    meta_data: Mapping[str, Any],
    conversations_raw: List[dict],
    products_raw: List[dict],
    *,
    source_dir: Optional[str] = None,
) -> CycleData:
    """Build normalized tables from already-decoded JSON payloads."""
    if not isinstance(meta_data, Mapping):
        raise ValueError("meta_data.json must contain a JSON object")
    if not isinstance(conversations_raw, list):
        raise ValueError("conversations.json must contain a JSON list")
    if not isinstance(products_raw, list):
        raise ValueError("products.json must contain a JSON list")

    campaigns, adsets, ads, creatives = _normalize_dimensions(meta_data)
    insights = _normalize_insights(meta_data)
    conversations, line_items = _normalize_conversations(conversations_raw, ads)
    products = pd.json_normalize(products_raw)
    if not products.empty and "id" in products:
        products = products.rename(columns={"id": "product_id"})
        products["product_id"] = products["product_id"].astype(str)
        products = products.drop_duplicates("product_id", keep="last")
    if not line_items.empty and not products.empty:
        line_items["product_id"] = line_items["product_id"].astype(str)
        line_items = line_items.merge(products, on="product_id", how="left")

    return CycleData(
        campaigns=campaigns,
        adsets=adsets,
        ads=ads,
        creatives=creatives,
        insights=insights,
        conversations=conversations,
        line_items=line_items,
        products=products,
        source_dir=source_dir,
    )


def default_sample2_dir() -> str:
    configured = os.getenv("SAMPLE2_DATA_DIR")
    if configured:
        configured_path = Path(configured).expanduser()
        if configured_path.is_absolute():
            return str(configured_path)
        workspace_relative = Path(__file__).resolve().parents[3] / configured_path
        if workspace_relative.exists():
            return str(workspace_relative)
        return str((Path.cwd() / configured_path).resolve())
    return str(Path(__file__).resolve().parents[3] / "samples (2)")


def load_cycle_data(data_dir: Optional[str] = None) -> CycleData:
    """Load one cycle from a directory containing the three Sample 2 files."""
    source = Path(data_dir or default_sample2_dir()).expanduser().resolve()
    required = {
        "meta_data": source / "meta_data.json",
        "conversations": source / "conversations.json",
        "products": source / "products.json",
    }
    missing = [path.name for path in required.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing cycle files in {source}: {', '.join(sorted(missing))}"
        )
    return build_cycle_data(
        _load_json(required["meta_data"]),
        _load_json(required["conversations"]),
        _load_json(required["products"]),
        source_dir=str(source),
    )


def data_quality_summary(data: CycleData) -> Dict[str, Any]:
    meta_conversation_starts = float(data.insights["meta_conversation_starts"].sum())
    meta_outcomes = data.conversations[
        data.conversations["source_platform"].eq("meta_ctwa")
    ]
    observed = int(meta_outcomes["conversation_id"].nunique())
    coverage = observed / meta_conversation_starts if meta_conversation_starts else None

    campaign_ids = set(data.campaigns["campaign_id"])
    adset_ids = set(data.adsets["adset_id"])
    ad_ids = set(data.ads["ad_id"])
    warnings = []
    if coverage is not None and coverage < 0.8:
        warnings.append(
            "The WhatsApp outcome file covers only part of Meta-attributed conversation starts; use outcome results as observed-sample evidence."
        )

    unmatched_campaigns = int((~meta_outcomes["campaign_id"].isin(campaign_ids)).sum())
    unmatched_adsets = int((~meta_outcomes["adset_id"].isin(adset_ids)).sum())
    unmatched_ads = int((~meta_outcomes["ad_id"].isin(ad_ids)).sum())
    if unmatched_campaigns or unmatched_adsets or unmatched_ads:
        warnings.append(
            "Some WhatsApp outcomes could not be joined to the Meta hierarchy."
        )

    return {
        "cycle_start": data.cycle_start,
        "cycle_end": data.cycle_end,
        "campaigns": len(data.campaigns),
        "adsets": len(data.adsets),
        "ads": len(data.ads),
        "creatives": len(data.creatives),
        "insight_rows": len(data.insights),
        "meta_conversation_starts": meta_conversation_starts,
        "observed_meta_whatsapp_conversations": observed,
        "outcome_coverage_ratio": coverage,
        "unmatched_campaign_outcomes": unmatched_campaigns,
        "unmatched_adset_outcomes": unmatched_adsets,
        "unmatched_ad_outcomes": unmatched_ads,
        "warnings": warnings,
    }
