"""Transparent target and funding classifications without weighted averages."""

from __future__ import annotations

from enum import Enum

from .models import EvidenceStatus


class TargetStatus(str, Enum):
    ACHIEVED = "achieved"
    ACHIEVED_WITH_CONCERNS = "achieved_with_concerns"
    NOT_ACHIEVED = "not_achieved"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    DATA_NOT_READY = "data_not_ready"


class NextCycleAction(str, Enum):
    SCALE = "scale"
    KEEP_AS_TEST = "keep_as_test"
    DO_NOT_FUND = "do_not_fund"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    DATA_NOT_READY = "data_not_ready"


def classify_target(
    *,
    primary_kpis_passed: bool,
    critical_guardrails_passed: bool,
    evidence_status: EvidenceStatus,
) -> TargetStatus:
    if evidence_status is EvidenceStatus.DATA_NOT_READY:
        return TargetStatus.DATA_NOT_READY
    if evidence_status is EvidenceStatus.INSUFFICIENT:
        return TargetStatus.INSUFFICIENT_EVIDENCE
    if not primary_kpis_passed:
        return TargetStatus.NOT_ACHIEVED
    if not critical_guardrails_passed or evidence_status is EvidenceStatus.LIMITED:
        return TargetStatus.ACHIEVED_WITH_CONCERNS
    return TargetStatus.ACHIEVED


def classify_next_cycle_action(
    *,
    allocation_metric_passed: bool,
    critical_guardrails_passed: bool,
    delivered_orders: int,
    spend: float,
    evidence_status: EvidenceStatus,
) -> NextCycleAction:
    if evidence_status is EvidenceStatus.DATA_NOT_READY:
        return NextCycleAction.DATA_NOT_READY
    if evidence_status is EvidenceStatus.INSUFFICIENT:
        return NextCycleAction.INSUFFICIENT_EVIDENCE
    if spend > 0 and delivered_orders == 0:
        return NextCycleAction.DO_NOT_FUND
    if allocation_metric_passed and critical_guardrails_passed:
        return (
            NextCycleAction.SCALE
            if evidence_status is EvidenceStatus.READY
            else NextCycleAction.KEEP_AS_TEST
        )
    if allocation_metric_passed or critical_guardrails_passed:
        return NextCycleAction.KEEP_AS_TEST
    return NextCycleAction.DO_NOT_FUND
