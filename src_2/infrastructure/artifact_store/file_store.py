"""Cycle-versioned JSON artifact persistence."""

from __future__ import annotations

import json
from pathlib import Path

from src_2.paths import ARTIFACT_DIR


class JsonArtifactStore:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or ARTIFACT_DIR)

    def save_json(self, cycle_id: str, name: str, payload: dict) -> Path:
        directory = self.root / cycle_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{name}.json"
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True, default=str),
            encoding="utf-8",
        )
        return path
