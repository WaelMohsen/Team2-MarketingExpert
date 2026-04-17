"""Shared test fixtures and mock data for src_2 test suite.

This module provides pytest fixtures for testing Campaign_Reader, DTOs,
and MetricsCalculator with realistic campaign data scenarios.
"""

import sys
from pathlib import Path

import pytest

# Add src_2 to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src_2"))


class MockCampaignMetrics:
    """Mock campaign metrics object for testing.

    Mimics Campaign_Metrics DTO with 19 campaign performance fields.
    Allows flexible creation of test scenarios with overridable parameters.
    """

    def __init__(
        self,
        name="Test Campaign",
        date="2026-01-01",
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
    ):
        self.name = name
        self.date = date
        self.channel = channel
        self.impressions = impressions
        self.clicks = clicks
        self.conversions = conversions
        self.spend = spend
        self.revenue = revenue
        self.new_customers = new_customers
        self.reach = reach
        self.likes = likes
        self.comments = comments
        self.shares = shares
        self.bounce_rate = bounce_rate
        self.frequency = frequency
        self.retained_customers = retained_customers
        self.churn_rate = churn_rate
        self.purchases_per_year = purchases_per_year
        self.product_profit_margin = product_profit_margin


@pytest.fixture
def single_campaign():
    """Single campaign fixture with default metrics."""
    return MockCampaignMetrics()


@pytest.fixture
def multiple_campaigns():
    """Multiple campaign fixtures with varying performance metrics."""
    return [
        MockCampaignMetrics(
            name="Campaign 1",
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
            retained_customers=30,
            churn_rate=0.1,
        ),
        MockCampaignMetrics(
            name="Campaign 2",
            impressions=15000,
            clicks=900,
            conversions=90,
            spend=8000.0,
            revenue=18000.0,
            new_customers=75,
            reach=12000,
            likes=400,
            comments=100,
            shares=50,
            retained_customers=60,
            churn_rate=0.05,
        ),
    ]


@pytest.fixture
def zero_metrics_campaign():
    """Campaign fixture with all zero metrics for edge case testing."""
    return MockCampaignMetrics(
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
        retained_customers=0,
        churn_rate=0.0,
    )
