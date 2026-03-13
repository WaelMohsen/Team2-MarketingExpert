from .registry import register_target


@register_target("Customer Retention")
def calculate(df, metrics):

    retained_customers = (
        int(df["retained_customers"].sum())
        if "retained_customers" in df else 0
    )

    churn_rate = (
        float(df["churn_rate"].mean())
        if "churn_rate" in df else None
    )

    if churn_rate is not None:
        churn_percent = churn_rate * 100 if churn_rate <= 1 else churn_rate
        retention_rate = 100 - churn_percent
    else:
        churn_percent = None
        retention_rate = None

    metrics["Retained Customers"] = retained_customers
    metrics["Churn Rate"] = round(churn_percent, 2) if churn_percent else None
    metrics["Retention Rate"] = round(retention_rate, 2) if retention_rate else None

    return metrics