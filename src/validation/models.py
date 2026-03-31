"""Validation result contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation issue with enough detail for debugging."""

    code: str
    message: str
    severity: str = "error"
    field_name: str | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationResult:
    """Validation summary used across ingestion and reporting flows."""

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def raise_for_errors(self) -> None:
        """Raise a value error with explicit failure scenarios when invalid."""

        if self.is_valid:
            return

        error_messages = [
            f"{issue.code}: {issue.message}"
            if issue.field_name is None
            else f"{issue.code} [{issue.field_name}]: {issue.message}"
            for issue in self.errors
        ]
        raise ValueError("; ".join(error_messages))
