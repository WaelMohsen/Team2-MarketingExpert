"""Tests for the CampaignAssessor / BudgetAllocator decision ports (offline)."""

from src_2.analytics import (
    DeterministicCampaignAssessor,
    build_evidence_packs,
    build_scorecards,
)
from src_2.application import run_completed_cycle
from src_2.contracts import (
    BudgetScenario,
    CampaignAssessment,
    CampaignInsight,
    PortfolioInsight,
    StakeholderReport,
)
from src_2.domain.assessment_rules import NextCycleAction, TargetStatus
from src_2.infrastructure.configuration import load_campaign_type_registry
from src_2.ingestion import (
    build_data_quality_report,
    load_sample2,
    normalize_cycle,
)


# --- offline narrative stubs so nothing hits the LLM ---
class _Analyst:
    def analyze(self, e):
        return CampaignInsight(
            campaign_id=e.campaign_id, target_assessment="x",
            supporting_evidence=[], strategic_lesson="x",
            evidence_status=e.evidence_status,
        )


class _Synth:
    def synthesize(self, a, i):
        return PortfolioInsight(cycle_id=a[0].cycle_id if a else "x")


class _Narr:
    def narrate(self, p, b):
        return StakeholderReport(cycle_id=p.cycle_id, executive_summary="x")


def _packs_and_registry():
    canonical = normalize_cycle(load_sample2())
    quality = build_data_quality_report(canonical)
    registry = load_campaign_type_registry()
    cycle_id = f"cycle_{canonical.cycle_start.date()}_{canonical.cycle_end.date()}"
    packs = build_evidence_packs(cycle_id, build_scorecards(canonical), registry, quality)
    return packs, registry


def test_evidence_pack_carries_allocation_kpi():
    packs, registry = _packs_and_registry()
    assert packs
    for p in packs:
        assert p.allocation_kpi is not None
        assert p.allocation_kpi.metric == registry.campaign_types[p.campaign_type].allocation_metric.metric


def test_assessor_reproduces_full_portfolio_from_pack_and_config():
    # With allocation_kpi on the pack, assess(pack, config) closes the notebook
    # prototype's one gap: the seasonal campaign now decides correctly from the pack.
    packs, registry = _packs_and_registry()
    assessor = DeterministicCampaignAssessor()
    by_name = {
        p.campaign_name: assessor.assess(p, registry.campaign_types[p.campaign_type])
        for p in packs
    }
    assert by_name["Eid Gifting Premium"].next_cycle_action is NextCycleAction.KEEP_AS_TEST
    assert by_name["Always-On Premium Acquisition"].next_cycle_action is NextCycleAction.DO_NOT_FUND
    assert all(isinstance(a.next_cycle_action, NextCycleAction) for a in by_name.values())


def test_run_completed_cycle_uses_injected_decision_ports():
    captured = {"assess_calls": 0}

    class FakeAssessor:
        def assess(self, evidence, config):
            captured["assess_calls"] += 1
            return CampaignAssessment(
                cycle_id=evidence.cycle_id, campaign_id=evidence.campaign_id,
                campaign_name=evidence.campaign_name, campaign_type=evidence.campaign_type,
                target_status=TargetStatus.NOT_ACHIEVED,
                next_cycle_action=NextCycleAction.DO_NOT_FUND,
                evidence_status=evidence.evidence_status,
                primary_results=[], guardrail_results=[],
            )

    class FakeAllocator:
        def allocate(self, cycle_id, campaign_scorecard, assessments, registry, policy, quality):
            captured["alloc_actions"] = {a.next_cycle_action.value for a in assessments}
            return BudgetScenario(
                cycle_id=cycle_id, scenario_name="fake", total_budget_units=100,
                evidence_status=quality.status, operational=False,
                assumptions=[], allocations=[], unallocated_units=100,
            )

    report = run_completed_cycle(
        campaign_assessor=FakeAssessor(), budget_allocator=FakeAllocator(),
        campaign_analyst=_Analyst(), portfolio_synthesizer=_Synth(), report_narrator=_Narr(),
    )

    assert captured["assess_calls"] == 12                       # assessor port invoked per campaign
    assert all(a.next_cycle_action is NextCycleAction.DO_NOT_FUND for a in report.assessments)
    assert captured["alloc_actions"] == {"do_not_fund"}          # allocator received the assessments
    assert report.budget_scenario.scenario_name == "fake"        # allocator port output used
