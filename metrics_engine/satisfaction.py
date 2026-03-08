from .registry import register_target


@register_target("Customer Satisfaction")
def calculate(df, metrics):

    total_reach = df["reach"].sum() if "reach" in df else 0

    total_engagements = (
        df["likes"].sum() +
        df["comments"].sum() +
        df["shares"].sum()
    )

    engagement_rate = (total_engagements / total_reach) * 100 if total_reach else 0

    metrics["Engagement Rate"] = round(engagement_rate, 2)

    metrics["Average Bounce Rate"] = (
        round(float(df["bounce_rate"].mean()), 2)
        if "bounce_rate" in df else None
    )

    metrics["Average Frequency"] = (
        round(float(df["frequency"].mean()), 2)
        if "frequency" in df else None
    )

    return metrics