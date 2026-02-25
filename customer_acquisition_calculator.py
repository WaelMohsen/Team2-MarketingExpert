import pandas as pd

def load_marketing_data(file_path=None):
    """
    Reads data from the provided CSV file and generates the missing 
    columns needed for Customer Acquisition KPIs.
    """
    if file_path:
        try:
            df = pd.read_csv("/Users/a12/Downloads/meeting records/poc/enriched_global_ads_dataset.csv")
            
            # 1. Generate 'total_orders' from 'conversions'
            df['total_orders'] = df['conversions']
            
            # 2. Generate 'sessions' from 'clicks' (Assuming 95% of clicks turn into actual sessions)
            df['sessions'] = (df['clicks'] * 0.95).astype(int)
            
            # 3. Generate 'new_customers' (Assuming 80% of the conversions are first-time buyers)
            df['new_customers'] = (df['total_orders'] * 0.80).astype(int)
            
            # Since the dataset is large, let's group it by 'platform' to see high-level KPIs
            summary_df = df.groupby('platform').agg({
                'ad_spend': 'sum',
                'clicks': 'sum',
                'sessions': 'sum',
                'total_orders': 'sum',
                'new_customers': 'sum',
                'revenue': 'sum'
            }).reset_index()
            
            # Rename 'revenue' to 'total_revenue' to match our existing KPI functions
            summary_df.rename(columns={'revenue': 'total_revenue'}, inplace=True)
            
            # We'll use 'platform' as the 'campaign_name' for the report display
            summary_df.rename(columns={'platform': 'campaign_name'}, inplace=True)
            
            return summary_df
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
    else:
        # Sample synthetic data representing 3 different campaigns
        data = {
            'campaign_name': ['Meta_Summer_Sale', 'TikTok_Viral_Video', 'Google_Search_Brand'],
            'ad_spend': [1500.00, 800.00, 300.00],        # in USD
            'clicks': [3200, 4500, 850],
            'sessions': [2900, 4100, 800],                # Traffic that actually landed on the site
            'total_orders': [45, 85, 30],
            'new_customers': [38, 80, 15],                # Subset of orders from first-time buyers
            'total_revenue': [4500.00, 6800.00, 3500.00]  # in USD
        }
        return pd.DataFrame(data)

def calculate_cvr(total_orders, sessions):
    """
    Calculates Conversion Rate (CVR).
    Formula: (Total Orders / Sessions) * 100
    """
    if sessions == 0: return 0
    return (total_orders / sessions) * 100

def calculate_cac(ad_spend, new_customers):
    """
    Calculates Customer Acquisition Cost (CAC).
    Formula: Total Ad Spend / Number of New Customers
    """
    if new_customers == 0: return 0
    return ad_spend / new_customers

def calculate_roas(total_revenue, ad_spend):
    """
    Calculates Return on Ad Spend (ROAS).
    Formula: Total Revenue / Total Ad Spend
    """
    if ad_spend == 0: return 0
    return total_revenue / ad_spend

def calculate_cpc(ad_spend, clicks):
    """
    Calculates Cost Per Click (CPC).
    Formula: Total Ad Spend / Total Clicks
    """
    if clicks == 0: return 0
    return ad_spend / clicks

def generate_kpi_report(df):
    """
    Takes a DataFrame of marketing data and calculates KPIs for each campaign.
    """
    print("--- CUSTOMER ACQUISITION KPI REPORT ---\n")
    
    for index, row in df.iterrows():
        campaign = row['campaign_name']
        cvr = calculate_cvr(row['total_orders'], row['sessions'])
        cac = calculate_cac(row['ad_spend'], row['new_customers'])
        roas = calculate_roas(row['total_revenue'], row['ad_spend'])
        cpc = calculate_cpc(row['ad_spend'], row['clicks'])
        
        print(f"Campaign: {campaign}")
        print(f"  - CVR (Conversion Rate): {cvr:.2f}%")
        print(f"  - CAC (Acquisition Cost): ${cac:.2f} per new customer")
        print(f"  - ROAS (Return on Ad Spend): {roas:.2f}x")
        print(f"  - CPC (Cost Per Click): ${cpc:.2f}")
        print("-" * 40)

# Execute the code
if __name__ == "__main__":
    # Load the newly provided dataset instead of the default mock data
    df_campaigns = load_marketing_data('global_ads_performance_dataset.csv')
    
    # Generate and print the report
    if df_campaigns is not None:
        generate_kpi_report(df_campaigns)