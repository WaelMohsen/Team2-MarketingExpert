"""Versionable Markdown prompt loading."""

from __future__ import annotations

from pathlib import Path

from src_2.paths import PROMPT_DIR


def load_prompt(name: str, prompt_directory: str | Path | None = None) -> str:
    directory = Path(prompt_directory or PROMPT_DIR)
    path = directory / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")
