from .registry import register_target


@register_target("Revenue Growth")
def calculate(df, metrics):

    revenue = metrics["Total Revenue"]
    conversions = metrics["Total Conversions"]

    aov = revenue / conversions if conversions else 0

    purchases_per_year = (
        float(df["purchases_per_year"].iloc[0])
        if "purchases_per_year" in df else 0
    )

    annual_customer_value = aov * purchases_per_year

    metrics["AOV"] = round(aov, 2)
    metrics["Annual Customer Value"] = round(annual_customer_value, 2)

    if metrics["CPA"]:
        metrics["LTV:CAC Ratio"] = round(annual_customer_value / metrics["CPA"], 2)

    return metrics