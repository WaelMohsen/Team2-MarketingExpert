import json
import math
import re
from typing import Any, Dict, List

from pydantic import BaseModel, field_validator


def _assert_ascii(v: str) -> str:
    if not re.match(r"^[\x00-\x7F]+$", v):
        raise ValueError("Field must contain only English (ASCII) characters")
    return v


class AnalysisOutput(BaseModel):
    analysis: str
    key_signals: List[str]
    detected_issues: List[str]
    root_cause_hypothesis: str
    business_risks: List[str]
    confidence_score: float

    @field_validator("analysis", "root_cause_hypothesis")
    @classmethod
    def string_fields_must_be_english(cls, v: str) -> str:
        return _assert_ascii(v)

    @field_validator("key_signals", "detected_issues", "business_risks")
    @classmethod
    def list_items_must_be_english(cls, v: List[str]) -> List[str]:
        for item in v:
            _assert_ascii(item)
        return v


def _loads_json(payload: str) -> Dict[str, Any]:
    """Parse JSON strictly.

    With response_format={"type":"json_object"}, the model should already return valid JSON.
    """
    return json.loads(payload)


def _clean_nans(value: Any) -> Any:
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {k: _clean_nans(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean_nans(v) for v in value]
    return value


def parse_analysis_output_json(text: str) -> Dict[str, Any]:
    data = _loads_json(text)
    return _clean_nans(data)


def validate_analysis_output(text: str) -> AnalysisOutput:
    data = parse_analysis_output_json(text)
    model = AnalysisOutput(**data)
    if not model.analysis.strip():
        raise ValueError("Missing or empty 'analysis'")
    if not model.root_cause_hypothesis.strip():
        raise ValueError("Missing or empty 'root_cause_hypothesis'")

    # Allow either 0–1 or 0–100.
    score = float(model.confidence_score or 0)
    if 0.0 <= score <= 1.0:
        score *= 100.0
    score = max(0.0, min(100.0, score))
    model.confidence_score = round(score, 2)
    return model
