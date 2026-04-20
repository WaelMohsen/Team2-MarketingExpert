class Retention_Metrics:
    def __init__(self,retained_customers: float, churn_rate: float, retention_rate: float):
        self.retained_customers = retained_customers
        self.churn_rate = churn_rate
        self.retention_rate = retention_rate

    def convert_to_dictionary(self):
        return {
            "retained_customers": self.retained_customers,
            "churn_rate": self.churn_rate,
            "retention_rate": self.retention_rate,
        }
