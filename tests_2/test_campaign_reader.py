"""Unit tests for Campaign_Reader class."""

import sys
import tempfile
from pathlib import Path

# Add src_2 to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src_2"))

import pytest  # noqa: E402
from readers.campaign_reader import Campaign_Reader  # noqa: E402


class TestCampaignReaderValidation:
    """Tests for Campaign_Reader input validation and error handling."""

    def test_read_campaign_with_invalid_file_raises_error(self):
        """Low: Non-existent file raises appropriate error."""
        reader = Campaign_Reader("/nonexistent/file.csv")

        with pytest.raises(FileNotFoundError):
            reader.read_campaign()

    def test_read_campaign_with_empty_csv_returns_empty_list(self):
        """Medium: Empty CSV file returns empty list."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            # Write only header, no data rows
            f.write(
                "campaign_name,date,channel,impressions,clicks,conversions,spend,revenue,new_customers,"
                "reach,likes,comments,shares,bounce_rate,frequency,retained_customers,churn_rate,"
                "purchases_per_year,product_profit_margin\n"
            )
            temp_path = f.name

        try:
            reader = Campaign_Reader(temp_path)
            campaigns = reader.read_campaign()
            assert campaigns == []
        finally:
            Path(temp_path).unlink()


class TestCampaignReaderParsing:
    """Tests for CSV parsing and Campaign_Metrics creation."""

    def test_read_campaign_single_row(self):
        """High: Single CSV row parsed correctly."""
        csv_data = (
            "campaign_name,date,channel,impressions,clicks,conversions,spend,revenue,new_customers,"
            "reach,likes,comments,shares,bounce_rate,frequency,retained_customers,churn_rate,"
            "purchases_per_year,product_profit_margin\n"
            "Q1 Campaign,2026-01-15,Facebook,10000,500,50,5000.0,10000.0,40,8000,200,50,25,0.25,1.5,30,0.1,2.5,0.3\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_data)
            temp_path = f.name

        try:
            reader = Campaign_Reader(temp_path)
            campaigns = reader.read_campaign()

            assert len(campaigns) == 1
            campaign = campaigns[0]
            assert campaign.name == "Q1 Campaign"
            assert campaign.date == "2026-01-15"
            assert campaign.channel == "Facebook"
            assert campaign.impressions == 10000
            assert campaign.clicks == 500
            assert campaign.conversions == 50
            assert campaign.spend == 5000.0
            assert campaign.revenue == 10000.0
            assert campaign.new_customers == 40
            assert campaign.reach == 8000
            assert campaign.likes == 200
            assert campaign.comments == 50
            assert campaign.shares == 25
            assert campaign.bounce_rate == 0.25
            assert campaign.frequency == 1.5
            assert campaign.retained_customers == 30
            assert campaign.churn_rate == 0.1
            assert campaign.purchases_per_year == 2.5
            assert campaign.product_profit_margin == 0.3
        finally:
            Path(temp_path).unlink()

    def test_read_campaign_multiple_rows(self):
        """High: Multiple CSV rows parsed correctly."""
        csv_data = (
            "campaign_name,date,channel,impressions,clicks,conversions,spend,revenue,new_customers,"
            "reach,likes,comments,shares,bounce_rate,frequency,retained_customers,churn_rate,"
            "purchases_per_year,product_profit_margin\n"
            "Campaign 1,2026-01-15,Facebook,10000,500,50,5000.0,10000.0,40,8000,200,50,25,0.25,1.5,30,0.1,2.5,0.3\n"
            "Campaign 2,2026-01-20,Email,15000,900,90,8000.0,18000.0,75,12000,400,100,50,0.20,2.0,60,0.05,3.0,0.35\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_data)
            temp_path = f.name

        try:
            reader = Campaign_Reader(temp_path)
            campaigns = reader.read_campaign()

            assert len(campaigns) == 2
            assert campaigns[0].name == "Campaign 1"
            assert campaigns[1].name == "Campaign 2"
            assert campaigns[0].channel == "Facebook"
            assert campaigns[1].channel == "Email"
        finally:
            Path(temp_path).unlink()

    def test_read_campaign_with_zero_metrics(self):
        """Medium: Zero metrics parsed and preserved correctly."""
        csv_data = (
            "campaign_name,date,channel,impressions,clicks,conversions,spend,revenue,new_customers,"
            "reach,likes,comments,shares,bounce_rate,frequency,retained_customers,churn_rate,"
            "purchases_per_year,product_profit_margin\n"
            "Zero Campaign,2026-01-15,Facebook,0,0,0,0.0,0.0,0,0,0,0,0,0.0,0.0,0,0.0,0.0,0.0\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_data)
            temp_path = f.name

        try:
            reader = Campaign_Reader(temp_path)
            campaigns = reader.read_campaign()

            assert len(campaigns) == 1
            campaign = campaigns[0]
            assert campaign.impressions == 0
            assert campaign.clicks == 0
            assert campaign.conversions == 0
            assert campaign.spend == 0.0
            assert campaign.revenue == 0.0
        finally:
            Path(temp_path).unlink()

    def test_read_campaign_with_large_numbers(self):
        """Medium: Large numbers parsed correctly."""
        csv_data = (
            "campaign_name,date,channel,impressions,clicks,conversions,spend,revenue,new_customers,"
            "reach,likes,comments,shares,bounce_rate,frequency,retained_customers,churn_rate,"
            "purchases_per_year,product_profit_margin\n"
            "Large Campaign,2026-01-15,Paid Search,1000000,50000,5000,500000.0,2500000.0,4500,800000,100000,50000,25000,0.25,1.5,3000,0.1,2.5,0.3\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_data)
            temp_path = f.name

        try:
            reader = Campaign_Reader(temp_path)
            campaigns = reader.read_campaign()

            assert len(campaigns) == 1
            campaign = campaigns[0]
            assert campaign.impressions == 1000000
            assert campaign.spend == 500000.0
            assert campaign.revenue == 2500000.0
        finally:
            Path(temp_path).unlink()

    def test_read_campaign_unicode_campaign_names(self):
        """Medium: Unicode in campaign names preserved."""
        csv_data = (
            "campaign_name,date,channel,impressions,clicks,conversions,spend,revenue,new_customers,"
            "reach,likes,comments,shares,bounce_rate,frequency,retained_customers,churn_rate,"
            "purchases_per_year,product_profit_margin\n"
            "Q1 Summer Sale,2026-01-15,Facebook,10000,500,50,5000.0,10000.0,40,8000,200,50,25,0.25,1.5,30,0.1,2.5,0.3\n"
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(csv_data)
            temp_path = f.name

        try:
            reader = Campaign_Reader(temp_path)
            campaigns = reader.read_campaign()

            assert len(campaigns) == 1
            assert campaigns[0].name == "Q1 Summer Sale"
        finally:
            Path(temp_path).unlink()

    def test_read_campaign_different_channels(self):
        """High: Different channels parsed correctly."""
        csv_data = (
            "campaign_name,date,channel,impressions,clicks,conversions,spend,revenue,new_customers,"
            "reach,likes,comments,shares,bounce_rate,frequency,retained_customers,churn_rate,"
            "purchases_per_year,product_profit_margin\n"
            "FB Campaign,2026-01-15,Facebook,10000,500,50,5000.0,10000.0,40,8000,200,50,25,0.25,1.5,30,0.1,2.5,0.3\n"
            "Email Campaign,2026-01-15,Email,5000,250,25,2000.0,5000.0,20,4000,100,25,10,0.30,1.0,15,0.15,2.0,0.25\n"
            "Paid Search,2026-01-15,Paid Search,20000,1000,150,8000.0,16000.0,120,0,0,0,0,0.15,0.0,90,0.05,3.0,0.4\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_data)
            temp_path = f.name

        try:
            reader = Campaign_Reader(temp_path)
            campaigns = reader.read_campaign()

            assert len(campaigns) == 3
            channels = [c.channel for c in campaigns]
            assert "Facebook" in channels
            assert "Email" in channels
            assert "Paid Search" in channels
        finally:
            Path(temp_path).unlink()


class TestCampaignReaderReturnType:
    """Tests for return types and data structure."""

    def test_read_campaign_returns_list(self):
        """High: read_campaign returns a list."""
        csv_data = (
            "campaign_name,date,channel,impressions,clicks,conversions,spend,revenue,new_customers,"
            "reach,likes,comments,shares,bounce_rate,frequency,retained_customers,churn_rate,"
            "purchases_per_year,product_profit_margin\n"
            "Test,2026-01-15,Facebook,10000,500,50,5000.0,10000.0,40,8000,200,50,25,0.25,1.5,30,0.1,2.5,0.3\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_data)
            temp_path = f.name

        try:
            reader = Campaign_Reader(temp_path)
            campaigns = reader.read_campaign()
            assert isinstance(campaigns, list)
        finally:
            Path(temp_path).unlink()

    def test_read_campaign_returns_campaign_metrics_objects(self):
        """High: Each item is a Campaign_Metrics object with expected attributes."""
        csv_data = (
            "campaign_name,date,channel,impressions,clicks,conversions,spend,revenue,new_customers,"
            "reach,likes,comments,shares,bounce_rate,frequency,retained_customers,churn_rate,"
            "purchases_per_year,product_profit_margin\n"
            "Test,2026-01-15,Facebook,10000,500,50,5000.0,10000.0,40,8000,200,50,25,0.25,1.5,30,0.1,2.5,0.3\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_data)
            temp_path = f.name

        try:
            reader = Campaign_Reader(temp_path)
            campaigns = reader.read_campaign()
            campaign = campaigns[0]

            # Check it has all expected attributes
            assert hasattr(campaign, "name")
            assert hasattr(campaign, "date")
            assert hasattr(campaign, "channel")
            assert hasattr(campaign, "impressions")
            assert hasattr(campaign, "clicks")
            assert hasattr(campaign, "revenue")
        finally:
            Path(temp_path).unlink()
