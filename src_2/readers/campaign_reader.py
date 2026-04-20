import pandas as pd
from DTOs.campaign_metrics import Campaign_Metrics


class Campaign_Reader:
    def __init__(self, file_path):
        self.file_path = file_path

    def read_campaign(self):
        campaign_df = pd.read_csv(self.file_path)
        numeric_columns = [
            "impressions", "clicks", "conversions", "spend", "revenue", "new_customers",
            "reach", "likes", "comments", "shares",
            "bounce_rate", "frequency",
            "retained_customers", "churn_rate", "purchases_per_year", "product_profit_margin",
        ]
        campaign_df[numeric_columns] = (
            campaign_df[numeric_columns].apply(pd.to_numeric, errors="coerce").fillna(0)
        )
        return [
            Campaign_Metrics(
                name=row["campaign_name"],
                date=row["date"],
                channel=row["channel"],
                impressions=row["impressions"],
                clicks=row["clicks"],
                conversions=row["conversions"],
                spend=row["spend"],
                revenue=row["revenue"],
                new_customers=row["new_customers"],
                reach=row["reach"],
                likes=row["likes"],
                comments=row["comments"],
                shares=row["shares"],
                bounce_rate=row["bounce_rate"],
                frequency=row["frequency"],
                retained_customers=row["retained_customers"],
                churn_rate=row["churn_rate"],
                purchases_per_year=row["purchases_per_year"],
                product_profit_margin=row["product_profit_margin"],
            )
            for _, row in campaign_df.iterrows()
        ]
