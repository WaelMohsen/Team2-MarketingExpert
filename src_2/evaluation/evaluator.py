"""Evaluate the narrative in a completed-cycle report against its evidence."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

from src_2.application.reporting import CompletedCycleReport
from src_2.contracts import CampaignEvaluation, EvaluationReport
from src_2.evaluation.consistency import consistency_passed, run_consistency_checks
from src_2.evaluation.store import prompt_version


class NarrativeEvaluator:
    """Deterministic-first evaluator.

    The consistency layer runs today with no LLM cost. An LLM ``InsightJudge``
    can later populate ``criterion_scores`` / ``overall_score`` on each
    ``CampaignEvaluation`` without changing this class's shape.
    """

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5-mini")

    def evaluate(self, report: CompletedCycleReport) -> EvaluationReport:
        assessments = {item.campaign_id: item for item in report.assessments}
        campaign_evaluations: list[CampaignEvaluation] = []

        for insight in report.insights:
            pack = report.campaign_evidence(insight.campaign_id)
            assessment = assessments[insight.campaign_id]
            checks = run_consistency_checks(insight, pack, assessment)
            campaign_evaluations.append(
                CampaignEvaluation(
                    campaign_id=insight.campaign_id,
                    campaign_name=pack.campaign_name,
                    evidence_summary={
                        "campaign_type": pack.campaign_type.value,
                        "business_job": pack.business_job,
                        "evidence_status": pack.evidence_status.value,
                        "target_status": assessment.target_status.value,
                        "next_cycle_action": assessment.next_cycle_action.value,
                        "primary_kpis": [
                            {
                                "label": m.label,
                                "actual": m.actual,
                                "benchmark": m.benchmark,
                                "passed": m.passed,
                            }
                            for m in pack.primary_kpis
                        ],
                    },
                    narrative={
                        "target_assessment": insight.target_assessment,
                        "strategic_lesson": insight.strategic_lesson,
                        "performance_drivers": insight.performance_drivers,
                        "risks_and_confounders": insight.risks_and_confounders,
                        "next_controlled_test": insight.next_controlled_test,
                    },
                    consistency_checks=checks,
                    consistency_passed=consistency_passed(checks),
                )
            )

        total = len(campaign_evaluations)
        passed = sum(1 for c in campaign_evaluations if c.consistency_passed)
        scored = [c.overall_score for c in campaign_evaluations if c.overall_score is not None]

        return EvaluationReport(
            run_id=uuid4().hex[:12],
            run_timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            cycle_id=report.manifest.cycle_id,
            model=self.model,
            prompt_version=prompt_version(),
            campaigns_evaluated=total,
            consistency_pass_rate=round(passed / total, 3) if total else 0.0,
            mean_overall_score=round(sum(scored) / len(scored), 3) if scored else None,
            campaign_evaluations=campaign_evaluations,
        )
