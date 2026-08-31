"""Resumable use case for extracting governed conversation semantics."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

import pandas as pd

from src_2.contracts import (
    AdMessageContext,
    ConversationAttribution,
    ConversationSignalRecord,
)
from src_2.ingestion import load_sample2, normalize_cycle
from src_2.intelligence import (
    OpenAIConversationSignalExtractor,
    build_semantic_input,
    build_signal_record,
)
from src_2.paths import ARTIFACT_DIR
from src_2.application.ports import AdMessageMatchEvaluator, ConversationSignalExtractor


@dataclass(frozen=True)
class ConversationExtractionSummary:
    output_path: Path
    selected: int
    extracted: int
    skipped: int
    failed: int


def load_conversation_signal_records(
    path: str | Path,
) -> list[ConversationSignalRecord]:
    source = Path(path).expanduser().resolve()
    if not source.exists():
        return []
    records_by_conversation: dict[str, ConversationSignalRecord] = {}
    with source.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = ConversationSignalRecord.model_validate_json(line)
                previous = records_by_conversation.get(record.conversation_id)
                if previous is None or record.extracted_at >= previous.extracted_at:
                    records_by_conversation[record.conversation_id] = record
            except Exception as exc:
                raise ValueError(
                    f"Invalid conversation signal record at {source}:{line_number}"
                ) from exc
    return list(records_by_conversation.values())


def _str_or_none(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(value)


def _attribution(row: pd.Series) -> ConversationAttribution:
    return ConversationAttribution(
        source_platform=_str_or_none(row.get("source_platform")),
        campaign_id=_str_or_none(row.get("campaign_id")),
        adset_id=_str_or_none(row.get("adset_id")),
        ad_id=_str_or_none(row.get("ad_id")),
        creative_id=_str_or_none(row.get("creative_id")),
        audience_type=_str_or_none(row.get("audience_type")),
    )


def _ad_context(
    creative_id: str | None, creative_lookup: pd.DataFrame
) -> AdMessageContext | None:
    if not creative_id or creative_id not in creative_lookup.index:
        return None
    creative = creative_lookup.loc[creative_id]
    return AdMessageContext(
        creative_name=_str_or_none(creative.get("creative_name")),
        headline=_str_or_none(creative.get("object_story_spec.link_data.name")),
        message=_str_or_none(creative.get("object_story_spec.link_data.message")),
        description=_str_or_none(
            creative.get("object_story_spec.link_data.description")
        ),
        theme=_str_or_none(creative.get("theme")),
        angle=_str_or_none(creative.get("angle")),
    )


def _stratified_selection(
    conversations: list[dict[str, Any]], limit: int | None
) -> list[dict[str, Any]]:
    if limit is None or limit >= len(conversations):
        return conversations
    groups: dict[str, list[dict[str, Any]]] = {}
    for conversation in conversations:
        outcome = str((conversation.get("outcome") or {}).get("type") or "unknown")
        groups.setdefault(outcome, []).append(conversation)
    selected: list[dict[str, Any]] = []
    group_names = sorted(groups)
    index = 0
    while len(selected) < limit:
        added = False
        for name in group_names:
            if index < len(groups[name]) and len(selected) < limit:
                selected.append(groups[name][index])
                added = True
        if not added:
            break
        index += 1
    return selected


def _write_json_line(handle: Any, payload: dict[str, Any]) -> None:
    handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    handle.flush()


def extract_conversation_signals(
    input_directory: str | Path | None = None,
    *,
    output_path: str | Path | None = None,
    limit: int | None = None,
    campaign_id: str | None = None,
    campaign_name: str | None = None,
    resume: bool = True,
    extractor: ConversationSignalExtractor | None = None,
    ad_match_evaluator: AdMessageMatchEvaluator | None = None,
    progress: Callable[[str], None] | None = None,
) -> ConversationExtractionSummary:
    """Extract signals one record at a time and checkpoint every validated result."""

    payload = load_sample2(input_directory)
    canonical = normalize_cycle(payload)
    canonical_lookup = canonical.conversations.set_index("conversation_id")
    creative_lookup = canonical.creatives.set_index("creative_id")
    if campaign_id and campaign_name:
        raise ValueError("Supply campaign_id or campaign_name, not both")
    selected_campaign_id = campaign_id
    if campaign_name:
        matches = canonical.campaigns.loc[
            canonical.campaigns["campaign_name"].eq(campaign_name), "campaign_id"
        ].tolist()
        if len(matches) != 1:
            raise ValueError(
                f"Expected one campaign named {campaign_name!r}; found {len(matches)}"
            )
        selected_campaign_id = str(matches[0])

    conversations = payload.conversations
    if selected_campaign_id:
        eligible_ids = set(
            canonical.conversations.loc[
                canonical.conversations["campaign_id"].eq(str(selected_campaign_id)),
                "conversation_id",
            ]
        )
        conversations = [
            item for item in conversations if str(item.get("id")) in eligible_ids
        ]
        if not conversations:
            raise ValueError(
                f"No conversations found for campaign {selected_campaign_id!r}"
            )
    selected = _stratified_selection(conversations, limit)
    destination = Path(
        output_path or ARTIFACT_DIR / "conversation_signals.jsonl"
    ).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    failure_path = destination.with_suffix(".errors.jsonl")
    signal_extractor = extractor or OpenAIConversationSignalExtractor()
    match_evaluator = ad_match_evaluator

    existing = load_conversation_signal_records(destination) if resume else []
    completed = {
        (
            record.conversation_id,
            record.prompt_sha256,
            record.model,
            record.ad_match_prompt_sha256 or "",
        )
        for record in existing
    }
    extracted = 0
    skipped = 0
    failed = 0
    mode = "a" if resume else "w"
    with destination.open(mode, encoding="utf-8") as output, failure_path.open(
        mode, encoding="utf-8"
    ) as failures:
        for position, conversation in enumerate(selected, start=1):
            conversation_id = str(conversation.get("id") or "")
            key = (
                conversation_id,
                signal_extractor.prompt_sha256,
                signal_extractor.model,
                match_evaluator.prompt_sha256 if match_evaluator else "",
            )
            if key in completed:
                skipped += 1
                if progress:
                    progress(
                        f"[{position}/{len(selected)}] {conversation_id}: already extracted"
                    )
                continue
            if progress:
                progress(f"[{position}/{len(selected)}] {conversation_id}: extracting")
            try:
                row = canonical_lookup.loc[conversation_id]
                model_input = build_semantic_input(conversation)
                signals = signal_extractor.extract(model_input)
                attribution = _attribution(row)
                context = _ad_context(attribution.creative_id, creative_lookup)
                ad_message_match = (
                    match_evaluator.evaluate(context, signals)
                    if match_evaluator and context
                    else None
                )
                record = build_signal_record(
                    conversation_id=conversation_id,
                    attribution=attribution,
                    signals=signals,
                    extractor=signal_extractor,
                    ad_message_match=ad_message_match,
                    ad_match_evaluator=match_evaluator if context else None,
                )
                _write_json_line(output, record.model_dump(mode="json"))
                completed.add(key)
                extracted += 1
                if progress:
                    progress(f"[{position}/{len(selected)}] {conversation_id}: saved")
            except Exception as exc:
                _write_json_line(
                    failures,
                    {
                        "conversation_id": conversation_id,
                        "prompt_sha256": signal_extractor.prompt_sha256,
                        "model": signal_extractor.model,
                        "ad_match_prompt_sha256": (
                            match_evaluator.prompt_sha256 if match_evaluator else None
                        ),
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                )
                failed += 1
                if progress:
                    progress(
                        f"[{position}/{len(selected)}] {conversation_id}: failed ({type(exc).__name__})"
                    )

    return ConversationExtractionSummary(
        output_path=destination,
        selected=len(selected),
        extracted=extracted,
        skipped=skipped,
        failed=failed,
    )
