import pandas as pd

from ..schemas.input_schema import validate_campaign_data
from .base_metrics import calculate_base_metrics
from .registry import KPI_REGISTRY


def load_data(filepath="data/all_campaigns_data.csv"):
    try:
        df = pd.read_csv(filepath)
        canonical_data = validate_campaign_data(df)
        canonical_df = pd.DataFrame([record.model_dump() for record in canonical_data])
        return canonical_df
    except FileNotFoundError:
        return None


def calculate_metrics(df, target):

    base_metrics = calculate_base_metrics(df)

    if base_metrics is None:
        return {"error": "No data available"}

    calculator = KPI_REGISTRY.get(target)

    if not calculator:
        return base_metrics

    return calculator(df, base_metrics)


def calculate_metrics_full(df, target):
    """
    Calculates metrics both across all channels (overall) and per individual channel.

    Returns:
        {
            "overall": { ...metrics across all channels... },
            "per_channel": {
                "Instagram": { ...metrics... },
                "Google Ads": { ...metrics... },
                ...
            }
        }
    """
    if df is None or df.empty:
        return {"error": "No data available"}

    # --- Overall (across all channels) ---
    overall = calculate_metrics(df, target)

    # --- Per channel ---
    per_channel = {}

    if "channel" not in df.columns:
        return {"overall": overall, "per_channel": {}}

    for channel_name, channel_df in df.groupby("channel"):
        channel_df = channel_df.reset_index(drop=True)
        per_channel[channel_name] = calculate_metrics(channel_df, target)

    return {
        "overall": overall,
        "per_channel": per_channel,
    }
