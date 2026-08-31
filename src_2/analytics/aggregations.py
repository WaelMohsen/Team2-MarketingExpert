"""Build deterministic scorecards without joining fact tables at row level."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from src_2.contracts import ConversationSignalRecord
from src_2.ingestion.normalizer import CanonicalCycleData


OUTCOME_COLUMNS = [
    "observed_conversations",
    "mature_conversations",
    "unique_customers",
    "mature_unique_customers",
    "mature_returning_unique_customers",
    "delivered_customers",
    "returning_delivered_customers",
    "negative_outcome_customers",
    "repeated_customers",
    "new_customer_conversations",
    "returning_customer_conversations",
    "repeat_conversations",
    "repeat_delivered_orders",
    "orders_created",
    "mature_orders_created",
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
        valid_daily_reach_sum=("valid_reach", "sum"),
        avg_daily_reach=("valid_reach", "mean"),
        peak_daily_reach=("valid_reach", "max"),
        invalid_reach_rows=("reach_exceeds_impressions", "sum"),
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
    aggregated = frame.groupby("entity_id", as_index=False).agg(
        observed_conversations=("conversation_id", "nunique"),
        unique_customers=("customer_id", "nunique"),
        mature_conversations=("is_mature_outcome", "sum"),
        repeated_customers=(
            "customer_id",
            lambda values: values[frame.loc[values.index, "is_repeated_customer_in_cycle"]].nunique(),
        ),
        new_customer_conversations=("is_new_customer_conversation", "sum"),
        returning_customer_conversations=("is_returning_customer", "sum"),
        repeat_conversations=("is_repeat_cycle", "sum"),
        repeat_delivered_orders=("is_repeat_delivered", "sum"),
        orders_created=("has_order", "sum"),
        mature_orders_created=("has_mature_order", "sum"),
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

    mature = frame[frame["is_mature_outcome"]].copy()
    if mature.empty:
        aggregated["mature_unique_customers"] = 0
        aggregated["mature_returning_unique_customers"] = 0
        aggregated["delivered_customers"] = 0
        aggregated["returning_delivered_customers"] = 0
        aggregated["negative_outcome_customers"] = 0
        return aggregated

    customer_outcomes = mature.groupby(
        ["entity_id", "customer_id"], as_index=False
    ).agg(
        customer_delivered=("is_delivered", "max"),
        customer_negative=("is_negative", "max"),
        customer_returning=("is_returning_customer", "max"),
        returning_delivered=("is_repeat_delivered", "max"),
    )
    customer_summary = customer_outcomes.groupby("entity_id", as_index=False).agg(
        mature_unique_customers=("customer_id", "nunique"),
        mature_returning_unique_customers=("customer_returning", "sum"),
        delivered_customers=("customer_delivered", "sum"),
        returning_delivered_customers=("returning_delivered", "sum"),
        negative_outcome_customers=("customer_negative", "sum"),
    )
    return aggregated.merge(customer_summary, on="entity_id", how="left")


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
    scorecard["frequency_proxy"] = _safe_divide(
        scorecard["impressions"], scorecard["valid_daily_reach_sum"]
    )
    scorecard["link_ctr_pct"] = (
        _safe_divide(scorecard["link_clicks"], scorecard["impressions"]) * 100
    )
    scorecard["link_ctr"] = _safe_divide(
        scorecard["link_clicks"], scorecard["impressions"]
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
        scorecard["mature_orders_created"], scorecard["mature_conversations"]
    )
    scorecard["delivered_rate"] = _safe_divide(
        scorecard["delivered_orders"], scorecard["mature_conversations"]
    )
    scorecard["refund_rate"] = _safe_divide(
        scorecard["refunded_orders"],
        scorecard["delivered_orders"] + scorecard["refunded_orders"],
    )
    scorecard["negative_outcome_rate"] = _safe_divide(
        scorecard["negative_outcomes"], scorecard["mature_conversations"]
    )
    scorecard["unresolved_outcome_rate"] = _safe_divide(
        scorecard["open_or_pending_conversations"],
        scorecard["observed_conversations"],
    )
    scorecard["customer_delivered_rate"] = _safe_divide(
        scorecard["delivered_customers"], scorecard["mature_unique_customers"]
    )
    scorecard["customer_negative_outcome_rate"] = _safe_divide(
        scorecard["negative_outcome_customers"],
        scorecard["mature_unique_customers"],
    )
    scorecard["retention_delivery_rate"] = _safe_divide(
        scorecard["returning_delivered_customers"],
        scorecard["mature_returning_unique_customers"],
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
    scorecard["customer_delivered_rate_pct"] = (
        scorecard["customer_delivered_rate"] * 100
    )
    scorecard["unresolved_outcome_rate_pct"] = (
        scorecard["unresolved_outcome_rate"] * 100
    )
    for metric, successes, trials in (
        ("link_ctr", "link_clicks", "impressions"),
        ("order_creation_rate", "mature_orders_created", "mature_conversations"),
        ("delivered_rate", "delivered_orders", "mature_conversations"),
        ("negative_outcome_rate", "negative_outcomes", "mature_conversations"),
        ("customer_delivered_rate", "delivered_customers", "mature_unique_customers"),
        (
            "customer_negative_outcome_rate",
            "negative_outcome_customers",
            "mature_unique_customers",
        ),
        (
            "retention_delivery_rate",
            "returning_delivered_customers",
            "mature_returning_unique_customers",
        ),
    ):
        lower, upper = _wilson_interval(scorecard[successes], scorecard[trials])
        scorecard[f"{metric}_ci_low"] = lower
        scorecard[f"{metric}_ci_high"] = upper
    return scorecard


def _wilson_interval(
    successes: pd.Series, trials: pd.Series, z: float = 1.959963984540054
) -> tuple[pd.Series, pd.Series]:
    """Return a 95% Wilson interval for binomial proportions."""

    n = pd.to_numeric(trials, errors="coerce").astype(float)
    k = pd.to_numeric(successes, errors="coerce").astype(float)
    valid = n.gt(0)
    p = k.div(n.where(valid))
    z2 = z * z
    denominator = 1 + z2 / n.where(valid)
    centre = (p + z2 / (2 * n.where(valid))) / denominator
    margin = (
        z
        * ((p * (1 - p) / n.where(valid) + z2 / (4 * n.where(valid) ** 2)) ** 0.5)
        / denominator
    )
    return (centre - margin).clip(lower=0), (centre + margin).clip(upper=1)


def build_level_scorecard(
    data: CanonicalCycleData,
    level: str,
    conversation_signals: Sequence[ConversationSignalRecord] | None = None,
) -> pd.DataFrame:
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
        "valid_daily_reach_sum",
        "avg_daily_reach",
        "peak_daily_reach",
        "invalid_reach_rows",
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
    scorecard = _add_kpis(scorecard)
    if conversation_signals:
        from .conversation_signals import aggregate_conversation_signals

        semantic = aggregate_conversation_signals(data, conversation_signals, level)
        scorecard = scorecard.merge(semantic, on="entity_id", how="left")
        semantic_counts = [
            "semantic_conversations",
            "high_purchase_intent_conversations",
            "barrier_conversations",
            "agent_helpful_conversations",
            "high_urgency_conversations",
            "price_sensitive_conversations",
            "price_blocking_conversations",
            "deal_seeking_conversations",
            "deal_required_conversations",
            "delivery_ready_conversations",
            "sales_agreement_conversations",
            "blocking_barrier_conversations",
            "assessable_barrier_conversations",
            "resolved_barrier_conversations",
            "competitor_mention_conversations",
            "next_step_agreed_conversations",
            "next_step_observed_conversations",
        ]
        for column in semantic_counts:
            scorecard[column] = pd.to_numeric(
                scorecard.get(column, 0), errors="coerce"
            ).fillna(0)
        scorecard["semantic_coverage_rate"] = _safe_divide(
            scorecard["semantic_conversations"], scorecard["observed_conversations"]
        )
    return scorecard


def build_scorecards(
    data: CanonicalCycleData,
    conversation_signals: Sequence[ConversationSignalRecord] | None = None,
) -> CycleScorecards:
    return CycleScorecards(
        campaign=build_level_scorecard(data, "campaign", conversation_signals),
        adset=build_level_scorecard(data, "adset", conversation_signals),
        ad=build_level_scorecard(data, "ad", conversation_signals),
        creative=build_level_scorecard(data, "creative", conversation_signals),
        audience=build_level_scorecard(data, "audience", conversation_signals),
    )
