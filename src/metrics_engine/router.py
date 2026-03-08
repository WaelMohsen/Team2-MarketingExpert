from .base_metrics import calculate_base_metrics
from src.schemas.input_schema import validate_campaign_data
from .registry import KPI_REGISTRY
import pandas as pd


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