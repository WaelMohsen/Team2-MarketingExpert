"""Deterministic checks that a narrative is faithful to its evidence.

No LLM is used here, so these results are noise-free and form the trustworthy
baseline of the quality trend. Each check is 'hard' (a failure means the campaign
narrative is inconsistent) or 'warn' (advisory).
"""

from __future__ import annotations

import re

from src_2.contracts import (
    CampaignAssessment,
    CampaignEvidencePack,
    CampaignInsight,
    ConsistencyCheck,
)
from src_2.domain.models import EvidenceStatus

# Statuses that must be accompanied by a stated limitation in the narrative.
_LIMITED_STATUSES = {EvidenceStatus.LIMITED, EvidenceStatus.INSUFFICIENT}

# Decimal figures only (e.g. 0.46, 457574.0, 77.4). Bare small integers and long
# id-like numbers are intentionally excluded to limit false positives.
_NUMBER = re.compile(r"\d{1,3}(?:,\d{3})*\.\d+|\d+\.\d+")


def _allowed_numbers(pack: CampaignEvidencePack) -> set[float]:
    numbers: set[float] = set()
    metrics = [*pack.primary_kpis, *pack.supporting_kpis, *pack.guardrails]
    for entity in [pack.campaign, *pack.adsets, *pack.ads, *pack.creatives, *pack.audiences]:
        metrics.extend(entity.metrics)
    for metric in metrics:
        for value in (metric.actual, metric.benchmark):
            if value is not None:
                numbers.add(round(float(value), 2))
    return numbers


def _valid_entity_ids(pack: CampaignEvidencePack) -> set[str]:
    ids = {pack.campaign_id, pack.campaign.entity_id}
    for group in (pack.adsets, pack.ads, pack.creatives, pack.audiences):
        ids.update(entity.entity_id for entity in group)
    return ids


def _valid_metrics(pack: CampaignEvidencePack) -> set[str]:
    names = {m.metric for m in [*pack.primary_kpis, *pack.supporting_kpis, *pack.guardrails]}
    for entity in [pack.campaign, *pack.adsets, *pack.ads, *pack.creatives, *pack.audiences]:
        names.update(m.metric for m in entity.metrics)
    return names


def _narrative_text(insight: CampaignInsight) -> str:
    parts = [
        insight.target_assessment,
        insight.strategic_lesson,
        insight.next_controlled_test or "",
        *insight.performance_drivers,
        *insight.audience_findings,
        *insight.creative_findings,
        *insight.risks_and_confounders,
    ]
    return "\n".join(parts)


def run_consistency_checks(
    insight: CampaignInsight,
    pack: CampaignEvidencePack,
    assessment: CampaignAssessment,
) -> list[ConsistencyCheck]:
    checks: list[ConsistencyCheck] = []

    # 1. Evidence status must not be overstated by the narrative.
    status_match = insight.evidence_status == assessment.evidence_status
    checks.append(
        ConsistencyCheck(
            name="evidence_status_match",
            passed=status_match,
            severity="hard",
            detail=(
                "matches the deterministic evidence status"
                if status_match
                else f"insight says {insight.evidence_status.value} but the decision used "
                f"{assessment.evidence_status.value}"
            ),
        )
    )

    # 2. Cited supporting evidence must reference real entities and metrics.
    valid_ids = _valid_entity_ids(pack)
    valid_metrics = _valid_metrics(pack)
    bad_refs = [
        f"{ref.entity_id}/{ref.metric}"
        for ref in insight.supporting_evidence
        if ref.entity_id not in valid_ids or ref.metric not in valid_metrics
    ]
    checks.append(
        ConsistencyCheck(
            name="supporting_evidence_valid",
            passed=not bad_refs,
            severity="hard",
            detail=(
                "all references resolve to the evidence pack"
                if not bad_refs
                else "unknown references: " + ", ".join(bad_refs)
            ),
        )
    )

    # 3. Limited evidence must be disclosed as a risk/confounder.
    if pack.evidence_status in _LIMITED_STATUSES:
        disclosed = bool(insight.risks_and_confounders)
        checks.append(
            ConsistencyCheck(
                name="limitations_disclosed",
                passed=disclosed,
                severity="hard",
                detail=(
                    "evidence limitations are disclosed"
                    if disclosed
                    else f"evidence is {pack.evidence_status.value} but no risk/confounder is stated"
                ),
            )
        )

    # 4. Figures cited in prose should trace to computed evidence (advisory).
    allowed = _allowed_numbers(pack)
    ungrounded = []
    for token in _NUMBER.findall(_narrative_text(insight)):
        value = round(float(token.replace(",", "")), 2)
        if not any(abs(value - a) <= max(0.01, abs(a) * 0.02) for a in allowed):
            ungrounded.append(token)
    checks.append(
        ConsistencyCheck(
            name="figures_grounded",
            passed=not ungrounded,
            severity="warn",
            detail=(
                "all cited decimal figures trace to the evidence"
                if not ungrounded
                else "figures not found in evidence: " + ", ".join(sorted(set(ungrounded)))
            ),
        )
    )

    return checks


def consistency_passed(checks: list[ConsistencyCheck]) -> bool:
    """A campaign passes when no 'hard' check failed."""
    return all(check.passed for check in checks if check.severity == "hard")
