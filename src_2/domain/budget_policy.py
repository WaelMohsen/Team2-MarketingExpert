"""Small helpers for deriving POC budget envelopes from observed spend."""

from __future__ import annotations

from collections.abc import Iterable


def historical_type_shares(
    rows: Iterable[tuple[str, float]],
) -> dict[str, float]:
    totals: dict[str, float] = {}
    for campaign_type, spend in rows:
        totals[campaign_type] = totals.get(campaign_type, 0.0) + max(float(spend), 0)
    portfolio_spend = sum(totals.values())
    if portfolio_spend == 0:
        return {campaign_type: 0.0 for campaign_type in totals}
    return {
        campaign_type: spend / portfolio_spend
        for campaign_type, spend in totals.items()
    }
