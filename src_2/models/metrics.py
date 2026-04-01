
class Metrics:
    def __init__(
        self,
        campaign_name,total_spend,total_revenue,total_impressions,total_clicks,total_conversions,total_new_customers,
        ctr,conversion_rate,cpa,
        roas,aov,annual_customer_value,marketing_roi,revenue_per_click,ltv_cac_ratio,
        retained_customers,churn_rate,retention_rate,purchases_per_year,
        total_reach,engagement_rate,avg_bounce_rate,avg_frequency,
    ):
        # base
        self.campaign_name = campaign_name
        self.total_spend = total_spend
        self.total_revenue = total_revenue
        self.total_impressions = total_impressions
        self.total_clicks = total_clicks
        self.total_conversions = total_conversions
        self.total_new_customers = total_new_customers
        # acquisition
        self.ctr = ctr
        self.conversion_rate = conversion_rate
        self.cpa = cpa
        # revenue
        self.roas = roas
        self.aov = aov
        self.annual_customer_value = annual_customer_value
        self.marketing_roi = marketing_roi
        self.revenue_per_click = revenue_per_click
        self.ltv_cac_ratio = ltv_cac_ratio
        # retention
        self.retained_customers = retained_customers
        self.churn_rate = churn_rate
        self.retention_rate = retention_rate
        self.purchases_per_year = purchases_per_year
        # satisfaction
        self.total_reach = total_reach
        self.engagement_rate = engagement_rate
        self.avg_bounce_rate = avg_bounce_rate
        self.avg_frequency = avg_frequency
