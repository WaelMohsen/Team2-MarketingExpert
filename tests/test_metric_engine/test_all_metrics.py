import numpy as np
import pandas as pd
import pytest

from src.metrics_engine.acquisition import calculate as calc_acquisition
from src.metrics_engine.base_metrics import calculate_base_metrics
from src.metrics_engine.retention import calculate as calc_retention
from src.metrics_engine.revenue import calculate as calc_revenue
from src.metrics_engine.satisfaction import calculate as calc_satisfaction

# ── helpers ──────────────────────────────────────────────────────────────────


def _sample_campaign_df(overrides=None):
    data = {
        "campaign_name": ["Summer Sale"] * 5,
        "spend": [100, 150, 200, 175, 125],
        "revenue": [500, 750, 1000, 850, 600],
        "impressions": [10000, 12000, 15000, 13000, 11000],
        "clicks": [500, 600, 750, 650, 550],
        "conversions": [50, 60, 75, 65, 55],
        "new_customers": [45, 55, 70, 60, 50],
    }
    df = pd.DataFrame(data)
    if overrides:
        for col, values in overrides.items():
            df[col] = values
    return df


def _acq_metrics(impressions=100000, clicks=5000, conversions=500):
    return {
        "Total Impressions": impressions,
        "Total Clicks": clicks,
        "Total Conversions": conversions,
    }


def _retention_df(retained=50, churn=0.15):
    return pd.DataFrame({"retained_customers": [retained], "churn_rate": [churn]})


def _revenue_df(purchases_per_year=3):
    return pd.DataFrame({"purchases_per_year": [purchases_per_year]})


def _revenue_metrics(revenue=1000, conversions=10, spend=500, clicks=100, cpa=50):
    return {
        "Total Revenue": revenue,
        "Total Conversions": conversions,
        "Total Spend": spend,
        "Total Clicks": clicks,
        "CPA": cpa,
    }


def _satisfaction_df(
    reach=10000, likes=500, comments=100, shares=50, bounce_rate=0.35, frequency=2.5
):
    return pd.DataFrame(
        {
            "reach": [reach],
            "likes": [likes],
            "comments": [comments],
            "shares": [shares],
            "bounce_rate": [bounce_rate],
            "frequency": [frequency],
        }
    )


# ── base_metrics.py ──────────────────────────────────────────────────────────


class TestBaseMetrics:

    def test_valid_complete_dataset(self):
        result = calculate_base_metrics(_sample_campaign_df())
        assert result["Campaign Name"] == "Summer Sale"
        assert result["Total Spend"] == 750.0
        assert result["Total Revenue"] == 3700.0
        assert result["Total Impressions"] == 61000
        assert result["Total Clicks"] == 3050
        assert result["Total Conversions"] == 305
        assert "ROAS" in result and "CPA" in result

    def test_empty_dataframe_returns_none(self):
        assert calculate_base_metrics(pd.DataFrame()) is None

    def test_none_dataframe_returns_none(self):
        assert calculate_base_metrics(None) is None

    def test_missing_spend_defaults_zero(self):
        df = _sample_campaign_df()
        df = df.drop(columns=["spend"])
        assert calculate_base_metrics(df)["Total Spend"] == 0.0

    def test_zero_spend_roas_zero(self):
        result = calculate_base_metrics(_sample_campaign_df({"spend": [0] * 5}))
        assert result["ROAS"] == 0

    def test_zero_impressions_ctr_zero(self):
        result = calculate_base_metrics(
            _sample_campaign_df(
                {"impressions": [0] * 5, "clicks": [0] * 5, "conversions": [0] * 5}
            )
        )
        assert result["CTR"] == "0%"
        assert result["Conversion Rate"] == "0%"

    def test_ctr_percentage(self):
        result = calculate_base_metrics(
            _sample_campaign_df({"clicks": [100] * 5, "impressions": [10000] * 5})
        )
        assert result["CTR"] == "1.0%"

    def test_conversion_rate_percentage(self):
        result = calculate_base_metrics(
            _sample_campaign_df({"conversions": [50] * 5, "clicks": [500] * 5})
        )
        assert result["Conversion Rate"] == "10.0%"

    def test_cpa_calculation(self):
        result = calculate_base_metrics(
            _sample_campaign_df({"spend": [500] * 5, "new_customers": [50] * 5})
        )
        assert result["CPA"] == 10.0

    def test_roas_calculation(self):
        result = calculate_base_metrics(
            _sample_campaign_df({"revenue": [1000] * 5, "spend": [100] * 5})
        )
        assert result["ROAS"] == 10.0

    def test_zero_new_customers_cpa_zero(self):
        result = calculate_base_metrics(_sample_campaign_df({"new_customers": [0] * 5}))
        assert result["CPA"] == 0

    def test_missing_campaign_name_defaults_unknown(self):
        df = _sample_campaign_df()
        df = df.drop(columns=["campaign_name"])
        assert calculate_base_metrics(df)["Campaign Name"] == "Unknown Campaign"

    def test_missing_new_customers_falls_back_to_conversions(self):
        df = _sample_campaign_df()
        df = df.drop(columns=["new_customers"])
        result = calculate_base_metrics(df)
        assert result["Total New Customers"] == result["Total Conversions"]

    def test_large_dataset(self):
        data = {
            k: [v] * 1000
            for k, v in {
                "campaign_name": "C",
                "spend": 100,
                "revenue": 500,
                "impressions": 10000,
                "clicks": 500,
                "conversions": 50,
                "new_customers": 45,
            }.items()
        }
        result = calculate_base_metrics(pd.DataFrame(data))
        assert result["Total Spend"] == 100_000.0
        assert result["Total Revenue"] == 500_000.0


# ── acquisition.py ───────────────────────────────────────────────────────────


class TestAcquisitionMetrics:

    def test_valid_calculation(self):
        result = calc_acquisition(pd.DataFrame(), _acq_metrics(100000, 5000, 500))
        assert result["CTR"] == 5.0
        assert result["Conversion Rate"] == 10.0

    def test_zero_impressions(self):
        result = calc_acquisition(pd.DataFrame(), _acq_metrics(0, 100, 10))
        assert result["CTR"] == 0

    def test_zero_clicks(self):
        result = calc_acquisition(pd.DataFrame(), _acq_metrics(100000, 0, 10))
        assert result["CTR"] == 0.0
        assert result["Conversion Rate"] == 0

    def test_more_conversions_than_clicks(self):
        result = calc_acquisition(pd.DataFrame(), _acq_metrics(100000, 1000, 2000))
        assert result["Conversion Rate"] == 200.0

    def test_more_clicks_than_impressions(self):
        result = calc_acquisition(pd.DataFrame(), _acq_metrics(1000, 5000, 500))
        assert result["CTR"] == 500.0

    def test_precise_decimal(self):
        result = calc_acquisition(pd.DataFrame(), _acq_metrics(333333, 1000, 100))
        assert result["CTR"] == round((1000 / 333333) * 100, 2)


# ── retention.py ─────────────────────────────────────────────────────────────


class TestRetentionMetrics:

    def test_decimal_churn(self):
        result = calc_retention(_retention_df(150, 0.10), {})
        assert result["Retained Customers"] == 150
        assert result["Churn Rate"] == 10.0
        assert result["Retention Rate"] == 90.0

    def test_percentage_churn(self):
        result = calc_retention(_retention_df(200, 25.0), {})
        assert result["Churn Rate"] == 25.0
        assert result["Retention Rate"] == 75.0

    def test_missing_retained_customers(self):
        result = calc_retention(pd.DataFrame({"churn_rate": [0.15]}), {})
        assert result["Retained Customers"] == 0

    def test_missing_churn_rate(self):
        result = calc_retention(pd.DataFrame({"retained_customers": [100]}), {})
        assert result["Churn Rate"] is None
        assert result["Retention Rate"] is None

    def test_empty_dataframe(self):
        result = calc_retention(pd.DataFrame(), {})
        assert result["Retained Customers"] == 0
        assert result["Churn Rate"] is None

    def test_multiple_rows_averages(self):
        df = pd.DataFrame(
            {"retained_customers": [100, 150, 200], "churn_rate": [0.10, 0.15, 0.20]}
        )
        result = calc_retention(df, {})
        assert result["Retained Customers"] == 450
        assert result["Churn Rate"] == 15.0
        assert result["Retention Rate"] == 85.0

    def test_churn_above_100(self):
        result = calc_retention(_retention_df(0, 150.0), {})
        assert result["Churn Rate"] == 150.0
        assert result["Retention Rate"] == -50.0

    def test_nan_churn_rate(self):
        df = pd.DataFrame({"retained_customers": [100], "churn_rate": [np.nan]})
        result = calc_retention(df, {})
        assert result["Churn Rate"] is None or pd.isna(result["Churn Rate"])


# ── revenue.py ───────────────────────────────────────────────────────────────


class TestRevenueMetrics:

    def test_complete_revenue_data(self):
        result = calc_revenue(_revenue_df(3), _revenue_metrics(5000, 50, 1000, 100, 20))
        assert result["AOV"] == 100.0
        assert result["Annual Customer Value"] == 300.0
        assert result["Marketing ROI"] == 400.0
        assert result["Revenue Per Click"] == 50.0
        assert result["LTV:CAC Ratio"] == 15.0

    def test_zero_conversions(self):
        result = calc_revenue(_revenue_df(3), _revenue_metrics(0, 0, 1000, 100, 0))
        assert result["AOV"] == 0
        assert result["Marketing ROI"] == -100.0

    def test_zero_spend(self):
        result = calc_revenue(_revenue_df(3), _revenue_metrics(1000, 10, 0, 100, 0))
        assert result["Marketing ROI"] == 0

    def test_zero_clicks(self):
        result = calc_revenue(_revenue_df(3), _revenue_metrics(1000, 10, 500, 0, 50))
        assert result["Revenue Per Click"] == 0

    def test_missing_purchases_per_year(self):
        result = calc_revenue(pd.DataFrame(), _revenue_metrics())
        assert result["Annual Customer Value"] == 0.0

    def test_negative_revenue(self):
        result = calc_revenue(_revenue_df(3), _revenue_metrics(-500, 50, 1000, 100, 20))
        assert result["AOV"] == -10.0
        assert result["Marketing ROI"] == -150.0

    def test_large_scale(self):
        result = calc_revenue(
            _revenue_df(3), _revenue_metrics(1_000_000, 10000, 100_000, 50000, 10)
        )
        assert result["AOV"] == 100.0
        assert result["Marketing ROI"] == 900.0
        assert result["LTV:CAC Ratio"] == 30.0


# ── satisfaction.py ──────────────────────────────────────────────────────────


class TestSatisfactionMetrics:

    def test_valid_engagement(self):
        result = calc_satisfaction(_satisfaction_df(10000, 500, 100, 50), {})
        assert result["Engagement Rate"] == 6.5
        assert result["Average Bounce Rate"] == 0.35
        assert result["Average Frequency"] == 2.5

    def test_zero_reach(self):
        result = calc_satisfaction(_satisfaction_df(reach=0), {})
        assert result["Engagement Rate"] == 0

    def test_missing_reach(self):
        df = pd.DataFrame(
            {
                "likes": [500],
                "comments": [100],
                "shares": [50],
                "bounce_rate": [0.35],
                "frequency": [2.5],
            }
        )
        result = calc_satisfaction(df, {})
        assert result["Engagement Rate"] == 0

    def test_missing_engagement_columns_raises(self):
        df = pd.DataFrame({"reach": [10000], "bounce_rate": [0.35], "frequency": [2.5]})
        with pytest.raises(KeyError):
            calc_satisfaction(df, {})

    def test_missing_bounce_rate(self):
        df = pd.DataFrame(
            {
                "reach": [10000],
                "likes": [500],
                "comments": [100],
                "shares": [50],
                "frequency": [2.5],
            }
        )
        result = calc_satisfaction(df, {})
        assert result["Average Bounce Rate"] is None

    def test_missing_frequency(self):
        df = pd.DataFrame(
            {
                "reach": [10000],
                "likes": [500],
                "comments": [100],
                "shares": [50],
                "bounce_rate": [0.35],
            }
        )
        result = calc_satisfaction(df, {})
        assert result["Average Frequency"] is None

    def test_multiple_rows_averages(self):
        df = pd.DataFrame(
            {
                "reach": [5000, 5000],
                "likes": [250, 250],
                "comments": [50, 50],
                "shares": [25, 25],
                "bounce_rate": [0.30, 0.40],
                "frequency": [2.0, 3.0],
            }
        )
        result = calc_satisfaction(df, {})
        assert result["Engagement Rate"] == 6.5
        assert result["Average Bounce Rate"] == 0.35
        assert result["Average Frequency"] == 2.5

    def test_nan_likes_skipped(self):
        df = pd.DataFrame(
            {
                "reach": [10000],
                "likes": [np.nan],
                "comments": [100],
                "shares": [50],
                "bounce_rate": [0.35],
                "frequency": [2.5],
            }
        )
        result = calc_satisfaction(df, {})
        assert result["Engagement Rate"] == 1.5

    def test_empty_dataframe(self):
        df = pd.DataFrame(
            {
                "reach": [],
                "likes": [],
                "comments": [],
                "shares": [],
                "bounce_rate": [],
                "frequency": [],
            }
        )
        result = calc_satisfaction(df, {})
        assert result["Engagement Rate"] == 0.0
