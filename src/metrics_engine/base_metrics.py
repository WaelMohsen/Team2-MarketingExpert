import pandas as pd

def calculate_base_metrics(df: pd.DataFrame | None) -> dict[str, float | str] | None:
    """
    Calculate base marketing metrics from a campaign dataframe.
    This function aggregates marketing performance data from a dataframe and computes
    key metrics including spend, revenue, impressions, clicks, conversions, and derived
    metrics like CTR, conversion rate, CPA, and ROAS.
    Args:
        df (pandas.DataFrame or None): A dataframe containing campaign data with columns:
            - campaign_name (str): Name of the marketing campaign
            - spend (float): Total advertising spend
            - revenue (float): Total revenue generated
            - impressions (int): Total ad impressions
            - clicks (int): Total ad clicks
            - conversions (int): Total conversions
            - new_customers (int, optional): Total new customers (falls back to conversions if not present)
    Returns:
        dict or None: A dictionary containing calculated metrics with the following keys:
            - Campaign Name (str): Name of the campaign
            - Total Spend (float): Sum of all spend
            - Total Revenue (float): Sum of all revenue
            - Total Impressions (int): Sum of all impressions
            - Total Clicks (int): Sum of all clicks
            - Total Conversions (int): Sum of all conversions
            - Total New Customers (int): Sum of new customers
            - Conversion Rate (str): Percentage of clicks converted (formatted with 2 decimals)
            - CTR (str): Click-through rate in percentage (formatted with 2 decimals)
            - CPA (float): Cost per acquisition (total spend / new customers)
            - ROAS (float): Return on ad spend (total revenue / total spend)
        Returns None if the input dataframe is None or empty.
    Raises:
        None explicitly, but handles missing columns gracefully with default values.
    Notes:
        - If 'new_customers' column is missing, 'conversions' is used as fallback
        - Division by zero is handled for CTR, conversion rate, CPA, and ROAS calculations
        - All percentage values are formatted as strings with '%' suffix
        - Numeric conversions ensure correct data types for calculations
    """

    if df is None or df.empty:
        return None

    campaign_name = (
        df["campaign_name"].iloc[0]
        if "campaign_name" in df and not df.empty
        else "Unknown Campaign"
    )
    total_spend = float(df["spend"].sum()) if "spend" in df else 0.0
    total_revenue = float(df["revenue"].sum()) if "revenue" in df else 0.0
    total_impressions = int(df["impressions"].sum()) if "impressions" in df else 0
    total_clicks = int(df["clicks"].sum()) if "clicks" in df else 0
    total_conversions = int(df["conversions"].sum()) if "conversions" in df else 0

    new_customers_col = "new_customers" if "new_customers" in df else "conversions"
    total_new_customers = (
        int(df[new_customers_col].sum()) if new_customers_col in df else 0
    )
    # --- Click Through Rate ---
    ctr = (total_clicks / total_impressions) * 100 if total_impressions > 0 else 0
    # --- conversion rate ----
    conversion_rate = (total_conversions / total_clicks) * 100 if total_clicks else 0

    metrics: dict[str, float | str] = {}
    metrics["Campaign Name"] = campaign_name
    metrics["Total Spend"] = total_spend
    metrics["Total Revenue"] = total_revenue
    metrics["Total Impressions"] = total_impressions
    metrics["Total Clicks"] = total_clicks
    metrics["Total Conversions"] = total_conversions
    metrics["Total New Customers"] = total_new_customers
    metrics["Conversion Rate"] = f"{round(conversion_rate, 2)}%"
    metrics["CTR"] = f"{round(ctr, 2)}%"
    metrics["CPA"] = (
        round(total_spend / total_new_customers, 2) if total_new_customers else 0
    )
    metrics["ROAS"] = round(total_revenue / total_spend, 2) if total_spend else 0

    return metrics
