"""Run and persist the complete deterministic MVP pipeline."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from .allocation import allocate_budget
from .config import BudgetPolicy, ObjectiveRegistry, load_budget_policy, load_objectives
from .contracts import (
    BudgetAllocation,
    EntityScore,
    ExplorationTest,
    RecommendationInput,
    RecommendationReport,
)
from .data import CanonicalData, load_conversation_signals, load_cycle
from .packet import build_recommendation_input, entity_from_row
from .paths import OUTPUT_DIR
from .scorecards import build_scorecards
from .statistics import score_all_levels
from .semantics import add_semantic_scores


@dataclass(frozen=True)
class MVPResult:
    data: CanonicalData
    scorecards: Dict[str, pd.DataFrame]
    allocations: List[BudgetAllocation]
    exploration_tests: List[ExplorationTest]
    recommendation_input: RecommendationInput
    recommendation_output: Optional[RecommendationReport]
    output_directory: Path
    semantic_evidence: pd.DataFrame


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _write_outputs(
    output_directory: Path,
    scorecards: Dict[str, pd.DataFrame],
    allocations: List[BudgetAllocation],
    tests: List[ExplorationTest],
    packet: RecommendationInput,
    report: Optional[RecommendationReport],
) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    entities: List[EntityScore] = []
    for frame in scorecards.values():
        entities.extend(entity_from_row(row) for _, row in frame.iterrows())
    with (output_directory / "entity_scorecards.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for entity in entities:
            handle.write(json.dumps(entity.model_dump(mode="json"), ensure_ascii=True))
            handle.write("\n")
    _write_json(
        output_directory / "campaign_budget.json",
        {
            "allocations": [item.model_dump(mode="json") for item in allocations],
            "unallocated_budget_units": packet.unallocated_budget_units,
            "decision_policy": packet.decision_policy.model_dump(mode="json"),
        },
    )
    _write_json(
        output_directory / "exploration_tests.json",
        [item.model_dump(mode="json") for item in tests],
    )
    _write_json(
        output_directory / "recommendation_input.json",
        packet.model_dump(mode="json", exclude_none=True),
    )
    if report is not None:
        _write_json(
            output_directory / "recommendation_output.json",
            report.model_dump(mode="json"),
        )


def run_mvp(
    input_directory: Optional[Path] = None,
    signals_path: Optional[Path] = None,
    output_directory: Optional[Path] = None,
    registry: Optional[ObjectiveRegistry] = None,
    policy: Optional[BudgetPolicy] = None,
    with_llm: bool = False,
    model: Optional[str] = None,
) -> MVPResult:
    objectives = registry or load_objectives()
    budget_policy = policy or load_budget_policy()
    data = load_cycle(input_directory)
    signals = load_conversation_signals(signals_path)
    raw_scorecards = build_scorecards(data, signals)
    scored = score_all_levels(raw_scorecards, objectives)
    scored, semantic_evidence = add_semantic_scores(scored, data, signals, objectives)
    allocations, tests, unallocated = allocate_budget(
        scored["campaign"], objectives, budget_policy
    )
    packet = build_recommendation_input(
        data,
        scored,
        signals,
        objectives,
        budget_policy,
        allocations,
        tests,
        unallocated,
    )
    report = None
    if with_llm:
        from .recommendation import run_recommendation

        report = run_recommendation(packet, model=model)
    destination = (output_directory or OUTPUT_DIR).expanduser().resolve()
    _write_outputs(destination, scored, allocations, tests, packet, report)
    semantic_evidence.to_json(
        destination / "semantic_evidence.jsonl", orient="records", lines=True
    )
    return MVPResult(
        data=data,
        scorecards=scored,
        allocations=allocations,
        exploration_tests=tests,
        recommendation_input=packet,
        recommendation_output=report,
        output_directory=destination,
        semantic_evidence=semantic_evidence,
    )
