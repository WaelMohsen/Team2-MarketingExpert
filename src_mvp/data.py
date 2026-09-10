"""Load Sample 2 and keep only facts required by the MVP."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .paths import ARTIFACT_DIR, INPUT_DIR


META_CONVERSATION_ACTION = "onsite_conversion.messaging_conversation_started_7d"
OPEN_OUTCOMES = {"active", "stuck_pending"}


@dataclass(frozen=True)
class CanonicalData:
    campaigns: pd.DataFrame
    adsets: pd.DataFrame
    ads: pd.DataFrame
    creatives: pd.DataFrame
    media_daily: pd.DataFrame
    conversations: pd.DataFrame
    source_directory: Path

    @property
    def cycle_start(self) -> Optional[pd.Timestamp]:
        if self.media_daily.empty:
            return None
        return self.media_daily["date_start"].min()

    @property
    def cycle_end(self) -> Optional[pd.Timestamp]:
        if self.media_daily.empty:
            return None
        return self.media_daily["date_stop"].max()


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Required MVP input is missing: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _optional_id(value: Any) -> Optional[str]:
    if value is None or pd.isna(value):
        return None
    return str(value)


def _records(meta: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
    value = meta.get(key)
    if not isinstance(value, list):
        raise ValueError(f"meta_data.json must contain a list named {key!r}")
    return value


def _dimensions(
    meta: Dict[str, Any]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    campaigns = pd.json_normalize(_records(meta, "campaigns")).rename(
        columns={"id": "campaign_id", "name": "campaign_name"}
    )
    adsets = pd.json_normalize(_records(meta, "adsets")).rename(
        columns={"id": "adset_id", "name": "adset_name"}
    )
    ads = pd.json_normalize(_records(meta, "ads")).rename(
        columns={"id": "ad_id", "name": "ad_name", "creative.id": "creative_id"}
    )
    creatives = pd.json_normalize(_records(meta, "creatives")).rename(
        columns={"id": "creative_id", "name": "creative_name"}
    )

    selections = (
        (
            campaigns,
            [
                "campaign_id",
                "campaign_name",
                "objective",
                "status",
                "effective_status",
                "start_date",
                "end_date",
            ],
            ["campaign_id"],
        ),
        (
            adsets,
            [
                "adset_id",
                "adset_name",
                "campaign_id",
                "audience_type",
                "status",
                "effective_status",
            ],
            ["adset_id", "campaign_id"],
        ),
        (
            ads,
            [
                "ad_id",
                "ad_name",
                "adset_id",
                "campaign_id",
                "creative_id",
                "status",
                "effective_status",
                "start_date",
                "end_date",
            ],
            ["ad_id", "adset_id", "campaign_id", "creative_id"],
        ),
        (
            creatives,
            ["creative_id", "creative_name", "theme", "angle", "status"],
            ["creative_id"],
        ),
    )
    normalized = []
    for frame, columns, id_columns in selections:
        frame = frame[[column for column in columns if column in frame]].copy()
        for column in id_columns:
            if column in frame:
                frame[column] = frame[column].map(_optional_id)
        frame = frame.drop_duplicates(id_columns[0], keep="last")
        normalized.append(frame)

    campaigns, adsets, ads, creatives = normalized
    for frame in (campaigns, ads):
        for column in ("start_date", "end_date"):
            if column in frame:
                frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return campaigns, adsets, ads, creatives


def _action_value(actions: Any, action_type: str) -> float:
    if not isinstance(actions, list):
        return 0.0
    return sum(
        float(item.get("value", 0) or 0)
        for item in actions
        if item.get("action_type") == action_type
    )


def _media(
    meta: Dict[str, Any], ads: pd.DataFrame, adsets: pd.DataFrame
) -> pd.DataFrame:
    frame = pd.json_normalize(_records(meta, "insights"))
    required = {"ad_id", "adset_id", "campaign_id", "date_start", "date_stop"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Meta insights are missing fields: {sorted(missing)}")
    for column in ("ad_id", "adset_id", "campaign_id"):
        frame[column] = frame[column].map(_optional_id)
    for column in ("date_start", "date_stop"):
        frame[column] = pd.to_datetime(frame[column], errors="coerce")
    for column in ("impressions", "reach", "link_clicks", "spend"):
        frame[column] = pd.to_numeric(frame.get(column, 0), errors="coerce").fillna(0.0)
    actions = frame.get("actions", pd.Series([[]] * len(frame), index=frame.index))
    frame["meta_conversation_starts"] = actions.map(
        lambda value: _action_value(value, META_CONVERSATION_ACTION)
    )
    frame["reach_exceeds_impressions"] = frame["reach"].gt(frame["impressions"])
    frame = frame.drop_duplicates(["ad_id", "date_start"], keep="last")
    frame = frame.merge(
        ads[["ad_id", "creative_id"]].drop_duplicates("ad_id"),
        on="ad_id",
        how="left",
    )
    frame = frame.merge(
        adsets[["adset_id", "audience_type"]].drop_duplicates("adset_id"),
        on="adset_id",
        how="left",
    )
    return frame[
        [
            "campaign_id",
            "adset_id",
            "ad_id",
            "creative_id",
            "audience_type",
            "date_start",
            "date_stop",
            "impressions",
            "reach",
            "link_clicks",
            "spend",
            "meta_conversation_starts",
            "reach_exceeds_impressions",
        ]
    ]


def _conversations(
    raw: List[Dict[str, Any]],
    campaigns: pd.DataFrame,
    ads: pd.DataFrame,
    adsets: pd.DataFrame,
) -> pd.DataFrame:
    ad_lookup = ads.set_index("ad_id").to_dict("index")
    audience_lookup = adsets.set_index("adset_id")["audience_type"].to_dict()
    valid_campaigns = set(campaigns["campaign_id"].dropna().astype(str))
    rows: List[Dict[str, Any]] = []
    for item in raw:
        source = item.get("source") or {}
        outcome = item.get("outcome") or {}
        customer = item.get("customer") or {}
        conversation_id = _optional_id(item.get("id"))
        ad_id = _optional_id(source.get("ad_id"))
        ad = ad_lookup.get(ad_id, {}) if ad_id else {}
        campaign_id = _optional_id(source.get("campaign_id")) or _optional_id(
            ad.get("campaign_id")
        )
        if campaign_id not in valid_campaigns:
            continue
        adset_id = _optional_id(ad.get("adset_id"))
        creative_id = _optional_id(source.get("creative_id")) or _optional_id(
            ad.get("creative_id")
        )
        outcome_type = str(outcome.get("type") or "unknown").lower()
        mature = outcome_type not in OPEN_OUTCOMES
        has_order = bool(outcome.get("order_id"))
        total = float(outcome.get("total", 0) or 0)
        refunded = float(outcome.get("refunded_amount", 0) or 0)
        if outcome_type == "delivered":
            net_revenue = total
        elif outcome_type == "refunded":
            net_revenue = max(total - refunded, 0.0)
        else:
            net_revenue = 0.0
        customer_id = _optional_id(customer.get("id"))
        rows.append(
            {
                "conversation_id": conversation_id,
                "started_at": pd.to_datetime(item.get("started_at"), utc=True, errors="coerce"),
                "customer_key": customer_id or f"conversation::{conversation_id}",
                "campaign_id": campaign_id,
                "adset_id": adset_id,
                "ad_id": ad_id,
                "creative_id": creative_id,
                "audience_type": audience_lookup.get(adset_id),
                "outcome_type": outcome_type,
                "is_mature": mature,
                "is_unresolved": not mature,
                "has_order": has_order,
                "has_mature_order": has_order and mature,
                "is_delivered": outcome_type == "delivered",
                "net_revenue": net_revenue,
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("No paid-attributed conversations were found")
    return frame.drop_duplicates("conversation_id", keep="last")


def load_cycle(input_directory: Optional[Path] = None) -> CanonicalData:
    source = (input_directory or INPUT_DIR).expanduser().resolve()
    meta = _read_json(source / "meta_data.json")
    conversations = _read_json(source / "conversations.json")
    if not isinstance(meta, dict) or not isinstance(conversations, list):
        raise ValueError("Unexpected Sample 2 JSON structure")
    campaigns, adsets, ads, creatives = _dimensions(meta)
    return CanonicalData(
        campaigns=campaigns,
        adsets=adsets,
        ads=ads,
        creatives=creatives,
        media_daily=_media(meta, ads, adsets),
        conversations=_conversations(conversations, campaigns, ads, adsets),
        source_directory=source,
    )


def load_conversation_signals(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    source = path or ARTIFACT_DIR / "conversation_signals_v3_paid.jsonl"
    if not source.exists():
        return []
    records: List[Dict[str, Any]] = []
    with source.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if int(record.get("signal_schema_version", 0)) < 3:
                raise ValueError(
                    f"Signal line {line_number} is not schema v3 or later"
                )
            if not isinstance(record.get("signals"), dict):
                raise ValueError(f"Signal line {line_number} has no signals object")
            records.append(record)
    unique = {str(record["conversation_id"]): record for record in records}
    return list(unique.values())
