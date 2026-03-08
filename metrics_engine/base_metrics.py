def calculate_base_metrics(df):

    if df is None or df.empty:
        return None

    total_spend = float(df['spend'].sum()) if 'spend' in df else 0.0
    total_revenue = float(df['revenue'].sum()) if 'revenue' in df else 0.0
    total_impressions = int(df['impressions'].sum()) if 'impressions' in df else 0
    total_clicks = int(df['clicks'].sum()) if 'clicks' in df else 0
    total_conversions = int(df['conversions'].sum()) if 'conversions' in df else 0

    new_customers_col = 'new_customers' if 'new_customers' in df else 'conversions'
    total_new_customers = int(df[new_customers_col].sum()) if new_customers_col in df else 0
    # --- Click Through Rate ---
    ctr = (
        (total_clicks / total_impressions) * 100
        if total_impressions > 0 else 0
    )

    metrics = {}

    metrics["Total Spend"] = total_spend
    metrics["Total Revenue"] = total_revenue
    metrics["Total Impressions"] = total_impressions
    metrics["Total Clicks"] = total_clicks
    metrics["Total Conversions"] = total_conversions
    metrics["Total New Customers"] = total_new_customers

    metrics['CTR'] = f"{round(ctr, 2)}%"
    metrics["CPA"] = round(total_spend / total_new_customers, 2) if total_new_customers else 0
    metrics["ROAS"] = round(total_revenue / total_spend, 2) if total_spend else 0

    return metrics