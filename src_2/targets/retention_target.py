from targets.base_target import BaseTarget


class RetentionTarget(BaseTarget):
    def select(self, metrics):
        return {
            "retained_customers": metrics.retained_customers,
            "churn_rate": metrics.churn_rate,
            "retention_rate": metrics.retention_rate,
            "purchases_per_year": metrics.purchases_per_year,
        }
