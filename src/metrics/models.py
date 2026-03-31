"""Typed contracts for metric calculation results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MetricValue = str | int | float | None
MetricsMap = dict[str, MetricValue]


@dataclass(frozen=True)
class MetricsBundle:
    """Metrics calculated at the overall and per-channel levels."""

    overall: MetricsMap
    per_channel: dict[str, MetricsMap]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the bundle into a plain dictionary."""

        return {
            "overall": dict(self.overall),
            "per_channel": {channel: dict(metrics) for channel, metrics in self.per_channel.items()},
        }
