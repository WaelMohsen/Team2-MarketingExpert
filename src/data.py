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
        # Since the new CSV format does not have retention data (retained_customers, churn_rate),
        # we will set these to N/A or derive proxies if possible.
        # For this exercise, we'll mark them as Not Available.
        metrics['Retention Volume'] = "Data Not Available"
        metrics['Average Churn Rate'] = "Data Not Available"

    else:
        metrics['info'] = "General category, showing summary."

    return metrics
