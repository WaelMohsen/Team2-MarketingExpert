"""Build deterministic scorecards without joining fact tables at row level."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src_2.ingestion.normalizer import CanonicalCycleData


OUTCOME_COLUMNS = [
    "observed_conversations",
    "unique_customers",
    "repeat_conversations",
    "repeat_delivered_orders",
    "orders_created",
    "delivered_orders",
    "refunded_orders",
    "cancelled_orders",
    "ghosted_conversations",
    "negative_outcomes",
    "open_or_pending_conversations",
    "gross_order_value",
    "delivered_revenue",
    "net_revenue",
    "refunded_amount",
    "cancelled_value",
    "pending_value",
    "inbound_messages",
    "outbound_messages",
]


@dataclass(frozen=True)
class CycleScorecards:
    campaign: pd.DataFrame
    adset: pd.DataFrame
    ad: pd.DataFrame
    creative: pd.DataFrame
    audience: pd.DataFrame

    def by_level(self, level: str) -> pd.DataFrame:
        if level not in {"campaign", "adset", "ad", "creative", "audience"}:
            raise ValueError(f"Unsupported scorecard level: {level}")
        return getattr(self, level)


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    result = numerator.astype(float).div(denominator.astype(float))
    return result.where(denominator.astype(float).ne(0))


def _campaign_dimensions(data: CanonicalCycleData) -> pd.DataFrame:
    columns = [
        "campaign_id",
        "campaign_name",
        "campaign_type",
        "objective",
        "status",
        "effective_status",
        "start_date",
        "end_date",
    ]
    frame = data.campaigns[[column for column in columns if column in data.campaigns]].copy()
    frame = frame.rename(
        columns={
            "status": "entity_status",
            "effective_status": "entity_effective_status",
        }
    )
    frame["entity_id"] = frame["campaign_id"]
    frame["entity_name"] = frame["campaign_name"]
    return frame


def _dimensions(data: CanonicalCycleData, level: str) -> pd.DataFrame:
    campaigns = _campaign_dimensions(data)
    common_campaign = campaigns[
        [
            "campaign_id",
            "campaign_name",
            "campaign_type",
            "objective",
        ]
    ]
    if level == "campaign":
        dimensions = campaigns
    elif level == "adset":
        columns = [
            "adset_id",
            "adset_name",
            "campaign_id",
            "audience_type",
            "optimization_goal",
            "bid_strategy",
            "daily_budget_raw",
            "status",
            "effective_status",
        ]
        dimensions = data.adsets[
            [column for column in columns if column in data.adsets]
        ].copy()
        dimensions = dimensions.rename(
            columns={
                "status": "entity_status",
                "effective_status": "entity_effective_status",
            }
        ).merge(common_campaign, on="campaign_id", how="left")
        dimensions["entity_id"] = dimensions["adset_id"]
        dimensions["entity_name"] = dimensions["adset_name"]
    elif level == "ad":
        columns = [
            "ad_id",
            "ad_name",
            "adset_id",
            "campaign_id",
            "creative_id",
            "start_date",
            "end_date",
            "status",
            "effective_status",
        ]
        dimensions = data.ads[[column for column in columns if column in data.ads]].copy()
        dimensions = dimensions.rename(
            columns={
                "start_date": "entity_start_date",
                "end_date": "entity_end_date",
                "status": "entity_status",
                "effective_status": "entity_effective_status",
            }
        )
        dimensions = dimensions.merge(
            data.adsets[["adset_id", "adset_name", "audience_type"]],
            on="adset_id",
            how="left",
        ).merge(common_campaign, on="campaign_id", how="left")
        creative_columns = ["creative_id", "creative_name", "theme", "angle"]
        dimensions = dimensions.merge(
            data.creatives[
                [column for column in creative_columns if column in data.creatives]
            ],
            on="creative_id",
            how="left",
        )
        dimensions["entity_id"] = dimensions["ad_id"]
        dimensions["entity_name"] = dimensions["ad_name"]
    elif level == "creative":
        ad_creatives = data.ads[
            ["campaign_id", "adset_id", "ad_id", "creative_id"]
        ].dropna(subset=["creative_id"])
        dimensions = ad_creatives[["campaign_id", "creative_id"]].drop_duplicates()
        dimensions = dimensions.merge(common_campaign, on="campaign_id", how="left")
        creative_columns = ["creative_id", "creative_name", "theme", "angle"]
        dimensions = dimensions.merge(
            data.creatives[
                [column for column in creative_columns if column in data.creatives]
            ],
            on="creative_id",
            how="left",
        )
        dimensions["entity_id"] = (
            dimensions["campaign_id"] + "::creative::" + dimensions["creative_id"]
        )
        dimensions["entity_name"] = dimensions["creative_name"].fillna(
            dimensions["creative_id"]
        )
    elif level == "audience":
        dimensions = data.adsets[
            ["campaign_id", "audience_type"]
        ].drop_duplicates()
        dimensions = dimensions.merge(common_campaign, on="campaign_id", how="left")
        dimensions["audience_type"] = dimensions["audience_type"].fillna("unknown")
        dimensions["entity_id"] = (
            dimensions["campaign_id"]
            + "::audience::"
            + dimensions["audience_type"].astype(str)
        )
        dimensions["entity_name"] = dimensions["audience_type"].str.replace(
            "_", " ", regex=False
        ).str.title()
    else:
        raise ValueError(f"Unsupported scorecard level: {level}")
    return dimensions.drop_duplicates("entity_id", keep="last")


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


def _aggregate_media(data: CanonicalCycleData, level: str) -> pd.DataFrame:
    frame = data.media_daily.copy()
    frame["entity_id"] = _entity_ids(frame, level)
    frame = frame.dropna(subset=["entity_id"])
    if frame.empty:
        return pd.DataFrame(columns=["entity_id"])
    return frame.groupby("entity_id", as_index=False).agg(
        media_start=("date_start", "min"),
        media_end=("date_stop", "max"),
        active_days=("date_start", "nunique"),
        impressions=("impressions", "sum"),
        reach=("reach", "sum"),
        clicks=("clicks", "sum"),
        link_clicks=("link_clicks", "sum"),
        spend=("spend", "sum"),
        meta_conversation_starts=("meta_conversation_starts", "sum"),
    )


def _aggregate_outcomes(data: CanonicalCycleData, level: str) -> pd.DataFrame:
    frame = data.conversations.copy()
    frame["entity_id"] = _entity_ids(frame, level)
    frame = frame.dropna(subset=["entity_id"])
    if frame.empty:
        return pd.DataFrame(columns=["entity_id"])
    return frame.groupby("entity_id", as_index=False).agg(
        observed_conversations=("conversation_id", "nunique"),
        unique_customers=("customer_id", "nunique"),
        repeat_conversations=("is_repeat_cycle", "sum"),
        repeat_delivered_orders=("is_repeat_delivered", "sum"),
        orders_created=("has_order", "sum"),
        delivered_orders=("is_delivered", "sum"),
        refunded_orders=("is_refunded", "sum"),
        cancelled_orders=("is_cancelled", "sum"),
        ghosted_conversations=("is_ghosted", "sum"),
        negative_outcomes=("is_negative", "sum"),
        open_or_pending_conversations=("is_open_or_pending", "sum"),
        gross_order_value=("gross_order_value", "sum"),
        delivered_revenue=("delivered_revenue", "sum"),
        net_revenue=("net_revenue", "sum"),
        refunded_amount=("refunded_amount", "sum"),
        cancelled_value=("cancelled_value", "sum"),
        pending_value=("pending_value", "sum"),
        avg_conversation_minutes=("conversation_minutes", "mean"),
        avg_message_count=("message_count", "mean"),
        inbound_messages=("inbound_messages", "sum"),
        outbound_messages=("outbound_messages", "sum"),
    )


def _aggregate_products(data: CanonicalCycleData, level: str) -> pd.DataFrame:
    frame = data.order_lines.copy()
    if frame.empty:
        return pd.DataFrame(columns=["entity_id"])
    frame["entity_id"] = _entity_ids(frame, level)
    frame = frame.dropna(subset=["entity_id"])
    aggregations: dict[str, tuple[str, str]] = {
        "unique_products_ordered": ("product_id", "nunique"),
        "units_ordered": ("quantity", "sum"),
        "line_item_value": ("line_value", "sum"),
    }
    if "category" in frame:
        aggregations["unique_categories_ordered"] = ("category", "nunique")
    return frame.groupby("entity_id", as_index=False).agg(**aggregations)


def _setup_counts(data: CanonicalCycleData, level: str) -> pd.DataFrame:
    ads = data.ads.merge(
        data.adsets[["adset_id", "audience_type"]], on="adset_id", how="left"
    )
    ads["entity_id"] = _entity_ids(ads, level)
    ads = ads.dropna(subset=["entity_id"])
    return ads.groupby("entity_id", as_index=False).agg(
        ad_count=("ad_id", "nunique"),
        adset_count=("adset_id", "nunique"),
        unique_creatives=("creative_id", "nunique"),
    )


def _add_kpis(scorecard: pd.DataFrame) -> pd.DataFrame:
    scorecard = scorecard.copy()
    scorecard["period_days"] = scorecard["active_days"].clip(lower=1)
    scorecard["frequency"] = _safe_divide(
        scorecard["impressions"], scorecard["reach"]
    )
    scorecard["link_ctr_pct"] = (
        _safe_divide(scorecard["link_clicks"], scorecard["impressions"]) * 100
    )
    scorecard["cpm"] = (
        _safe_divide(scorecard["spend"], scorecard["impressions"]) * 1000
    )
    scorecard["cpc"] = _safe_divide(scorecard["spend"], scorecard["link_clicks"])
    scorecard["cost_per_meta_conversation"] = _safe_divide(
        scorecard["spend"], scorecard["meta_conversation_starts"]
    )
    scorecard["cost_per_observed_conversation"] = _safe_divide(
        scorecard["spend"], scorecard["observed_conversations"]
    )
    scorecard["cost_per_delivered_order"] = _safe_divide(
        scorecard["spend"], scorecard["delivered_orders"]
    )
    scorecard["net_roas"] = _safe_divide(
        scorecard["net_revenue"], scorecard["spend"]
    )
    scorecard["delivered_roas"] = _safe_divide(
        scorecard["delivered_revenue"], scorecard["spend"]
    )
    scorecard["aov"] = _safe_divide(
        scorecard["delivered_revenue"], scorecard["delivered_orders"]
    )
    scorecard["order_creation_rate"] = _safe_divide(
        scorecard["orders_created"], scorecard["observed_conversations"]
    )
    scorecard["delivered_rate"] = _safe_divide(
        scorecard["delivered_orders"], scorecard["observed_conversations"]
    )
    scorecard["refund_rate"] = _safe_divide(
        scorecard["refunded_orders"],
        scorecard["delivered_orders"] + scorecard["refunded_orders"],
    )
    scorecard["negative_outcome_rate"] = _safe_divide(
        scorecard["negative_outcomes"], scorecard["observed_conversations"]
    )
    scorecard["repeat_conversation_rate"] = _safe_divide(
        scorecard["repeat_conversations"], scorecard["observed_conversations"]
    )
    scorecard["repeat_order_rate"] = _safe_divide(
        scorecard["repeat_delivered_orders"], scorecard["delivered_orders"]
    )
    scorecard["net_revenue_per_day"] = _safe_divide(
        scorecard["net_revenue"], scorecard["period_days"]
    )
    scorecard["observed_conversations_per_day"] = _safe_divide(
        scorecard["observed_conversations"], scorecard["period_days"]
    )
    scorecard["delivered_rate_pct"] = scorecard["delivered_rate"] * 100
    scorecard["negative_outcome_rate_pct"] = (
        scorecard["negative_outcome_rate"] * 100
    )
    scorecard["order_creation_rate_pct"] = scorecard["order_creation_rate"] * 100
    return scorecard


def build_level_scorecard(data: CanonicalCycleData, level: str) -> pd.DataFrame:
    scorecard = (
        _dimensions(data, level)
        .merge(_aggregate_media(data, level), on="entity_id", how="left")
        .merge(_aggregate_outcomes(data, level), on="entity_id", how="left")
        .merge(_aggregate_products(data, level), on="entity_id", how="left")
        .merge(_setup_counts(data, level), on="entity_id", how="left")
    )
    numeric = [
        "active_days",
        "impressions",
        "reach",
        "clicks",
        "link_clicks",
        "spend",
        "meta_conversation_starts",
        *OUTCOME_COLUMNS,
        "unique_products_ordered",
        "unique_categories_ordered",
        "units_ordered",
        "line_item_value",
        "ad_count",
        "adset_count",
        "unique_creatives",
    ]
    for column in numeric:
        if column not in scorecard:
            scorecard[column] = 0.0
        scorecard[column] = pd.to_numeric(scorecard[column], errors="coerce").fillna(0)
    scorecard["entity_level"] = level
    return _add_kpis(scorecard)


def build_scorecards(data: CanonicalCycleData) -> CycleScorecards:
    return CycleScorecards(
        campaign=build_level_scorecard(data, "campaign"),
        adset=build_level_scorecard(data, "adset"),
        ad=build_level_scorecard(data, "ad"),
        creative=build_level_scorecard(data, "creative"),
        audience=build_level_scorecard(data, "audience"),
    )
