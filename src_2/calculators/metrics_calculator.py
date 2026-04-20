from __future__ import annotations

from DTOs.acquistion_metrics import Acquisition_Metrics
from DTOs.base_metrics import Base_Metrics
from DTOs.retention_metrics import Retention_Metrics
from DTOs.revenue_metrics import Revenue_Metrics
from DTOs.satisfaction_metrics import Satisfaction_Metrics


class MetricsCalculator:

    def validate_campaigns(self, campaigns):
        if not campaigns or not isinstance(campaigns, list):
            raise ValueError("campaigns must be a non-empty list")

    def run(self, campaigns, target: str) -> tuple:
        try:
            self.validate_campaigns(campaigns)
            base = Base_Metrics(*self.calculate_base_metrics(campaigns))

            builders = {
                "acquisition": lambda: Acquisition_Metrics(
                    *self.calculate_acquisition_metrics(campaigns)
                ),
                "revenue": lambda: Revenue_Metrics(
                    *self.calculate_revenue_metrics(campaigns)
                ),
                "retention": lambda: Retention_Metrics(
                    *self.calculate_retention_metrics(campaigns)
                ),
                "satisfaction": lambda: Satisfaction_Metrics(
                    *self.calculate_satisfaction_metrics(campaigns)
                ),
            }

            if target not in builders:
                raise ValueError(
                    f"Unknown target '{target}'. Choose from: {list(builders)}"
                )

            return base, builders[target]()
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"Failed to run metrics for target '{target}': {e}"
            ) from e

    def calculate_base_metrics(
        self, campaigns
    ) -> tuple[float, float, int, int, int, int]:
        try:
            self.validate_campaigns(campaigns)
            total_spend = sum(c.spend for c in campaigns)
            total_revenue = sum(c.revenue for c in campaigns)
            total_impressions = sum(c.impressions for c in campaigns)
            total_clicks = sum(c.clicks for c in campaigns)
            total_conversions = sum(c.conversions for c in campaigns)
            total_new_customers = sum(c.new_customers for c in campaigns)
            return (
                total_spend,
                total_revenue,
                total_impressions,
                total_clicks,
                total_conversions,
                total_new_customers,
            )
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to calculate base metrics: {e}") from e

    def calculate_acquisition_metrics(self, campaigns) -> tuple[float, float, float, int]:
        try:
            self.validate_campaigns(campaigns)
            total_spend, _, total_impressions, total_clicks, total_conversions, total_new_customers = self.calculate_base_metrics(campaigns)
            ctr = round((total_clicks / total_impressions) * 100, 2) if total_impressions else 0
            conversion_rate = round((total_conversions / total_clicks) * 100, 2) if total_clicks else 0
            cpa = round(total_spend / total_new_customers, 2) if total_new_customers else 0
            return ctr, conversion_rate, cpa, total_new_customers
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to calculate acquisition metrics: {e}") from e

    def calculate_revenue_metrics(
        self, campaigns
    ) -> tuple[float, float, float, float, float, float]:
        try:
            self.validate_campaigns(campaigns)
            total_spend, total_revenue, _, total_clicks, total_conversions, _ = self.calculate_base_metrics(campaigns)
            _, _, cpa, _ = self.calculate_acquisition_metrics(campaigns)
            roas = round(total_revenue / total_spend, 2) if total_spend else 0
            aov = (
                round(total_revenue / total_conversions, 2) if total_conversions else 0
            )
            purchases_per_year = sum(c.purchases_per_year for c in campaigns) / len(
                campaigns
            )
            annual_customer_value = round(aov * purchases_per_year, 2)
            marketing_roi = (
                round(((total_revenue - total_spend) / total_spend) * 100, 2)
                if total_spend
                else 0
            )
            revenue_per_click = (
                round(total_revenue / total_clicks, 2) if total_clicks else 0
            )
            ltv_cac_ratio = round(annual_customer_value / cpa, 2) if cpa else 0
            return (
                roas,
                aov,
                annual_customer_value,
                marketing_roi,
                revenue_per_click,
                ltv_cac_ratio,
            )
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to calculate revenue metrics: {e}") from e

    def calculate_retention_metrics(self, campaigns) -> tuple[int, float, float]:
        try:
            self.validate_campaigns(campaigns)
            retained_customers = sum(c.retained_customers for c in campaigns)
            churn_rate = (
                sum(c.churn_rate for c in campaigns) / len(campaigns)
                if campaigns
                else 0
            )
            churn_percent = churn_rate * 100 if churn_rate <= 1 else churn_rate
            retention_rate = round(100 - churn_percent, 2)
            churn_rate_percentage = round(churn_percent, 2)
            return retained_customers, churn_rate_percentage, retention_rate
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to calculate retention metrics: {e}") from e

    def calculate_satisfaction_metrics(
        self, campaigns
    ) -> tuple[float, float, float, float]:
        try:
            self.validate_campaigns(campaigns)
            total_reach = sum(c.reach for c in campaigns)
            total_engagements = sum(c.likes + c.comments + c.shares for c in campaigns)
            engagement_rate = (
                round((total_engagements / total_reach) * 100, 2) if total_reach else 0
            )
            avg_bounce_rate = (
                round(sum(c.bounce_rate for c in campaigns) / len(campaigns), 2)
                if campaigns
                else 0
            )
            avg_frequency = (
                round(sum(c.frequency for c in campaigns) / len(campaigns), 2)
                if campaigns
                else 0
            )
            return total_reach, engagement_rate, avg_bounce_rate, avg_frequency
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to calculate satisfaction metrics: {e}") from e
