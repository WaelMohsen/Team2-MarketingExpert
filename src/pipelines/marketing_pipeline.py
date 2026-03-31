"""End-to-end orchestration for the marketing analysis workflow."""

from __future__ import annotations

from pathlib import Path

from ..ingestion import CampaignDataService
from ..llm.pipeline import LLMReportService
from ..metrics import CampaignMetricsService
from .models import MarketingPipelineResult


class MarketingPipeline:
    """Coordinates ingestion, validation, metric calculation, and AI output."""

    def __init__(
        self,
        data_service: CampaignDataService | None = None,
        metrics_service: CampaignMetricsService | None = None,
        report_service: LLMReportService | None = None,
    ) -> None:
        self._data_service = data_service or CampaignDataService()
        self._metrics_service = metrics_service or CampaignMetricsService()
        self._report_service = report_service or LLMReportService()

    def run(self, category: str, filepath: str | Path | None = None) -> MarketingPipelineResult:
        """Execute the full workflow for a category."""

        dataset = self._data_service.load_dataframe(filepath)
        metrics = self._metrics_service.calculate_full(dataset, category)
        report = self._report_service.generate_report(dataset, category, metrics)
        return MarketingPipelineResult(dataset=dataset, metrics=metrics, report=report)
