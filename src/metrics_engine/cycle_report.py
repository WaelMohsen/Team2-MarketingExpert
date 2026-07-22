"""Ended-cycle scorecards and next-cycle budget recommendations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from .campaign_targets import get_target_config, kpi_label, target_framework_table
from .cycle_data import CycleData, data_quality_summary

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

MINIMUM_OUTCOME_EVIDENCE = {"campaign": 10, "adset": 5, "ad": 3}


@dataclass
class CycleReport:
    campaign_scorecard: pd.DataFrame
    adset_scorecard: pd.DataFrame
    ad_scorecard: pd.DataFrame
    target_kpi_details: pd.DataFrame
    allocation_kpi_details: pd.DataFrame
    target_framework: pd.DataFrame
    data_quality: Dict[str, Any]

    def to_llm_context(self, max_entities: int = 12) -> Dict[str, Any]:
        """Return compact, calculated evidence. Raw messages never enter prompts."""
        campaign_columns = [
            "campaign_id",
            "campaign_name",
            "campaign_type",
            "target_achievement_score",
            "target_status",
            "outcome_score",
            "next_cycle_action",
            "recommended_budget_share_pct",
            "observed_conversations",
            "delivered_orders",
            "net_revenue",
            "net_roas",
            "negative_outcome_rate",
            "recommendation_reason",
        ]
        lower_columns = [
            "campaign_id",
            "entity_id",
            "entity_name",
            "campaign_type",
            "outcome_score",
            "next_cycle_action",
            "recommended_budget_share_pct",
            "observed_conversations",
            "delivered_orders",
            "net_revenue",
            "net_roas",
            "negative_outcome_rate",
            "recommendation_reason",
        ]

        def records(frame: pd.DataFrame, columns: List[str]):
            available = [column for column in columns if column in frame]
            ordered = frame.sort_values(
                ["recommended_budget_share_pct", "outcome_score"],
                ascending=False,
                na_position="last",
            ).head(max_entities)
            return _json_safe_records(ordered[available])

        quality = {
            key: _json_safe_value(value) for key, value in self.data_quality.items()
        }
        return {
            "report_purpose": (
                "Score the completed results cycle and recommend where the next "
                "campaign budget should go. Scale/kill refers to the next cycle, "
                "not editing the ended cycle."
            ),
            "decision_basis": (
                "Next-cycle actions use observed WhatsApp outcomes. Meta delivery "
                "metrics are context or campaign-type target measures only."
            ),
            "data_quality": quality,
            "campaigns": records(self.campaign_scorecard, campaign_columns),
            "adsets": records(self.adset_scorecard, lower_columns),
            "ads": records(self.ad_scorecard, lower_columns),
        }


def _json_safe_value(value):
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _json_safe_records(frame: pd.DataFrame) -> List[dict]:
    return [
        {key: _json_safe_value(value) for key, value in record.items()}
        for record in frame.to_dict("records")
    ]


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = pd.to_numeric(denominator, errors="coerce").replace({0: pd.NA})
    return pd.to_numeric(numerator, errors="coerce").div(denominator)


def _aggregate_insights(insights: pd.DataFrame, key: str) -> pd.DataFrame:
    if insights.empty:
        return pd.DataFrame(columns=[key])
    return (
        insights.dropna(subset=[key])
        .groupby(key, as_index=False)
        .agg(
            first_insight_date=("date_start", "min"),
            last_insight_date=("date_stop", "max"),
            active_days=("date_start", "nunique"),
            impressions=("impressions", "sum"),
            reach=("reach", "sum"),
            clicks=("clicks", "sum"),
            link_clicks=("link_clicks", "sum"),
            spend=("spend", "sum"),
            meta_conversation_starts=("meta_conversation_starts", "sum"),
        )
    )


def _aggregate_outcomes(conversations: pd.DataFrame, key: str) -> pd.DataFrame:
    if conversations.empty:
        return pd.DataFrame(columns=[key])
    outcomes = conversations[
        conversations["source_platform"].eq("meta_ctwa") & conversations[key].notna()
    ]
    if outcomes.empty:
        return pd.DataFrame(columns=[key])
    return outcomes.groupby(key, as_index=False).agg(
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


def _aggregate_products(line_items: pd.DataFrame, key: str) -> pd.DataFrame:
    if line_items.empty or key not in line_items:
        return pd.DataFrame(columns=[key])
    aggregations = {
        "unique_products_ordered": ("product_id", "nunique"),
        "units_ordered": ("quantity", "sum"),
        "line_item_value": ("line_value", "sum"),
    }
    if "category" in line_items:
        aggregations["unique_categories_ordered"] = ("category", "nunique")
    return (
        line_items.dropna(subset=[key]).groupby(key, as_index=False).agg(**aggregations)
    )


def _setup_metrics(data: CycleData, level: str) -> pd.DataFrame:
    if level == "campaign":
        return data.ads.groupby("campaign_id", as_index=False).agg(
            ad_count=("ad_id", "nunique"),
            unique_creatives=("creative_id", "nunique"),
            adset_count=("adset_id", "nunique"),
        )
    if level == "adset":
        return data.ads.groupby("adset_id", as_index=False).agg(
            ad_count=("ad_id", "nunique"),
            unique_creatives=("creative_id", "nunique"),
        )
    return pd.DataFrame(
        {
            "ad_id": data.ads["ad_id"],
            "ad_count": 1,
            "unique_creatives": data.ads["creative_id"].notna().astype(int),
        }
    )


def _dimensions(data: CycleData, level: str) -> Tuple[pd.DataFrame, str]:
    campaigns = data.campaigns[
        [
            "campaign_id",
            "campaign_name",
            "campaign_type",
            "objective",
            "status",
            "effective_status",
            "start_date",
            "end_date",
        ]
    ].rename(
        columns={
            "status": "campaign_status",
            "effective_status": "campaign_effective_status",
        }
    )
    if level == "campaign":
        return campaigns, "campaign_id"

    adsets = data.adsets.copy().rename(
        columns={"status": "adset_status", "effective_status": "adset_effective_status"}
    )
    adset_columns = [
        "adset_id",
        "adset_name",
        "campaign_id",
        "audience_type",
        "optimization_goal",
        "bid_strategy",
        "daily_budget_raw",
        "adset_status",
        "adset_effective_status",
    ]
    adsets = adsets[[column for column in adset_columns if column in adsets]].merge(
        campaigns, on="campaign_id", how="left"
    )
    if level == "adset":
        return adsets, "adset_id"

    ads = data.ads.copy().rename(
        columns={"status": "ad_status", "effective_status": "ad_effective_status"}
    )
    ad_columns = [
        "ad_id",
        "ad_name",
        "adset_id",
        "campaign_id",
        "creative_id",
        "start_date",
        "end_date",
        "ad_status",
        "ad_effective_status",
    ]
    ads = ads[[column for column in ad_columns if column in ads]]
    ads = ads.merge(
        adsets[
            [
                "adset_id",
                "adset_name",
                "audience_type",
                "campaign_name",
                "campaign_type",
                "objective",
                "campaign_status",
                "campaign_effective_status",
            ]
        ],
        on="adset_id",
        how="left",
    )
    creative_columns = [
        "creative_id",
        "creative_name",
        "theme",
        "angle",
        "object_story_spec.link_data.name",
        "object_story_spec.link_data.message",
    ]
    ads = ads.merge(
        data.creatives[
            [column for column in creative_columns if column in data.creatives]
        ],
        on="creative_id",
        how="left",
    )
    return ads, "ad_id"


def _build_level_scorecard(data: CycleData, level: str) -> pd.DataFrame:
    dimensions, key = _dimensions(data, level)
    scorecard = dimensions.merge(
        _aggregate_insights(data.insights, key), on=key, how="left"
    ).merge(_aggregate_outcomes(data.conversations, key), on=key, how="left")
    scorecard = scorecard.merge(
        _aggregate_products(data.line_items, key), on=key, how="left"
    ).merge(_setup_metrics(data, level), on=key, how="left")

    numeric_defaults = [
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
    for column in numeric_defaults:
        if column not in scorecard:
            scorecard[column] = 0.0
        scorecard[column] = pd.to_numeric(scorecard[column], errors="coerce").fillna(0)

    scorecard["period_days"] = scorecard["active_days"].clip(lower=1)
    scorecard["frequency"] = _safe_divide(scorecard["impressions"], scorecard["reach"])
    scorecard["link_ctr_pct"] = (
        _safe_divide(scorecard["link_clicks"], scorecard["impressions"]) * 100
    )
    scorecard["cpm"] = _safe_divide(scorecard["spend"], scorecard["impressions"]) * 1000
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
    scorecard["net_roas"] = _safe_divide(scorecard["net_revenue"], scorecard["spend"])
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

    scorecard["primary_kpis"] = scorecard["campaign_type"].map(
        lambda value: ", ".join(
            metric["label"] for metric in get_target_config(value)["primary_kpis"]
        )
    )
    scorecard["recommended_kpis"] = scorecard["campaign_type"].map(
        lambda value: ", ".join(
            kpi_label(metric) for metric in get_target_config(value)["recommended_kpis"]
        )
    )
    scorecard["entity_level"] = level
    scorecard["entity_id"] = scorecard[key]
    name_column = {
        "campaign": "campaign_name",
        "adset": "adset_name",
        "ad": "ad_name",
    }[level]
    scorecard["entity_name"] = scorecard[name_column]
    return scorecard


def _valid_metric_values(frame: pd.DataFrame, metric: str) -> pd.Series:
    if metric not in frame:
        return pd.Series(dtype=float)
    values = (
        pd.to_numeric(frame[metric], errors="coerce")
        .replace([float("inf"), float("-inf")], pd.NA)
        .dropna()
    )
    if metric.endswith("_rate") or metric.endswith("_rate_pct"):
        return values[values >= 0]
    return values[values > 0]


def _resolve_target(frame: pd.DataFrame, metric_config: dict):
    direction = metric_config["direction"]
    if direction == "range":
        return (
            metric_config["min_target"],
            metric_config["max_target"],
            "configured healthy range",
        )
    fixed = metric_config.get("fixed_target")
    if fixed is not None:
        return fixed, None, "configured minimum"
    values = _valid_metric_values(frame, metric_config["metric"])
    if values.empty:
        return None, None, "no peer benchmark"
    target = float(values.median()) * float(metric_config.get("factor", 1.0))
    factor = metric_config.get("factor", 1.0)
    source = "peer median" if factor == 1 else f"{factor:.0%} of peer median"
    return target, None, source


def _score_metric(value, metric_config: dict, target, max_target=None):
    if pd.isna(value) or target is None:
        return None, False
    value = float(value)
    direction = metric_config["direction"]
    if direction == "higher":
        if target <= 0:
            return None, False
        return min(max(value / target, 0), 1) * 100, value >= target
    if direction == "lower":
        if target < 0:
            return None, False
        if value <= target:
            return 100.0, True
        if value == 0:
            return 100.0, True
        return min(max(target / value, 0), 1) * 100, False
    if direction == "range":
        if target <= value <= max_target:
            return 100.0, True
        if value < target:
            return (value / target * 100 if target > 0 else 0), False
        return (max_target / value * 100 if value > 0 else 0), False
    return None, False


def _comparison_text(metric_config: dict, target, max_target=None) -> str:
    if target is None:
        return "No benchmark"
    if metric_config["direction"] == "higher":
        return f">= {target:,.2f}"
    if metric_config["direction"] == "lower":
        return f"<= {target:,.2f}"
    return f"{target:,.2f} to {max_target:,.2f}"


def _evaluate_campaign_targets(
    campaigns: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    details = []
    scores = []
    for _, row in campaigns.iterrows():
        config = get_target_config(row["campaign_type"])
        weighted_score = 0.0
        total_weight = 0.0
        achieved_count = 0
        evaluated_count = 0
        for metric_config in config["primary_kpis"]:
            target, max_target, source = _resolve_target(campaigns, metric_config)
            value = row.get(metric_config["metric"])
            score, achieved = _score_metric(value, metric_config, target, max_target)
            if score is not None:
                weighted_score += score * metric_config["weight"]
                total_weight += metric_config["weight"]
                achieved_count += int(achieved)
                evaluated_count += 1
            details.append(
                {
                    "entity_level": "campaign",
                    "entity_id": row["campaign_id"],
                    "entity_name": row["campaign_name"],
                    "campaign_type": row["campaign_type"],
                    "metric": metric_config["metric"],
                    "metric_label": metric_config["label"],
                    "actual_value": value,
                    "direction": metric_config["direction"],
                    "comparison_target": _comparison_text(
                        metric_config, target, max_target
                    ),
                    "target_source": source,
                    "weight": metric_config["weight"],
                    "kpi_score": score,
                    "achieved": achieved,
                }
            )
        score = weighted_score / total_weight if total_weight else None
        if score is None:
            status = "Insufficient data"
        elif score >= 85:
            status = "On target"
        elif score >= 65:
            status = "Partially on target"
        elif score >= 40:
            status = "Needs attention"
        else:
            status = "Off target"
        scores.append(
            {
                "campaign_id": row["campaign_id"],
                "target_achievement_score": score,
                "target_status": status,
                "primary_kpis_achieved": achieved_count,
                "primary_kpis_evaluated": evaluated_count,
                "target_job": config["target_job"],
                "success_question": config["success_question"],
            }
        )
    return campaigns.merge(
        pd.DataFrame(scores), on="campaign_id", how="left"
    ), pd.DataFrame(details)


def _peer_frame(scorecard: pd.DataFrame, row: pd.Series, level: str) -> pd.DataFrame:
    if level == "campaign":
        same_type = scorecard[scorecard["campaign_type"].eq(row["campaign_type"])]
        return same_type if len(same_type) >= 2 else scorecard
    return scorecard[scorecard["campaign_id"].eq(row["campaign_id"])]


def _evaluate_outcomes(
    scorecard: pd.DataFrame, level: str
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    detail_rows = []
    score_rows = []
    minimum_evidence = MINIMUM_OUTCOME_EVIDENCE[level]

    for _, row in scorecard.iterrows():
        config = get_target_config(row["campaign_type"])
        peers = _peer_frame(scorecard, row, level)
        weighted_score = 0.0
        total_weight = 0.0
        entity_details = []
        for metric_config in config["allocation_kpis"]:
            target, max_target, source = _resolve_target(peers, metric_config)
            value = row.get(metric_config["metric"])
            score, achieved = _score_metric(value, metric_config, target, max_target)
            if score is not None:
                weighted_score += score * metric_config["weight"]
                total_weight += metric_config["weight"]
            detail = {
                "entity_level": level,
                "entity_id": row["entity_id"],
                "entity_name": row["entity_name"],
                "campaign_id": row["campaign_id"],
                "campaign_type": row["campaign_type"],
                "metric": metric_config["metric"],
                "metric_label": metric_config["label"],
                "actual_value": value,
                "direction": metric_config["direction"],
                "comparison_target": _comparison_text(
                    metric_config, target, max_target
                ),
                "target_source": source,
                "weight": metric_config["weight"],
                "kpi_score": score,
                "achieved": achieved,
            }
            detail_rows.append(detail)
            entity_details.append(detail)

        outcome_score = weighted_score / total_weight if total_weight else None
        evidence = int(row.get("observed_conversations", 0) or 0)
        if evidence < minimum_evidence or outcome_score is None:
            action = "INSUFFICIENT_EVIDENCE"
        elif int(row.get("delivered_orders", 0) or 0) == 0 and row.get("spend", 0) > 0:
            action = "DO_NOT_FUND_NEXT_CYCLE"
        elif outcome_score >= 75:
            action = "SCALE_NEXT_CYCLE"
        elif outcome_score >= 55:
            action = "KEEP_AS_TEST"
        else:
            action = "DO_NOT_FUND_NEXT_CYCLE"

        valid_details = [
            detail for detail in entity_details if detail["kpi_score"] is not None
        ]
        strongest = sorted(
            valid_details, key=lambda detail: detail["kpi_score"], reverse=True
        )[:2]
        weakest = sorted(valid_details, key=lambda detail: detail["kpi_score"])[:1]
        score_rows.append(
            {
                "entity_id": row["entity_id"],
                "outcome_score": outcome_score,
                "next_cycle_action": action,
                "minimum_evidence_required": minimum_evidence,
                "strongest_outcome_kpis": ", ".join(
                    detail["metric_label"] for detail in strongest
                ),
                "weakest_outcome_kpi": weakest[0]["metric_label"] if weakest else None,
            }
        )

    scored = scorecard.merge(pd.DataFrame(score_rows), on="entity_id", how="left")
    details = pd.DataFrame(detail_rows)
    scored = _allocate_next_budget(scored, level)
    scored["recommendation_reason"] = scored.apply(_recommendation_reason, axis=1)
    return scored, details


def _allocate_next_budget(scorecard: pd.DataFrame, level: str) -> pd.DataFrame:
    result = scorecard.copy()
    result["allocation_weight"] = 0.0
    eligible = result["next_cycle_action"].isin(["SCALE_NEXT_CYCLE", "KEEP_AS_TEST"])
    evidence_target = result["minimum_evidence_required"] * 2
    evidence_factor = (
        result["observed_conversations"] / evidence_target.replace({0: 1})
    ).clip(upper=1)
    action_factor = (
        result["next_cycle_action"]
        .map({"SCALE_NEXT_CYCLE": 1.25, "KEEP_AS_TEST": 0.75})
        .fillna(0)
    )
    result.loc[eligible, "allocation_weight"] = (
        (result.loc[eligible, "outcome_score"] - 50).clip(lower=1)
        * evidence_factor.loc[eligible]
        * action_factor.loc[eligible]
    )

    group_columns = ["campaign_type"] if level == "campaign" else ["campaign_id"]
    group_total = result.groupby(group_columns)["allocation_weight"].transform("sum")
    result["recommended_budget_share_pct"] = 0.0
    funded_groups = group_total.gt(0)
    result.loc[funded_groups, "recommended_budget_share_pct"] = (
        result.loc[funded_groups, "allocation_weight"]
        .div(group_total.loc[funded_groups])
        .mul(100)
    )
    return result


def _recommendation_reason(row: pd.Series) -> str:
    action = row.get("next_cycle_action")
    strongest = row.get("strongest_outcome_kpis") or "the strongest outcome measures"
    weakest = row.get("weakest_outcome_kpi") or "outcome quality"
    evidence = int(row.get("observed_conversations", 0) or 0)
    if action == "INSUFFICIENT_EVIDENCE":
        return (
            f"Do not make a firm next-cycle budget decision: only {evidence} "
            f"observed WhatsApp conversations were available."
        )
    if action == "SCALE_NEXT_CYCLE":
        return (
            f"Increase next-cycle allocation because {strongest} were the "
            f"strongest outcome signals; continue monitoring {weakest}."
        )
    if action == "KEEP_AS_TEST":
        return (
            f"Keep a controlled test allocation: {strongest} were promising, "
            f"but {weakest} did not support aggressive scaling."
        )
    return (
        f"Assign no next-cycle budget because WhatsApp outcomes did not clear "
        f"the peer threshold; the clearest weakness was {weakest}."
    )


def generate_cycle_report(data: CycleData) -> CycleReport:
    """Create campaign, ad set, and ad scorecards for one completed cycle."""
    campaign_scorecard = _build_level_scorecard(data, "campaign")
    adset_scorecard = _build_level_scorecard(data, "adset")
    ad_scorecard = _build_level_scorecard(data, "ad")

    campaign_scorecard, target_details = _evaluate_campaign_targets(campaign_scorecard)
    campaign_scorecard, campaign_allocation = _evaluate_outcomes(
        campaign_scorecard, "campaign"
    )
    adset_scorecard, adset_allocation = _evaluate_outcomes(adset_scorecard, "adset")
    ad_scorecard, ad_allocation = _evaluate_outcomes(ad_scorecard, "ad")

    allocation_details = pd.concat(
        [campaign_allocation, adset_allocation, ad_allocation], ignore_index=True
    )
    return CycleReport(
        campaign_scorecard=campaign_scorecard,
        adset_scorecard=adset_scorecard,
        ad_scorecard=ad_scorecard,
        target_kpi_details=target_details,
        allocation_kpi_details=allocation_details,
        target_framework=pd.DataFrame(target_framework_table()),
        data_quality=data_quality_summary(data),
    )
