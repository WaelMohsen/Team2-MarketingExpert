"""Pure functions for campaign metric calculations."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from .models import MetricsMap

MetricCalculator = Callable[[pd.DataFrame, MetricsMap], MetricsMap]


def _column_sum(dataframe: pd.DataFrame, column_name: str, *, as_int: bool = False) -> int | float:
    if column_name not in dataframe:
        return 0 if as_int else 0.0

    total = dataframe[column_name].fillna(0).sum()
    return int(total) if as_int else float(total)


def _column_mean(dataframe: pd.DataFrame, column_name: str) -> float | None:
    if column_name not in dataframe:
        return None

    non_null_values = dataframe[column_name].dropna()
    if non_null_values.empty:
        return None

    return round(float(non_null_values.mean()), 2)


def calculate_base_metrics(dataframe: pd.DataFrame) -> MetricsMap:
    """Calculate metrics shared by every marketing category."""

    if dataframe is None or dataframe.empty:
        return {}

    campaign_name = (
        str(dataframe["campaign_name"].iloc[0])
        if "campaign_name" in dataframe and not dataframe.empty
        else "Unknown Campaign"
    )
    total_spend = _column_sum(dataframe, "spend")
    total_revenue = _column_sum(dataframe, "revenue")
    total_impressions = _column_sum(dataframe, "impressions", as_int=True)
    total_clicks = _column_sum(dataframe, "clicks", as_int=True)
    total_conversions = _column_sum(dataframe, "conversions", as_int=True)

    new_customers_column = "new_customers" if "new_customers" in dataframe else "conversions"
    total_new_customers = _column_sum(dataframe, new_customers_column, as_int=True)

    ctr = round((total_clicks / total_impressions) * 100, 2) if total_impressions else 0.0
    conversion_rate = round((total_conversions / total_clicks) * 100, 2) if total_clicks else 0.0

    return {
        "Campaign Name": campaign_name,
        "Total Spend": total_spend,
        "Total Revenue": total_revenue,
        "Total Impressions": total_impressions,
        "Total Clicks": total_clicks,
        "Total Conversions": total_conversions,
        "Total New Customers": total_new_customers,
        "Conversion Rate": conversion_rate,
        "CTR": ctr,
        "CPA": round(total_spend / total_new_customers, 2) if total_new_customers else 0.0,
        "ROAS": round(total_revenue / total_spend, 2) if total_spend else 0.0,
    }


def calculate_acquisition_metrics(dataframe: pd.DataFrame, metrics: MetricsMap) -> MetricsMap:
    """Calculate customer acquisition-specific metrics."""

    impressions = int(metrics["Total Impressions"])
    clicks = int(metrics["Total Clicks"])
    conversions = int(metrics["Total Conversions"])

    metrics["CTR"] = round((clicks / impressions) * 100, 2) if impressions else 0.0
    metrics["Conversion Rate"] = round((conversions / clicks) * 100, 2) if clicks else 0.0
    return metrics


def calculate_satisfaction_metrics(dataframe: pd.DataFrame, metrics: MetricsMap) -> MetricsMap:
    """Calculate customer satisfaction-specific metrics."""

    total_reach = _column_sum(dataframe, "reach")
    total_engagements = sum(
        _column_sum(dataframe, column_name)
        for column_name in ("likes", "comments", "shares")
    )

    engagement_rate = round((total_engagements / total_reach) * 100, 2) if total_reach else 0.0

    metrics["Engagement Rate"] = engagement_rate
    metrics["Average Bounce Rate"] = _column_mean(dataframe, "bounce_rate")
    metrics["Average Frequency"] = _column_mean(dataframe, "frequency")
    return metrics


def calculate_revenue_metrics(dataframe: pd.DataFrame, metrics: MetricsMap) -> MetricsMap:
    """Calculate revenue-growth-specific metrics."""

    total_conversions = int(metrics["Total Conversions"])
    total_clicks = int(metrics["Total Clicks"])
    total_spend = float(metrics["Total Spend"])
    total_revenue = float(metrics["Total Revenue"])
    cpa = float(metrics["CPA"])

    average_order_value = round(total_revenue / total_conversions, 2) if total_conversions else 0.0
    purchases_per_year = _column_mean(dataframe, "purchases_per_year") or 0.0
    annual_customer_value = round(average_order_value * purchases_per_year, 2)

    metrics["AOV"] = average_order_value
    metrics["Annual Customer Value"] = annual_customer_value
    metrics["Marketing ROI"] = round(((total_revenue - total_spend) / total_spend) * 100, 2) if total_spend else 0.0
    metrics["Revenue Per Click"] = round(total_revenue / total_clicks, 2) if total_clicks else 0.0
    if cpa:
        metrics["LTV:CAC Ratio"] = round(annual_customer_value / cpa, 2)

    return metrics


def calculate_retention_metrics(dataframe: pd.DataFrame, metrics: MetricsMap) -> MetricsMap:
    """Calculate customer retention-specific metrics."""

    retained_customers = _column_sum(dataframe, "retained_customers", as_int=True)
    churn_rate = _column_mean(dataframe, "churn_rate")

    if churn_rate is None:
        churn_percent = None
        retention_rate = None
    else:
        churn_percent = churn_rate * 100 if churn_rate <= 1 else churn_rate
        retention_rate = round(100 - churn_percent, 2)
        churn_percent = round(churn_percent, 2)

    metrics["Retained Customers"] = retained_customers
    metrics["Churn Rate"] = churn_percent
    metrics["Retention Rate"] = retention_rate
    return metrics
