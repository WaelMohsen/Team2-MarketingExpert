class Satisfaction_Metrics:
    def __init__(self,total_reach:float,engagement_rate:float,avg_bounce_rate:float,avg_frequency:float):
        self.total_reach = total_reach
        self.engagement_rate = engagement_rate
        self.avg_bounce_rate = avg_bounce_rate
        self.avg_frequency = avg_frequency

    def convert_to_dictionary(self):
        return {
            "total_reach": self.total_reach,
            "engagement_rate": self.engagement_rate,
            "avg_bounce_rate": self.avg_bounce_rate,
            "avg_frequency": self.avg_frequency,
        }
