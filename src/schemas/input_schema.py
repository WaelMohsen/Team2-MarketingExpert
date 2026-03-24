import math
from pydantic import BaseModel
from typing import Optional


class CampaignInput(BaseModel):

    # --- Identity ---
    campaign_name: str
    date: str
    channel: str

    # --- Core (used in base_metrics) ---
    impressions: int
    clicks: int
    conversions: int
    spend: float
    revenue: float

    # --- Customer Acquisition ---
    new_customers: Optional[int] = None

    # --- Customer Satisfaction ---
    reach: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    bounce_rate: Optional[float] = None
    frequency: Optional[float] = None

    # --- Customer Retention ---
    retained_customers: Optional[int] = None
    churn_rate: Optional[float] = None

    # --- Revenue Growth ---
    purchases_per_year: Optional[float] = None
    product_profit_margin: Optional[float] = None


def validate_campaign_data(df):
    records = df.to_dict(orient="records")
    validated = []
    for record in records:
        # Replace nan with None so Pydantic accepts Optional fields
        cleaned = {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in record.items()}
        validated.append(CampaignInput(**cleaned))
    return validated
