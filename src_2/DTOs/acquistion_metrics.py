class Acquisition_Metrics:
    def __init__(self, ctr: float, conversion_rate: float, cpa: float, total_new_customers: int):
        self.ctr = ctr
        self.conversion_rate = conversion_rate
        self.cpa = cpa
        self.total_new_customers = total_new_customers

    def convert_to_dictionary(self):
        return {
            "ctr": self.ctr,
            "conversion_rate": self.conversion_rate,
            "cpa": self.cpa,
            "total_new_customers": self.total_new_customers,
        }
