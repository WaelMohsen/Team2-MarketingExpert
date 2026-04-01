# calculators/metrics_calculator.py
from models.metrics import Metrics


class MetricsCalculator:
    def calculate(self, campaigns):
        n = len(campaigns)

        # --- base ---
        campaign_name = campaigns[0].campaign_name if campaigns else "Unknown"
        total_spend = sum(c.spend for c in campaigns)
        total_revenue = sum(c.revenue for c in campaigns)
        total_impressions = sum(c.impressions for c in campaigns)
        total_clicks = sum(c.clicks for c in campaigns)
        total_conversions = sum(c.conversions for c in campaigns)
        total_new_customers = sum(c.new_customers for c in campaigns)

        # --- acquisition ---
        ctr = (
            round((total_clicks / total_impressions) * 100, 2)
            if total_impressions
            else 0
        )
        conversion_rate = (
            round((total_conversions / total_clicks) * 100, 2) if total_clicks else 0
        )
        cpa = round(total_spend / total_new_customers, 2) if total_new_customers else 0

        # --- revenue ---
        roas = round(total_revenue / total_spend, 2) if total_spend else 0
        aov = round(total_revenue / total_conversions, 2) if total_conversions else 0
        purchases_per_year = sum(c.purchases_per_year for c in campaigns) / n
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

        # --- retention ---
        retained_customers = sum(c.retained_customers for c in campaigns)
        churn_rate = sum(c.churn_rate for c in campaigns) / n
        churn_percent = churn_rate * 100 if churn_rate <= 1 else churn_rate
        retention_rate = round(100 - churn_percent, 2)
        churn_rate = round(churn_percent, 2)

        # --- satisfaction ---
        total_reach = sum(c.reach for c in campaigns)
        total_engagements = sum(c.likes + c.comments + c.shares for c in campaigns)
        engagement_rate = (
            round((total_engagements / total_reach) * 100, 2) if total_reach else 0
        )
        avg_bounce_rate = round(sum(c.bounce_rate for c in campaigns) / n, 2)
        avg_frequency = round(sum(c.frequency for c in campaigns) / n, 2)

        return Metrics(
            # base
            campaign_name=campaign_name,
            total_spend=round(total_spend, 2),
            total_revenue=round(total_revenue, 2),
            total_impressions=total_impressions,
            total_clicks=total_clicks,
            total_conversions=total_conversions,
            total_new_customers=total_new_customers,
            # acquisition
            ctr=ctr,
            conversion_rate=conversion_rate,
            cpa=cpa,
            # revenue
            roas=roas,
            aov=aov,
            annual_customer_value=annual_customer_value,
            marketing_roi=marketing_roi,
            revenue_per_click=revenue_per_click,
            ltv_cac_ratio=ltv_cac_ratio,
            # retention
            retained_customers=retained_customers,
            churn_rate=churn_rate,
            retention_rate=retention_rate,
            purchases_per_year=round(purchases_per_year, 2),
            # satisfaction
            total_reach=total_reach,
            engagement_rate=engagement_rate,
            avg_bounce_rate=avg_bounce_rate,
            avg_frequency=avg_frequency,
        )
