"""End-to-end orchestration for the marketing analysis workflow."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ..core import DataValidationError
from ..core.observability import correlation_context
from ..ingestion import CampaignDataService
from ..llm.pipeline import LLMReportService
from ..metrics import CampaignMetricsService
from ..preprocessing import CampaignPreprocessingService, PreprocessingResult
from ..validation import CampaignValidationService, ValidationResult
from .models import MarketingPipelineResult

logger = logging.getLogger(__name__)


class MarketingPipeline:
    """Coordinates ingestion, validation, metric calculation, and AI output."""

    def __init__(
        self,
        data_service: CampaignDataService | None = None,
        metrics_service: CampaignMetricsService | None = None,
        report_service: LLMReportService | None = None,
        preprocessing_service: CampaignPreprocessingService | None = None,
        validation_service: CampaignValidationService | None = None,
    ) -> None:
        self._data_service = data_service or CampaignDataService()
        self._metrics_service = metrics_service or CampaignMetricsService()
        self._report_service = report_service or LLMReportService()
        self._preprocessing_service = preprocessing_service or CampaignPreprocessingService()
        self._validation_service = validation_service or CampaignValidationService()

    def load_raw_dataset(self, filepath: str | Path | None = None) -> pd.DataFrame:
        """Load raw dataset input without preprocessing."""

        return self._data_service.load_raw_dataframe(filepath)

    def preprocess_dataset(self, raw_dataset: pd.DataFrame) -> PreprocessingResult:
        """Preprocess a raw dataset independently of the full pipeline."""

        return self._preprocessing_service.preprocess(raw_dataset)

    def validate_dataset(self, dataset: pd.DataFrame) -> ValidationResult:
        """Validate a dataset independently of the full pipeline."""

        return self._validation_service.validate_dataframe(dataset)

    def canonicalize_dataset(self, dataset: pd.DataFrame) -> pd.DataFrame:
        """Convert a validated dataset into the canonical schema format."""

        validation_result = self.validate_dataset(dataset)
        try:
            validation_result.raise_for_errors()
        except ValueError as exc:
            raise DataValidationError(str(exc)) from exc
        return self._data_service.validate_dataframe(dataset)

    def calculate_metrics(self, dataset: pd.DataFrame, category: str):
        """Calculate metrics independently of the full pipeline."""

        return self._metrics_service.calculate_full(dataset, category)

    def generate_report(self, dataset: pd.DataFrame, category: str, metrics):
        """Generate a report independently of the full pipeline."""

        return self._report_service.generate_report(dataset, category, metrics)

    def run(self, category: str, filepath: str | Path | None = None) -> MarketingPipelineResult:
        """Execute the full workflow for a category."""

        with correlation_context() as correlation_id:
            logger.info("Starting marketing pipeline for category %s", category)
            raw_dataset = self.load_raw_dataset(filepath)
            preprocessing = self.preprocess_dataset(raw_dataset)
            input_validation = self.validate_dataset(preprocessing.dataframe)
            try:
                input_validation.raise_for_errors()
            except ValueError as exc:
                logger.error("Input validation failed for category %s: %s", category, exc)
                raise DataValidationError(str(exc)) from exc
            dataset = self._data_service.validate_dataframe(preprocessing.dataframe)
            metrics = self.calculate_metrics(dataset, category)
            report = self.generate_report(dataset, category, metrics)
            logger.info("Completed marketing pipeline for category %s", category)
            return MarketingPipelineResult(
                correlation_id=correlation_id,
                raw_dataset=raw_dataset,
                dataset=dataset,
                preprocessing=preprocessing,
                input_validation=input_validation,
                metrics=metrics,
                report=report,
            )
