"""Validation services for input data and structured outputs."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import pandas as pd

from ..schemas.analysis_output_schema import AnalysisOutput, validate_analysis_output
from ..schemas.input_schema import CampaignInput
from ..schemas.recommendation_output_schema import RecommendationOutput, validate_recommendation_output
from ..logging.logger import logger

from .models import ValidationIssue, ValidationResult

REQUIRED_COLUMNS: tuple[str, ...] = (
    "campaign_name",
    "date",
    "channel",
    "impressions",
    "clicks",
    "conversions",
    "spend",
    "revenue",
)

NON_NEGATIVE_COLUMNS: tuple[str, ...] = (
    "impressions",
    "clicks",
    "conversions",
    "spend",
    "revenue",
    "new_customers",
    "reach",
    "likes",
    "comments",
    "shares",
    "retained_customers",
    "purchases_per_year",
    "product_profit_margin",
)

RATE_COLUMNS: tuple[str, ...] = ("bounce_rate", "churn_rate")


class CampaignValidationService:
    """Performs explicit validation checks before row-level schema validation."""

    def __init__(
        self,
        *,
        required_columns: Sequence[str] = REQUIRED_COLUMNS,
        non_negative_columns: Sequence[str] = NON_NEGATIVE_COLUMNS,
        rate_columns: Sequence[str] = RATE_COLUMNS,
    ) -> None:
        self._required_columns = tuple(required_columns)
        self._non_negative_columns = tuple(non_negative_columns)
        self._rate_columns = tuple(rate_columns)

    def validate_dataframe(self, dataframe: pd.DataFrame) -> ValidationResult:
        """Validate a dataframe and return explicit issues."""

        issues: list[ValidationIssue] = []

        if dataframe is None:
            issues.append(ValidationIssue(code="dataset_none", message="Dataset is missing."))
            return ValidationResult(issues=tuple(issues))

        if dataframe.empty:
            issues.append(ValidationIssue(code="dataset_empty", message="Dataset is empty."))
            return ValidationResult(issues=tuple(issues))

        missing_columns = [column for column in self._required_columns if column not in dataframe.columns]
        for column_name in missing_columns:
            issues.append(
                ValidationIssue(
                    code="missing_required_column",
                    field_name=column_name,
                    message="Required column is missing from the dataset.",
                )
            )

        if missing_columns:
            return ValidationResult(issues=tuple(issues))

        issues.extend(self._validate_required_nulls(dataframe))
        issues.extend(self._validate_non_negative_columns(dataframe))
        issues.extend(self._validate_monotonic_funnel(dataframe))
        issues.extend(self._validate_rate_columns(dataframe))
        issues.extend(self._validate_dates(dataframe))
        issues.extend(self._warn_on_duplicates(dataframe))

        result = ValidationResult(issues=tuple(issues))
        logger.info(
            "Campaign validation completed: errors=%s warnings=%s",
            len(result.errors),
            len(result.warnings),
        )
        return result

    def _validate_required_nulls(self, dataframe: pd.DataFrame) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        for column_name in self._required_columns:
            if dataframe[column_name].isna().any():
                issues.append(
                    ValidationIssue(
                        code="null_required_value",
                        field_name=column_name,
                        message="Required column contains null values.",
                    )
                )

        return issues

    def _validate_non_negative_columns(self, dataframe: pd.DataFrame) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        for column_name in self._non_negative_columns:
            if column_name in dataframe.columns and dataframe[column_name].dropna().lt(0).any():
                issues.append(
                    ValidationIssue(
                        code="negative_value",
                        field_name=column_name,
                        message="Column contains negative values that are not allowed.",
                    )
                )

        return issues

    @staticmethod
    def _validate_monotonic_funnel(dataframe: pd.DataFrame) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if (dataframe["clicks"] > dataframe["impressions"]).any():
            issues.append(
                ValidationIssue(
                    code="clicks_exceed_impressions",
                    field_name="clicks",
                    message="Clicks exceed impressions in at least one row.",
                )
            )

        if (dataframe["conversions"] > dataframe["clicks"]).any():
            issues.append(
                ValidationIssue(
                    code="conversions_exceed_clicks",
                    field_name="conversions",
                    message="Conversions exceed clicks in at least one row.",
                )
            )

        if "new_customers" in dataframe.columns:
            comparable_rows = dataframe["new_customers"].notna()
            if (dataframe.loc[comparable_rows, "new_customers"] > dataframe.loc[comparable_rows, "conversions"]).any():
                issues.append(
                    ValidationIssue(
                        code="new_customers_exceed_conversions",
                        field_name="new_customers",
                        severity="warning",
                        message="New customers exceed conversions in at least one row.",
                    )
                )

        return issues

    def _validate_rate_columns(self, dataframe: pd.DataFrame) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        for column_name in self._rate_columns:
            if column_name not in dataframe.columns:
                continue

            non_null_values = dataframe[column_name].dropna()
            if non_null_values.empty:
                continue

            invalid_values = non_null_values[(non_null_values < 0) | (non_null_values > 100)]
            if not invalid_values.empty:
                issues.append(
                    ValidationIssue(
                        code="invalid_rate_value",
                        field_name=column_name,
                        message="Rate column contains values outside the supported 0-100 range.",
                    )
                )

        return issues

    @staticmethod
    def _validate_dates(dataframe: pd.DataFrame) -> list[ValidationIssue]:
        try:
            pd.to_datetime(dataframe["date"], errors="raise")
            return []
        except Exception:
            return [
                ValidationIssue(
                    code="invalid_date",
                    field_name="date",
                    message="Date column contains values that cannot be parsed.",
                )
            ]

    @staticmethod
    def _warn_on_duplicates(dataframe: pd.DataFrame) -> list[ValidationIssue]:
        if not dataframe.duplicated().any():
            return []

        return [
            ValidationIssue(
                code="duplicate_rows",
                severity="warning",
                message="Dataset contains duplicate rows.",
                context={"duplicate_count": int(dataframe.duplicated().sum())},
            )
        ]

    def required_input_fields(self) -> tuple[str, ...]:
        """Expose the core input fields expected by the application."""

        model_fields = getattr(CampaignInput, "model_fields", {})
        if model_fields:
            return tuple(model_fields.keys())
        return self._required_columns


class ReportValidationService:
    """Wraps schema validators behind a stable service interface."""

    def validate_analysis(self, payload: str | dict[str, Any] | AnalysisOutput) -> AnalysisOutput:
        """Validate analysis output from string, dict, or model input."""

        if isinstance(payload, AnalysisOutput):
            payload_text = json.dumps(payload.model_dump(), ensure_ascii=False)
        elif isinstance(payload, dict):
            payload_text = json.dumps(payload, ensure_ascii=False)
        else:
            payload_text = payload

        result = validate_analysis_output(payload_text)
        logger.info("Validated analysis output successfully")
        return result

    def validate_recommendations(
        self,
        payload: str | dict[str, Any] | RecommendationOutput,
    ) -> RecommendationOutput:
        """Validate recommendation output from string, dict, or model input."""

        if isinstance(payload, RecommendationOutput):
            payload_text = json.dumps(payload.model_dump(), ensure_ascii=False)
        elif isinstance(payload, dict):
            payload_text = json.dumps(payload, ensure_ascii=False)
        else:
            payload_text = payload

        result = validate_recommendation_output(payload_text)
        logger.info("Validated recommendation output successfully")
        return result
