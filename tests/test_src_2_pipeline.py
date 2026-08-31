import json

import pytest
from openai.lib._pydantic import to_strict_json_schema

from src_2.application import run_completed_cycle
from src_2.contracts import CampaignInsight, PortfolioInsight, StakeholderReport
from src_2.domain.models import EvidenceStatus
from src_2.presentation import streamlit_app


class _FakeAnalyst:
    """Offline narrative port so deterministic-layer tests need no OpenAI key."""

    def analyze(self, evidence):
        return CampaignInsight(
            campaign_id=evidence.campaign_id,
            target_assessment="stub",
            supporting_evidence=[],
            strategic_lesson="stub",
            evidence_status=evidence.evidence_status,
        )


class _FakeSynthesizer:
    def synthesize(self, assessments, insights):
        cycle_id = assessments[0].cycle_id if assessments else "stub-cycle"
        return PortfolioInsight(cycle_id=cycle_id)


class _FakeNarrator:
    def narrate(self, portfolio, budget):
        return StakeholderReport(cycle_id=portfolio.cycle_id, executive_summary="stub")


@pytest.fixture(scope="module")
def report():
    # Inject stub narrative ports; the assertions below exercise the deterministic
    # measurement and decision layers, which run without any LLM call.
    return run_completed_cycle(
        campaign_analyst=_FakeAnalyst(),
        portfolio_synthesizer=_FakeSynthesizer(),
        report_narrator=_FakeNarrator(),
    )


def test_canonical_facts_match_sample2_inventory(report):
    data = report.canonical_data

    assert len(data.campaigns) == 12
    assert len(data.adsets) == 26
    assert len(data.ads) == 40
    assert len(data.creatives) == 30
    assert len(data.media_daily) == 1243
    assert len(data.conversations) == 788


def test_aggregations_do_not_duplicate_spend_or_outcomes(report):
    expected = (402_274.64, 617, 457_574.0)

    for level in ("campaign", "adset", "ad", "creative", "audience"):
        scorecard = report.scorecards.by_level(level)
        assert float(scorecard["spend"].sum()) == pytest.approx(expected[0])
        assert int(scorecard["observed_conversations"].sum()) == expected[1]
        assert float(scorecard["net_revenue"].sum()) == pytest.approx(expected[2])


def test_data_quality_preserves_reconciliation_warning(report):
    quality = report.data_quality

    assert quality.status is EvidenceStatus.LIMITED
    assert quality.meta_conversation_starts == 116_098
    assert quality.observed_meta_whatsapp_conversations == 617
    assert quality.reconciliation_ratio == pytest.approx(617 / 116_098)
    assert quality.unmatched_campaigns == 0
    assert quality.unmatched_adsets == 0
    assert quality.unmatched_ads == 0
    assert quality.event_definitions_reconciled is False
    assert quality.open_or_pending_conversations == 61
    assert quality.repeated_customers == 123
    assert quality.organic_direct_conversations == 171
    assert quality.reach_exceeds_impressions_rows == 118
    assert quality.daily_reach_is_non_additive is True


def test_mature_and_customer_level_rates_do_not_count_unresolved_as_failures(report):
    campaigns = report.scorecards.campaign

    assert (
        campaigns["mature_conversations"]
        == campaigns["observed_conversations"]
        - campaigns["open_or_pending_conversations"]
    ).all()
    assert (
        campaigns["customer_delivered_rate_ci_low"]
        <= campaigns["customer_delivered_rate"]
    ).all()
    assert (
        campaigns["customer_delivered_rate"]
        <= campaigns["customer_delivered_rate_ci_high"]
    ).all()


def test_awareness_reach_is_not_scored_from_invalid_non_additive_daily_rows(report):
    awareness = next(
        item for item in report.assessments if item.campaign_type.value == "awareness"
    )

    assert awareness.evidence_status is EvidenceStatus.DATA_NOT_READY
    assert awareness.next_cycle_action.value == "data_not_ready"


def test_decisions_use_campaign_type_primary_kpis(report):
    eid = next(
        item for item in report.assessments if item.campaign_name == "Eid Gifting Premium"
    )
    always_on = next(
        item
        for item in report.assessments
        if item.campaign_name == "Always-On Premium Acquisition"
    )

    assert eid.primary_results[0].metric == "net_revenue_per_day"
    assert eid.primary_results[0].passed is True
    assert eid.next_cycle_action.value == "keep_as_test"
    assert always_on.primary_results[0].metric == "net_roas"
    assert always_on.next_cycle_action.value == "keep_as_test"
    always_on_row = report.scorecards.campaign.loc[
        report.scorecards.campaign["campaign_name"].eq(
            "Always-On Premium Acquisition"
        )
    ].iloc[0]
    assert always_on_row["raw_score"] != pytest.approx(always_on_row["corrected_score"])
    assert always_on_row["lift_low"] < 0 < always_on_row["lift_high"]
    assert always_on_row["funding_decision"] == "hold"


def test_budget_scenario_uses_the_agreed_70_30_split(report):
    scenario = report.budget_scenario
    campaigns = report.scorecards.campaign
    experimental_ids = set(
        campaigns.loc[
            campaigns["campaign_type"].eq("experimental"), "campaign_id"
        ]
    )
    assert scenario.operational is False
    assert sum(item.budget_units for item in scenario.allocations) == pytest.approx(30)
    assert scenario.unallocated_units == pytest.approx(70)
    assert any("Exploit is fixed at 70%" in item for item in scenario.assumptions)
    assert any("Explore is fixed at 30%" in item for item in scenario.assumptions)
    assert sum(item.budget_units for item in scenario.allocations) + scenario.unallocated_units == pytest.approx(
        scenario.total_budget_units
    )
    assert all(
        item.budget_units == 0
        for item in scenario.allocations
        if item.action.value == "do_not_fund"
    )
    assert len(scenario.exploration_tests) == sum(
        item.budget_units > 0 for item in scenario.allocations
    )
    assert all(test.hypothesis and test.stop_rule for test in scenario.exploration_tests)
    assert sum(
        test.assigned_budget_units for test in scenario.exploration_tests
    ) == pytest.approx(30)


def test_export_is_structured_and_excludes_raw_customer_fields(report):
    payload = report.to_export_dict()
    serialized = json.dumps(payload)

    assert len(payload["scorecards"]["campaign"]) == 12
    assert "first_name" not in serialized
    assert "last_name" not in serialized
    assert "phone" not in serialized
    assert "message_text" not in serialized


def test_streamlit_llm_mode_injects_all_prompt_adapters(monkeypatch):
    captured = {}
    expected_report = object()

    class FakeAdapter:
        def __init__(self, name, model):
            self.name = name
            self.model = model

    monkeypatch.setattr(
        streamlit_app,
        "OpenAICampaignAnalyst",
        lambda model: FakeAdapter("campaign", model),
    )
    monkeypatch.setattr(
        streamlit_app,
        "OpenAIPortfolioSynthesizer",
        lambda model: FakeAdapter("portfolio", model),
    )
    monkeypatch.setattr(
        streamlit_app,
        "OpenAIReportNarrator",
        lambda model: FakeAdapter("report", model),
    )

    def fake_run_completed_cycle(input_directory, **kwargs):
        captured["input_directory"] = input_directory
        captured.update(kwargs)
        return expected_report

    monkeypatch.setattr(
        streamlit_app, "run_completed_cycle", fake_run_completed_cycle
    )

    actual_report = streamlit_app._load_report.__wrapped__(
        "sample-directory", "test-model"
    )

    assert actual_report is expected_report
    assert captured["input_directory"] == "sample-directory"
    assert captured["campaign_analyst"].name == "campaign"
    assert captured["portfolio_synthesizer"].name == "portfolio"
    assert captured["report_narrator"].name == "report"
    assert {
        captured["campaign_analyst"].model,
        captured["portfolio_synthesizer"].model,
        captured["report_narrator"].model,
    } == {"test-model"}


def test_llm_output_contracts_use_closed_openai_schemas():
    def assert_closed_objects(schema):
        if isinstance(schema, dict):
            if schema.get("type") == "object":
                properties = schema.get("properties", {})
                assert schema.get("additionalProperties") is False
                assert set(schema.get("required", [])) == set(properties)
            for value in schema.values():
                assert_closed_objects(value)
        elif isinstance(schema, list):
            for value in schema:
                assert_closed_objects(value)

    for output_model in (CampaignInsight, PortfolioInsight, StakeholderReport):
        assert_closed_objects(to_strict_json_schema(output_model))

    lessons_schema = to_strict_json_schema(PortfolioInsight)["properties"][
        "campaign_type_lessons"
    ]
    assert lessons_schema["type"] == "array"
