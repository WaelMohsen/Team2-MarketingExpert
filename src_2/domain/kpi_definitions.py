"""Pure KPI formulas; YAML selects metrics but never executes formulas."""

from __future__ import annotations


def safe_divide(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def ratio_percent(numerator: float, denominator: float) -> float | None:
    value = safe_divide(numerator, denominator)
    return None if value is None else value * 100


def net_roas(net_revenue: float, spend: float) -> float | None:
    return safe_divide(net_revenue, spend)


def average_order_value(
    delivered_revenue: float, delivered_orders: float
) -> float | None:
    return safe_divide(delivered_revenue, delivered_orders)


def cost_per_outcome(spend: float, outcomes: float) -> float | None:
    return safe_divide(spend, outcomes)
