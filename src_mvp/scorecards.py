"""Build compact objective-ready aggregates at five entity levels."""

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from .data import CanonicalData


LEVELS = ("campaign", "adset", "ad", "creative", "audience")


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = pd.to_numeric(denominator, errors="coerce").astype(float)
    numerator = pd.to_numeric(numerator, errors="coerce").astype(float)
    return numerator.div(denominator).where(denominator.ne(0))


def _dimensions(data: CanonicalData, level: str) -> pd.DataFrame:
    campaigns = data.campaigns[
        [
            "campaign_id",
            "campaign_name",
            "objective",
            "status",
            "start_date",
            "end_date",
        ]
    ].copy()
    campaigns = campaigns.rename(columns={"status": "entity_status"})
    common = campaigns[["campaign_id", "campaign_name", "objective"]]
    if level == "campaign":
        frame = campaigns
        frame["entity_id"] = frame["campaign_id"]
        frame["entity_name"] = frame["campaign_name"]
        frame["parent_entity_id"] = None
    elif level == "adset":
        columns = ["adset_id", "adset_name", "campaign_id", "audience_type", "status"]
        frame = data.adsets[[column for column in columns if column in data.adsets]].copy()
        frame = frame.rename(columns={"status": "entity_status"}).merge(
            common, on="campaign_id", how="left"
        )
        frame["entity_id"] = frame["adset_id"]
        frame["entity_name"] = frame["adset_name"]
        frame["parent_entity_id"] = frame["campaign_id"]
    elif level == "ad":
        columns = [
            "ad_id",
            "ad_name",
            "adset_id",
            "campaign_id",
            "creative_id",
            "status",
            "start_date",
            "end_date",
        ]
        frame = data.ads[[column for column in columns if column in data.ads]].copy()
        frame = frame.rename(
            columns={
                "status": "entity_status",
                "start_date": "configured_start_date",
                "end_date": "configured_end_date",
            }
        ).merge(common, on="campaign_id", how="left")
        frame = frame.merge(
            data.adsets[["adset_id", "adset_name", "audience_type"]],
            on="adset_id",
            how="left",
        ).merge(
            data.creatives[
                [
                    column
                    for column in ("creative_id", "creative_name", "theme", "angle")
                    if column in data.creatives
                ]
            ],
            on="creative_id",
            how="left",
        )
        frame["entity_id"] = frame["ad_id"]
        frame["entity_name"] = frame["ad_name"]
        frame["parent_entity_id"] = frame["adset_id"]
    elif level == "creative":
        frame = data.ads[["campaign_id", "creative_id"]].dropna().drop_duplicates()
        frame = frame.merge(common, on="campaign_id", how="left").merge(
            data.creatives[
                [
                    column
                    for column in ("creative_id", "creative_name", "theme", "angle")
                    if column in data.creatives
                ]
            ],
            on="creative_id",
            how="left",
        )
        frame["entity_id"] = (
            frame["campaign_id"].astype(str)
            + "::creative::"
            + frame["creative_id"].astype(str)
        )
        frame["entity_name"] = frame["creative_name"].fillna(frame["creative_id"])
        frame["parent_entity_id"] = frame["campaign_id"]
        frame["entity_status"] = None
    elif level == "audience":
        frame = data.adsets[["campaign_id", "audience_type"]].drop_duplicates()
        frame["audience_type"] = frame["audience_type"].fillna("unknown")
        frame = frame.merge(common, on="campaign_id", how="left")
        frame["entity_id"] = (
            frame["campaign_id"].astype(str)
            + "::audience::"
            + frame["audience_type"].astype(str)
        )
        frame["entity_name"] = frame["audience_type"].str.replace(
            "_", " ", regex=False
        ).str.title()
        frame["parent_entity_id"] = frame["campaign_id"]
        frame["entity_status"] = None
    else:
        raise ValueError(f"Unsupported scorecard level: {level}")
    frame["entity_level"] = level
    return frame.drop_duplicates("entity_id", keep="last")


def entity_ids(frame: pd.DataFrame, level: str) -> pd.Series:
    if level == "campaign":
        return frame["campaign_id"]
    if level == "adset":
        return frame["adset_id"]
    if level == "ad":
        return frame["ad_id"]
    if level == "creative":
        return (
            frame["campaign_id"].astype(str)
            + "::creative::"
            + frame["creative_id"].astype(str)
        ).where(frame["creative_id"].notna())
    if level == "audience":
        return (
            frame["campaign_id"].astype(str)
            + "::audience::"
            + frame["audience_type"].fillna("unknown").astype(str)
        )
    raise ValueError(f"Unsupported scorecard level: {level}")


def _aggregate_media(data: CanonicalData, level: str) -> pd.DataFrame:
    frame = data.media_daily.copy()
    frame["entity_id"] = entity_ids(frame, level)
    frame = frame.dropna(subset=["entity_id"])
    return frame.groupby("entity_id", as_index=False).agg(
        media_start=("date_start", "min"),
        media_end=("date_stop", "max"),
        active_days=("date_start", "nunique"),
        impressions=("impressions", "sum"),
        link_clicks=("link_clicks", "sum"),
        spend=("spend", "sum"),
        invalid_reach_rows=("reach_exceeds_impressions", "sum"),
    )


def _aggregate_outcomes(data: CanonicalData, level: str) -> pd.DataFrame:
    frame = data.conversations.copy()
    frame["entity_id"] = entity_ids(frame, level)
    frame = frame.dropna(subset=["entity_id"])
    totals = frame.groupby("entity_id", as_index=False).agg(
        observed_conversations=("conversation_id", "nunique"),
        mature_conversations=("is_mature", "sum"),
        unresolved_conversations=("is_unresolved", "sum"),
        unique_customers=("customer_key", "nunique"),
        mature_orders_created=("has_mature_order", "sum"),
        delivered_orders=("is_delivered", "sum"),
        net_revenue=("net_revenue", "sum"),
    )
    mature = frame[frame["is_mature"]].copy()
    if mature.empty:
        totals["mature_unique_customers"] = 0
        totals["delivered_customers"] = 0
        return totals
    customer = mature.groupby(["entity_id", "customer_key"], as_index=False).agg(
        delivered=("is_delivered", "max")
    )
    customer = customer.groupby("entity_id", as_index=False).agg(
        mature_unique_customers=("customer_key", "nunique"),
        delivered_customers=("delivered", "sum"),
    )
    return totals.merge(customer, on="entity_id", how="left")


def _rate(numerator: int, denominator: int) -> Optional[float]:
    return float(numerator) / float(denominator) if denominator else None


def _top(values: Iterable[str]) -> Optional[str]:
    cleaned = [str(value).strip() for value in values if str(value).strip()]
    if not cleaned:
        return None
    return Counter(cleaned).most_common(1)[0][0]


def _semantic_rows(
    data: CanonicalData, records: List[Dict[str, Any]]
) -> pd.DataFrame:
    attribution = data.conversations.set_index("conversation_id")[
        [
            "campaign_id",
            "adset_id",
            "ad_id",
            "creative_id",
            "audience_type",
            "has_order",
        ]
    ].to_dict("index")
    rows: List[Dict[str, Any]] = []
    for record in records:
        conversation_id = str(record.get("conversation_id"))
        canonical = attribution.get(conversation_id)
        if canonical is None:
            continue
        signals = record.get("signals") or {}
        purchase = signals.get("purchase_intent") or {}
        price = signals.get("price_sensitivity") or {}
        agent = signals.get("agent_evaluation") or {}
        next_step = signals.get("next_step_agreed") or {}
        barriers = signals.get("barriers") or []
        resolutions = {
            str(barrier.get("resolution"))
            for barrier in barriers
            if isinstance(barrier, dict)
        }
        barrier_types = [
            str(barrier.get("barrier_type"))
            for barrier in barriers
            if isinstance(barrier, dict) and barrier.get("barrier_type")
        ]
        value_drivers = [
            str(driver.get("driver"))
            for driver in signals.get("value_drivers") or []
            if isinstance(driver, dict) and driver.get("driver")
        ]
        match_level = str((record.get("ad_message_match") or {}).get("level") or "unknown")
        intent_level = str(purchase.get("level") or "unknown")
        price_level = str(price.get("level") or "unknown")
        helpfulness = str(agent.get("helpfulness") or "not_assessable")
        agreed = next_step.get("agreed")
        rows.append(
            {
                "conversation_id": conversation_id,
                **canonical,
                "customer_need": signals.get("customer_need"),
                "barrier_types": barrier_types,
                "value_drivers": value_drivers,
                "purchase_assessable": intent_level != "unknown",
                "high_purchase_intent": intent_level == "high",
                "price_assessable": price_level != "unknown",
                "price_blocking": price_level == "blocking",
                "barrier_assessable": bool(
                    resolutions.intersection({"resolved", "unresolved"})
                ),
                "barrier_resolved": "resolved" in resolutions,
                "alignment_assessable": match_level != "unknown",
                "ad_aligned": match_level == "aligned",
                "agent_assessable": helpfulness != "not_assessable",
                "agent_helpful": helpfulness in {"good", "strong"},
                "next_step_assessable": agreed is not None,
                "next_step_agreed": agreed is True,
            }
        )
    return pd.DataFrame(rows)


def _aggregate_semantics(
    data: CanonicalData, records: List[Dict[str, Any]], level: str
) -> pd.DataFrame:
    frame = _semantic_rows(data, records)
    if frame.empty:
        return pd.DataFrame(columns=["entity_id"])
    frame["entity_id"] = entity_ids(frame, level)
    frame = frame.dropna(subset=["entity_id"])
    rows: List[Dict[str, Any]] = []
    for entity_id, group in frame.groupby("entity_id"):
        purchase_denominator = int(group["purchase_assessable"].sum())
        price_denominator = int(group["price_assessable"].sum())
        barrier_denominator = int(group["barrier_assessable"].sum())
        alignment_denominator = int(group["alignment_assessable"].sum())
        agent_denominator = int(group["agent_assessable"].sum())
        next_step_denominator = int(group["next_step_assessable"].sum())
        agreed_denominator = int(group["next_step_agreed"].sum())
        rows.append(
            {
                "entity_id": entity_id,
                "semantic_conversations": int(group["conversation_id"].nunique()),
                "high_purchase_intent_rate": _rate(
                    int(group["high_purchase_intent"].sum()), purchase_denominator
                ),
                "price_blocking_rate": _rate(
                    int(group["price_blocking"].sum()), price_denominator
                ),
                "barrier_resolution_rate": _rate(
                    int(group["barrier_resolved"].sum()), barrier_denominator
                ),
                "ad_alignment_rate": _rate(
                    int(group["ad_aligned"].sum()), alignment_denominator
                ),
                "agent_helpful_rate": _rate(
                    int(group["agent_helpful"].sum()), agent_denominator
                ),
                "next_step_agreement_rate": _rate(
                    agreed_denominator, next_step_denominator
                ),
                "next_step_order_progression_rate": _rate(
                    int((group["next_step_agreed"] & group["has_order"]).sum()),
                    agreed_denominator,
                ),
                "top_customer_need": _top(group["customer_need"].dropna()),
                "top_barrier": _top(
                    value for values in group["barrier_types"] for value in values
                ),
                "top_value_driver": _top(
                    value for values in group["value_drivers"] for value in values
                ),
            }
        )
    return pd.DataFrame(rows)


def build_scorecards(
    data: CanonicalData, conversation_signals: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, pd.DataFrame]:
    results: Dict[str, pd.DataFrame] = {}
    for level in LEVELS:
        scorecard = _dimensions(data, level)
        scorecard = scorecard.merge(
            _aggregate_media(data, level), on="entity_id", how="left"
        ).merge(_aggregate_outcomes(data, level), on="entity_id", how="left")
        if conversation_signals:
            scorecard = scorecard.merge(
                _aggregate_semantics(data, conversation_signals, level),
                on="entity_id",
                how="left",
            )
        numeric = [
            "active_days",
            "impressions",
            "link_clicks",
            "spend",
            "invalid_reach_rows",
            "observed_conversations",
            "mature_conversations",
            "unresolved_conversations",
            "unique_customers",
            "mature_unique_customers",
            "mature_orders_created",
            "delivered_orders",
            "delivered_customers",
            "net_revenue",
            "semantic_conversations",
        ]
        for column in numeric:
            if column not in scorecard:
                scorecard[column] = 0
            scorecard[column] = pd.to_numeric(
                scorecard[column], errors="coerce"
            ).fillna(0)
        scorecard["running_days"] = (
            pd.to_datetime(scorecard["media_end"], errors="coerce")
            - pd.to_datetime(scorecard["media_start"], errors="coerce")
        ).dt.days.add(1).fillna(0).clip(lower=0).astype(int)
        scorecard["link_ctr"] = _safe_divide(
            scorecard["link_clicks"], scorecard["impressions"]
        )
        scorecard["cpm"] = (
            _safe_divide(scorecard["spend"], scorecard["impressions"]) * 1000
        )
        scorecard["cpc"] = _safe_divide(
            scorecard["spend"], scorecard["link_clicks"]
        )
        scorecard["order_creation_rate"] = _safe_divide(
            scorecard["mature_orders_created"], scorecard["mature_conversations"]
        )
        scorecard["customer_delivered_rate"] = _safe_divide(
            scorecard["delivered_customers"], scorecard["mature_unique_customers"]
        )
        scorecard["cost_per_created_order"] = _safe_divide(
            scorecard["spend"], scorecard["mature_orders_created"]
        )
        scorecard["net_roas"] = _safe_divide(
            scorecard["net_revenue"], scorecard["spend"]
        )
        scorecard["semantic_coverage_rate"] = _safe_divide(
            scorecard["semantic_conversations"], scorecard["observed_conversations"]
        )
        results[level] = scorecard
    return results
