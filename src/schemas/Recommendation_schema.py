from typing import List, Optional
import json

from pydantic import BaseModel, ValidationError


class RecommendationValidationError(ValueError):
    """Raised when an LLM response is not valid recommendation JSON."""


# -----------------------------
# Nested Models
# -----------------------------
class ActionStep(BaseModel):
    '''This model captures the details of each action step in the recommendation.'''
    step: str
    where: str
    how: str
    guardrails: List[str]

class ExpectedImpact(BaseModel):
    '''This model captures the expected impact of the recommendation.'''
    primary_kpi: str
    direction: str
    explanation: str

class MeasurementPlan(BaseModel):
    '''This model captures the details of how to measure the impact of the recommendation.'''
    how_to_measure: str
    success_criteria: str
    check_timing: str
    notes: str

# -----------------------------
# Recommendation Model
# -----------------------------
class Recommendation(BaseModel):
    ''' Model representing a single recommendation. '''
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
    ''' Root model for the recommendation response. '''
    recommendations: List[Recommendation]

def validate_recommendation_response(response_text: str) -> List[Recommendation]:
    '''Validates recommendation JSON and returns typed recommendation objects.'''
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise RecommendationValidationError(
            f"Recommendation response is not valid JSON: {exc}"
        ) from exc

    try:
        validated = RecommendationResponse.model_validate(data)
    except ValidationError as exc:
        raise RecommendationValidationError(
            f"Recommendation response does not match expected schema: {exc}"
        ) from exc

    return validated.recommendations
