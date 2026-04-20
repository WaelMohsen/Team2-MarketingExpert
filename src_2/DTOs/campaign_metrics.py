class Campaign_Metrics:
    def __init__(
        self,
        name: str,
        date: str,
        channel: str,
        impressions: int,
        clicks: int,
        conversions: int,
        spend: float,
        revenue: float,
        new_customers: int,
        reach: int,
        likes: int,
        comments: int,
        shares: int,
        bounce_rate: float,
        frequency: float,
        retained_customers: float,
        churn_rate: float,
        purchases_per_year: float,
        product_profit_margin: float,
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
