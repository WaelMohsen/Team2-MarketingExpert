import json
from typing import List, Optional

from pydantic import BaseModel, field_validator

from .validators import assert_ascii

# -----------------------------
# Nested Models
# -----------------------------


class ActionStep(BaseModel):
    step: str
    where: str
    how: str
    guardrails: List[str]

    @field_validator("step", "where", "how")
    @classmethod
    def string_fields_ascii(cls, v: str) -> str:
        return assert_ascii(v)

    @field_validator("guardrails")
    @classmethod
    def list_fields_ascii(cls, v: List[str]) -> List[str]:
        for item in v:
            assert_ascii(item)
        return v


class ExpectedImpact(BaseModel):
    primary_kpi: str
    direction: str
    explanation: str

    @field_validator("primary_kpi", "direction", "explanation")
    @classmethod
    def string_fields_ascii(cls, v: str) -> str:
        return _assert_ascii(v)


class MeasurementPlan(BaseModel):
    how_to_measure: str
    success_criteria: str
    check_timing: str
    notes: str

    @field_validator("how_to_measure", "success_criteria", "check_timing", "notes")
    @classmethod
    def string_fields_ascii(cls, v: str) -> str:
        return _assert_ascii(v)


# -----------------------------
# Recommendation Model
# -----------------------------


class Recommendation(BaseModel):
    id: str
    title: str
    category: str
    priority: str
    effort: str
    time_to_see_impact: str
    confidence: str

    whats_happening: str
    evidence: List[str]

    what_you_should_do: List[ActionStep]

    why_this_matters: Optional[str] = None

    expected_impact: ExpectedImpact

    dependency_or_risk: List[str]

    measurement_plan: MeasurementPlan

    owner_suggestion: str

    @field_validator(
        "id",
        "title",
        "category",
        "priority",
        "effort",
        "time_to_see_impact",
        "confidence",
        "whats_happening",
        "owner_suggestion",
    )
    @classmethod
    def string_fields_ascii(cls, v: str) -> str:
        return _assert_ascii(v)

    @field_validator("why_this_matters")
    @classmethod
    def optional_string_ascii(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            _assert_ascii(v)
        return v

    @field_validator("evidence", "dependency_or_risk")
    @classmethod
    def list_fields_ascii(cls, v: List[str]) -> List[str]:
        for item in v:
            _assert_ascii(item)
        return v


# -----------------------------
# Root Response Model
# -----------------------------


class RecommendationResponse(BaseModel):
    recommendations: List[Recommendation]


def validate_recommendation_response(response_text: str):

    try:
        data = json.loads(response_text)
        validated = RecommendationResponse(**data)
        print("Recommendations validated successfuly")
        return validated.recommendations

    except Exception as e:
        print(f"Recommendation validation error: {e}")
