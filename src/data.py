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
        # In the new single-row CSV, we might not have CSAT. 
        # If missing, we might omit or set a placeholder.
        if 'customer_satisfaction_score' in df:
            metrics['Average CSAT Score'] = round(float(df['customer_satisfaction_score'].mean()), 2)
        else:
             metrics['Average CSAT Score'] = "N/A (Not in data)"

    elif category_name == "Revenue Growth":
        # Additional metrics specific to Revenue
        # ROAS and Revenue are already in base metrics
        pass

    elif category_name == "Customer Retention":
        # Since the new CSV format does not have retention data (retained_customers, churn_rate),
        # we will set these to N/A or derive proxies if possible.
        # For this exercise, we'll mark them as Not Available.
        metrics['Retention Volume'] = "Data Not Available"
        metrics['Average Churn Rate'] = "Data Not Available"

    else:
        metrics['info'] = "General category, showing summary."

    return metrics
