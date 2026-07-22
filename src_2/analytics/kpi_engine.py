"""Core derived fields shared by every aggregation level."""

from __future__ import annotations

from src_2.domain.kpi_definitions import (
    average_order_value,
    cost_per_outcome,
    net_roas,
    ratio_percent,
)


def calculate_core_kpis(totals: dict[str, float]) -> dict[str, float | None]:
    return {
        "link_ctr_pct": ratio_percent(
            totals.get("link_clicks", 0), totals.get("impressions", 0)
        ),
        "cpm": cost_per_outcome(
            totals.get("spend", 0) * 1000, totals.get("impressions", 0)
        ),
        "cost_per_observed_conversation": cost_per_outcome(
            totals.get("spend", 0), totals.get("observed_conversations", 0)
        ),
        "cost_per_delivered_order": cost_per_outcome(
            totals.get("spend", 0), totals.get("delivered_orders", 0)
        ),
        "net_roas": net_roas(
            totals.get("net_revenue", 0), totals.get("spend", 0)
        ),
        "aov": average_order_value(
            totals.get("delivered_revenue", 0), totals.get("delivered_orders", 0)
        ),
        "delivered_rate_pct": ratio_percent(
            totals.get("delivered_orders", 0),
            totals.get("observed_conversations", 0),
        ),
        "negative_outcome_rate_pct": ratio_percent(
            totals.get("negative_outcomes", 0),
            totals.get("observed_conversations", 0),
        ),
    }
