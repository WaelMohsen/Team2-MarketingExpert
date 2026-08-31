import json

import pytest
from openai.lib._pydantic import to_strict_json_schema

from src_2.analytics import build_scorecards
from src_2.application import (
    extract_conversation_signals,
    load_conversation_signal_records,
)
from src_2.contracts import (
    AdMessageMatchLevel,
    AdMessageMatchSignal,
    AgentEvaluation,
    AgentRating,
    BarrierSignal,
    BarrierType,
    ConversationAttribution,
    ConversationPurpose,
    ConversationSignalRecord,
    ConversationSignals,
    ConversationStage,
    PriceSensitivityLevel,
    PriceSensitivitySignal,
    PurchaseIntentLevel,
    PurchaseIntentSignal,
    UrgencyLevel,
    UrgencySignal,
)
from src_2.ingestion import load_sample2, normalize_cycle
from src_2.intelligence import build_semantic_input


def _signals() -> ConversationSignals:
    return ConversationSignals(
        conversation_purpose=ConversationPurpose.PURCHASE,
        customer_need="A product suitable for a time-sensitive occasion.",
        purchase_intent=PurchaseIntentSignal(
            level=PurchaseIntentLevel.HIGH,
            elicited_by_agent=False,
            evidence_message_indexes=[0],
        ),
        barriers=[
            BarrierSignal(
                barrier_type=BarrierType.PRICE,
                description="The customer questioned the price.",
                evidence_message_indexes=[0],
            )
        ],
        mentioned_products=[],
        conversation_stage=ConversationStage.CONSIDERATION,
        agent_evaluation=AgentEvaluation(
            helpfulness=AgentRating.GOOD,
            needs_discovery=AgentRating.ADEQUATE,
            objection_handling=AgentRating.GOOD,
            progression=AgentRating.GOOD,
            tone=AgentRating.STRONG,
            evidence_message_indexes=[1],
        ),
        conversation_summary="Customer considered a product and raised a price concern.",
        not_assessable_reasons=[],
    )


class _FakeExtractor:
    prompt_version = "test-v1"
    prompt_sha256 = "a" * 64
    model = "test-model"

    def extract(self, model_input):
        assert "outcome" not in model_input.model_dump_json()
        return _signals()


class _FakeAdMatchEvaluator:
    prompt_version = "ad-match-test-v1"
    prompt_sha256 = "c" * 64
    model = "test-model"

    def evaluate(self, ad_context, signals):
        assert ad_context.message
        assert signals.customer_need
        assert "outcome" not in ad_context.model_dump_json()
        return AdMessageMatchSignal(
            level=AdMessageMatchLevel.ALIGNED,
            rationale="The validated need matches the stated ad promise.",
            evidence_message_indexes=[0],
        )


def test_semantic_input_excludes_customer_source_and_outcome_data():
    raw = load_sample2().conversations[0]
    model_input = build_semantic_input(raw)
    serialized = model_input.model_dump_json()

    assert set(model_input.model_dump()) == {"language", "messages"}
    assert raw["customer"]["first_name"] not in serialized
    assert raw["customer"]["phone"] not in serialized
    assert raw["source"]["ctwa_clid"] not in serialized
    assert raw["outcome"]["order_id"] not in serialized
    assert "REDACTED" in serialized


def test_conversation_signal_schema_is_closed_for_structured_outputs():
    schema = to_strict_json_schema(ConversationSignals)

    def assert_closed(value):
        if isinstance(value, dict):
            if value.get("type") == "object":
                assert value.get("additionalProperties") is False
                assert set(value.get("required", [])) == set(
                    value.get("properties", {})
                )
            for child in value.values():
                assert_closed(child)
        elif isinstance(value, list):
            for child in value:
                assert_closed(child)

    assert_closed(schema)


def test_signal_records_aggregate_to_the_attributed_campaign():
    canonical = normalize_cycle(load_sample2())
    row = canonical.conversations.iloc[0]
    record = ConversationSignalRecord(
        conversation_id=row["conversation_id"],
        attribution=ConversationAttribution(
            source_platform=row["source_platform"],
            campaign_id=row["campaign_id"],
            adset_id=row["adset_id"],
            ad_id=row["ad_id"],
            creative_id=row["creative_id"],
            audience_type=row["audience_type"],
        ),
        prompt_version="test-v1",
        prompt_sha256="a" * 64,
        model="test-model",
        extracted_at="2026-08-30T00:00:00Z",
        signals=_signals(),
    )
    scorecards = build_scorecards(canonical, [record])
    campaign = scorecards.campaign.loc[
        scorecards.campaign["campaign_id"].eq(row["campaign_id"])
    ].iloc[0]

    assert campaign["semantic_conversations"] == 1
    assert campaign["high_purchase_intent_rate"] == 1
    assert campaign["top_barrier"] == "price"


def test_v2_high_value_signals_aggregate_as_diagnostic_rates():
    canonical = normalize_cycle(load_sample2())
    row = canonical.conversations.iloc[0]
    signals = _signals().model_copy(
        update={
            "urgency": UrgencySignal(
                level=UrgencyLevel.HIGH, evidence_message_indexes=[0]
            ),
            "price_sensitivity": PriceSensitivitySignal(
                level=PriceSensitivityLevel.BLOCKING,
                evidence_message_indexes=[0],
            ),
        }
    )
    record = ConversationSignalRecord(
        conversation_id=row["conversation_id"],
        attribution=ConversationAttribution(
            source_platform=row["source_platform"],
            campaign_id=row["campaign_id"],
            adset_id=row["adset_id"],
            ad_id=row["ad_id"],
            creative_id=row["creative_id"],
            audience_type=row["audience_type"],
        ),
        prompt_version="test-v2",
        prompt_sha256="b" * 64,
        model="test-model",
        extracted_at="2026-08-30T00:00:00Z",
        signals=signals,
        signal_schema_version=2,
        ad_message_match=AdMessageMatchSignal(
            level=AdMessageMatchLevel.ALIGNED,
            rationale="The customer need matches the ad promise.",
            evidence_message_indexes=[0],
        ),
    )
    campaign = build_scorecards(canonical, [record]).campaign.loc[
        lambda frame: frame["campaign_id"].eq(row["campaign_id"])
    ].iloc[0]

    assert campaign["high_urgency_rate"] == 1
    assert campaign["price_blocking_rate"] == 1
    assert campaign["ad_message_alignment_rate"] == 1
    assert campaign["semantic_coverage_rate"] == pytest.approx(
        1 / campaign["observed_conversations"]
    )


def test_extraction_checkpoints_joinable_records_and_resumes(tmp_path):
    output = tmp_path / "signals.jsonl"
    first = extract_conversation_signals(
        output_path=output,
        limit=3,
        campaign_name="Post-Eid Lookalike Test",
        extractor=_FakeExtractor(),
    )
    second = extract_conversation_signals(
        output_path=output,
        limit=3,
        campaign_name="Post-Eid Lookalike Test",
        extractor=_FakeExtractor(),
    )
    records = load_conversation_signal_records(output)
    serialized = output.read_text(encoding="utf-8")

    assert first.extracted == 3
    assert first.failed == 0
    assert second.extracted == 0
    assert second.skipped == 3
    assert len(records) == 3
    assert all(record.conversation_id for record in records)
    assert all(record.attribution.source_platform for record in records)
    assert {
        record.attribution.campaign_id for record in records
    } == {"120209876543220008"}
    assert "first_name" not in serialized
    assert "phone" not in serialized
    assert "message_text" not in serialized


def test_ad_message_match_is_a_separate_versioned_evaluation(tmp_path):
    output = tmp_path / "signals-with-match.jsonl"
    summary = extract_conversation_signals(
        output_path=output,
        limit=1,
        campaign_name="Post-Eid Lookalike Test",
        extractor=_FakeExtractor(),
        ad_match_evaluator=_FakeAdMatchEvaluator(),
    )
    record = load_conversation_signal_records(output)[0]

    assert summary.extracted == 1
    assert record.ad_message_match.level is AdMessageMatchLevel.ALIGNED
    assert record.ad_match_prompt_version == "ad-match-test-v1"
    assert record.ad_match_prompt_sha256 == "c" * 64
