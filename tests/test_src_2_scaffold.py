import json

import pytest

from src_2.analytics import calculate_core_kpis
from src_2.domain.assessment_rules import (
    NextCycleAction,
    TargetStatus,
    classify_next_cycle_action,
    classify_target,
)
from src_2.domain.models import CampaignType, EvidenceStatus
from src_2.infrastructure.configuration import (
    load_budget_policy,
    load_campaign_type_registry,
)
from src_2.ingestion import load_sample2
from src_2.ingestion.data_quality import inventory
from src_2.paths import INPUT_DIR, PROMPT_DIR, V2_ROOT


def test_sample2_input_is_self_contained():
    payload = load_sample2()
    source_inventory = inventory(payload)

    assert payload.source_directory == INPUT_DIR.resolve()
    assert source_inventory.campaigns == 12
    assert source_inventory.adsets == 26
    assert source_inventory.ads == 40
    assert source_inventory.creatives == 30
    assert source_inventory.insights > 0
    assert source_inventory.conversations == 788
    assert source_inventory.products > 0


def test_campaign_type_lookup_is_complete_and_unweighted():
    registry = load_campaign_type_registry()

    assert set(registry.campaign_types) == set(CampaignType)
    assert registry.campaign_types[CampaignType.SEASONAL].primary_kpis == [
        "net_revenue_per_day"
    ]
    assert not hasattr(
        registry.campaign_types[CampaignType.SEASONAL], "primary_kpi_weights"
    )
    assert registry.campaign_types[CampaignType.EXPERIMENTAL].budget_pool.value == "test"


def test_poc_budget_policy_has_historical_test_envelope_and_no_cap():
    policy = load_budget_policy()

    assert policy.budget_units == 100
    assert policy.test_envelope.campaign_type is CampaignType.EXPERIMENTAL
    assert policy.maximum_campaign_concentration is None
    assert policy.allow_unallocated_budget is True


def test_core_kpis_are_recomputed_from_totals():
    metrics = calculate_core_kpis(
        {
            "impressions": 10_000,
            "link_clicks": 200,
            "spend": 1_000,
            "observed_conversations": 20,
            "delivered_orders": 10,
            "delivered_revenue": 3_000,
            "net_revenue": 2_500,
            "negative_outcomes": 4,
        }
    )

    assert metrics["link_ctr_pct"] == pytest.approx(2.0)
    assert metrics["cpm"] == pytest.approx(100.0)
    assert metrics["net_roas"] == pytest.approx(2.5)
    assert metrics["aov"] == pytest.approx(300.0)
    assert metrics["delivered_rate_pct"] == pytest.approx(50.0)


def test_limited_evidence_downgrades_scale_to_test():
    target = classify_target(
        primary_kpis_passed=True,
        critical_guardrails_passed=True,
        evidence_status=EvidenceStatus.LIMITED,
    )
    action = classify_next_cycle_action(
        allocation_metric_passed=True,
        critical_guardrails_passed=True,
        delivered_orders=10,
        spend=1_000,
        evidence_status=EvidenceStatus.LIMITED,
    )

    assert target is TargetStatus.ACHIEVED_WITH_CONCERNS
    assert action is NextCycleAction.KEEP_AS_TEST


def test_prompts_and_json_schemas_are_present_and_parseable():
    prompt_names = {
        "campaign_analysis.md",
        "portfolio_synthesis.md",
        "recommendation_narrator.md",
    }
    assert prompt_names.issubset({path.name for path in PROMPT_DIR.glob("*.md")})

    for path in (V2_ROOT / "schemas").glob("*.schema.json"):
        assert json.loads(path.read_text(encoding="utf-8"))["type"] == "object"
