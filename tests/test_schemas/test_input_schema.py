import math

import pandas as pd
import pytest

from src.schemas.input_schema import CampaignInput, validate_campaign_data


def _campaign_record(overrides=None):
    """Helper to create sample campaign input record."""
    record = {
        "campaign_name": "Q1 Social Ads",
        "date": "2026-01-15",
        "channel": "Facebook",
        "impressions": 10000,
        "clicks": 500,
        "conversions": 25,
        "spend": 2500.50,
        "revenue": 5000.00,
        "new_customers": 20,
        "reach": 8000,
        "likes": 150,
        "comments": 30,
        "shares": 10,
        "bounce_rate": 0.35,
        "frequency": 2.5,
        "retained_customers": 18,
        "churn_rate": 0.10,
        "purchases_per_year": 3.5,
        "product_profit_margin": 0.40,
    }
    if overrides:
        record.update(overrides)
    return record


class TestCampaignInputSchemaValidation:
    """Test suite for campaign input schema validation."""

    def test_campaign_valid_complete_record_passes_validation(self):
        """High: Complete valid campaign record passes validation."""
        record = _campaign_record()
        campaign = CampaignInput(**record)

        assert campaign.campaign_name == "Q1 Social Ads"
        assert campaign.channel == "Facebook"
        assert campaign.impressions == 10000
        assert campaign.clicks == 500
        assert campaign.conversions == 25

    def test_campaign_required_fields_only_passes_validation(self):
        """High: Record with only required fields (no optional) passes validation."""
        record = {
            "campaign_name": "Minimal Campaign",
            "date": "2026-02-01",
            "channel": "Email",
            "impressions": 5000,
            "clicks": 250,
            "conversions": 10,
            "spend": 1000.00,
            "revenue": 2500.00,
        }
        campaign = CampaignInput(**record)

        assert campaign.campaign_name == "Minimal Campaign"
        assert campaign.new_customers is None
        assert campaign.bounce_rate is None

    def test_campaign_missing_required_field_raises_value_error(self):
        """Low: Missing required field (campaign_name) raises ValueError."""
        record = _campaign_record()
        del record["campaign_name"]

        with pytest.raises(ValueError):
            CampaignInput(**record)

    def test_campaign_invalid_metric_type_raises_value_error(self):
        """Low: Invalid metric type (string for impressions) raises ValueError."""
        record = _campaign_record({"impressions": "ten thousand"})

        with pytest.raises(ValueError):
            CampaignInput(**record)

    def test_campaign_negative_spend_accepted(self):
        """Medium: Negative spend is accepted by schema (no validation enforced)."""
        record = _campaign_record({"spend": -500.00})
        campaign = CampaignInput(**record)

        assert campaign.spend == -500.00

    def test_campaign_float_for_integer_field_coerced(self):
        """Medium: Float value for integer field (impressions) coerced to int."""
        record = _campaign_record({"impressions": 5000.0})
        campaign = CampaignInput(**record)

        assert campaign.impressions == 5000
        assert isinstance(campaign.impressions, int)

    def test_campaign_optional_field_nan_converted_to_none(self):
        """High: NaN value in optional field converted to None."""
        record = _campaign_record({"bounce_rate": math.nan})

        # Simulate dataframe processing
        cleaned = {
            k: (None if isinstance(v, float) and math.isnan(v) else v)
            for k, v in record.items()
        }
        campaign = CampaignInput(**cleaned)

        assert campaign.bounce_rate is None

    def test_campaign_all_optional_fields_set(self):
        """High: All optional fields properly set and accessible."""
        record = _campaign_record()
        campaign = CampaignInput(**record)

        assert campaign.new_customers == 20
        assert campaign.reach == 8000
        assert campaign.retained_customers == 18
        assert campaign.purchases_per_year == 3.5

    def test_campaign_zero_values_valid(self):
        """Medium: Zero values for metrics (conversions, clicks) valid."""
        record = _campaign_record(
            {
                "clicks": 0,
                "conversions": 0,
                "revenue": 0.0,
            }
        )
        campaign = CampaignInput(**record)

        assert campaign.clicks == 0
        assert campaign.conversions == 0
        assert campaign.revenue == 0.0

    def test_campaign_high_precision_float_preserved(self):
        """High: High-precision floats (spend, margins) preserved correctly."""
        record = _campaign_record(
            {
                "spend": 2500.123456,
                "product_profit_margin": 0.3456789,
            }
        )
        campaign = CampaignInput(**record)

        assert campaign.spend == 2500.123456
        assert campaign.product_profit_margin == 0.3456789

    def test_campaign_non_english_name_raises_value_error(self):
        """High: Non-English characters in campaign_name raise ValueError."""
        from pydantic_core import ValidationError

        record = _campaign_record({"campaign_name": "Q1 Café Campaign 中文"})

        with pytest.raises(ValidationError, match="English"):
            CampaignInput(**record)

    def test_campaign_english_name_accepted(self):
        """High: English-only campaign_name passes validation."""
        record = _campaign_record({"campaign_name": "Q1 Summer Sale!"})
        campaign = CampaignInput(**record)

        assert campaign.campaign_name == "Q1 Summer Sale!"

    def test_campaign_date_format_preserved(self):
        """Medium: Date string preserved as-is (no validation enforced)."""
        record = _campaign_record({"date": "2026-Q1"})
        campaign = CampaignInput(**record)

        assert campaign.date == "2026-Q1"

    def test_validate_campaign_data_dataframe_single_row(self):
        """High: Single row dataframe validates correctly."""
        df = pd.DataFrame([_campaign_record()])
        validated = validate_campaign_data(df)

        assert len(validated) == 1
        assert validated[0].campaign_name == "Q1 Social Ads"

    def test_validate_campaign_data_dataframe_multiple_rows(self):
        """High: Multiple rows dataframe validates all records correctly."""
        records = [
            _campaign_record(
                {"campaign_name": f"Campaign {i}", "impressions": 1000 * (i + 1)}
            )
            for i in range(5)
        ]
        df = pd.DataFrame(records)
        validated = validate_campaign_data(df)

        assert len(validated) == 5
        assert validated[0].campaign_name == "Campaign 0"
        assert validated[4].impressions == 5000

    def test_validate_campaign_data_with_nan_values(self):
        """High: NaN values in optional fields converted to None."""
        record = _campaign_record(
            {"bounce_rate": math.nan, "retained_customers": math.nan}
        )
        df = pd.DataFrame([record])
        validated = validate_campaign_data(df)

        assert validated[0].bounce_rate is None
        assert validated[0].retained_customers is None

    def test_validate_campaign_data_mixed_nan_and_values(self):
        """High: Mix of NaN and valid values in optional fields handled correctly."""
        records = [
            _campaign_record({"bounce_rate": 0.25}),
            _campaign_record({"bounce_rate": math.nan}),
            _campaign_record({"bounce_rate": 0.45}),
        ]
        df = pd.DataFrame(records)
        validated = validate_campaign_data(df)

        assert validated[0].bounce_rate == 0.25
        assert validated[1].bounce_rate is None
        assert validated[2].bounce_rate == 0.45

    def test_campaign_to_dict_preserves_all_fields(self):
        """High: Converting model to dict preserves all fields."""
        record = _campaign_record()
        campaign = CampaignInput(**record)
        campaign_dict = campaign.model_dump()

        assert "campaign_name" in campaign_dict
        assert "impressions" in campaign_dict
        assert "bounce_rate" in campaign_dict
        assert campaign_dict["campaign_name"] == "Q1 Social Ads"

    def test_campaign_extra_fields_ignored(self):
        """Medium: Extra fields in record are ignored."""
        record = _campaign_record()
        record["extra_field"] = "should be ignored"

        campaign = CampaignInput(**record)
        assert not hasattr(campaign, "extra_field")

    def test_campaign_fractional_metric_values(self):
        """Medium: Fractional values for rate fields (bounce_rate, churn_rate) accepted."""
        record = _campaign_record(
            {
                "bounce_rate": 0.3456,
                "churn_rate": 0.0789,
                "frequency": 1.23,
            }
        )
        campaign = CampaignInput(**record)

        assert campaign.bounce_rate == 0.3456
        assert campaign.churn_rate == 0.0789
        assert campaign.frequency == 1.23
