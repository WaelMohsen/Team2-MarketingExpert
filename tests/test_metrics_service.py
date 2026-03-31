import pandas as pd

from src.metrics import CampaignMetricsService


def _sample_campaign_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "campaign_name": "Launch",
                "date": "2026-03-01",
                "channel": "Email",
                "impressions": 100,
                "clicks": 10,
                "conversions": 2,
                "spend": 50.0,
                "revenue": 200.0,
                "new_customers": 2,
                "reach": 0,
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "bounce_rate": 0.2,
                "frequency": 1.5,
                "retained_customers": 20,
                "churn_rate": 0.0,
                "purchases_per_year": 4.0,
                "product_profit_margin": 0.4,
            },
            {
                "campaign_name": "Launch",
                "date": "2026-03-02",
                "channel": "Social",
                "impressions": 200,
                "clicks": 20,
                "conversions": 4,
                "spend": 100.0,
                "revenue": 400.0,
                "new_customers": 4,
                "reach": 150,
                "likes": 10,
                "comments": 5,
                "shares": 5,
                "bounce_rate": 0.3,
                "frequency": 2.5,
                "retained_customers": 30,
                "churn_rate": 0.0,
                "purchases_per_year": 4.0,
                "product_profit_margin": 0.4,
            },
        ]
    )


def test_calculate_full_returns_overall_and_per_channel_metrics():
    service = CampaignMetricsService()

    result = service.calculate_full(_sample_campaign_dataframe(), "Revenue Growth")

    assert result.overall["Total Spend"] == 150.0
    assert result.overall["Total Revenue"] == 600.0
    assert result.overall["CTR"] == 10.0
    assert result.overall["Conversion Rate"] == 20.0
    assert result.overall["AOV"] == 100.0
    assert result.overall["Annual Customer Value"] == 400.0
    assert result.overall["Marketing ROI"] == 300.0
    assert result.overall["Revenue Per Click"] == 20.0
    assert result.overall["LTV:CAC Ratio"] == 16.0
    assert set(result.per_channel.keys()) == {"Email", "Social"}


def test_retention_metrics_preserve_zero_churn_values():
    service = CampaignMetricsService()

    result = service.calculate(_sample_campaign_dataframe(), "Customer Retention")

    assert result["Retained Customers"] == 50
    assert result["Churn Rate"] == 0.0
    assert result["Retention Rate"] == 100.0


def test_calculate_full_without_channel_returns_empty_per_channel():
    service = CampaignMetricsService()
    dataframe = _sample_campaign_dataframe().drop(columns=["channel"])

    result = service.calculate_full(dataframe, "Customer Acquisition")

    assert result.per_channel == {}
