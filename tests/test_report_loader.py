import json

import pytest

from src.evaluation.report_loader import (
    build_candidate_from_report_file,
    load_marketing_report,
    select_benchmark_cases,
)
from src.evaluation import RecommendationBenchmarkRepository


def _report_payload() -> dict:
    return {
        "correlation_id": "abc123",
        "category": "Customer Retention",
        "analysis": {
            "analysis": "Retention is weakening and churn is rising.",
            "key_signals": ["Retention rate fell week over week."],
            "detected_issues": ["Churn increased among newer customers."],
            "root_cause_hypothesis": "Follow-up and onboarding are not engaging users quickly enough.",
            "business_risks": ["Repeat revenue may decline."],
            "confidence_score": 80.0,
        },
        "recommendations": [
            {
                "id": "retention-1",
                "title": "Launch segmented follow-up campaign",
                "category": "Customer Retention",
                "priority": "High",
                "effort": "Medium",
                "time_to_see_impact": "2 weeks",
                "confidence": "High",
                "whats_happening": "Customer retention is weakening and churn is rising.",
                "evidence": ["Churn rate increased and retention rate declined."],
                "what_you_should_do": [
                    {
                        "step": "Launch a segmented follow-up campaign",
                        "where": "CRM",
                        "how": "Target churn-risk customers with a win-back and onboarding sequence.",
                        "guardrails": ["Avoid spamming recent purchasers."],
                    }
                ],
                "why_this_matters": "It protects repeat revenue.",
                "expected_impact": {
                    "primary_kpi": "Retention rate",
                    "direction": "Increase",
                    "explanation": "At-risk customers receive timely intervention.",
                },
                "dependency_or_risk": ["Needs lifecycle operations support."],
                "measurement_plan": {
                    "how_to_measure": "Compare retention before and after the campaign.",
                    "success_criteria": "Retention rate improves by 5%.",
                    "check_timing": "2 weeks",
                    "notes": "Monitor by segment.",
                },
                "owner_suggestion": "Lifecycle team",
            }
        ]
        * 5,
    }


def test_load_marketing_report_from_output_log_payload(tmp_path):
    report_file = tmp_path / "pipeline_output_example.json"
    report_file.write_text(json.dumps(_report_payload()), encoding="utf-8")

    report = load_marketing_report(report_file)

    assert report.category == "Customer Retention"
    assert report.analysis.confidence_score == 80.0
    assert len(report.recommendations) == 5


def test_build_candidate_from_report_file_merges_parameter_settings(tmp_path):
    report_file = tmp_path / "saved_report.json"
    payload = _report_payload()
    payload["parameter_settings"] = {"temperature": 0.2}
    report_file.write_text(json.dumps(payload), encoding="utf-8")

    candidate = build_candidate_from_report_file(
        report_file,
        parameter_settings={"prompt_version": "v2"},
    )

    assert candidate.candidate_id == "saved_report"
    assert candidate.parameter_settings == {"temperature": 0.2, "prompt_version": "v2"}


def test_select_benchmark_cases_filters_by_case_id():
    cases = RecommendationBenchmarkRepository().load_cases()

    selected = select_benchmark_cases(cases, case_id="retention-risk-001")

    assert len(selected) == 1
    assert selected[0].category == "Customer Retention"


def test_select_benchmark_cases_raises_for_unknown_case():
    cases = RecommendationBenchmarkRepository().load_cases()

    with pytest.raises(ValueError, match="No benchmark case found"):
        select_benchmark_cases(cases, case_id="missing-case")
