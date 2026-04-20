class Revenue_Metrics:
    def __init__(
        self,
        roas: float,
        aov: float,
        annual_customer_value: float,
        marketing_roi: float,
        revenue_per_click: float,
        ltv_cac_ratio: float,
    ):
        self.roas = roas
        self.aov = aov
        self.annual_customer_value = annual_customer_value
        self.marketing_roi = marketing_roi
        self.revenue_per_click = revenue_per_click
        self.ltv_cac_ratio = ltv_cac_ratio

    def convert_to_dictionary(self):
        return {
            "roas": self.roas,
            "aov": self.aov,
            "annual_customer_value": self.annual_customer_value,
            "marketing_roi": self.marketing_roi,
            "revenue_per_click": self.revenue_per_click,
            "ltv_cac_ratio": self.ltv_cac_ratio,
        }
