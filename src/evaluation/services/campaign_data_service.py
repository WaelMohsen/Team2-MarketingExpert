from typing import Callable


class CampaignDataService:
    def __init__(self, load_data_callable: Callable):
        self._load_data_callable = load_data_callable

    def load_all(self):
        df = self._load_data_callable()
        if df is None or df.empty:
            raise ValueError("No campaign data loaded. Check input data source.")
        return df

    def campaign_frame(self, campaign_name: str, source_df=None):
        df = source_df if source_df is not None else self.load_all()
        if "campaign_name" not in df.columns:
            return df

        campaign_df = df[df["campaign_name"] == campaign_name].copy()
        if campaign_df.empty:
            raise ValueError(f"Campaign not found in data: {campaign_name}")
        return campaign_df.reset_index(drop=True)
