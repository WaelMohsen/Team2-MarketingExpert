"""Load the two explicit MVP business configurations."""

from pathlib import Path
from typing import Dict, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .contracts import ObjectiveContract
from .paths import CONFIG_DIR


class ObjectiveRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    objectives: Dict[str, ObjectiveContract]


class BudgetPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    budget_units: float = Field(gt=0)
    currency: str
    allocation_mode: str
    objective_envelope_basis: str
    campaign_weight: str
    concentration_cap: Optional[float] = Field(default=None, ge=0, le=1)


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing MVP configuration: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a YAML object in {path}")
    return payload


def load_objectives(path: Optional[Path] = None) -> ObjectiveRegistry:
    source = path or CONFIG_DIR / "objectives.yaml"
    payload = _read_yaml(source)
    objectives = payload.get("objectives") or {}
    payload["objectives"] = {
        name: {"objective": name, **spec} for name, spec in objectives.items()
    }
    return ObjectiveRegistry.model_validate(payload)


def load_budget_policy(path: Optional[Path] = None) -> BudgetPolicy:
    return BudgetPolicy.model_validate(
        _read_yaml(path or CONFIG_DIR / "budget_policy.yaml")
    )
