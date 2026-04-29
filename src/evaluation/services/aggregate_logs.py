import csv
import os
from datetime import datetime, timezone
from typing import Dict, List

from .log_reader import list_json_files, safe_read_json
from .log_schema import (
    ANALYSIS_COLUMNS,
    ANALYSIS_CSV,
    ANALYSIS_DIR,
    RECOMMENDATION_COLUMNS,
    RECOMMENDATION_CSV,
    RECOMMENDATION_DIR,
)
from .row_mapper import analysis_row, recommendation_row


def _write_csv(path: str, columns: List[str], rows: List[Dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def aggregate_logs() -> Dict[str, str]:
    ingested_at = datetime.now(timezone.utc).isoformat()

    analysis_rows = []
    for path in list_json_files(ANALYSIS_DIR):
        payload = safe_read_json(path)
        if payload is None:
            continue
        analysis_rows.append(analysis_row(payload, path, ingested_at))

    recommendation_rows = []
    for path in list_json_files(RECOMMENDATION_DIR):
        payload = safe_read_json(path)
        if payload is None:
            continue
        recommendation_rows.append(recommendation_row(payload, path, ingested_at))

    _write_csv(ANALYSIS_CSV, ANALYSIS_COLUMNS, analysis_rows)
    _write_csv(RECOMMENDATION_CSV, RECOMMENDATION_COLUMNS, recommendation_rows)

    return {
        "overall_analysis_csv": ANALYSIS_CSV,
        "overall_recommendation_csv": RECOMMENDATION_CSV,
        "analysis_rows": str(len(analysis_rows)),
        "recommendation_rows": str(len(recommendation_rows)),
    }
