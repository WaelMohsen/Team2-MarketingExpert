"""Services for loading and validating campaign datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import AppSettings
from ..core import DataLoadError, DataValidationError
from ..preprocessing import CampaignPreprocessingService, PreprocessingResult
from ..schemas.input_schema import validate_campaign_data
from ..logging.logger import logger

from ..validation import CampaignValidationService, ValidationResult


class CampaignDataService:
    """Loads campaign datasets and returns validated canonical data frames."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        *,
        preprocessor: CampaignPreprocessingService | None = None,
        validator: CampaignValidationService | None = None,
    ) -> None:
        self._settings = settings or AppSettings.default()
        self._preprocessor = preprocessor or CampaignPreprocessingService()
        self._validator = validator or CampaignValidationService()

    def load_dataframe(self, filepath: str | Path | None = None) -> pd.DataFrame:
        """Load a campaign dataset from disk and validate its schema."""

        return self.prepare_dataframe(self.load_raw_dataframe(filepath))

    def load_raw_dataframe(self, filepath: str | Path | None = None) -> pd.DataFrame:
        """Load a campaign dataset from disk without applying business validation."""

        data_path = Path(filepath) if filepath else self._settings.paths.data_file
        logger.info("Loading raw campaign data from %s", data_path)

        try:
            return pd.read_csv(data_path)
        except FileNotFoundError as exc:
            raise DataLoadError(f"Data file not found: {data_path}") from exc

    def preprocess_dataframe(self, dataframe: pd.DataFrame) -> PreprocessingResult:
        """Apply lightweight normalization before validation."""

        logger.info("Preprocessing campaign dataframe with %s rows", len(dataframe))
        return self._preprocessor.preprocess(dataframe)

    def validate_input_dataframe(self, dataframe: pd.DataFrame) -> ValidationResult:
        """Run explicit input validation checks for failure scenarios."""

        result = self._validator.validate_dataframe(dataframe)
        logger.info(
            "Validated campaign dataframe: errors=%s warnings=%s",
            len(result.errors),
            len(result.warnings),
        )
        return result

    def prepare_dataframe(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Preprocess, validate, and canonicalize a raw dataframe."""

        preprocessing_result = self.preprocess_dataframe(dataframe)
        validation_result = self.validate_input_dataframe(preprocessing_result.dataframe)

        try:
            validation_result.raise_for_errors()
        except ValueError as exc:
            raise DataValidationError(str(exc)) from exc

        return self.validate_dataframe(preprocessing_result.dataframe)

    @staticmethod
    def validate_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
        """Validate and canonicalize a campaign dataframe."""

        if dataframe is None or dataframe.empty:
            raise DataValidationError("Campaign dataset is empty.")

        try:
            canonical_data = validate_campaign_data(dataframe)
        except Exception as exc:  # pragma: no cover - Pydantic handles detail.
            raise DataValidationError(f"Campaign dataset failed validation: {exc}") from exc

        logger.info("Canonicalized campaign dataframe with %s rows", len(dataframe))
        return pd.DataFrame([record.model_dump() for record in canonical_data])
