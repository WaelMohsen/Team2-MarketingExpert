import copy

import pandas as pd
import pytest

from src_mvp.allocation import _score_weights
from src_mvp.config import load_objectives
from src_mvp.data import load_cycle, load_conversation_signals
from src_mvp.scorecards import build_scorecards
from src_mvp.semantics import add_semantic_scores, build_semantic_evidence, semantic_success
from src_mvp.statistics import score_all_levels


def record():
    return {
        "signals": {
            "conversation_purpose": "purchase",
            "conversation_stage": "checkout",
            "specificity": {"level": "high", "evidence_message_indexes": [0]},
            "purchase_intent": {"level": "high", "evidence_message_indexes": [0]},
            "sales_agreement": {"level": "complete", "evidence_message_indexes": [2]},
            "next_step_agreed": {"agreed": True, "evidence_message_indexes": [2]},
        },
        "ad_message_match": {"level": "aligned", "evidence_message_indexes": [0]},
    }


@pytest.mark.parametrize("metric", ["ad_alignment", "meaningful_conversation", "qualified_conversation", "checkout_readiness"])
def test_rules_preserve_unknown_and_require_evidence(metric):
    assert semantic_success(record(), metric) is True
    assert semantic_success(None, metric) is None
    assert semantic_success({"signals": {}}, metric) is None


def test_explicit_negatives_partial_alignment_and_missing_indexes():
    value = record()
    value["ad_message_match"]["level"] = "partial"
    assert semantic_success(value, "ad_alignment") is False
    assert semantic_success(value, "meaningful_conversation") is True
    value["signals"]["purchase_intent"]["level"] = "low"
    assert semantic_success(value, "qualified_conversation") is False
    value["signals"]["next_step_agreed"]["agreed"] = False
    assert semantic_success(value, "checkout_readiness") is False
    value = record()
    value["signals"]["specificity"]["evidence_message_indexes"] = []
    assert semantic_success(value, "qualified_conversation") is None


def test_semantics_do_not_read_revenue_order_or_delivery():
    value = record()
    before = [semantic_success(value, m) for m in ("qualified_conversation", "checkout_readiness")]
    value.update(revenue=0, outcome="refunded", has_order=False, recommended_action="kill")
    assert before == [semantic_success(value, m) for m in ("qualified_conversation", "checkout_readiness")]


def test_budget_multiplies_primary_probability_and_semantic_lower_bound():
    rows = pd.DataFrame([
        {"campaign_id": "a", "probability_better": .5, "semantic_score": {"range_low": .2}},
        {"campaign_id": "b", "probability_better": .25, "semantic_score": {"range_low": .6}},
    ])
    weights, priorities = _score_weights(rows)
    assert priorities == pytest.approx({"a": .1, "b": .15})
    assert weights == pytest.approx({"a": .4, "b": .6})


def test_budget_weight_omits_campaign_with_a_missing_component():
    rows = pd.DataFrame([
        {"campaign_id": "a", "probability_better": .5, "semantic_score": {"range_low": .2}},
        {"campaign_id": "b", "probability_better": None, "semantic_score": {"range_low": .6}},
    ])
    weights, priorities = _score_weights(rows)
    assert priorities == {"a": pytest.approx(.1)}
    assert weights == {"a": pytest.approx(1.0)}


@pytest.fixture(scope="module")
def semantic_result():
    data = load_cycle()
    records = load_conversation_signals()
    registry = load_objectives()
    primary = score_all_levels(build_scorecards(data, records), registry)
    scored, audit = add_semantic_scores(primary, data, records, registry)
    return data, records, registry, primary, scored, audit


def test_all_levels_have_auditable_counts_and_primary_scores_are_unchanged(semantic_result):
    _, _, _, primary, scored, audit = semantic_result
    for level, frame in scored.items():
        pd.testing.assert_frame_equal(primary[level], frame.drop(columns="semantic_score"))
        for _, row in frame.iterrows():
            s = row["semantic_score"]
            evidence = audit[audit.entity_level.eq(level) & audit.entity_id.eq(row.entity_id) & audit.selected]
            assert s["eligible_customers"] == len(evidence)
            assert s["trials"] + s["unknown_customers"] + s["missing_customers"] == len(evidence)
            assert s["successes"] == evidence.success.dropna().sum()
            if s["trials"]:
                assert s["corrected_rate"] == pytest.approx(
                    s["posterior_alpha"] / (s["posterior_alpha"] + s["posterior_beta"])
                )
                assert 0 <= s["range_low"] <= s["range_high"] <= 1
            if s["prior_source"] == "jeffreys_no_peer_comparison":
                assert s["prior_alpha"] == s["prior_beta"] == .5
                assert s["probability_better"] is None
                assert s["benchmark"] is None


def test_selection_precedes_labels_and_excludes_unresolved_and_repeats(semantic_result):
    data, records, registry, _, _, audit = semantic_result
    joined = audit.merge(data.conversations[["conversation_id", "customer_key", "is_mature"]], on="conversation_id")
    selected = joined[joined.selected]
    assert selected.is_mature.all()
    assert not selected.duplicated(["entity_level", "entity_id", "customer_key"]).any()
    without = build_semantic_evidence(data, [], registry)
    assert audit.selected.tolist() == without.selected.tolist()
    assert without.success.isna().all()
    with pytest.raises(ValueError, match="Duplicate semantic"):
        build_semantic_evidence(data, records + [copy.deepcopy(records[0])], registry)


def test_no_semantics_returns_no_quality_evidence(semantic_result):
    data, _, registry, primary, _, _ = semantic_result
    scored, _ = add_semantic_scores(primary, data, [], registry)
    for frame in scored.values():
        assert all(s["trials"] == 0 and s["corrected_rate"] is None for s in frame.semantic_score)


def test_real_peer_prior_excludes_the_scored_entity(semantic_result):
    _, _, _, _, scored, _ = semantic_result
    leads = scored["campaign"].query("objective == 'OUTCOME_LEADS'")
    for _, row in leads.iterrows():
        peers = leads[leads.entity_id.ne(row.entity_id)].semantic_score
        expected = (sum(s["successes"] for s in peers) + .5) / (sum(s["trials"] for s in peers) + 1)
        assert row.semantic_score["benchmark"] == pytest.approx(expected)
