"""Load human-editable YAML and validate it with domain contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from src_2.domain.config import BudgetPolicy, CampaignTypeRegistry
from src_2.paths import CONFIG_DIR

ConfigModel = TypeVar("ConfigModel", bound=BaseModel)


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required to load v2 configuration; install requirements.txt"
        ) from exc
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Configuration must be a YAML object: {path}")
    return payload


def _validate(path: Path, model: type[ConfigModel]) -> ConfigModel:
    if not path.exists():
        raise FileNotFoundError(f"Configuration not found: {path}")
    return model.model_validate(_load_yaml(path))


def load_campaign_type_registry(
    path: str | Path | None = None,
) -> CampaignTypeRegistry:
    return _validate(
        Path(path or CONFIG_DIR / "campaign_types.yaml"), CampaignTypeRegistry
    )


def load_budget_policy(path: str | Path | None = None) -> BudgetPolicy:
    return _validate(Path(path or CONFIG_DIR / "budget_policy.poc.yaml"), BudgetPolicy)
