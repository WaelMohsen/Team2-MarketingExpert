import json
from collections import Counter
from pathlib import Path

import nbformat
import pandas as pd
import pytest

from src_mvp.config import load_objectives
from src_mvp.contracts import EntityScore, RecommendationInput
from src_mvp.pipeline import run_mvp
from src_mvp.presentation.streamlit_app import _budget_plan
from src_mvp.statistics import score_level


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    return run_mvp(output_directory=tmp_path_factory.mktemp("src_mvp"))


def test_mvp_loads_only_paid_attributed_conversations(result):
    assert len(result.data.conversations) == 617
    assert result.data.conversations["campaign_id"].notna().all()


def test_objective_registry_contains_only_four_objective_contracts():
    registry = load_objectives()
    assert set(registry.objectives) == {
        "OUTCOME_AWARENESS",
        "OUTCOME_ENGAGEMENT",
        "OUTCOME_LEADS",
        "OUTCOME_SALES",
    }
    assert registry.objectives["OUTCOME_LEADS"].primary_metric == "order_creation_rate"
    assert registry.objectives["OUTCOME_SALES"].efficiency_metric == "net_roas"


def test_five_scorecard_levels_have_expected_real_entity_counts(result):
    assert {level: len(frame) for level, frame in result.scorecards.items()} == {
        "campaign": 12,
        "adset": 26,
        "ad": 40,
        "creative": 31,
        "audience": 22,
    }


def test_post_eid_uses_mature_lead_outcomes_and_empirical_bayes(result):
    campaigns = result.scorecards["campaign"]
    row = campaigns[campaigns["campaign_name"].eq("Post-Eid Lookalike Test")].iloc[0]
    assert row["score_metric"] == "order_creation_rate"
    assert row["score_successes"] == 38
    assert row["score_trials"] == 52
    assert row["raw_rate"] == pytest.approx(38 / 52)
    assert row["corrected_rate"] == pytest.approx(0.738950276243094)
    assert row["benchmark_peer_count"] == 2
    assert row["statistical_decision"] == "hold"
    assert 0 <= row["probability_better"] <= 1


def test_upper_funnel_campaigns_use_provisional_shared_link_ctr_fallback(result):
    campaigns = result.scorecards["campaign"]
    upper_funnel = campaigns[
        campaigns["objective"].isin(["OUTCOME_AWARENESS", "OUTCOME_ENGAGEMENT"])
    ]
    assert set(upper_funnel["same_objective_peer_count"]) == {0, 1}
    assert set(upper_funnel["benchmark_peer_count"]) == {2}
    assert set(upper_funnel["benchmark_scope"]) == {"shared_primary_kpi_group"}
    assert set(upper_funnel["benchmark_quality"]) == {"provisional"}
    assert upper_funnel["corrected_rate"].notna().all()
    assert upper_funnel["range_low"].notna().all()
    assert upper_funnel["range_high"].notna().all()
    assert set(upper_funnel["recommended_action"]) == {"keep_as_test"}
    assert all(
        "FALLBACK_ACTION_CAPPED_AT_TEST" in reasons
        for reasons in upper_funnel["reason_codes"]
    )


def test_provisional_fallback_caps_a_statistical_scale_at_keep_as_test():
    frame = pd.DataFrame(
        [
            {
                "entity_id": "awareness_target",
                "objective": "OUTCOME_AWARENESS",
                "link_clicks": 900,
                "impressions": 1000,
                "cpm": 5.0,
                "cpc": 0.01,
            },
            {
                "entity_id": "awareness_peer",
                "objective": "OUTCOME_AWARENESS",
                "link_clicks": 100,
                "impressions": 1000,
                "cpm": 6.0,
                "cpc": 0.06,
            },
            {
                "entity_id": "engagement_peer",
                "objective": "OUTCOME_ENGAGEMENT",
                "link_clicks": 100,
                "impressions": 1000,
                "cpm": 6.0,
                "cpc": 0.06,
            },
        ]
    )
    scored = score_level(frame, "campaign", load_objectives())
    target = scored[scored["entity_id"].eq("awareness_target")].iloc[0]
    assert target["benchmark_quality"] == "provisional"
    assert target["statistical_decision"] == "scale"
    assert target["recommended_action"] == "keep_as_test"
    assert "FALLBACK_ACTION_CAPPED_AT_TEST" in target["reason_codes"]


def test_budget_balances_and_only_campaigns_receive_it(result):
    allocated = sum(item.recommended_budget_units for item in result.allocations)
    unallocated = result.recommendation_input.unallocated_budget_units
    assert allocated + unallocated == pytest.approx(100.0)
    assert len(result.allocations) == 12
    assert all(item.campaign_id for item in result.allocations)
    assert allocated == pytest.approx(100.0)
    assert unallocated == pytest.approx(0.0)
    assert all(item.recommended_budget_units > 0 for item in result.allocations)


def test_streamlit_budget_view_uses_the_pipeline_allocation(result):
    plan = _budget_plan(result)
    assert set(plan["Objective"]) == {"Awareness", "Engagement", "Leads", "Sales"}
    assert plan["Objective envelope"].sum() == pytest.approx(100.0)
    assert plan["Score-based allocation"].sum() == pytest.approx(
        sum(item.recommended_budget_units for item in result.allocations)
    )
    assert plan["Unallocated"].sum() == pytest.approx(
        result.recommendation_input.unallocated_budget_units
    )


def test_compact_packet_is_valid_and_has_no_campaign_type(result):
    payload = result.recommendation_input.model_dump(mode="json")
    validated = RecommendationInput.model_validate(payload)
    assert validated.data_scope.outcome_data_assumption == "complete_for_cycle"
    assert validated.data_scope.paid_attributed_conversations == 617
    assert '"campaign_type"' not in json.dumps(payload)


def test_written_entity_artifact_contains_all_levels(result):
    path = result.output_directory / "entity_scorecards.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line]
    assert all(EntityScore.model_validate(row) for row in rows)
    assert len(rows) == 131
    assert Counter(row["entity_level"] for row in rows) == {
        "campaign": 12,
        "adset": 26,
        "ad": 40,
        "creative": 31,
        "audience": 22,
    }


def test_recommendation_packet_excludes_row_level_private_data(result):
    payload = result.recommendation_input.model_dump(mode="json")
    forbidden = {
        "customer_id",
        "customer_key",
        "conversation_id",
        "messages",
        "redacted_text",
        "order_id",
        "phone",
        "email",
        "address",
    }

    def keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from keys(child)

    assert forbidden.isdisjoint(set(keys(payload)))


def test_all_objective_notebooks_are_executed_without_errors():
    notebook_directory = Path(__file__).parents[1] / "src_mvp" / "notebooks"
    notebooks = sorted(notebook_directory.glob("*_OUTCOME_*_Analysis.ipynb"))
    assert len(notebooks) == 4
    assert {nbformat.read(path, as_version=4).metadata["mvp_objective"] for path in notebooks} == {
        "OUTCOME_AWARENESS",
        "OUTCOME_ENGAGEMENT",
        "OUTCOME_LEADS",
        "OUTCOME_SALES",
    }
    for path in notebooks:
        notebook = nbformat.read(path, as_version=4)
        code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
        assert code_cells
        assert all(cell.execution_count is not None for cell in code_cells)
        assert not [
            output
            for cell in code_cells
            for output in cell.get("outputs", [])
            if output.output_type == "error"
        ]
