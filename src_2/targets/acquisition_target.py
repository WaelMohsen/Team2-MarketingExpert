from targets.base_target import BaseTarget


class AcquisitionTarget(BaseTarget):
    def select(self, metrics):
        return {
            "ctr": metrics.ctr,
            "cpa": metrics.cpa,
            "conversion_rate": metrics.conversion_rate,
            "total_new_customers": metrics.total_new_customers,
        }
