import math
import typing
import pandas
import pydantic

class CampaignInput(pydantic.BaseModel):
    """
    Pydantic model for campaign input data validation.
    This schema defines the structure and validation rules for marketing campaign metrics
    across multiple performance dimensions.
    Attributes:
        campaign_name (str):
            The name or identifier of the marketing campaign.
            date (str): The date associated with the campaign data entry.
        channel (str):
            The marketing channel through which the campaign was executed
            (e.g., 'email', 'social', 'search', 'display').
        impressions (int):
            Total number of times the campaign content was displayed.
        clicks (int):
            Total number of clicks on the campaign content.
        conversions (int):
            Total number of conversions attributed to the campaign.
        spend (float):
            Total monetary amount spent on the campaign.
        revenue (float):
            Total revenue generated from the campaign.
        new_customers (Optional[int]):
            Number of new customers acquired from the campaign.
        reach (Optional[int]):
            Number of unique users who saw the campaign content.
        likes (Optional[int]):
            Number of likes/reactions received on campaign content.
        comments (Optional[int]):
            Number of comments received on campaign content.
        shares (Optional[int]):
            umber of times campaign content was shared.
        bounce_rate (Optional[float]):
            Percentage of users who left without further interaction (0-100).
        frequency (Optional[float]):
            Average number of times the campaign was shown to each user.
        retained_customers (Optional[int]):
            Number of existing customers retained during the campaign period.
        churn_rate (Optional[float]):
            Percentage of customers lost during the campaign period (0-100).
        purchases_per_year (Optional[float]):
            Average number of purchases per customer per year from the campaign.
        product_profit_margin (Optional[float]):
            Profit margin percentage for products sold through the campaign (0-100).
    """

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
    new_customers: typing.Optional[int] = None

    # --- Customer Satisfaction ---
    reach: typing.Optional[int] = None
    likes: typing.Optional[int] = None
    comments: typing.Optional[int] = None
    shares: typing.Optional[int] = None
    bounce_rate: typing.Optional[float] = None
    frequency: typing.Optional[float] = None

    # --- Customer Retention ---
    retained_customers: typing.Optional[int] = None
    churn_rate: typing.Optional[float] = None

    # --- Revenue Growth ---
    purchases_per_year: typing.Optional[float] = None
    product_profit_margin: typing.Optional[float] = None


def validate_campaign_data(df: pandas.DataFrame) -> typing.List[CampaignInput]:
    """
    Validate campaign data from a DataFrame using Pydantic schema.
    Converts a pandas DataFrame into a list of validated CampaignInput objects.
    Handles NaN values by converting them to None to satisfy Pydantic's Optional field requirements.
    Args:
        df (pandas.DataFrame): DataFrame containing campaign data to be validated.
    Returns:
        list[CampaignInput]: List of validated CampaignInput objects.
    Raises:
        ValidationError: If any record fails Pydantic validation against the CampaignInput schema.
    """
    records = df.to_dict(orient="records")
    validated = []
    for record in records:
        # Replace nan with None so Pydantic accepts Optional fields
        cleaned: typing.Dict[str, typing.Any] = {
            k: (None if isinstance(v, float) and math.isnan(v) else v)
            for k, v in record.items()
        }
        validated.append(CampaignInput(**cleaned))
    return validated
