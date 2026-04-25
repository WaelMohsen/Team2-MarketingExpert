"""Tests for aggregate_overall_logs: row building, CSV output, schema stability."""

import csv
import json
import os

import pytest

import src.evaluation.aggregate_overall_logs as agg_module
from src.evaluation.aggregate_overall_logs import (
    ANALYSIS_COLUMNS,
    RECOMMENDATION_COLUMNS,
    aggregate_logs,
)

ANALYSIS_PAYLOAD = {
    "category": "acquisition",
    "campaign_id": "Spring Launch",
    "target": "customer_acquisition",
    "score": 0.75,
    "dimensions": {
        "clarity": 0.8,
        "data_grounding": 0.7,
        "logic_coherence": 0.8,
        "business_focus": 0.55,
        "confidence_calibration": 0.75,
        "no_recommendation": 0.8,
    },
    "flags": ["low_business_focus"],
}

RECOMMENDATION_PAYLOAD = {
    "category": "acquisition",
    "campaign_id": "Spring Launch",
    "target": "customer_acquisition",
    "final_score": 0.82,
    "business": {"score": 0.85, "flags": [], "weak_recommendations": []},
    "compliance": {"score": 0.9, "flags": []},
    "ground_truth": {
        "score": 0.78,
        "avg_similarity": 0.75,
        "coverage": 0.8,
        "llm_calls": 3,
        "total_recommendations": 5,
        "total_ground_truth": 4,
        "flags": ["low_similarity_to_expert"],
    },
}


def _write_fixture(directory, filename, payload):
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    return path


def _patch_dirs(monkeypatch, tmp_path, analysis_dir, rec_dir):
    analysis_csv = str(tmp_path / "overall" / "overall_analysis.csv")
    rec_csv = str(tmp_path / "overall" / "overall_recommendation.csv")
    monkeypatch.setattr(agg_module, "ANALYSIS_DIR", str(analysis_dir))
    monkeypatch.setattr(agg_module, "RECOMMENDATION_DIR", str(rec_dir))
    monkeypatch.setattr(agg_module, "ANALYSIS_CSV", analysis_csv)
    monkeypatch.setattr(agg_module, "RECOMMENDATION_CSV", rec_csv)
    return analysis_csv, rec_csv


def test_aggregate_logs_analysis_row_columns(tmp_path, monkeypatch):
    analysis_dir = tmp_path / "analysis"
    _write_fixture(str(analysis_dir), "eval_20260420_120000.json", ANALYSIS_PAYLOAD)

    analysis_csv, rec_csv = _patch_dirs(
        monkeypatch, tmp_path, analysis_dir, tmp_path / "recommendation"
    )

    result = aggregate_logs(ingested_at="2026-04-25T00:00:00Z")

    assert int(result["analysis_rows"]) == 1
    assert int(result["recommendation_rows"]) == 0

    with open(analysis_csv, newline="") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 1
    row = rows[0]

    for col in ANALYSIS_COLUMNS:
        assert col in row, f"Missing column: {col}"

    # Stable deterministic id (32-char md5 hex)
    assert len(row["id"]) == 32

    assert row["category"] == "acquisition"
    assert row["campaign_id"] == "Spring Launch"
    assert row["target"] == "customer_acquisition"
    assert float(row["analysis_score"]) == pytest.approx(0.75)
    assert row["ts_utc"] == "2026-04-20T12:00:00Z"
    assert row["ingested_at_utc"] == "2026-04-25T00:00:00Z"
    assert row["has_low_business_focus"] == "1"
    assert row["has_low_clarity"] == "0"
    assert row["flag_count"] == "1"


def test_aggregate_logs_recommendation_row_columns(tmp_path, monkeypatch):
    rec_dir = tmp_path / "recommendation"
    _write_fixture(str(rec_dir), "eval_20260420_130000.json", RECOMMENDATION_PAYLOAD)

    analysis_csv, rec_csv = _patch_dirs(
        monkeypatch, tmp_path, tmp_path / "analysis", rec_dir
    )

    result = aggregate_logs(ingested_at="2026-04-25T00:00:00Z")

    assert int(result["analysis_rows"]) == 0
    assert int(result["recommendation_rows"]) == 1

    with open(rec_csv, newline="") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 1
    row = rows[0]

    for col in RECOMMENDATION_COLUMNS:
        assert col in row, f"Missing column: {col}"

    assert row["category"] == "acquisition"
    assert row["campaign_id"] == "Spring Launch"
    assert row["target"] == "customer_acquisition"
    assert float(row["final_score"]) == pytest.approx(0.82)
    assert row["ts_utc"] == "2026-04-20T13:00:00Z"
    assert row["has_low_similarity_to_expert"] == "1"
    assert row["has_missing_key_expert_insights"] == "0"


def test_aggregate_logs_skips_invalid_json(tmp_path, monkeypatch):
    analysis_dir = tmp_path / "analysis"
    os.makedirs(str(analysis_dir))
    bad_path = str(analysis_dir / "eval_20260420_140000.json")
    with open(bad_path, "w") as f:
        f.write("not json {{{")

    analysis_csv, rec_csv = _patch_dirs(
        monkeypatch, tmp_path, analysis_dir, tmp_path / "recommendation"
    )

    result = aggregate_logs(ingested_at="2026-04-25T00:00:00Z")
    assert int(result["analysis_rows"]) == 0


def test_aggregate_logs_stable_id_across_runs(tmp_path, monkeypatch):
    """Re-running aggregation on the same file must produce the same row id."""
    analysis_dir = tmp_path / "analysis"
    _write_fixture(str(analysis_dir), "eval_20260420_120000.json", ANALYSIS_PAYLOAD)

    analysis_csv, rec_csv = _patch_dirs(
        monkeypatch, tmp_path, analysis_dir, tmp_path / "recommendation"
    )

    aggregate_logs(ingested_at="2026-04-25T00:00:00Z")
    with open(analysis_csv, newline="") as f:
        first_id = list(csv.DictReader(f))[0]["id"]

    aggregate_logs(ingested_at="2026-04-25T00:00:00Z")
    with open(analysis_csv, newline="") as f:
        second_id = list(csv.DictReader(f))[0]["id"]

    assert first_id == second_id


def test_aggregate_logs_missing_optional_fields(tmp_path, monkeypatch):
    """Rows with missing keys should produce empty strings, not KeyError."""
    minimal = {"score": 0.5, "flags": []}

    analysis_dir = tmp_path / "analysis"
    _write_fixture(str(analysis_dir), "eval_20260420_150000.json", minimal)

    analysis_csv, rec_csv = _patch_dirs(
        monkeypatch, tmp_path, analysis_dir, tmp_path / "recommendation"
    )

    aggregate_logs(ingested_at="2026-04-25T00:00:00Z")

    with open(analysis_csv, newline="") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 1
    assert rows[0]["category"] == ""
    assert rows[0]["campaign_id"] == ""
