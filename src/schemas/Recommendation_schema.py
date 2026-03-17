from pydantic import BaseModel
from typing import List , Optional
import json


# -----------------------------
# Nested Models
# -----------------------------

class ActionStep(BaseModel):
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
