import pandas as pd

def load_data(filepath="data/campaign_data.csv"):
    try:
        df = pd.read_csv(filepath)
        return df
    except FileNotFoundError:
        return None

def get_metrics_for_category(category_name, df):
    """
    Calculates metrics specific to the prompt category.
    Categories:
    1. Customer Acquisition
    2. Customer Satisfaction (Ad & Content Relevance)
    3. Revenue Growth
    4. Customer Retention
    """
    if df is None or df.empty:
        return {"error": "No data available"}

    metrics = {}
    
    # Calculate overall totals/averages first
    # Convert numpy types to native Python types for JSON serialization
    # Since we now have a single row, sum() works (it just sums the single value)
    # but we should handle potential missing columns gracefully if needed.
    
    # Extract values safely
    total_spend = float(df['spend'].sum()) if 'spend' in df else 0.0
    total_revenue = float(df['revenue'].sum()) if 'revenue' in df else 0.0
    total_impressions = int(df['impressions'].sum()) if 'impressions' in df else 0
    total_clicks = int(df['clicks'].sum()) if 'clicks' in df else 0
    total_conversions = int(df['conversions'].sum()) if 'conversions' in df else 0
    
    # 'new_customers' might not exist in the new CSV format if we removed it, 
    # but let's check. If not, use conversions as proxy for new customers?
    # The prompts use Cost per Customer (CPA).
    # If new_customers column is missing, we use conversions.
    new_customers_col = 'new_customers' if 'new_customers' in df else 'conversions'
    total_new_customers = int(df[new_customers_col].sum()) if new_customers_col in df else 0

    campaign_name = df['campaign_name'].iloc[0] if 'campaign_name' in df and not df.empty else "Unknown Campaign"

    # Common base metrics for the LLM prompt
    metrics['Campaign Name'] = campaign_name
    metrics['Total Spend'] = total_spend
    metrics['Total Revenue'] = total_revenue
    metrics['Total Impressions'] = total_impressions
    metrics['Total Clicks'] = total_clicks
    metrics['Total Conversions'] = total_conversions
    metrics['Total New Customers'] = total_new_customers # Always include for UI consistency
    
    # Derived Metrics
    # CPA (Cost Per Acquisition)
    metrics['CPA'] = round(total_spend / total_new_customers, 2) if total_new_customers > 0 else 0.0
    
    # Conversion Rate
    metrics['Conversion Rate'] = f"{round((total_conversions / total_clicks) * 100, 2)}%" if total_clicks > 0 else "0%"
    
    # CTR
    metrics['CTR'] = f"{round((total_clicks / total_impressions) * 100, 2)}%" if total_impressions > 0 else "0%"
    
    # ROAS
    metrics['ROAS'] = round(total_revenue / total_spend, 2) if total_spend > 0 else 0.0

    if category_name == "Customer Acquisition":
        metrics['Total New Customers'] = total_new_customers

    elif category_name == "Customer Satisfaction":
        # --- Totals ---
        total_reach = df['reach'].sum()
        total_impressions = df['impressions'].sum()
        total_clicks = df['clicks'].sum()

        total_engagements = (
            df['likes'].sum() +
            df['comments'].sum() +
            df['shares'].sum()
        )

        # --- Engagement Rate ---
        engagement_rate = (
            (total_engagements / total_reach) * 100
            if total_reach > 0 else 0
        )

        # --- Click Through Rate ---
        ctr = (
            (total_clicks / total_impressions) * 100
            if total_impressions > 0 else 0
        )

        # --- Average Bounce Rate ---
        avg_bounce_rate = round(float(df['bounce_rate'].mean()), 2)

        # --- Average Frequency ---
        avg_frequency = round(float(df['frequency'].mean()), 2)

        # --- Optional Relevance Score ---
        avg_relevance_score = (
            round(float(df['relevance_score'].mean()), 2)
            if 'relevance_score' in df.columns
            else None
        )

        # --- Store Metrics ---
        metrics['Engagement Rate'] = f"{round(engagement_rate, 2)}%"
        metrics['CTR'] = f"{round(ctr, 2)}%"
        metrics['Average Bounce Rate'] = f"{avg_bounce_rate}%"
        metrics['Average Frequency'] = avg_frequency

        
    elif category_name == "Revenue Growth":
        # Additional metrics specific to Revenue
        # ROAS and Revenue are already in base metrics
        aov = round(total_revenue / total_conversions, 2) if total_conversions > 0 else 0
        purchases = int(df["purchases_per_year"].iloc[0]) if "purchases_per_year" in df else 0
        margin = float(df["product_profit_margin"].iloc[0]) if "product_profit_margin" in df else 0
        monthly_spend = float(df["total_monthly_ad_spend"].iloc[0]) if "total_monthly_ad_spend" in df else 0

        annual_customer_value = aov * purchases
        ltv_cac_ratio = round(annual_customer_value / metrics["CPA"], 2) if metrics["CPA"] > 0 else 0
        margin_decimal = margin / 100 if margin else 0
        break_even_roas = round(1 / margin_decimal, 2) if margin_decimal else 0
        mer = round(total_revenue / monthly_spend, 2) if monthly_spend else 0

        metrics["AOV"] = aov
        metrics["Annual Customer Value"] = round(annual_customer_value, 2)
        metrics["LTV:CAC Ratio"] = ltv_cac_ratio
        metrics["Break-Even ROAS"] = break_even_roas
        metrics["MER"] = mer
        metrics["Product Profit Margin"] = margin
        metrics["Ad Format"] = df["ad_format"].iloc[0] if "ad_format" in df else "Unknown"
        metrics["Campaign Goal"] = df["campaign_goal"].iloc[0] if "campaign_goal" in df else "Unknown"

    elif category_name == "Customer Retention":
        # Use provided retention fields if available.
        retained_customers_total = (
            int(df["retained_customers"].sum())
            if "retained_customers" in df.columns
            else 0
        )

        churn_rate_raw = (
            float(df["churn_rate"].mean())
            if "churn_rate" in df.columns
            else None
        )

        # Churn rate may be expressed as a fraction (0-1) or a percent (0-100).
        churn_rate_percent = None
        if churn_rate_raw is not None:
            churn_rate_percent = churn_rate_raw * 100 if churn_rate_raw <= 1 else churn_rate_raw

        retention_rate_percent = (
            round(100 - churn_rate_percent, 2)
            if churn_rate_percent is not None
            else None
        )

        purchases_per_year = (
            float(df["purchases_per_year"].iloc[0])
            if "purchases_per_year" in df.columns and not df.empty
            else None
        )

        # Optional leading indicator that can correlate with future retention.
        customer_satisfaction_score = (
            float(df["customer_satisfaction_score"].iloc[0])
            if "customer_satisfaction_score" in df.columns and not df.empty
            else None
        )

        # Useful context to size the retained cohort vs new customers.
        customer_base = retained_customers_total + total_new_customers
        retained_customer_share_percent = (
            round((retained_customers_total / customer_base) * 100, 2)
            if customer_base > 0
            else None
        )

        # Value proxy: average order value * purchases per year.
        avg_order_value = round(total_revenue / total_conversions, 2) if total_conversions > 0 else 0.0
        estimated_annual_value_per_customer = (
            round(avg_order_value * purchases_per_year, 2)
            if purchases_per_year is not None
            else None
        )

        metrics["Retained Customers"] = retained_customers_total
        metrics["Churn Rate"] = (
            f"{round(churn_rate_percent, 2)}%" if churn_rate_percent is not None else "N/A"
        )
        metrics["Retention Rate"] = (
            f"{retention_rate_percent}%" if retention_rate_percent is not None else "N/A"
        )
        metrics["Retained Customer Share"] = (
            f"{retained_customer_share_percent}%" if retained_customer_share_percent is not None else "N/A"
        )
        metrics["Repeat Purchases Per Year"] = purchases_per_year if purchases_per_year is not None else "N/A"
        metrics["Customer Satisfaction Score"] = (
            customer_satisfaction_score if customer_satisfaction_score is not None else "N/A"
        )
        metrics["Estimated Annual Value Per Customer"] = (
            estimated_annual_value_per_customer if estimated_annual_value_per_customer is not None else "N/A"
        )

    else:
        metrics['info'] = "General category, showing summary."

    return metrics
