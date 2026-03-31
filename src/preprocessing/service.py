"""Preprocessing services for campaign datasets."""

from __future__ import annotations

from collections.abc import Sequence
import logging

import pandas as pd

from .models import PreprocessingResult

logger = logging.getLogger(__name__)

STRING_COLUMNS: tuple[str, ...] = ("campaign_name", "channel", "date")
NUMERIC_COLUMNS: tuple[str, ...] = (
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
    "bounce_rate",
    "frequency",
    "retained_customers",
    "churn_rate",
    "purchases_per_year",
    "product_profit_margin",
)
SORT_COLUMNS: tuple[str, ...] = ("date", "campaign_name", "channel")


class CampaignPreprocessingService:
    """Applies lightweight normalization before schema validation."""

    def __init__(
        self,
        *,
        string_columns: Sequence[str] = STRING_COLUMNS,
        numeric_columns: Sequence[str] = NUMERIC_COLUMNS,
        sort_columns: Sequence[str] = SORT_COLUMNS,
    ) -> None:
        self._string_columns = tuple(string_columns)
        self._numeric_columns = tuple(numeric_columns)
        self._sort_columns = tuple(sort_columns)

    def preprocess(self, dataframe: pd.DataFrame) -> PreprocessingResult:
        """Return a normalized dataframe plus a trace of applied steps."""

        normalized = dataframe.copy()
        applied_steps: list[str] = []

        if normalized.empty:
            return PreprocessingResult(
                dataframe=normalized,
                applied_steps=tuple(applied_steps),
                row_count_before=0,
                row_count_after=0,
            )

        if self._has_any_columns(normalized, self._string_columns):
            normalized = self._normalize_string_columns(normalized)
            applied_steps.append("normalize_strings")

        if self._has_any_columns(normalized, self._numeric_columns):
            normalized = self._coerce_numeric_columns(normalized)
            applied_steps.append("coerce_numeric_columns")

        if "date" in normalized.columns:
            normalized = self._normalize_dates(normalized)
            applied_steps.append("normalize_dates")

        if self._has_any_columns(normalized, self._sort_columns):
            normalized = self._sort_dataframe(normalized)
            applied_steps.append("sort_rows")

        logger.info(
            "Preprocessed dataframe: rows_before=%s rows_after=%s steps=%s",
            len(dataframe),
            len(normalized),
            ",".join(applied_steps) or "none",
        )
        return PreprocessingResult(
            dataframe=normalized,
            applied_steps=tuple(applied_steps),
            row_count_before=len(dataframe),
            row_count_after=len(normalized),
        )

    def _normalize_string_columns(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        result = dataframe.copy()

        for column_name in self._string_columns:
            if column_name in result.columns:
                result[column_name] = result[column_name].apply(
                    lambda value: value.strip() if isinstance(value, str) else value
                )

        return result

    def _coerce_numeric_columns(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        result = dataframe.copy()

        for column_name in self._numeric_columns:
            if column_name in result.columns:
                result[column_name] = pd.to_numeric(result[column_name], errors="raise")

        return result

    @staticmethod
    def _normalize_dates(dataframe: pd.DataFrame) -> pd.DataFrame:
        result = dataframe.copy()
        parsed_dates = pd.to_datetime(result["date"], errors="raise", format="mixed")
        result["date"] = parsed_dates.dt.strftime("%Y-%m-%d")
        return result

    def _sort_dataframe(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        available_sort_columns = [column for column in self._sort_columns if column in dataframe.columns]
        return dataframe.sort_values(available_sort_columns).reset_index(drop=True)

    @staticmethod
    def _has_any_columns(dataframe: pd.DataFrame, columns: Sequence[str]) -> bool:
        return any(column in dataframe.columns for column in columns)
