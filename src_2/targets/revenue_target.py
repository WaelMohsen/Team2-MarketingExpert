from targets.base_target import BaseTarget


class RevenueTarget(BaseTarget):
    def select_target(self, metrics):
        return {
            "roas": metrics.roas,
            "aov": metrics.aov,
            "annual_customer_value": metrics.annual_customer_value,
            "marketing_roi": metrics.marketing_roi,
            "revenue_per_click": metrics.revenue_per_click,
            "ltv_cac_ratio": metrics.ltv_cac_ratio,
        }
