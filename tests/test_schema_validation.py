import json

import pytest
from src.schemas.analysis_output_schema import AnalysisOutput, validate_analysis_output
from src.schemas.recommendation_output_schema import validate_recommendation_output


def _recommendation_card(overrides=None):
    card = {
        "id": "REC-01",
        "title": "Improve landing page speed",
        "category": "Landing_Page",
        "priority": "High",
        "effort": "Medium",
        "time_to_see_impact": "1-2 weeks",
        "confidence": "High",
        "whats_happening": "People click but do not buy.",
        "evidence": ["Clicks are high while conversions are low."],
        "what_you_should_do": [
            {
                "step": "Compress images",
                "where": "website",
                "how": "Use modern formats and lazy-load below the fold.",
                "guardrails": ["Do not reduce readability"],
            }
        ],
        "why_this_matters": "Faster pages usually lead to more sales.",
        "expected_impact": {
            "primary_kpi": "Sales",
            "direction": "Increase",
            "explanation": "Less waiting reduces drop-off.",
        },
        "dependency_or_risk": ["Needs web team time"],
        "measurement_plan": {
            "how_to_measure": "Compare sales before and after",
            "success_criteria": "Sales increase",
            "check_timing": "2 weeks",
            "notes": "Allow for seasonality",
        },
        "owner_suggestion": "Web team",
    }
    if overrides:
        card.update(overrides)
    return card


def test_analysis_valid_strict_json_scales_confidence_fraction_to_percent():
    payload = {
        "analysis": "OK",
        "key_signals": ["s"],
        "detected_issues": ["i"],
        "root_cause_hypothesis": "r",
        "business_risks": ["b"],
        "confidence_score": 0.72,
    }

    model = validate_analysis_output(json.dumps(payload))
    assert model.confidence_score == 72.0


def test_analysis_missing_required_text_fields_raises_value_error():
    payload = {
        "analysis": "   ",
        "key_signals": [],
        "detected_issues": [],
        "root_cause_hypothesis": "r",
        "business_risks": [],
        "confidence_score": 0.5,
    }

    with pytest.raises(ValueError):
        validate_analysis_output(json.dumps(payload))


def test_analysis_broken_json_is_rejected_in_strict_json_mode():
    # In strict JSON mode, "almost JSON" should be rejected.
    broken = "{ 'analysis': 'ok', 'key_signals': ['s1',], 'detected_issues': ['i1',], 'root_cause_hypothesis': 'r', 'business_risks': ['b',], 'confidence_score': 0.8, }"
    with pytest.raises(json.JSONDecodeError):
        validate_analysis_output(broken)


def test_analysis_output_to_json_returns_valid_json_and_preserves_unicode():
    model = AnalysisOutput(
        analysis="Café analysis",
        key_signals=["Signal"],
        detected_issues=["Issue"],
        root_cause_hypothesis="Root cause",
        business_risks=["Risk"],
        confidence_score=55.5,
    )

    json_str = json.dumps(model.dict(), ensure_ascii=False)
    parsed = json.loads(json_str)

    assert parsed["analysis"] == "Café analysis"
    assert parsed["confidence_score"] == 55.5
    assert set(parsed.keys()) == {
        "analysis",
        "key_signals",
        "detected_issues",
        "root_cause_hypothesis",
        "business_risks",
        "confidence_score",
    }


def test_recommendations_valid_5_cards_passes():
    payload = {
        "recommendations": [
            _recommendation_card({"id": f"REC-0{i}"}) for i in range(1, 6)
        ]
    }
    model = validate_recommendation_output(json.dumps(payload))
    assert len(model.recommendations) == 5


def test_recommendations_wrong_count_raises_value_error():
    payload = {
        "recommendations": [
            _recommendation_card({"id": f"REC-0{i}"}) for i in range(1, 5)
        ]
    }
    with pytest.raises(ValueError):
        validate_recommendation_output(json.dumps(payload))


def test_recommendations_empty_evidence_raises_value_error():
    payload = {
        "recommendations": [
            _recommendation_card({"id": f"REC-0{i}", "evidence": []})
            for i in range(1, 6)
        ]
    }
    with pytest.raises(ValueError):
        validate_recommendation_output(json.dumps(payload))


def test_recommendations_broken_json_python_dict_repr_is_rejected_in_strict_json_mode():
    # Python dict repr (single quotes) is not valid JSON and should fail.
    payload = {
        "recommendations": [
            _recommendation_card({"id": f"REC-0{i}"}) for i in range(1, 6)
        ]
    }
    broken = str(payload)
    with pytest.raises(json.JSONDecodeError):
        validate_recommendation_output(broken)
