import json
import math
from typing import Any, Dict, List

from pydantic import BaseModel


class RecommendationActionStep(BaseModel):
    step: str
    where: str
    how: str
    guardrails: List[str]


class ExpectedImpact(BaseModel):
    primary_kpi: str
    direction: str
    explanation: str


class MeasurementPlan(BaseModel):
    how_to_measure: str
    success_criteria: str
    check_timing: str
    notes: str


class RecommendationCard(BaseModel):
    id: str
    title: str
    category: str
    priority: str
    effort: str
    time_to_see_impact: str
    confidence: str
    whats_happening: str
    evidence: List[str]
    what_you_should_do: List[RecommendationActionStep]
    why_this_matters: str
    expected_impact: ExpectedImpact
    dependency_or_risk: List[str]
    measurement_plan: MeasurementPlan
    owner_suggestion: str


class RecommendationOutput(BaseModel):
    recommendations: List[RecommendationCard]


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


def parse_recommendation_output_json(text: str) -> Dict[str, Any]:
    data = _loads_json(text)
    data = _clean_nans(data)
    return data


def validate_recommendation_output(text: str) -> RecommendationOutput:
    data = parse_recommendation_output_json(text)
    model = RecommendationOutput(**data)

    if not isinstance(model.recommendations, list):
        raise ValueError("'recommendations' must be a list")
    if len(model.recommendations) < 5 or len(model.recommendations) > 8:
        raise ValueError("'recommendations' must contain 5–8 items")

    for rec in model.recommendations:
        if not rec.title.strip():
            raise ValueError("Each recommendation must have a non-empty 'title'")
        if not rec.evidence:
            raise ValueError(
                "Each recommendation must have a non-empty 'evidence' list"
            )
        if not rec.what_you_should_do:
            raise ValueError(
                "Each recommendation must have a non-empty 'what_you_should_do' list"
            )

    return model
