"""Refresh the minimal input and prompt snapshot from src_2."""

import argparse
import json
import shutil
from pathlib import Path
from typing import Optional

from .paths import ARTIFACT_DIR, INPUT_DIR, PROMPT_DIR


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "src_2"


def _copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def sync_assets(source_root: Optional[Path] = None) -> int:
    source = (source_root or SOURCE_ROOT).expanduser().resolve()
    _copy(source / "data" / "input" / "sampe_2" / "meta_data.json", INPUT_DIR / "meta_data.json")
    _copy(
        source / "data" / "input" / "sampe_2" / "conversations.json",
        INPUT_DIR / "conversations.json",
    )
    _copy(source / "prompts" / "conversation_signals.md", PROMPT_DIR / "conversation_signals.md")
    _copy(source / "prompts" / "ad_message_match.md", PROMPT_DIR / "ad_message_match.md")

    source_artifact = source / "artifacts" / "conversation_signals_v3_paid.jsonl"
    records = []
    with source_artifact.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if int(record.get("signal_schema_version", 0)) < 3:
                raise ValueError(
                    f"Artifact line {line_number} is not schema v3 or later"
                )
            records.append(record)
    destination = ARTIFACT_DIR / "conversation_signals_v3_paid.jsonl"
    temporary = destination.with_suffix(".jsonl.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True))
            handle.write("\n")
    temporary.replace(destination)
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()
    count = sync_assets(args.source_root)
    print(f"Synced {count} schema-v3 conversation signal records")


if __name__ == "__main__":
    main()
