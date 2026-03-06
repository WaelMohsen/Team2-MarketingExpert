import pandas as pd

def load_data(filepath="data/campaign_data.csv"):
    try:
        df = pd.read_csv(filepath)
        return df
    except FileNotFoundError:
        return None

## Calculating KPIs

class MetricsKPI:
    """Calculates individual marketing KPI metrics."""

    @staticmethod
    def ctr(impressions, clicks):
        return round(clicks / impressions * 100, 2) if impressions > 0 else 0

    @staticmethod
    def cvr(clicks, conversions):
        return round(conversions / clicks * 100, 2) if clicks > 0 else 0

    @staticmethod
    def cpc(ad_spend, clicks):
        return round(ad_spend / clicks, 2) if clicks > 0 else 0

    @staticmethod
    def cpa(ad_spend, conversions):
        return round(ad_spend / conversions, 2) if conversions > 0 else 0

    @staticmethod
    def aov(revenue, conversions):
        return round(revenue / conversions, 2) if conversions > 0 else 0

    @staticmethod
    def roas(revenue, ad_spend):
        return round(revenue / ad_spend, 2) if ad_spend > 0 else 0

    @staticmethod
    def retention_rate(retained_customers, total_customers):
        return round(retained_customers / total_customers * 100, 2) if total_customers > 0 else 0

    @staticmethod
    def churn_rate(churned_customers, total_customers):
        return round(churned_customers / total_customers * 100, 2) if total_customers > 0 else 0


class RevenueGrowth:
    """Target: grow revenue using spend efficiency metrics."""

    def __init__(self, df):
        self.df = df

    def calculate(self):
        spend = self.df["spend"].sum()
        revenue = self.df["revenue"].sum()
        clicks = self.df["clicks"].sum()
        conversions = self.df["conversions"].sum()
        impressions = self.df["impressions"].sum()

        return {
            "CTR": MetricsKPI.ctr(impressions, clicks),
            "CVR": MetricsKPI.cvr(clicks, conversions),
            "ROAS": MetricsKPI.roas(revenue, spend),
            "AOV": MetricsKPI.aov(revenue, conversions),
            "CPA": MetricsKPI.cpa(spend, conversions),
        }


class CustomerAcquisition:
    """Target: acquire new customers cost-effectively."""

    def __init__(self, df):
        self.df = df

    def calculate(self):
        spend = self.df["spend"].sum()
        clicks = self.df["clicks"].sum()
        conversions = self.df["conversions"].sum()
        impressions = self.df["impressions"].sum()

        return {
            "CTR": MetricsKPI.ctr(impressions, clicks),
            "CVR": MetricsKPI.cvr(clicks, conversions),
            "CPC": MetricsKPI.cpc(spend, clicks),
            "CPA": MetricsKPI.cpa(spend, conversions),
        }


class CustomerSatisfaction:
    """Target: measure ad and content relevance/engagement."""

    def __init__(self, df):
        self.df = df

    def calculate(self):
        impressions = self.df["impressions"].sum()
        clicks = self.df["clicks"].sum()
        conversions = self.df["conversions"].sum()
        reach = self.df["reach"].sum() if "reach" in self.df else 0
        engagements = (
            self.df["likes"].sum() +
            self.df["comments"].sum() +
            self.df["shares"].sum()
        ) if all(c in self.df for c in ["likes", "comments", "shares"]) else 0

        engagement_rate = round(engagements / reach * 100, 2) if reach > 0 else 0
        bounce_rate = round(float(self.df["bounce_rate"].mean()), 2) if "bounce_rate" in self.df else 0

        return {
            "CTR": MetricsKPI.ctr(impressions, clicks),
            "CVR": MetricsKPI.cvr(clicks, conversions),
            "Engagement Rate": engagement_rate,
            "Bounce Rate": bounce_rate,
        }


class CustomerRetention:
    """Target: keep existing customers coming back."""

    def __init__(self, df):
        self.df = df

    def calculate(self):
        revenue = self.df["revenue"].sum()
        conversions = self.df["conversions"].sum()
        spend = self.df["spend"].sum()

        retained = int(self.df["retained_customers"].sum()) if "retained_customers" in self.df else 0
        new_customers = int(self.df["new_customers"].sum()) if "new_customers" in self.df else 0
        total_customers = retained + new_customers

        churn = float(self.df["churn_rate"].mean()) if "churn_rate" in self.df else 0
        purchases_per_year = float(self.df["purchases_per_year"].iloc[0]) if "purchases_per_year" in self.df else 0

        aov = MetricsKPI.aov(revenue, conversions)

        return {
            "Retention Rate": MetricsKPI.retention_rate(retained, total_customers),
            "Churn Rate": churn,
            "AOV": aov,
            "CPA": MetricsKPI.cpa(spend, conversions),
            "Estimated Annual Value": round(aov * purchases_per_year, 2),
        }
