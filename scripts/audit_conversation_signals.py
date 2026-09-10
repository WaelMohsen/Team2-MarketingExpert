"""Audit a conversation-signal artifact without exposing transcript text."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src_2.application import load_conversation_signal_records
from src_2.ingestion import load_sample2, normalize_cycle
from src_2.intelligence import (
    build_semantic_input,
    merge_token_usage,
    validate_evidence_message_indexes,
    validate_semantic_evidence_rules,
)


EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
FORBIDDEN_KEYS = {
    "first_name",
    "last_name",
    "phone",
    "address",
    "order_id",
    "ctwa_clid",
    "messages",
    "redacted_text",
}


def _keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            found.add(str(key))
            found.update(_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_keys(child))
    return found


def _known_customer_tokens(conversation: dict[str, Any]) -> set[str]:
    customer = conversation.get("customer") or {}
    tokens = {
        str(customer.get(key) or "").strip().casefold()
        for key in ("first_name", "last_name", "phone")
    }
    return {token for token in tokens if len(token) >= 4}


def _contains_customer_token(serialized: str, token: str) -> bool:
    if any(character.isdigit() for character in token):
        return token in serialized
    return re.search(rf"(?<!\w){re.escape(token)}(?!\w)", serialized) is not None


def _signal_row(record: Any) -> dict[str, Any]:
    signals = record.signals
    total_usage = merge_token_usage(record.semantic_usage, record.ad_match_usage)
    return {
        "conversation_id": record.conversation_id,
        "campaign_id": record.attribution.campaign_id,
        "prompt_version": record.prompt_version,
        "schema_version": record.signal_schema_version,
        "ad_match_prompt_version": record.ad_match_prompt_version,
        "purpose": signals.conversation_purpose.value,
        "purchase_intent": signals.purchase_intent.level.value,
        "specificity": signals.specificity.level.value,
        "stage": signals.conversation_stage.value,
        "urgency": signals.urgency.level.value,
        "urgency_elicited_by_agent": signals.urgency.elicited_by_agent,
        "price_sensitivity": signals.price_sensitivity.level.value,
        "deal_seeking": signals.deal_seeking.level.value,
        "financing": signals.financing.level.value,
        "delivery_intent": signals.delivery_intent.level.value,
        "delivery_elicited_by_agent": signals.delivery_intent.elicited_by_agent,
        "sales_agreement": signals.sales_agreement.level.value,
        "stated_exit_reason": signals.stated_exit_reason.reason.value,
        "next_step_agreed": signals.next_step_agreed.agreed,
        "barrier_count": len(signals.barriers),
        "blocking_barrier": any(
            item.severity.value == "blocking" for item in signals.barriers
        ),
        "resolved_barrier": any(
            item.resolution.value == "resolved" for item in signals.barriers
        ),
        "competitor_mentioned": signals.competitor_mention.mentioned,
        "value_driver_count": len(signals.value_drivers),
        "commercial_trait_count": len(signals.commercial_traits),
        "agent_tone_quality": signals.agent_tone.quality.value,
        "ad_message_match": record.ad_message_match.level.value,
        "usage_recorded": total_usage.request_count > 0,
        "api_requests": total_usage.request_count,
        "input_tokens": total_usage.input_tokens,
        "cached_input_tokens": total_usage.cached_input_tokens,
        "output_tokens": total_usage.output_tokens,
        "reasoning_output_tokens": total_usage.reasoning_output_tokens,
        "total_tokens": total_usage.total_tokens,
        "estimated_cost_usd": total_usage.estimated_cost_usd,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifact",
        default=str(ROOT / "src_2" / "artifacts" / "conversation_signals_v3_paid.jsonl"),
    )
    parser.add_argument("--input-directory")
    parser.add_argument("--expected-records", type=int, required=True)
    parser.add_argument("--expected-schema-version", type=int, default=3)
    parser.add_argument(
        "--expected-prompt-prefix", default="conversation-signals-v3"
    )
    parser.add_argument(
        "--expected-input-projection-version", default="semantic-input-v3"
    )
    parser.add_argument(
        "--output-directory",
        default=str(ROOT / "outputs" / "conversation_signals_v3_paid_audit"),
    )
    args = parser.parse_args()

    artifact = Path(args.artifact).expanduser().resolve()
    output = Path(args.output_directory).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    payload = load_sample2(args.input_directory)
    canonical = normalize_cycle(payload)
    records = load_conversation_signal_records(artifact)
    canonical_by_id = canonical.conversations.set_index("conversation_id")
    raw_by_id = {str(item.get("id")): item for item in payload.conversations}
    paid = canonical.conversations.loc[canonical.conversations["campaign_id"].notna()]
    paid_ids = set(paid["conversation_id"])
    issues: list[dict[str, str]] = []

    if len(records) != args.expected_records:
        issues.append({
            "conversation_id": "*",
            "issue": f"Expected {args.expected_records} records; found {len(records)}",
        })
    duplicate_count = len(records) - len({record.conversation_id for record in records})
    if duplicate_count:
        issues.append({
            "conversation_id": "*",
            "issue": f"Latest-record loader returned {duplicate_count} duplicate IDs",
        })

    rows: list[dict[str, Any]] = []
    for record in records:
        conversation_id = record.conversation_id
        rows.append(_signal_row(record))
        if record.signal_schema_version != args.expected_schema_version:
            issues.append({
                "conversation_id": conversation_id,
                "issue": (
                    f"Expected schema version {args.expected_schema_version}; "
                    f"found {record.signal_schema_version}"
                ),
            })
        if not record.prompt_version.startswith(args.expected_prompt_prefix):
            issues.append({
                "conversation_id": conversation_id,
                "issue": f"Unexpected signal prompt version: {record.prompt_version}",
            })
        if record.input_projection_version != args.expected_input_projection_version:
            issues.append({
                "conversation_id": conversation_id,
                "issue": (
                    f"Expected {args.expected_input_projection_version}; found "
                    f"{record.input_projection_version}"
                ),
            })
        if record.ad_match_prompt_version != "ad-message-match-v1":
            issues.append({
                "conversation_id": conversation_id,
                "issue": (
                    "Expected ad-message-match-v1; found "
                    f"{record.ad_match_prompt_version}"
                ),
            })
        if conversation_id not in paid_ids:
            issues.append({
                "conversation_id": conversation_id,
                "issue": "Record is not attributed to a paid campaign",
            })
            continue
        expected = canonical_by_id.loc[conversation_id]
        for field in ("campaign_id", "adset_id", "ad_id", "creative_id", "audience_type"):
            actual_value = getattr(record.attribution, field)
            expected_value = expected.get(field)
            expected_value = None if pd.isna(expected_value) else str(expected_value)
            if actual_value != expected_value:
                issues.append({
                    "conversation_id": conversation_id,
                    "issue": f"Attribution mismatch for {field}",
                })

        raw = raw_by_id[conversation_id]
        model_input = build_semantic_input(raw)
        valid_indexes = set(range(len(model_input.messages)))
        try:
            validate_evidence_message_indexes(
                record.signals, valid_indexes, context="Stored conversation signals"
            )
            validate_evidence_message_indexes(
                record.ad_message_match,
                valid_indexes,
                context="Stored ad-message match",
            )
            if record.signal_schema_version >= 3:
                validate_semantic_evidence_rules(record.signals, model_input)
        except ValueError as exc:
            issues.append({"conversation_id": conversation_id, "issue": str(exc)})

        semantic_payload = {
            "signals": record.signals.model_dump(mode="json"),
            "ad_message_match": record.ad_message_match.model_dump(mode="json"),
        }
        forbidden = _keys(semantic_payload).intersection(FORBIDDEN_KEYS)
        if forbidden:
            issues.append({
                "conversation_id": conversation_id,
                "issue": f"Forbidden semantic keys: {sorted(forbidden)}",
            })
        serialized = json.dumps(semantic_payload, ensure_ascii=False).casefold()
        if EMAIL.search(serialized):
            issues.append({
                "conversation_id": conversation_id,
                "issue": "Email-like text found in semantic output",
            })
        leaked_tokens = {
            token
            for token in _known_customer_tokens(raw)
            if _contains_customer_token(serialized, token)
        }
        if leaked_tokens:
            issues.append({
                "conversation_id": conversation_id,
                "issue": "Known customer token found in semantic output",
            })

    detail = pd.DataFrame(rows)
    campaigns = canonical.campaigns[["campaign_id", "campaign_name", "objective"]]
    detail = detail.merge(campaigns, on="campaign_id", how="left")
    by_campaign = detail.groupby(
        ["objective", "campaign_id", "campaign_name"], as_index=False
    ).agg(
        semantic_records=("conversation_id", "nunique"),
        expected_schema_records=(
            "schema_version",
            lambda values: values.eq(args.expected_schema_version).sum(),
        ),
        ad_match_records=("ad_match_prompt_version", lambda values: values.notna().sum()),
        high_intent=("purchase_intent", lambda values: values.eq("high").sum()),
        known_urgency=("urgency", lambda values: values.ne("unknown").sum()),
        known_specificity=(
            "specificity", lambda values: values.ne("unknown").sum()
        ),
        known_price_sensitivity=(
            "price_sensitivity", lambda values: values.ne("unknown").sum()
        ),
        known_delivery_intent=(
            "delivery_intent", lambda values: values.ne("unknown").sum()
        ),
        known_financing=("financing", lambda values: values.ne("unknown").sum()),
        known_sales_agreement=(
            "sales_agreement", lambda values: values.ne("unknown").sum()
        ),
        assessable_ad_match=(
            "ad_message_match", lambda values: values.ne("unknown").sum()
        ),
        usage_records=("usage_recorded", "sum"),
        api_requests=("api_requests", "sum"),
        input_tokens=("input_tokens", "sum"),
        cached_input_tokens=("cached_input_tokens", "sum"),
        output_tokens=("output_tokens", "sum"),
        reasoning_output_tokens=("reasoning_output_tokens", "sum"),
        total_tokens=("total_tokens", "sum"),
        estimated_cost_usd=(
            "estimated_cost_usd", lambda values: values.sum(min_count=1)
        ),
    )
    expected_by_campaign = paid.groupby("campaign_id", as_index=False).agg(
        paid_conversations=("conversation_id", "nunique")
    )
    by_campaign = by_campaign.merge(expected_by_campaign, on="campaign_id", how="left")
    by_campaign["semantic_coverage_rate"] = (
        by_campaign["semantic_records"] / by_campaign["paid_conversations"]
    )

    distribution_fields = [
        "purpose", "purchase_intent", "specificity", "stage", "urgency",
        "urgency_elicited_by_agent", "price_sensitivity", "deal_seeking",
        "financing", "delivery_intent", "delivery_elicited_by_agent",
        "sales_agreement", "agent_tone_quality",
        "stated_exit_reason", "next_step_agreed", "blocking_barrier",
        "resolved_barrier", "competitor_mentioned", "ad_message_match",
    ]
    distribution_rows: list[dict[str, Any]] = []
    for field in distribution_fields:
        for value, count in detail[field].fillna("null").value_counts().items():
            distribution_rows.append({
                "signal": field,
                "value": value,
                "count": int(count),
                "share": count / len(detail) if len(detail) else None,
            })
    distributions = pd.DataFrame(distribution_rows)
    issue_frame = pd.DataFrame(issues, columns=["conversation_id", "issue"])
    recorded_usage = merge_token_usage(
        *[
            merge_token_usage(record.semantic_usage, record.ad_match_usage)
            for record in records
        ]
    )
    usage_records = int(detail["usage_recorded"].sum()) if not detail.empty else 0

    summary = {
        "artifact": str(artifact),
        "expected_records": args.expected_records,
        "validated_records": len(records),
        "paid_population": len(paid_ids),
        "schema_versions": dict(Counter(record.signal_schema_version for record in records)),
        "input_projection_versions": dict(
            Counter(record.input_projection_version for record in records)
        ),
        "prompt_versions": dict(Counter(record.prompt_version for record in records)),
        "ad_match_prompt_versions": dict(
            Counter(str(record.ad_match_prompt_version) for record in records)
        ),
        "campaigns_covered": int(detail["campaign_id"].nunique()) if not detail.empty else 0,
        "usage": {
            "records_with_usage": usage_records,
            "record_coverage_rate": usage_records / len(records) if records else None,
            "historical_records_without_usage": len(records) - usage_records,
            "recorded_totals": recorded_usage.model_dump(mode="json"),
        },
        "issues": len(issues),
        "passed": len(issues) == 0 and len(records) == args.expected_records,
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    detail.to_csv(output / "records.csv", index=False)
    by_campaign.to_csv(output / "by_campaign.csv", index=False)
    distributions.to_csv(output / "signal_distributions.csv", index=False)
    issue_frame.to_csv(output / "issues.csv", index=False)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
