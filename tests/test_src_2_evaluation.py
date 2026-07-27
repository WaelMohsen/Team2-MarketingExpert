"""Offline tests for the deterministic narrative evaluator (no LLM calls)."""

import pytest

from src_2.application import run_completed_cycle
from src_2.contracts import CampaignInsight, EvidenceReference, PortfolioInsight, StakeholderReport
from src_2.domain.models import EntityLevel
from src_2.evaluation import NarrativeEvaluator


def _grounded_insight(evidence):
    """A narrative that is faithful to its evidence pack (should pass all checks)."""
    primary = evidence.primary_kpis[0]
    return CampaignInsight(
        campaign_id=evidence.campaign_id,
        target_assessment=f"Primary {primary.label} result is {primary.actual}.",
        supporting_evidence=[
            EvidenceReference(
                entity_level=EntityLevel.CAMPAIGN,
                entity_id=evidence.campaign_id,
                metric=primary.metric,
                actual=primary.actual,
                benchmark=primary.benchmark,
            )
        ],
        strategic_lesson="Judge the objective by its primary KPI.",
        risks_and_confounders=(evidence.limitations or ["Observed sample only."]),
        evidence_status=evidence.evidence_status,
        next_controlled_test="Run a matched test.",
    )


class _GroundedAnalyst:
    def analyze(self, evidence):
        return _grounded_insight(evidence)


class _Synth:
    def synthesize(self, assessments, insights):
        return PortfolioInsight(cycle_id=assessments[0].cycle_id if assessments else "x")


class _Narrator:
    def narrate(self, portfolio, budget):
        return StakeholderReport(cycle_id=portfolio.cycle_id, executive_summary="x")


@pytest.fixture(scope="module")
def grounded_report():
    return run_completed_cycle(
        campaign_analyst=_GroundedAnalyst(),
        portfolio_synthesizer=_Synth(),
        report_narrator=_Narrator(),
    )


def test_grounded_narrative_passes_all_hard_checks(grounded_report):
    result = NarrativeEvaluator(model="test").evaluate(grounded_report)

    assert result.campaigns_evaluated == 12
    assert result.consistency_pass_rate == 1.0
    assert all(ev.consistency_passed for ev in result.campaign_evaluations)
    assert result.prompt_version  # attribution metadata is recorded
    assert result.model == "test"


def test_bad_reference_fails_hard_check(grounded_report):
    evaluator = NarrativeEvaluator(model="test")
    pack = grounded_report.evidence_packs[0]
    assessment = next(a for a in grounded_report.assessments if a.campaign_id == pack.campaign_id)

    bad = _grounded_insight(pack)
    bad.supporting_evidence = [
        EvidenceReference(
            entity_level=EntityLevel.CAMPAIGN,
            entity_id="does-not-exist",
            metric="not_a_metric",
            actual=1.0,
            benchmark=None,
        )
    ]
    from src_2.evaluation.consistency import consistency_passed, run_consistency_checks

    checks = run_consistency_checks(bad, pack, assessment)
    ref_check = next(c for c in checks if c.name == "supporting_evidence_valid")
    assert ref_check.passed is False
    assert consistency_passed(checks) is False


def test_ungrounded_figure_is_warn_not_hard(grounded_report):
    pack = grounded_report.evidence_packs[0]
    assessment = next(a for a in grounded_report.assessments if a.campaign_id == pack.campaign_id)

    insight = _grounded_insight(pack)
    insight.strategic_lesson = "Return on ad spend reached 999.99 this cycle."  # fabricated figure

    from src_2.evaluation.consistency import consistency_passed, run_consistency_checks

    checks = run_consistency_checks(insight, pack, assessment)
    figures = next(c for c in checks if c.name == "figures_grounded")
    assert figures.passed is False
    assert figures.severity == "warn"
    assert consistency_passed(checks) is True  # a warn does not fail the campaign
