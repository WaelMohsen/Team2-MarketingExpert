"""Deterministic narratives used when an LLM is unavailable or unnecessary."""

from __future__ import annotations

from collections import Counter
from typing import Sequence

from src_2.contracts import (
    BudgetScenario,
    CampaignAssessment,
    CampaignEvidencePack,
    CampaignInsight,
    CampaignTypeLesson,
    EvidenceReference,
    PortfolioInsight,
    StakeholderReport,
)
from src_2.domain.models import EntityLevel


def _format_metric(value: float | None) -> str:
    return "not available" if value is None else f"{value:,.2f}"


def _metric(entity, name: str):
    return next((item for item in entity.metrics if item.metric == name), None)


def _best_entity(entities, metric: str, minimum_evidence: int):
    candidates = []
    for entity in entities:
        value = _metric(entity, metric)
        observations = _metric(entity, "observed_conversations")
        if (
            value is not None
            and value.actual is not None
            and observations is not None
            and (observations.actual or 0) >= minimum_evidence
        ):
            candidates.append((value.actual, entity))
    return max(candidates, default=(None, None), key=lambda item: item[0])[1]


class DeterministicCampaignAnalyst:
    def analyze(self, evidence: CampaignEvidencePack) -> CampaignInsight:
        primary = evidence.primary_kpis[0]
        result = "met" if primary.passed else "did not meet"
        target_assessment = (
            f"The {evidence.campaign_type.value.replace('_', ' ')} campaign {result} "
            f"its primary {primary.label} reference: {_format_metric(primary.actual)} "
            f"versus {_format_metric(primary.benchmark)}."
        )
        references = [
            EvidenceReference(
                entity_level=EntityLevel.CAMPAIGN,
                entity_id=evidence.campaign_id,
                metric=item.metric,
                actual=item.actual,
                benchmark=item.benchmark,
            )
            for item in [*evidence.primary_kpis, *evidence.supporting_kpis[:3]]
        ]
        drivers = [
            f"{item.label}: {_format_metric(item.actual)}"
            for item in evidence.supporting_kpis[:3]
        ]
        best_audience = _best_entity(evidence.audiences, "net_roas", 5)
        best_creative = _best_entity(evidence.creatives, "net_roas", 3)
        audience_findings = []
        creative_findings = []
        if best_audience is not None:
            roas = _metric(best_audience, "net_roas")
            audience_findings.append(
                f"{best_audience.entity_name} has the strongest observed audience-level net ROAS ({_format_metric(roas.actual)})."
            )
        if best_creative is not None:
            roas = _metric(best_creative, "net_roas")
            angle = best_creative.dimensions.get("angle")
            creative_findings.append(
                f"{best_creative.entity_name} has the strongest observed creative-level net ROAS ({_format_metric(roas.actual)})"
                + (f" with the {angle} angle." if angle else ".")
            )
        risks = list(evidence.limitations[:2])
        risks.append(
            "Audience, creative, timing, and spend often changed together, so observed winners are hypotheses rather than causal proof."
        )
        controlled_test = None
        if best_audience is not None or best_creative is not None:
            audience_name = best_audience.entity_name if best_audience else "the current audience"
            creative_name = best_creative.entity_name if best_creative else "the current creative"
            controlled_test = (
                f"Test {audience_name} and {creative_name} in matched cells with the same budget, timing, offer, and optimization settings."
            )
        return CampaignInsight(
            campaign_id=evidence.campaign_id,
            target_assessment=target_assessment,
            supporting_evidence=references,
            performance_drivers=drivers,
            audience_findings=audience_findings,
            creative_findings=creative_findings,
            risks_and_confounders=risks,
            strategic_lesson=(
                f"Use {primary.label} to judge the campaign job, then use supporting outcomes to explain why it happened; do not replace the objective with a blended score."
            ),
            next_controlled_test=controlled_test,
            evidence_status=evidence.evidence_status,
        )


class DeterministicPortfolioSynthesizer:
    def synthesize(
        self,
        assessments: Sequence[CampaignAssessment],
        insights: Sequence[CampaignInsight],
    ) -> PortfolioInsight:
        target_counts = Counter(item.target_status.value for item in assessments)
        action_counts = Counter(item.next_cycle_action.value for item in assessments)
        lessons_by_campaign_type: dict[str, list[str]] = {}
        for assessment, insight in zip(assessments, insights):
            lessons_by_campaign_type.setdefault(
                assessment.campaign_type.value, []
            ).append(insight.strategic_lesson)
        campaign_type_lessons = [
            CampaignTypeLesson(campaign_type=campaign_type, lessons=lessons)
            for campaign_type, lessons in sorted(lessons_by_campaign_type.items())
        ]
        return PortfolioInsight(
            cycle_id=assessments[0].cycle_id if assessments else "unknown",
            repeated_patterns=[
                f"{target_counts.get('achieved_with_concerns', 0)} campaigns met their primary benchmark with evidence concerns.",
                f"{action_counts.get('keep_as_test', 0)} campaigns remain test candidates rather than operational scale decisions.",
            ],
            conflicting_results=[
                "Strong Meta delivery does not consistently correspond to strong observed WhatsApp order economics."
            ],
            campaign_type_lessons=campaign_type_lessons,
            portfolio_risks=[
                "The Meta conversation-start population is not reconciled to the supplied WhatsApp outcome population.",
                "Current-cycle peer medians are provisional benchmarks, not approved profitability targets.",
            ],
            tests_to_prioritize=[
                insight.next_controlled_test
                for insight in insights
                if insight.next_controlled_test
            ][:5],
        )


class DeterministicReportNarrator:
    def narrate(
        self, portfolio: PortfolioInsight, budget: BudgetScenario
    ) -> StakeholderReport:
        funded = [item for item in budget.allocations if item.budget_units > 0]
        funded.sort(key=lambda item: item.budget_units, reverse=True)
        leaders = ", ".join(
            f"{item.entity_name} ({item.budget_units:.1f} units)" for item in funded[:3]
        )
        return StakeholderReport(
            cycle_id=portfolio.cycle_id,
            executive_summary=(
                f"This completed-cycle report assigns {sum(item.budget_units for item in funded):.1f} "
                f"of {budget.total_budget_units:.0f} illustrative units. The leading candidates are {leaders or 'none'}."
            ),
            business_owner_sections=[
                "Review observed net revenue, return on ad spend, unallocated budget, and the evidence warning before approving money.",
                f"{budget.unallocated_units:.1f} units remain unallocated because blocked campaigns are not automatically redistributed.",
            ],
            marketing_director_sections=[
                "Compare campaigns against the job of their campaign type, not one universal KPI.",
                "Carry repeated lessons into the next brief and reserve controlled cells for unresolved audience and creative questions.",
            ],
            performance_manager_sections=[
                "Use campaign decisions as parent guardrails, then inspect adset, audience, ad, and creative evidence before trafficking the next cycle.",
                "Scale is not operational while evidence is limited; matched tests are the appropriate next action.",
            ],
            data_limitations=portfolio.portfolio_risks,
        )
