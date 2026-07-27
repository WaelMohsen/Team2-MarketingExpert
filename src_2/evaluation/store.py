"""Local JSON persistence for evaluation runs and their history."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src_2.contracts import EvaluationReport
from src_2.paths import ARTIFACT_DIR, PROMPT_DIR

EVAL_DIR = ARTIFACT_DIR / "evaluations"


def prompt_version() -> str:
    """Short hash of the prompt files, so trends are attributable to prompt changes."""
    digest = hashlib.sha256()
    for path in sorted(PROMPT_DIR.glob("*.md")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:8]


def save_evaluation(report: EvaluationReport) -> Path:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{report.run_timestamp.replace(':', '').replace('-', '')}_{report.cycle_id}.json"
    path = EVAL_DIR / filename
    path.write_text(json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=True))
    return path


def load_history() -> list[EvaluationReport]:
    """All persisted runs, oldest first."""
    if not EVAL_DIR.exists():
        return []
    reports: list[EvaluationReport] = []
    for path in EVAL_DIR.glob("*.json"):
        try:
            reports.append(EvaluationReport.model_validate_json(path.read_text()))
        except Exception:
            # Skip records written by an incompatible schema version.
            continue
    return sorted(reports, key=lambda r: r.run_timestamp)
