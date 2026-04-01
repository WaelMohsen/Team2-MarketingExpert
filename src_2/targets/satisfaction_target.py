from targets.base_target import BaseTarget


class SatisfactionTarget(BaseTarget):
    def select(self, metrics):
        return {
            "engagement_rate": metrics.engagement_rate,
            "avg_bounce_rate": metrics.avg_bounce_rate,
            "avg_frequency": metrics.avg_frequency,
        }
