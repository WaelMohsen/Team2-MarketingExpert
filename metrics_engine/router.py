from .base_metrics import calculate_base_metrics
from .registry import KPI_REGISTRY
import pandas as pd


def load_data(filepath="data/campaign_data.csv"):
    try:
        df = pd.read_csv(filepath)
        return df
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