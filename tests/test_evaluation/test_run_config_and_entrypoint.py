import json

import pytest

from src.evaluation.run_config import load_run_config
from src.evaluation.run_evaluation import main, run_from_config


def _config_payload(category=None):
    return {
        "runtime": {
            "campaign_id": "Spring Launch",
            "category": category,
            "context_rows": 7,
        },
        "generation": {
            "analysis_model": "gpt-4o-mini",
            "analysis_temp": 0.2,
            "recommendation_model": "gpt-4o",
            "recommendation_temp": 0.3,
        },
        "evaluation": {
            "analysis_judge_model": "gpt-4o-mini",
            "analysis_judge_temp": 0.1,
            "recommendation_judge_model": "gpt-4o",
            "recommendation_judge_temp": 0.1,
        },
    }


def test_load_run_config_reads_runtime_section(tmp_path):
    config_path = tmp_path / "evaluation_run_config.json"
    config_path.write_text(json.dumps(_config_payload("Customer Acquisition")))

    config = load_run_config(str(config_path))

    assert config.runtime.campaign_id == "Spring Launch"
    assert config.runtime.category == "Customer Acquisition"
    assert config.runtime.context_rows == 7


def test_run_from_config_dispatches_single_category(monkeypatch, tmp_path):
    config_path = tmp_path / "evaluation_run_config.json"
    config_path.write_text(json.dumps(_config_payload("Customer Acquisition")))
    captured = {}

    def fake_run_target(**kwargs):
        captured.update(kwargs)
        return {"mode": "single"}

    monkeypatch.setattr("src.evaluation.run_evaluation.run_target", fake_run_target)

    result = run_from_config(str(config_path))

    assert result == {"mode": "single"}
    assert captured["campaign_name"] == "Spring Launch"
    assert captured["category"] == "Customer Acquisition"
    assert captured["context_rows"] == 7


def test_run_from_config_dispatches_all_categories(monkeypatch, tmp_path):
    config_path = tmp_path / "evaluation_run_config.json"
    config_path.write_text(json.dumps(_config_payload(None)))
    captured = {}

    def fake_run_all_targets(**kwargs):
        captured.update(kwargs)
        return {"mode": "all"}

    monkeypatch.setattr(
        "src.evaluation.run_evaluation.run_all_targets", fake_run_all_targets
    )

    result = run_from_config(str(config_path))

    assert result == {"mode": "all"}
    assert captured["campaign_name"] == "Spring Launch"
    assert captured["context_rows"] == 7
    assert captured["config_path"] == str(config_path)


def test_main_accepts_positional_config_path(monkeypatch):
    captured = {}

    def fake_run_from_config(config_path):
        captured["config_path"] = config_path
        return {"mode": "cli"}

    monkeypatch.setattr(
        "src.evaluation.run_evaluation.run_from_config", fake_run_from_config
    )
    monkeypatch.setattr(
        "src.evaluation.run_evaluation.sys.argv",
        [
            "python -m src.evaluation.run_evaluation",
            "config/evaluation_run_config.high-quality.temp0.json",
        ],
    )

    main()

    assert (
        captured["config_path"]
        == "config/evaluation_run_config.high-quality.temp0.json"
    )


def test_main_rejects_extra_cli_arguments(monkeypatch):
    monkeypatch.setattr(
        "src.evaluation.run_evaluation.sys.argv",
        ["python -m src.evaluation.run_evaluation", "one.json", "two.json"],
    )

    with pytest.raises(SystemExit, match="Usage:"):
        main()
