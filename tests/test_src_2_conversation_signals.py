import json
from types import SimpleNamespace

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
    AgentToneLabel,
    AgentToneQuality,
    AgentToneSignal,
    BarrierResolution,
    BarrierSignal,
    BarrierType,
    CommercialTrait,
    CommercialTraitSignal,
    CommercialTraitStrength,
    ConversationAttribution,
    ConversationPurpose,
    ConversationSignalRecord,
    ConversationSignals,
    ConversationStage,
    DeliveryIntentSignal,
    FinancingLevel,
    FinancingSignal,
    LLMTokenUsage,
    NextStepAgreementSignal,
    PriceSensitivityLevel,
    PriceSensitivitySignal,
    PurchaseIntentLevel,
    PurchaseIntentSignal,
    SpecificityLevel,
    SpecificitySignal,
    UrgencyLevel,
    UrgencySignal,
)
from src_2.ingestion import load_sample2, normalize_cycle
from src_2.intelligence import (
    OpenAIConversationSignalExtractor,
    build_semantic_input,
    merge_token_usage,
    response_token_usage,
    validate_evidence_message_indexes,
    validate_semantic_evidence_rules,
)


def _signals(customer_index=0, agent_index=1) -> ConversationSignals:
    customer_evidence = [] if customer_index is None else [customer_index]
    agent_evidence = [] if agent_index is None else [agent_index]
    agent_rating = (
        AgentRating.NOT_ASSESSABLE if agent_index is None else AgentRating.GOOD
    )
    return ConversationSignals(
        conversation_purpose=ConversationPurpose.PURCHASE,
        customer_need="A product suitable for a time-sensitive occasion.",
        purchase_intent=PurchaseIntentSignal(
            level=(
                PurchaseIntentLevel.UNKNOWN
                if customer_index is None
                else PurchaseIntentLevel.HIGH
            ),
            elicited_by_agent=False,
            evidence_message_indexes=customer_evidence,
        ),
        barriers=(
            []
            if customer_index is None
            else [
                BarrierSignal(
                    barrier_type=BarrierType.PRICE,
                    description="The customer questioned the price.",
                    evidence_message_indexes=customer_evidence,
                )
            ]
        ),
        mentioned_products=[],
        conversation_stage=ConversationStage.CONSIDERATION,
        agent_evaluation=AgentEvaluation(
            helpfulness=agent_rating,
            needs_discovery=agent_rating,
            objection_handling=agent_rating,
            progression=agent_rating,
            tone=agent_rating,
            evidence_message_indexes=agent_evidence,
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
        customer_index = next(
            (
                message.message_index
                for message in model_input.messages
                if message.role.value == "customer"
            ),
            None,
        )
        agent_index = next(
            (
                message.message_index
                for message in model_input.messages
                if message.role.value == "agent"
            ),
            None,
        )
        return _signals(customer_index, agent_index)


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


def test_evidence_indexes_must_exist_in_the_redacted_model_input():
    signals = _signals().model_copy(
        update={
            "purchase_intent": PurchaseIntentSignal(
                level=PurchaseIntentLevel.HIGH,
                elicited_by_agent=False,
                evidence_message_indexes=[99],
            )
        }
    )

    with pytest.raises(ValueError, match="99"):
        validate_evidence_message_indexes(
            signals, {0, 1}, context="Test conversation signals"
        )


def test_redaction_does_not_replace_names_inside_product_words_and_hides_greetings():
    conversation = {
        "started_at": "2026-01-01T00:00:00Z",
        "language": "mixed",
        "customer": {
            "first_name": "Lola",
            "last_name": "Test",
            "phone": "+201234567890",
        },
        "messages": [
            {
                "direction": "outbound",
                "sent_at": "2026-01-01T00:00:00Z",
                "text": "Hi Lola, chocolate is available.",
            },
            {
                "direction": "outbound",
                "sent_at": "2026-01-01T00:01:00Z",
                "text": "أهلاً ساندرا. كيف نساعد؟",
            },
            {
                "direction": "inbound",
                "sent_at": "2026-01-01T00:02:00Z",
                "text": "Email lola.test@example.com",
            },
        ],
    }

    model_input = build_semantic_input(conversation)

    assert "chocolate" in model_input.messages[0].redacted_text
    assert "Lola" not in model_input.messages[0].redacted_text
    assert "ساندرا" not in model_input.messages[1].redacted_text
    assert "example.com" not in model_input.messages[2].redacted_text


def test_agent_address_request_keeps_non_address_commercial_context():
    conversation = {
        "started_at": "2026-01-01T00:00:00Z",
        "language": "en",
        "customer": {},
        "messages": [
            {
                "direction": "outbound",
                "sent_at": "2026-01-01T00:00:00Z",
                "text": "The bundle is 947 EGP. Delivery is tomorrow. Address?",
            },
            {
                "direction": "inbound",
                "sent_at": "2026-01-01T00:01:00Z",
                "text": "12 Example Street",
            },
        ],
    }

    model_input = build_semantic_input(conversation)

    assert "bundle is 947 EGP" in model_input.messages[0].redacted_text
    assert "Delivery is tomorrow" in model_input.messages[0].redacted_text
    assert "[ADDRESS_REQUEST]" in model_input.messages[0].redacted_text
    assert model_input.messages[1].redacted_text == "[REDACTED_ADDRESS_MESSAGE]"


def test_resolved_barrier_requires_later_customer_acceptance():
    raw = {
        "started_at": "2026-01-01T00:00:00Z",
        "language": "en",
        "customer": {},
        "messages": [
            {
                "direction": "inbound",
                "sent_at": "2026-01-01T00:00:00Z",
                "text": "Please cancel because this product no longer fits.",
            },
            {
                "direction": "outbound",
                "sent_at": "2026-01-01T00:01:00Z",
                "text": "The cancellation is processed.",
            },
        ],
    }
    model_input = build_semantic_input(raw)
    signals = _signals().model_copy(
        update={
            "barriers": [
                BarrierSignal(
                    barrier_type=BarrierType.PRODUCT_FIT,
                    description="The customer no longer wants the product.",
                    evidence_message_indexes=[0, 1],
                    resolution=BarrierResolution.RESOLVED,
                )
            ]
        }
    )

    with pytest.raises(ValueError, match="later customer message"):
        validate_semantic_evidence_rules(signals, model_input)


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


def test_v3_high_value_signals_aggregate_with_assessable_denominators():
    canonical = normalize_cycle(load_sample2())
    row = canonical.conversations.iloc[0]
    signals = _signals().model_copy(
        update={
            "urgency": UrgencySignal(
                level=UrgencyLevel.HIGH,
                evidence_message_indexes=[0],
                elicited_by_agent=False,
            ),
            "price_sensitivity": PriceSensitivitySignal(
                level=PriceSensitivityLevel.BLOCKING,
                evidence_message_indexes=[0],
            ),
            "specificity": SpecificitySignal(
                level=SpecificityLevel.HIGH,
                evidence_message_indexes=[0],
            ),
            "financing": FinancingSignal(
                level=FinancingLevel.INQUIRY,
                evidence_message_indexes=[0],
            ),
            "commercial_traits": [
                CommercialTraitSignal(
                    trait=CommercialTrait.FEATURE_PRIORITY,
                    strength=CommercialTraitStrength.HIGH,
                    detail="The customer specified a required product feature.",
                    evidence_message_indexes=[0],
                )
            ],
            "agent_tone": AgentToneSignal(
                labels=[AgentToneLabel.PROFESSIONAL, AgentToneLabel.INFORMATIVE],
                quality=AgentToneQuality.POSITIVE,
                evidence_message_indexes=[1],
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
        signal_schema_version=3,
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
    assert campaign["high_specificity_rate"] == 1
    assert campaign["financing_discussion_rate"] == 1
    assert campaign["positive_agent_tone_rate"] == 1
    assert campaign["top_commercial_trait"] == "feature_priority"
    assert campaign["price_blocking_rate"] == 1
    assert campaign["ad_message_alignment_rate"] == 1
    assert campaign["semantic_coverage_rate"] == pytest.approx(
        1 / campaign["observed_conversations"]
    )


def test_unknown_semantic_values_are_excluded_from_rate_denominators():
    canonical = normalize_cycle(load_sample2())
    rows = canonical.conversations.loc[
        canonical.conversations["campaign_id"].notna()
    ].groupby("campaign_id").filter(lambda group: len(group) >= 2).iloc[:2]
    campaign_id = rows.iloc[0]["campaign_id"]
    rows = canonical.conversations.loc[
        canonical.conversations["campaign_id"].eq(campaign_id)
    ].iloc[:2]
    records = []
    for position, (_, row) in enumerate(rows.iterrows()):
        signals = _signals()
        if position == 0:
            signals = signals.model_copy(
                update={
                    "specificity": SpecificitySignal(
                        level=SpecificityLevel.HIGH,
                        evidence_message_indexes=[0],
                    )
                }
            )
        records.append(
            ConversationSignalRecord(
                conversation_id=row["conversation_id"],
                attribution=ConversationAttribution(
                    source_platform=row["source_platform"],
                    campaign_id=row["campaign_id"],
                    adset_id=row["adset_id"],
                    ad_id=row["ad_id"],
                    creative_id=row["creative_id"],
                    audience_type=row["audience_type"],
                ),
                prompt_version="test-v3",
                prompt_sha256="f" * 64,
                model="test-model",
                extracted_at="2026-09-02T00:00:00Z",
                signals=signals,
                signal_schema_version=3,
            )
        )

    campaign = build_scorecards(canonical, records).campaign.loc[
        lambda frame: frame["campaign_id"].eq(campaign_id)
    ].iloc[0]

    assert campaign["semantic_conversations"] == 2
    assert campaign["assessable_specificity_conversations"] == 1
    assert campaign["high_specificity_conversations"] == 1
    assert campaign["high_specificity_rate"] == 1


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


def test_extraction_persists_current_run_usage_and_sidecar(tmp_path):
    class UsageExtractor(_FakeExtractor):
        last_usage = LLMTokenUsage()

        def extract(self, model_input):
            result = super().extract(model_input)
            self.last_usage = LLMTokenUsage(
                request_count=1,
                input_tokens=100,
                cached_input_tokens=40,
                output_tokens=20,
                reasoning_output_tokens=5,
                total_tokens=120,
                model="gpt-5-mini",
                input_usd_per_million=0.25,
                cached_input_usd_per_million=0.025,
                output_usd_per_million=2,
                pricing_as_of="test",
                estimated_cost_usd=0.000056,
            )
            return result

    output = tmp_path / "signals.jsonl"
    summary = extract_conversation_signals(
        output_path=output,
        limit=1,
        campaign_name="Post-Eid Lookalike Test",
        extractor=UsageExtractor(),
    )
    record = load_conversation_signal_records(output)[0]
    usage_log = json.loads(
        output.with_suffix(".usage.jsonl").read_text(encoding="utf-8")
    )

    assert record.semantic_usage.input_tokens == 100
    assert record.semantic_usage.reasoning_output_tokens == 5
    assert summary.total_usage.estimated_cost_usd == pytest.approx(0.000056)
    assert usage_log["scope"] == "current_invocation_only"
    assert usage_log["total_usage"]["request_count"] == 1


def test_openai_usage_tracks_cached_reasoning_and_retry_costs():
    response = SimpleNamespace(
        usage=SimpleNamespace(
            input_tokens=1000,
            input_tokens_details=SimpleNamespace(cached_tokens=400),
            output_tokens=300,
            output_tokens_details=SimpleNamespace(reasoning_tokens=100),
            total_tokens=1300,
        )
    )

    single = response_token_usage(response, "gpt-5-mini")
    combined = merge_token_usage(single, single)

    assert single.cached_input_tokens == 400
    assert single.reasoning_output_tokens == 100
    assert single.estimated_cost_usd == pytest.approx(0.00076)
    assert combined.request_count == 2
    assert combined.total_tokens == 2600
    assert combined.estimated_cost_usd == pytest.approx(0.00152)


def test_paid_only_pilot_resumes_to_all_617_attributed_conversations(tmp_path):
    output = tmp_path / "paid-signals-v3.jsonl"
    pilot = extract_conversation_signals(
        output_path=output,
        limit=10,
        paid_only=True,
        extractor=_FakeExtractor(),
    )
    full = extract_conversation_signals(
        output_path=output,
        paid_only=True,
        extractor=_FakeExtractor(),
    )
    records = load_conversation_signal_records(output)

    assert pilot.selected == 10
    assert pilot.extracted == 10
    assert full.selected == 617
    assert full.skipped == 10
    assert full.extracted == 607
    assert full.failed == 0
    assert len(records) == 617
    assert all(record.signal_schema_version == 3 for record in records)
    assert all(record.attribution.campaign_id for record in records)


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


def test_agreed_next_step_uses_observed_order_progression_proxy():
    canonical = normalize_cycle(load_sample2())
    row = canonical.conversations.loc[
        canonical.conversations["has_order"].eq(True)
        & canonical.conversations["campaign_id"].notna()
    ].iloc[0]
    signals = _signals().model_copy(
        update={
            "next_step_agreed": NextStepAgreementSignal(
                agreed=True,
                next_step="Confirm an order",
                evidence_message_indexes=[0],
            )
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
        prompt_sha256="d" * 64,
        model="test-model",
        extracted_at="2026-09-02T00:00:00Z",
        signals=signals,
        signal_schema_version=2,
    )

    campaign = build_scorecards(canonical, [record]).campaign.loc[
        lambda frame: frame["campaign_id"].eq(row["campaign_id"])
    ].iloc[0]

    assert campaign["next_step_agreement_rate"] == 1
    assert campaign["next_step_order_progression_rate"] == 1
    assert "next_step_completion_rate" not in campaign.index


def test_v3_elicited_signal_requires_preceding_agent_evidence():
    raw = {
        "started_at": "2026-01-01T00:00:00Z",
        "language": "en",
        "customer": {},
        "messages": [
            {
                "direction": "outbound",
                "sent_at": "2026-01-01T00:00:00Z",
                "text": "When do you need it?",
            },
            {
                "direction": "inbound",
                "sent_at": "2026-01-01T00:01:00Z",
                "text": "Tomorrow morning.",
            },
        ],
    }
    model_input = build_semantic_input(raw)
    signals = _signals(customer_index=1, agent_index=0).model_copy(
        update={
            "urgency": UrgencySignal(
                level=UrgencyLevel.HIGH,
                elicited_by_agent=True,
                evidence_message_indexes=[0, 1],
            )
        }
    )

    validate_semantic_evidence_rules(signals, model_input)
    invalid = signals.model_copy(
        update={
            "urgency": UrgencySignal(
                level=UrgencyLevel.HIGH,
                elicited_by_agent=False,
                evidence_message_indexes=[0, 1],
            )
        }
    )
    with pytest.raises(ValueError, match="only customer messages"):
        validate_semantic_evidence_rules(invalid, model_input)

    missing_flag = signals.model_copy(
        update={
            "delivery_intent": DeliveryIntentSignal(
                level="checkout_details",
                elicited_by_agent=None,
                evidence_message_indexes=[1],
            )
        }
    )
    with pytest.raises(ValueError, match="must set elicited_by_agent"):
        validate_semantic_evidence_rules(missing_flag, model_input)


def test_validation_feedback_is_supplied_on_structured_output_retry(monkeypatch):
    raw = {
        "started_at": "2026-01-01T00:00:00Z",
        "language": "en",
        "customer": {},
        "messages": [
            {
                "direction": "inbound",
                "sent_at": "2026-01-01T00:00:00Z",
                "text": "I agree to place the order.",
            },
            {
                "direction": "outbound",
                "sent_at": "2026-01-01T00:01:00Z",
                "text": "Please complete checkout.",
            },
        ],
    }
    invalid = _signals().model_copy(
        update={
            "next_step_agreed": NextStepAgreementSignal(
                agreed=True,
                next_step="Complete checkout",
                evidence_message_indexes=[1],
            )
        }
    )
    valid = invalid.model_copy(
        update={
            "next_step_agreed": NextStepAgreementSignal(
                agreed=True,
                next_step="Complete checkout",
                evidence_message_indexes=[0],
            )
        }
    )

    class FakeResponses:
        def __init__(self):
            self.inputs = []

        def parse(self, **kwargs):
            self.inputs.append(kwargs["input"])
            output = invalid if len(self.inputs) == 1 else valid
            return SimpleNamespace(
                output_parsed=output,
                usage=SimpleNamespace(
                    input_tokens=100,
                    input_tokens_details=SimpleNamespace(cached_tokens=25),
                    output_tokens=50,
                    output_tokens_details=SimpleNamespace(reasoning_tokens=10),
                    total_tokens=150,
                ),
            )

    responses = FakeResponses()
    monkeypatch.setattr(
        "src_2.intelligence.conversation_signals.time.sleep", lambda _: None
    )
    extractor = OpenAIConversationSignalExtractor(
        client=SimpleNamespace(responses=responses),
        model="test-model",
        max_attempts=2,
    )

    result = extractor.extract(build_semantic_input(raw))

    assert result.next_step_agreed.evidence_message_indexes == [0]
    assert "previous structured output was rejected" in responses.inputs[1]
    assert "Agreed next step" in responses.inputs[1]
    assert extractor.last_usage.request_count == 2
    assert extractor.last_usage.input_tokens == 200
    assert extractor.last_usage.reasoning_output_tokens == 20


def test_old_signal_record_remains_readable_with_v3_defaults():
    legacy_payload = {
        "conversation_id": "legacy-conversation",
        "attribution": {
            "source_platform": "meta_ctwa",
            "campaign_id": "campaign",
            "adset_id": "adset",
            "ad_id": "ad",
            "creative_id": "creative",
            "audience_type": "broad",
        },
        "prompt_version": "conversation-signals-v2.1",
        "prompt_sha256": "e" * 64,
        "model": "test-model",
        "extracted_at": "2026-09-02T00:00:00Z",
        "signals": _signals().model_dump(mode="json", exclude={
            "specificity", "financing", "commercial_traits", "agent_tone"
        }),
        "signal_schema_version": 2,
    }

    restored = ConversationSignalRecord.model_validate(legacy_payload)

    assert restored.signals.specificity.level is SpecificityLevel.UNKNOWN
    assert restored.signals.financing.level is FinancingLevel.UNKNOWN
    assert restored.signals.agent_tone.quality is AgentToneQuality.NOT_ASSESSABLE


def test_response_times_are_derived_from_timestamped_customer_turns():
    canonical = normalize_cycle(load_sample2())
    conversation = canonical.conversations.loc[
        canonical.conversations["conversation_id"].eq("conv_001")
    ].iloc[0]

    assert conversation["first_agent_response_minutes"] == 2
    assert conversation["response_eligible_turns"] == 3
    assert conversation["answered_customer_turns"] == 2
    assert conversation["unanswered_customer_turns"] == 1

    campaign_id = conversation["campaign_id"]
    events = canonical.response_events.loc[
        canonical.response_events["campaign_id"].eq(campaign_id)
    ]
    campaign = build_scorecards(canonical).campaign.loc[
        lambda frame: frame["campaign_id"].eq(campaign_id)
    ].iloc[0]

    assert campaign["median_agent_response_minutes"] == pytest.approx(
        events["response_minutes"].median()
    )
    assert campaign["p90_agent_response_minutes"] == pytest.approx(
        events["response_minutes"].quantile(0.9)
    )
