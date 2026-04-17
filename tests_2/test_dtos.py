"""Unit tests for DTO (Data Transfer Object) classes."""

import sys
from pathlib import Path

# Add src_2 to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src_2"))

from DTOs.acquistion_metrics import Acquisition_Metrics  # noqa: E402
from DTOs.base_metrics import Base_Metrics  # noqa: E402
from DTOs.campaign_metrics import Campaign_Metrics  # noqa: E402
from DTOs.retention_metrics import Retention_Metrics  # noqa: E402
from DTOs.revenue_metrics import Revenue_Metrics  # noqa: E402
from DTOs.satisfaction_metrics import Satisfaction_Metrics  # noqa: E402


class TestBaseMetricsDTO:
    """Tests for Base_Metrics data transfer object."""

    def test_base_metrics_creation(self):
        """High: Base_Metrics created with all required fields."""
        metrics = Base_Metrics(
            total_spend=5000.0,
            total_revenue=10000.0,
            total_impressions=10000,
            total_clicks=500,
            total_conversions=50,
            total_new_customers=40,
        )

        assert metrics.total_spend == 5000.0
        assert metrics.total_revenue == 10000.0
        assert metrics.total_impressions == 10000
        assert metrics.total_clicks == 500
        assert metrics.total_conversions == 50
        assert metrics.total_new_customers == 40

    def test_base_metrics_with_zero_values(self):
        """Medium: Base_Metrics accepts zero values."""
        metrics = Base_Metrics(
            total_spend=0.0,
            total_revenue=0.0,
            total_impressions=0,
            total_clicks=0,
            total_conversions=0,
            total_new_customers=0,
        )

        assert metrics.total_spend == 0.0
        assert metrics.total_impressions == 0

    def test_base_metrics_with_large_values(self):
        """Medium: Base_Metrics handles large numbers."""
        metrics = Base_Metrics(
            total_spend=1000000.0,
            total_revenue=5000000.0,
            total_impressions=10000000,
            total_clicks=500000,
            total_conversions=50000,
            total_new_customers=40000,
        )

        assert metrics.total_spend == 1000000.0
        assert metrics.total_impressions == 10000000


class TestAcquisitionMetricsDTO:
    """Tests for Acquisition_Metrics DTO."""

    def test_acquisition_metrics_creation(self):
        """High: Acquisition_Metrics created with all fields."""
        metrics = Acquisition_Metrics(ctr=5.0, conversion_rate=10.0, cpa=125.0)

        assert metrics.ctr == 5.0
        assert metrics.conversion_rate == 10.0
        assert metrics.cpa == 125.0

    def test_acquisition_metrics_with_zero_values(self):
        """Medium: Acquisition_Metrics accepts zero metrics."""
        metrics = Acquisition_Metrics(ctr=0, conversion_rate=0, cpa=0)

        assert metrics.ctr == 0
        assert metrics.conversion_rate == 0

    def test_acquisition_metrics_with_decimals(self):
        """Medium: Acquisition_Metrics preserves decimal precision."""
        metrics = Acquisition_Metrics(ctr=5.68, conversion_rate=10.42, cpa=113.04)

        assert metrics.ctr == 5.68
        assert metrics.conversion_rate == 10.42
        assert metrics.cpa == 113.04


class TestRevenueMetricsDTO:
    """Tests for Revenue_Metrics DTO."""

    def test_revenue_metrics_creation(self):
        """High: Revenue_Metrics created with all fields."""
        metrics = Revenue_Metrics(
            roas=2.0,
            aov=200.0,
            annual_customer_value=500.0,
            marketing_roi=100.0,
            revenue_per_click=20.0,
            ltv_cac_ratio=4.0,
        )

        assert metrics.roas == 2.0
        assert metrics.aov == 200.0
        assert metrics.annual_customer_value == 500.0
        assert metrics.marketing_roi == 100.0
        assert metrics.revenue_per_click == 20.0
        assert metrics.ltv_cac_ratio == 4.0

    def test_revenue_metrics_with_zero_values(self):
        """Medium: Revenue_Metrics accepts zero values."""
        metrics = Revenue_Metrics(
            roas=0,
            aov=0,
            annual_customer_value=0,
            marketing_roi=0,
            revenue_per_click=0,
            ltv_cac_ratio=0,
        )

        assert metrics.roas == 0
        assert metrics.aov == 0

    def test_revenue_metrics_with_negative_roi(self):
        """Medium: Revenue_Metrics accepts negative ROI."""
        metrics = Revenue_Metrics(
            roas=0.5,
            aov=100.0,
            annual_customer_value=250.0,
            marketing_roi=-50.0,
            revenue_per_click=10.0,
            ltv_cac_ratio=2.5,
        )

        assert metrics.marketing_roi == -50.0  # Valid negative ROI


class TestRetentionMetricsDTO:
    """Tests for Retention_Metrics DTO."""

    def test_retention_metrics_creation(self):
        """High: Retention_Metrics created with all fields."""
        metrics = Retention_Metrics(
            retained_customers=30,
            churn_rate=10.0,
            retention_rate=90.0,
            purchases_per_year=2.5,
        )

        assert metrics.retained_customers == 30
        assert metrics.churn_rate == 10.0
        assert metrics.retention_rate == 90.0
        assert metrics.purchases_per_year == 2.5

    def test_retention_metrics_with_zero_churn(self):
        """Medium: Retention_Metrics handles perfect retention."""
        metrics = Retention_Metrics(
            retained_customers=100,
            churn_rate=0.0,
            retention_rate=100.0,
            purchases_per_year=3.0,
        )

        assert metrics.churn_rate == 0.0
        assert metrics.retention_rate == 100.0

    def test_retention_metrics_with_high_churn(self):
        """Medium: Retention_Metrics handles high churn."""
        metrics = Retention_Metrics(
            retained_customers=10,
            churn_rate=90.0,
            retention_rate=10.0,
            purchases_per_year=0.5,
        )

        assert metrics.churn_rate == 90.0
        assert metrics.retention_rate == 10.0


class TestSatisfactionMetricsDTO:
    """Tests for Satisfaction_Metrics DTO."""

    def test_satisfaction_metrics_creation(self):
        """High: Satisfaction_Metrics created with all fields."""
        metrics = Satisfaction_Metrics(
            total_reach=8000,
            engagement_rate=3.44,
            avg_bounce_rate=0.25,
            avg_frequency=1.5,
        )

        assert metrics.total_reach == 8000
        assert metrics.engagement_rate == 3.44
        assert metrics.avg_bounce_rate == 0.25
        assert metrics.avg_frequency == 1.5

    def test_satisfaction_metrics_with_zero_engagement(self):
        """Medium: Satisfaction_Metrics handles zero engagement."""
        metrics = Satisfaction_Metrics(
            total_reach=0, engagement_rate=0, avg_bounce_rate=0.5, avg_frequency=0
        )

        assert metrics.engagement_rate == 0
        assert metrics.total_reach == 0

    def test_satisfaction_metrics_with_high_bounce_rate(self):
        """Medium: Satisfaction_Metrics accepts high bounce rates."""
        metrics = Satisfaction_Metrics(
            total_reach=5000,
            engagement_rate=0.5,
            avg_bounce_rate=0.95,
            avg_frequency=1.0,
        )

        assert metrics.avg_bounce_rate == 0.95


class TestCampaignMetricsDTO:
    """Tests for Campaign_Metrics DTO."""

    def test_campaign_metrics_creation(self):
        """High: Campaign_Metrics created with all fields."""
        campaign = Campaign_Metrics(
            name="Q1 Campaign",
            date="2026-01-15",
            channel="Facebook",
            impressions=10000,
            clicks=500,
            conversions=50,
            spend=5000.0,
            revenue=10000.0,
            new_customers=40,
            reach=8000,
            likes=200,
            comments=50,
            shares=25,
            bounce_rate=0.25,
            frequency=1.5,
            retained_customers=30,
            churn_rate=0.1,
            purchases_per_year=2.5,
            product_profit_margin=0.3,
        )

        assert campaign.name == "Q1 Campaign"
        assert campaign.date == "2026-01-15"
        assert campaign.channel == "Facebook"
        assert campaign.impressions == 10000
        assert campaign.spend == 5000.0
        assert campaign.product_profit_margin == 0.3

    def test_campaign_metrics_with_different_channels(self):
        """High: Campaign_Metrics preserves different channel types."""
        channels = ["Facebook", "Email", "Paid Search", "LinkedIn", "TikTok"]

        for channel in channels:
            campaign = Campaign_Metrics(
                name="Test",
                date="2026-01-15",
                channel=channel,
                impressions=1000,
                clicks=50,
                conversions=5,
                spend=500.0,
                revenue=1000.0,
                new_customers=4,
                reach=800,
                likes=20,
                comments=5,
                shares=2,
                bounce_rate=0.3,
                frequency=1.2,
                retained_customers=3,
                churn_rate=0.15,
                purchases_per_year=2.0,
                product_profit_margin=0.25,
            )

            assert campaign.channel == channel

    def test_campaign_metrics_with_zero_metrics(self):
        """Medium: Campaign_Metrics accepts zero metrics."""
        campaign = Campaign_Metrics(
            name="Zero Campaign",
            date="2026-01-15",
            channel="Facebook",
            impressions=0,
            clicks=0,
            conversions=0,
            spend=0.0,
            revenue=0.0,
            new_customers=0,
            reach=0,
            likes=0,
            comments=0,
            shares=0,
            bounce_rate=0.0,
            frequency=0.0,
            retained_customers=0,
            churn_rate=0.0,
            purchases_per_year=0.0,
            product_profit_margin=0.0,
        )

        assert campaign.impressions == 0
        assert campaign.spend == 0.0

    def test_campaign_metrics_with_large_values(self):
        """Medium: Campaign_Metrics handles large numbers."""
        campaign = Campaign_Metrics(
            name="Large Campaign",
            date="2026-01-15",
            channel="Facebook",
            impressions=10000000,
            clicks=500000,
            conversions=50000,
            spend=5000000.0,
            revenue=10000000.0,
            new_customers=40000,
            reach=8000000,
            likes=2000000,
            comments=500000,
            shares=250000,
            bounce_rate=0.25,
            frequency=1.5,
            retained_customers=30000,
            churn_rate=0.1,
            purchases_per_year=2.5,
            product_profit_margin=0.3,
        )

        assert campaign.impressions == 10000000
        assert campaign.spend == 5000000.0


class TestDTODataTypes:
    """Tests for correct data type handling across DTOs."""

    def test_base_metrics_numeric_types(self):
        """High: Base_Metrics maintains correct numeric types."""
        metrics = Base_Metrics(
            total_spend=5000.5,
            total_revenue=10000.75,
            total_impressions=10000,
            total_clicks=500,
            total_conversions=50,
            total_new_customers=40,
        )

        assert isinstance(metrics.total_spend, float)
        assert isinstance(metrics.total_revenue, float)
        assert isinstance(metrics.total_impressions, int)
        assert isinstance(metrics.total_clicks, int)

    def test_campaign_metrics_string_fields(self):
        """High: Campaign_Metrics preserves string fields."""
        campaign = Campaign_Metrics(
            name="Test Campaign",
            date="2026-01-15",
            channel="Facebook",
            impressions=1000,
            clicks=50,
            conversions=5,
            spend=500.0,
            revenue=1000.0,
            new_customers=4,
            reach=800,
            likes=20,
            comments=5,
            shares=2,
            bounce_rate=0.3,
            frequency=1.2,
            retained_customers=3,
            churn_rate=0.15,
            purchases_per_year=2.0,
            product_profit_margin=0.25,
        )

        assert isinstance(campaign.name, str)
        assert isinstance(campaign.date, str)
        assert isinstance(campaign.channel, str)
