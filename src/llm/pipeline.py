from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from ..config import AppSettings
from ..metrics import MetricsBundle
from ..reporting import MarketingReport
from ..schemas.analysis_output_schema import AnalysisOutput, validate_analysis_output
from ..schemas.recommendation_output_schema import (
    RecommendationOutput,
    validate_recommendation_output,
)
from .prompts import (
    analysis_system_prompt,
    build_analysis_user_prompt,
    build_context_block,
    build_recommendation_user_prompt,
    recommendation_system_prompt,
)
from src.llm.client import chat_completion, get_client

CATEGORIES = [
    "Customer Acquisition",
    "Customer Satisfaction",
    "Revenue Growth",
    "Customer Retention",
]

_CATEGORY_PROMPT_FILES = {
    "Customer Acquisition": "customer_acquisition.md",
    "Customer Satisfaction": "customer_satisfaction.md",
    "Revenue Growth": "revenue_growth.md",
    "Customer Retention": "customer_retention.md",
}

logger = logging.getLogger(__name__)


class PromptRepository:
    """Resolves prompt file locations without leaking filesystem concerns."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self._settings = settings or AppSettings.default()

    def category_prompt_path(self, category: str) -> Path:
        prompt_file = _CATEGORY_PROMPT_FILES.get(category, "response_generation.md")
        return self._settings.paths.prompt_dir / prompt_file

    def analysis_system_prompt_path(self) -> Path:
        return self._settings.paths.prompt_dir / "system_analysis_prompt.md"

    def recommendation_system_prompt_path(self) -> Path:
        return self._settings.paths.prompt_dir / "recommendation_system_prompt.md"


class OutputLogWriter:
    """Persists pipeline outputs for debugging and traceability."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self._settings = settings or AppSettings.default()

    def save(self, output: dict[str, Any]) -> Path:
        output_directory = self._settings.paths.output_log_dir
        output_directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_directory / f"pipeline_output_{timestamp}.json"

        with output_path.open("w", encoding="utf-8") as output_file:
            json.dump(output, output_file, indent=4, ensure_ascii=False)

        logger.info("Saved pipeline output to %s", output_path)
        return output_path


class LLMReportService:
    """Generates structured analysis and recommendation reports."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        client_factory: Callable[[], Any] = get_client,
        output_writer: OutputLogWriter | None = None,
    ) -> None:
        self._settings = settings or AppSettings.default()
        self._client_factory = client_factory
        self._prompts = PromptRepository(self._settings)
        self._output_writer = output_writer or OutputLogWriter(self._settings)

    def generate_report(
        self,
        dataframe: pd.DataFrame,
        category: str,
        metrics: MetricsBundle | dict[str, Any],
    ) -> MarketingReport:
        """Run the two-step LLM workflow and return a structured report."""

        client = self._client_factory()
        metrics_payload = metrics.to_dict() if isinstance(metrics, MetricsBundle) else dict(metrics)
        context_block = build_context_block(category, dataframe, metrics_payload)

        analysis_model = self._generate_analysis(client, category, context_block)
        recommendation_model = self._generate_recommendations(
            client=client,
            category=category,
            context_block=context_block,
            analysis_model=analysis_model,
        )

        report = MarketingReport(
            category=category,
            analysis=analysis_model,
            recommendations=tuple(recommendation_model.recommendations),
        )

        output_payload = {
            "category": category,
            "metrics": metrics_payload,
            **report.to_response_dict(),
        }
        self._output_writer.save(output_payload)
        return report

    def _generate_analysis(self, client: Any, category: str, context_block: str) -> AnalysisOutput:
        analysis_system_text = analysis_system_prompt(
            category,
            str(self._prompts.category_prompt_path(category)),
            str(self._prompts.analysis_system_prompt_path()),
        )
        analysis_user_text = build_analysis_user_prompt(context_block)
        analysis_response = chat_completion(
            client,
            analysis_system_text,
            analysis_user_text,
            response_format=AnalysisOutput,
            model=self._settings.llm.analysis_model,
            temperature=self._settings.llm.analysis_temperature,
        )
        parsed_analysis = analysis_response.choices[0].message.parsed
        analysis_json = json.dumps(parsed_analysis.model_dump(), ensure_ascii=False)
        return validate_analysis_output(analysis_json)

    def _generate_recommendations(
        self,
        *,
        client: Any,
        category: str,
        context_block: str,
        analysis_model: AnalysisOutput,
    ) -> RecommendationOutput:
        analysis_json = json.dumps(analysis_model.model_dump(), ensure_ascii=False)
        recommendation_system_text = recommendation_system_prompt(
            category,
            str(self._prompts.category_prompt_path(category)),
            str(self._prompts.recommendation_system_prompt_path()),
        )
        recommendation_user_text = build_recommendation_user_prompt(
            context_block,
            analysis_input=analysis_json,
        )
        recommendation_response = chat_completion(
            client,
            recommendation_system_text,
            recommendation_user_text,
            response_format=RecommendationOutput,
            model=self._settings.llm.recommendation_model,
            temperature=self._settings.llm.recommendation_temperature,
        )
        parsed_recommendations = recommendation_response.choices[0].message.parsed
        recommendation_json = json.dumps(parsed_recommendations.model_dump(), ensure_ascii=False)
        return validate_recommendation_output(recommendation_json)


def save_output(output: dict[str, Any]) -> Path:
    """Backward-compatible wrapper for saving pipeline output."""

    return OutputLogWriter().save(output)


def generate_response(dataframe: pd.DataFrame, category: str, metrics: dict[str, Any]) -> str:
    """Backward-compatible wrapper returning the historical JSON response string."""

    try:
        report = LLMReportService().generate_report(dataframe, category, metrics)
        return json.dumps(report.to_response_dict(), ensure_ascii=False)
    except Exception as exc:  # pragma: no cover - exercised through UI flows.
        logger.exception("Failed to generate marketing report for category %s", category)
        return f"Error generating response: {exc}"
