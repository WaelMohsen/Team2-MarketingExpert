"""Services for loading and validating campaign datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import AppSettings
from ..core import DataLoadError, DataValidationError
from ..schemas.input_schema import validate_campaign_data


class CampaignDataService:
    """Loads campaign datasets and returns validated canonical data frames."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self._settings = settings or AppSettings.default()

    def load_dataframe(self, filepath: str | Path | None = None) -> pd.DataFrame:
        """Load a campaign dataset from disk and validate its schema."""

        data_path = Path(filepath) if filepath else self._settings.paths.data_file

        try:
            raw_dataframe = pd.read_csv(data_path)
        except FileNotFoundError as exc:
            raise DataLoadError(f"Data file not found: {data_path}") from exc

        return self.validate_dataframe(raw_dataframe)

    @staticmethod
    def validate_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
        """Validate and canonicalize a campaign dataframe."""

        if dataframe is None or dataframe.empty:
            raise DataValidationError("Campaign dataset is empty.")

        try:
            canonical_data = validate_campaign_data(dataframe)
        except Exception as exc:  # pragma: no cover - Pydantic handles detail.
            raise DataValidationError(f"Campaign dataset failed validation: {exc}") from exc

        return pd.DataFrame([record.model_dump() for record in canonical_data])
