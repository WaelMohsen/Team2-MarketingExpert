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
    total_spend = float(df['spend'].sum())
    total_revenue = float(df['revenue'].sum())
    total_impressions = int(df['impressions'].sum())
    total_clicks = int(df['clicks'].sum())
    total_conversions = int(df['conversions'].sum())
    total_new_customers = int(df['new_customers'].sum())
    
    if category_name == "Customer Acquisition":
        metrics['Total New Customers'] = total_new_customers
        metrics['Total Spend'] = total_spend
        # Cost Per Acquisition (CPA)
        metrics['CPA'] = round(total_spend / total_new_customers, 2) if total_new_customers > 0 else 0
        # Conversion Rate
        metrics['Conversion Rate'] = f"{round((total_conversions / total_clicks) * 100, 2)}%" if total_clicks > 0 else "0%"

    elif category_name == "Customer Satisfaction":
        # Ad & Content Relevance metrics
        metrics['Average CSAT Score'] = round(float(df['customer_satisfaction_score'].mean()), 2)
        # Click Through Rate (indicative of relevance)
        metrics['CTR'] = f"{round((total_clicks / total_impressions) * 100, 2)}%" if total_impressions > 0 else "0%"
        metrics['Total Clicks'] = total_clicks

    elif category_name == "Revenue Growth":
        metrics['Total Revenue'] = total_revenue
        metrics['Total Spend'] = total_spend
        # Return on Ad Spend (ROAS)
        metrics['ROAS'] = round(total_revenue / total_spend, 2) if total_spend > 0 else 0
        retained_sum = int(df['retained_customers'].sum())
        metrics['Revenue Per Customer'] = round(total_revenue / (total_new_customers + retained_sum), 2)

    elif category_name == "Customer Retention":
        avg_churn = float(df['churn_rate'].mean())
        total_retained = int(df['retained_customers'].sum())
        metrics['Average Churn Rate'] = f"{round(avg_churn * 100, 2)}%"
        metrics['Total Retained Customers'] = total_retained
        # Simple retention rate proxy
        metrics['Retention Volume'] = total_retained

    else:
        metrics['info'] = "General category, showing summary."
        metrics['Total Revenue'] = total_revenue
        metrics['Total Spend'] = total_spend

    return metrics
