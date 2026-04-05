"""Helpers for loading persisted marketing reports into evaluation candidates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..logging.logger import logger
from ..reporting import MarketingReport
from ..schemas.analysis_output_schema import AnalysisOutput
from ..schemas.recommendation_output_schema import RecommendationCard
from .benchmarks import RecommendationBenchmarkCandidate, RecommendationBenchmarkCase


def load_report_payload(report_file: str | Path) -> dict[str, Any]:
    """Load a saved report payload from disk."""

    report_path = Path(report_file)
    logger.debug("Loading report payload from {}", report_path)
    with report_path.open("r", encoding="utf-8") as input_file:
        payload = json.load(input_file)

    if not isinstance(payload, dict):
        raise ValueError(f"Report payload at {report_path} must be a JSON object.")

    return payload


def marketing_report_from_payload(payload: Mapping[str, Any]) -> MarketingReport:
    """Build a ``MarketingReport`` from a persisted JSON payload."""

    normalized_payload: Mapping[str, Any] = payload
    if "report" in payload and isinstance(payload["report"], Mapping):
        nested_report = dict(payload["report"])
        if "category" not in nested_report and "category" in payload:
            nested_report["category"] = payload["category"]
        normalized_payload = nested_report

    category = normalized_payload.get("category")
    analysis_payload = normalized_payload.get("analysis")
    recommendations_payload = normalized_payload.get("recommendations")

    if not isinstance(category, str) or not category.strip():
        raise ValueError("Report payload is missing a valid 'category'.")
    if not isinstance(analysis_payload, Mapping):
        raise ValueError("Report payload is missing a valid 'analysis' object.")
    if not isinstance(recommendations_payload, list):
        raise ValueError("Report payload is missing a valid 'recommendations' list.")

    analysis = AnalysisOutput(**dict(analysis_payload))
    recommendations = tuple(RecommendationCard(**item) for item in recommendations_payload)
    return MarketingReport(
        category=category,
        analysis=analysis,
        recommendations=recommendations,
    )


def load_marketing_report(report_file: str | Path) -> MarketingReport:
    """Load a ``MarketingReport`` from a saved JSON file."""

    return marketing_report_from_payload(load_report_payload(report_file))


def build_candidate_from_report_file(
    report_file: str | Path,
    *,
    candidate_id: str | None = None,
    parameter_settings: Mapping[str, Any] | None = None,
) -> RecommendationBenchmarkCandidate:
    """Create an evaluation candidate from a saved report JSON file."""

    report_path = Path(report_file)
    logger.debug("Building evaluation candidate from {}", report_path)
    payload = load_report_payload(report_path)
    report = marketing_report_from_payload(payload)

    merged_parameter_settings: dict[str, Any] = {}
    payload_parameter_settings = payload.get("parameter_settings")
    if isinstance(payload_parameter_settings, Mapping):
        merged_parameter_settings.update(dict(payload_parameter_settings))
    if parameter_settings:
        merged_parameter_settings.update(dict(parameter_settings))

    return RecommendationBenchmarkCandidate(
        candidate_id=candidate_id or report_path.stem,
        report=report,
        parameter_settings=merged_parameter_settings,
    )


def select_benchmark_cases(
    cases: Sequence[RecommendationBenchmarkCase],
    *,
    case_id: str | None = None,
    category: str | None = None,
) -> tuple[RecommendationBenchmarkCase, ...]:
    """Select benchmark cases by explicit id and/or category."""

    selected_cases = tuple(cases)
    if case_id:
        selected_cases = tuple(case for case in selected_cases if case.case_id == case_id)
        if not selected_cases:
            raise ValueError(f"No benchmark case found for case_id='{case_id}'.")

    if category:
        selected_cases = tuple(case for case in selected_cases if case.category == category)
        if not selected_cases:
            raise ValueError(f"No benchmark cases found for category='{category}'.")

    return selected_cases
