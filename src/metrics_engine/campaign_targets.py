"""Campaign-type KPI definitions for ended-cycle reporting.

Primary KPIs describe whether a campaign achieved the job associated with its
campaign type. Allocation KPIs are deliberately outcome-first: they decide
where the next cycle's budget should go using observed WhatsApp outcomes.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Optional


def _metric(
    metric: str,
    label: str,
    direction: str,
    weight: float,
    *,
    factor: float = 1.0,
    fixed_target: Optional[float] = None,
    min_target: Optional[float] = None,
    max_target: Optional[float] = None,
) -> dict:
    return {
        "metric": metric,
        "label": label,
        "direction": direction,
        "weight": weight,
        "factor": factor,
        "fixed_target": fixed_target,
        "min_target": min_target,
        "max_target": max_target,
    }


TARGET_CONFIGS = {
    "awareness": {
        "target_job": "Create efficient qualified visibility before expecting sales.",
        "success_question": "Did the campaign create efficient visibility, and did that attention produce useful WhatsApp outcomes?",
        "primary_kpis": [
            _metric("reach", "Reach", "higher", 0.30),
            _metric("cpm", "Cost per 1,000 Impressions", "lower", 0.25),
            _metric(
                "frequency",
                "Frequency",
                "range",
                0.20,
                min_target=1.0,
                max_target=3.5,
            ),
            _metric("link_ctr_pct", "Link Click Rate", "higher", 0.25),
        ],
        "recommended_kpis": [
            "observed_conversations",
            "delivered_rate",
            "cost_per_delivered_order",
            "negative_outcome_rate",
        ],
        "allocation_kpis": [
            _metric("delivered_rate", "Delivered Order Rate", "higher", 0.30),
            _metric(
                "cost_per_delivered_order",
                "Cost per Delivered Order",
                "lower",
                0.25,
            ),
            _metric("net_revenue", "Net Revenue", "higher", 0.20),
            _metric(
                "negative_outcome_rate",
                "Negative Outcome Rate",
                "lower",
                0.25,
            ),
        ],
    },
    "always_on": {
        "target_job": "Acquire steady sales with stable economics.",
        "success_question": "Did the campaign generate continuous delivered orders at acceptable cost and quality?",
        "primary_kpis": [
            _metric("net_roas", "Net Return on Ad Spend", "higher", 0.30),
            _metric("delivered_rate", "Delivered Order Rate", "higher", 0.25),
            _metric(
                "cost_per_delivered_order",
                "Cost per Delivered Order",
                "lower",
                0.20,
            ),
            _metric(
                "observed_conversations",
                "Observed WhatsApp Conversations",
                "higher",
                0.15,
            ),
            _metric(
                "negative_outcome_rate",
                "Negative Outcome Rate",
                "lower",
                0.10,
            ),
        ],
        "recommended_kpis": [
            "order_creation_rate",
            "aov",
            "net_revenue_per_day",
            "repeat_order_rate",
        ],
        "allocation_kpis": [
            _metric("net_roas", "Net Return on Ad Spend", "higher", 0.35),
            _metric("delivered_rate", "Delivered Order Rate", "higher", 0.25),
            _metric(
                "cost_per_delivered_order",
                "Cost per Delivered Order",
                "lower",
                0.25,
            ),
            _metric(
                "negative_outcome_rate",
                "Negative Outcome Rate",
                "lower",
                0.15,
            ),
        ],
    },
    "promotional": {
        "target_job": "Turn offer-driven WhatsApp interest into delivered orders quickly and efficiently.",
        "success_question": "Did the promotion create affordable conversations that became valuable orders?",
        "primary_kpis": [
            _metric(
                "cost_per_observed_conversation",
                "Cost per Observed WhatsApp Conversation",
                "lower",
                0.25,
            ),
            _metric("order_creation_rate", "Order Creation Rate", "higher", 0.25),
            _metric("net_roas", "Net Return on Ad Spend", "higher", 0.20),
            _metric("aov", "Average Order Value", "higher", 0.15),
            _metric(
                "negative_outcome_rate",
                "Negative Outcome Rate",
                "lower",
                0.15,
            ),
        ],
        "recommended_kpis": [
            "delivered_rate",
            "refund_rate",
            "cancelled_orders",
            "net_revenue_per_day",
        ],
        "allocation_kpis": [
            _metric("net_roas", "Net Return on Ad Spend", "higher", 0.30),
            _metric("delivered_rate", "Delivered Order Rate", "higher", 0.25),
            _metric("aov", "Average Order Value", "higher", 0.20),
            _metric(
                "negative_outcome_rate",
                "Negative Outcome Rate",
                "lower",
                0.25,
            ),
        ],
    },
    "seasonal": {
        "target_job": "Capture time-sensitive demand during a limited cycle.",
        "success_question": "Did the campaign produce strong delivered revenue during its seasonal window?",
        "primary_kpis": [
            _metric("net_revenue_per_day", "Net Revenue per Day", "higher", 0.30),
            _metric("delivered_orders", "Delivered Orders", "higher", 0.25),
            _metric("net_roas", "Net Return on Ad Spend", "higher", 0.25),
            _metric(
                "cost_per_delivered_order",
                "Cost per Delivered Order",
                "lower",
                0.10,
            ),
            _metric(
                "negative_outcome_rate",
                "Negative Outcome Rate",
                "lower",
                0.10,
            ),
        ],
        "recommended_kpis": [
            "aov",
            "order_creation_rate",
            "refund_rate",
            "unique_products_ordered",
        ],
        "allocation_kpis": [
            _metric("net_revenue_per_day", "Net Revenue per Day", "higher", 0.30),
            _metric("net_roas", "Net Return on Ad Spend", "higher", 0.25),
            _metric("delivered_rate", "Delivered Order Rate", "higher", 0.25),
            _metric(
                "negative_outcome_rate",
                "Negative Outcome Rate",
                "lower",
                0.20,
            ),
        ],
    },
    "experimental": {
        "target_job": "Generate enough evidence to identify audiences and creatives worth funding again.",
        "success_question": "Did the test produce enough outcome evidence to separate winners from losers?",
        "primary_kpis": [
            _metric(
                "unique_creatives",
                "Unique Creatives",
                "higher",
                0.20,
                fixed_target=2.0,
            ),
            _metric("ad_count", "Ads Tested", "higher", 0.20, fixed_target=3.0),
            _metric(
                "observed_conversations",
                "Observed WhatsApp Conversations",
                "higher",
                0.25,
            ),
            _metric(
                "cost_per_observed_conversation",
                "Cost per Observed WhatsApp Conversation",
                "lower",
                0.20,
            ),
            _metric(
                "negative_outcome_rate",
                "Negative Outcome Rate",
                "lower",
                0.15,
            ),
        ],
        "recommended_kpis": [
            "delivered_rate",
            "net_roas",
            "aov",
            "orders_created",
        ],
        "allocation_kpis": [
            _metric("delivered_rate", "Delivered Order Rate", "higher", 0.30),
            _metric(
                "cost_per_observed_conversation",
                "Cost per Observed WhatsApp Conversation",
                "lower",
                0.25,
            ),
            _metric("net_roas", "Net Return on Ad Spend", "higher", 0.20),
            _metric(
                "negative_outcome_rate",
                "Negative Outcome Rate",
                "lower",
                0.25,
            ),
        ],
    },
    "launch": {
        "target_job": "Validate demand for newly launched or newly emphasized products.",
        "success_question": "Did the launch create product adoption and delivered revenue without poor-quality outcomes?",
        "primary_kpis": [
            _metric("net_revenue", "Net Revenue", "higher", 0.30),
            _metric(
                "unique_products_ordered",
                "Unique Products Ordered",
                "higher",
                0.20,
            ),
            _metric("net_revenue_per_day", "Net Revenue per Day", "higher", 0.20),
            _metric("delivered_rate", "Delivered Order Rate", "higher", 0.15),
            _metric(
                "negative_outcome_rate",
                "Negative Outcome Rate",
                "lower",
                0.15,
            ),
        ],
        "recommended_kpis": [
            "units_ordered",
            "aov",
            "cost_per_delivered_order",
            "refund_rate",
        ],
        "allocation_kpis": [
            _metric("net_revenue", "Net Revenue", "higher", 0.30),
            _metric(
                "unique_products_ordered",
                "Unique Products Ordered",
                "higher",
                0.20,
            ),
            _metric("delivered_rate", "Delivered Order Rate", "higher", 0.25),
            _metric(
                "negative_outcome_rate",
                "Negative Outcome Rate",
                "lower",
                0.25,
            ),
        ],
    },
    "scale": {
        "target_job": "Increase outcome volume while protecting efficiency and quality.",
        "success_question": "Did the campaign grow WhatsApp outcome volume without breaking return, cost, or quality?",
        "primary_kpis": [
            _metric(
                "observed_conversations",
                "Observed WhatsApp Conversations",
                "higher",
                0.30,
            ),
            _metric(
                "net_roas",
                "Net Return on Ad Spend",
                "higher",
                0.25,
                factor=0.80,
            ),
            _metric(
                "cost_per_delivered_order",
                "Cost per Delivered Order",
                "lower",
                0.20,
                factor=1.20,
            ),
            _metric(
                "observed_conversations_per_day",
                "Observed Conversations per Day",
                "higher",
                0.15,
            ),
            _metric(
                "negative_outcome_rate",
                "Negative Outcome Rate",
                "lower",
                0.10,
            ),
        ],
        "recommended_kpis": [
            "delivered_rate",
            "net_revenue_per_day",
            "aov",
            "refund_rate",
        ],
        "allocation_kpis": [
            _metric("net_roas", "Net Return on Ad Spend", "higher", 0.30),
            _metric("delivered_rate", "Delivered Order Rate", "higher", 0.25),
            _metric(
                "cost_per_delivered_order",
                "Cost per Delivered Order",
                "lower",
                0.25,
            ),
            _metric(
                "negative_outcome_rate",
                "Negative Outcome Rate",
                "lower",
                0.20,
            ),
        ],
    },
    "retention": {
        "target_job": "Re-engage existing customers and create profitable repeat orders.",
        "success_question": "Did the campaign bring previous customers back and convert them into valuable delivered orders?",
        "primary_kpis": [
            _metric(
                "repeat_conversation_rate",
                "Repeat Conversation Rate",
                "higher",
                0.25,
            ),
            _metric(
                "repeat_delivered_orders",
                "Repeat Delivered Orders",
                "higher",
                0.25,
            ),
            _metric("net_roas", "Net Return on Ad Spend", "higher", 0.20),
            _metric("aov", "Average Order Value", "higher", 0.15),
            _metric(
                "negative_outcome_rate",
                "Negative Outcome Rate",
                "lower",
                0.15,
            ),
        ],
        "recommended_kpis": [
            "repeat_order_rate",
            "delivered_rate",
            "cost_per_delivered_order",
            "refund_rate",
        ],
        "allocation_kpis": [
            _metric(
                "repeat_delivered_orders",
                "Repeat Delivered Orders",
                "higher",
                0.30,
            ),
            _metric(
                "repeat_conversation_rate",
                "Repeat Conversation Rate",
                "higher",
                0.25,
            ),
            _metric("net_roas", "Net Return on Ad Spend", "higher", 0.25),
            _metric(
                "negative_outcome_rate",
                "Negative Outcome Rate",
                "lower",
                0.20,
            ),
        ],
    },
}


CAMPAIGN_TYPES = tuple(TARGET_CONFIGS)

KPI_LABELS = {
    "observed_conversations": "Observed WhatsApp Conversations",
    "orders_created": "Orders Created",
    "delivered_orders": "Delivered Orders",
    "delivered_rate": "Delivered Order Rate",
    "cost_per_observed_conversation": "Cost per Observed WhatsApp Conversation",
    "cost_per_delivered_order": "Cost per Delivered Order",
    "net_revenue": "Net Revenue",
    "net_revenue_per_day": "Net Revenue per Day",
    "net_roas": "Net Return on Ad Spend",
    "aov": "Average Order Value",
    "order_creation_rate": "Order Creation Rate",
    "negative_outcome_rate": "Negative Outcome Rate",
    "refund_rate": "Refund Rate",
    "cancelled_orders": "Cancelled Orders",
    "repeat_conversation_rate": "Repeat Conversation Rate",
    "repeat_delivered_orders": "Repeat Delivered Orders",
    "repeat_order_rate": "Repeat Order Rate",
    "unique_products_ordered": "Unique Products Ordered",
    "units_ordered": "Units Ordered",
}


def kpi_label(metric: str) -> str:
    return KPI_LABELS.get(metric, metric.replace("_", " ").title())


def get_target_config(campaign_type: str) -> dict:
    """Return an isolated target configuration for one campaign type."""
    key = str(campaign_type or "").strip().lower()
    if key not in TARGET_CONFIGS:
        raise ValueError(f"Unsupported campaign_type: {campaign_type!r}")
    return deepcopy(TARGET_CONFIGS[key])


def target_framework_table() -> list[dict]:
    """Return a serializable overview used by the report UI and LLM context."""
    rows = []
    for campaign_type, config in TARGET_CONFIGS.items():
        rows.append(
            {
                "campaign_type": campaign_type,
                "target_job": config["target_job"],
                "success_question": config["success_question"],
                "primary_kpis": ", ".join(
                    metric["label"] for metric in config["primary_kpis"]
                ),
                "recommended_kpis": ", ".join(
                    kpi_label(metric) for metric in config["recommended_kpis"]
                ),
                "next_budget_kpis": ", ".join(
                    metric["label"] for metric in config["allocation_kpis"]
                ),
            }
        )
    return rows
