"""Compare two signal artifacts without reading or exporting transcript text."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src_2.application import load_conversation_signal_records


SHARED_FIELDS = [
    "purpose",
    "purchase_intent",
    "urgency",
    "price_sensitivity",
    "deal_seeking",
    "delivery_intent",
    "sales_agreement",
    "conversation_stage",
    "agent_helpfulness",
    "ad_message_match",
]

NEW_FIELDS = [
    "specificity",
    "financing",
    "urgency_elicited_by_agent",
    "delivery_elicited_by_agent",
    "agent_tone_quality",
    "commercial_traits",
]


def _flatten(record: Any) -> dict[str, Any]:
    signals = record.signals
    return {
        "conversation_id": record.conversation_id,
        "campaign_id": record.attribution.campaign_id,
        "schema_version": record.signal_schema_version,
        "prompt_version": record.prompt_version,
        "purpose": signals.conversation_purpose.value,
        "purchase_intent": signals.purchase_intent.level.value,
        "urgency": signals.urgency.level.value,
        "price_sensitivity": signals.price_sensitivity.level.value,
        "deal_seeking": signals.deal_seeking.level.value,
        "delivery_intent": signals.delivery_intent.level.value,
        "sales_agreement": signals.sales_agreement.level.value,
        "conversation_stage": signals.conversation_stage.value,
        "agent_helpfulness": signals.agent_evaluation.helpfulness.value,
        "ad_message_match": record.ad_message_match.level.value,
        "specificity": signals.specificity.level.value,
        "financing": signals.financing.level.value,
        "urgency_elicited_by_agent": signals.urgency.elicited_by_agent,
        "delivery_elicited_by_agent": signals.delivery_intent.elicited_by_agent,
        "agent_tone_quality": signals.agent_tone.quality.value,
        "commercial_traits": "|".join(
            sorted(item.trait.value for item in signals.commercial_traits)
        ),
    }


def _unknown_share(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame:
        return None
    return float(
        frame[column].isna().add(frame[column].astype(str).eq("unknown")).gt(0).mean()
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--baseline",
        default=str(
            ROOT / "src_2" / "artifacts" / "conversation_signals_v2_paid.jsonl"
        ),
    )
    parser.add_argument(
        "--candidate",
        default=str(
            ROOT / "src_2" / "artifacts" / "conversation_signals_v3_paid.jsonl"
        ),
    )
    parser.add_argument(
        "--output-directory",
        default=str(ROOT / "outputs" / "conversation_signals_v3_pilot_comparison"),
    )
    args = parser.parse_args()

    baseline_path = Path(args.baseline).expanduser().resolve()
    candidate_path = Path(args.candidate).expanduser().resolve()
    output = Path(args.output_directory).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    baseline_records = load_conversation_signal_records(baseline_path)
    candidate_records = load_conversation_signal_records(candidate_path)
    if not baseline_records:
        raise ValueError(f"No validated records found in baseline: {baseline_path}")
    if not candidate_records:
        raise ValueError(f"No validated records found in candidate: {candidate_path}")
    baseline = pd.DataFrame(_flatten(record) for record in baseline_records)
    candidate = pd.DataFrame(_flatten(record) for record in candidate_records)
    overlap = baseline.merge(
        candidate,
        on="conversation_id",
        how="inner",
        suffixes=("_baseline", "_candidate"),
    )

    agreement: dict[str, float | None] = {}
    for field in SHARED_FIELDS:
        if overlap.empty:
            agreement[field] = None
        else:
            agreement[field] = float(
                overlap[f"{field}_baseline"].eq(
                    overlap[f"{field}_candidate"]
                ).mean()
            )

    unknown_rates: dict[str, dict[str, float | None]] = {}
    for field in SHARED_FIELDS:
        unknown_rates[field] = {
            "baseline": _unknown_share(baseline, field),
            "candidate": _unknown_share(candidate, field),
        }
    for field in NEW_FIELDS:
        unknown_rates[field] = {
            "baseline": None,
            "candidate": _unknown_share(candidate, field),
        }

    summary = {
        "baseline_artifact": str(baseline_path),
        "candidate_artifact": str(candidate_path),
        "baseline_records": len(baseline),
        "candidate_records": len(candidate),
        "overlapping_conversations": len(overlap),
        "baseline_schema_versions": dict(
            Counter(record.signal_schema_version for record in baseline_records)
        ),
        "candidate_schema_versions": dict(
            Counter(record.signal_schema_version for record in candidate_records)
        ),
        "baseline_prompt_versions": dict(
            Counter(record.prompt_version for record in baseline_records)
        ),
        "candidate_prompt_versions": dict(
            Counter(record.prompt_version for record in candidate_records)
        ),
        "shared_field_agreement": agreement,
        "unknown_rates": unknown_rates,
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    overlap.to_csv(output / "conversation_comparison.csv", index=False)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
