from src.evaluation.recommendation.business_relevance_evaluator import (
    BusinessRelevanceEvaluator,
)
from src.evaluation.recommendation.prompt_compliance_evaluator import (
    PromptComplianceEvaluator,
)


def test_business_relevance_accepts_json_response_string():
    evaluator = BusinessRelevanceEvaluator(
        lambda prompt, model, temp: """
        {
          "overall": {
            "scores": {
              "insight_quality": 1.0,
              "actionability": 1.0,
              "data_grounding": 1.0,
              "kpi_alignment": 1.0,
              "priority_accuracy": 1.0,
              "decision_quality": 1.0,
              "feasibility": 1.0,
              "readability": 1.0
            },
            "explanations": {}
          },
          "per_recommendation": [
            {
              "id": "rec-1",
              "scores": {
                "insight_quality": 0.4,
                "actionability": 0.4,
                "data_grounding": 0.4,
                "kpi_alignment": 0.4,
                "decision_quality": 0.4,
                "feasibility": 0.4
              },
              "issues": ["needs more evidence"]
            }
          ]
        }
        """
    )

    result = evaluator.evaluate(
        recs=[{"id": "rec-1"}],
        analysis={"summary": "Some analysis"},
        kpis=["ctr"],
        model="gpt-test",
        temp=0,
    )

    assert result["score"] == 1.0
    assert result["weak_recommendations"] == ["rec-1"]
    assert result["flags"] == []


def test_business_relevance_accepts_python_literal_response_string():
    evaluator = BusinessRelevanceEvaluator(
        lambda prompt, model, temp: "{'overall': {'scores': {'insight_quality': 0.5, 'actionability': 0.5, 'data_grounding': 0.5, 'kpi_alignment': 0.5, 'priority_accuracy': 0.5, 'decision_quality': 0.5, 'feasibility': 0.5, 'readability': 0.5}, 'explanations': {}}, 'per_recommendation': []}"
    )

    result = evaluator.evaluate(
        recs=[{"id": "rec-1"}],
        analysis={"summary": "Some analysis"},
        kpis=["ctr"],
        model="gpt-test",
        temp=0,
    )

    assert result["score"] == 0.5
    assert "low_insight_quality" in result["flags"]


def test_prompt_compliance_uses_safe_parser_and_rounds_score():
    evaluator = PromptComplianceEvaluator(
        lambda prompt, model, temp: (
            '{"no_hallucination": 1.0, "clarity": 0.3333333333, '
            '"non_repetition": 1.0}'
        )
    )

    result = evaluator.evaluate(
        recommendations=[
            {
                "title": "Improve landing page",
                "priority": "Low",
                "what_you_should_do": ["Update headline"],
                "evidence": ["CTR down"],
            },
            {
                "title": "Refine audience",
                "priority": "High",
                "what_you_should_do": ["Exclude low intent users"],
                "evidence": ["CPC up"],
            },
        ],
        analysis={"summary": "Some analysis"},
        kpis=["ctr"],
        model="gpt-test",
        temp=0,
    )

    assert result["dimensions"]["clarity"] == 0.3333333333
    assert result["score"] == 0.556
    assert "invalid_recommendation_count" in result["flags"]
    assert "priority_not_sorted" in result["flags"]
