import os

TARGET_FILE_MAP = {
    "Customer Acquisition": "customer_acquisition.md",
    "Customer Satisfaction": "customer_satisfaction.md",
    "Revenue Growth": "revenue_growth.md",
    "Customer Retention": "customer_retention.md",
}

def load_prompt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error loading target prompt: {e}")
        return ""


def build_insight_user_prompt(business_domain, campaigns_df, metrics):
    channels_summary = []
    for _, row in campaigns_df.iterrows():
        channel_label = row.get("channel", row.get("campaign_name", "Unknown"))
        # Skip None/NaN fields to keep prompt clean
        fields = "\n".join([
            f"  - {col}: {row[col]}"
            for col in campaigns_df.columns
            if row[col] is not None and str(row[col]) != "nan"
        ])
        channels_summary.append(f"[ {channel_label} ]\n{fields}")

    campaigns_text = "\n\n".join(channels_summary)
    metrics_text = "\n".join([f"  - {k}: {v}" for k, v in metrics.items()]) if isinstance(metrics, dict) else str(metrics)

    return f"""
Business Domain: {business_domain}

═══════════════════════════════════════
CAMPAIGN CHANNELS DATA
═══════════════════════════════════════
{campaigns_text}

═══════════════════════════════════════
AGGREGATED KEY METRICS
═══════════════════════════════════════
{metrics_text}
"""


def build_recommendations_sys_prompt(target):
    base_recommendation_prompt = os.path.join(os.path.dirname(__file__), "recommendation_prompt.md")
    template = load_prompt(base_recommendation_prompt)
    target_filename = TARGET_FILE_MAP.get(target)
    target_prompt = load_prompt(os.path.join(os.path.dirname(__file__), target_filename))
    prompt = template.replace("{target}", target_prompt)
    return prompt


def build_recommendations_user_prompt(business_domain, insights, target, metrics):
    metrics_text = "\n".join([f"  - {k}: {v}" for k, v in metrics.items()]) if isinstance(metrics, dict) else str(metrics)

    return f"""
Business Domain: {business_domain}

═══════════════════════════════════════
CAMPAIGN INSIGHTS
═══════════════════════════════════════
{insights}

═══════════════════════════════════════
CAMPAIGN TARGET
═══════════════════════════════════════
Target: {target}

═══════════════════════════════════════
METRICS TO IMPROVE
═══════════════════════════════════════
{metrics_text}
"""