class Campaign:
    def __init__(self,campaign_name,date,channel,impressions,clicks,conversions,spend,revenue,new_customers,
                 reach,likes,comments,shares,bounce_rate,frequency,retained_customers,churn_rate,
                 purchases_per_year,product_profit_margin):
        self.campaign_name = campaign_name
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