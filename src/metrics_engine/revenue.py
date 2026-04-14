from .registry import register_target


@register_target("Revenue Growth")
def calculate(df, metrics):

    aov = (
        metrics["Total Revenue"] / metrics["Total Conversions"]
        if metrics["Total Conversions"]
        else 0
    )

    purchases_per_year = (
        float(df["purchases_per_year"].iloc[0]) if "purchases_per_year" in df else 0
    )

    annual_customer_value = aov * purchases_per_year

    metrics["AOV"] = round(aov, 2)
    metrics["Annual Customer Value"] = round(annual_customer_value, 2)
    ##added new metrices
    metrics["Marketing ROI"] = (
        round(
            (
                (metrics["Total Revenue"] - metrics["Total Spend"])
                / metrics["Total Spend"]
            )
            * 100,
            2,
        )
        if metrics["Total Spend"]
        else 0
    )
    metrics["Revenue Per Click"] = (
        round(metrics["Total Revenue"] / metrics["Total Clicks"], 2)
        if metrics["Total Clicks"]
        else 0
    )
    if metrics["CPA"]:
        metrics["LTV:CAC Ratio"] = round(annual_customer_value / metrics["CPA"], 2)

    return metrics
