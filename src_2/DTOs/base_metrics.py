
class Base_Metrics:
    def __init__(
        self,
        total_spend: float,
        total_revenue: float,
        total_impressions: int,
        total_clicks: int,
        total_conversions: int,
        total_new_customers: int
    ):
        self.total_spend = total_spend
        self.total_revenue = total_revenue
        self.total_impressions = total_impressions
        self.total_clicks = total_clicks
        self.total_conversions = total_conversions
        self.total_new_customers = total_new_customers
        
