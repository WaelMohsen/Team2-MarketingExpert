import pandas as pd
from src.schemas.input_schema import validate_campaign_data
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

def calculate_metrics(df: pd.DataFrame | None, target: str) -> dict[str, float | str]:
    """
    Calculate metrics for a given dataset and target KPI.
    This function computes base metrics from the provided dataframe and then
    applies a target-specific KPI calculator if available in the registry.
    Args:
        df (pd.DataFrame | None): The input dataframe containing data to analyze.
                                  Can be None if no data is available.
        target (str): The name of the target KPI to calculate. Used to look up
                      the appropriate calculator in the KPI_REGISTRY.
    Returns:
        dict[str, float | str]: A dictionary containing calculated metrics.
                                - If no data is available: returns error message
                                - If target not found: returns base metrics only
                                - If target found: returns base metrics enhanced with
                                  target-specific KPI calculations
    Raises:
        None: Function handles errors gracefully and returns them in the result dict.
    Examples:
        >>> result = calculate_metrics(df, "revenue")
        >>> if "error" not in result:
        ...     print(result["total"])
    """

    base_metrics = calculate_base_metrics(df)

    if base_metrics is None:
        return {"error": "No data available"}

    calculator = KPI_REGISTRY.get(target)

    if not calculator:
        return base_metrics

    return calculator(df, base_metrics)