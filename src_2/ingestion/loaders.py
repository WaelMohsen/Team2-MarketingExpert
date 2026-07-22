"""Read the three Sample 2 JSON files without applying business logic."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src_2.paths import INPUT_DIR


@dataclass(frozen=True)
class RawCyclePayload:
    meta: dict[str, Any]
    conversations: list[dict[str, Any]]
    products: list[dict[str, Any]]
    source_directory: Path


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Required cycle input is missing: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_sample2(input_directory: str | Path | None = None) -> RawCyclePayload:
    source = Path(input_directory or INPUT_DIR).expanduser().resolve()
    meta = _read_json(source / "meta_data.json")
    conversations = _read_json(source / "conversations.json")
    products = _read_json(source / "products.json")
    if not isinstance(meta, dict):
        raise ValueError("meta_data.json must contain a JSON object")
    if not isinstance(conversations, list):
        raise ValueError("conversations.json must contain a JSON array")
    if not isinstance(products, list):
        raise ValueError("products.json must contain a JSON array")
    return RawCyclePayload(meta, conversations, products, source)
