class Retention_Metrics:
    def __init__(self,retained_customers: float, churn_rate: float, retention_rate: float, purchases_per_year: float):
        self.retained_customers = retained_customers
        self.churn_rate = churn_rate
        self.retention_rate = retention_rate
        self.purchases_per_year = purchases_per_year
