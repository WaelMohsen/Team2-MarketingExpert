from .registry import register_target


@register_target("Customer Acquisition")
def calculate(df, metrics):

    impressions = metrics["Total Impressions"]
    clicks = metrics["Total Clicks"]
    conversions = metrics["Total Conversions"]

    metrics["CTR"] = round((clicks / impressions) * 100, 2) if impressions else 0
    metrics["Conversion Rate"] = round((conversions / clicks) * 100, 2) if clicks else 0

    return metrics