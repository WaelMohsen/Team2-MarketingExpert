"""Typed objects exchanged between pipeline stages."""

from .assessment import CampaignAssessment, MetricAssessment
from .cycle import CycleManifest, DataQualityReport
from .evaluation import (
    EVALUATION_SCHEMA_VERSION,
    CampaignEvaluation,
    ConsistencyCheck,
    CriterionScore,
    EvaluationReport,
)
from .evidence import CampaignEvidencePack, EntityEvidence, MetricEvidence
from .insight import (
    CampaignInsight,
    CampaignTypeLesson,
    EvidenceReference,
    PortfolioInsight,
)
from .recommendation import BudgetAllocation, BudgetScenario, StakeholderReport

__all__ = [
    "BudgetAllocation",
    "BudgetScenario",
    "CampaignAssessment",
    "CampaignEvaluation",
    "CampaignEvidencePack",
    "CampaignInsight",
    "CampaignTypeLesson",
    "ConsistencyCheck",
    "CriterionScore",
    "CycleManifest",
    "DataQualityReport",
    "EVALUATION_SCHEMA_VERSION",
    "EntityEvidence",
    "EvaluationReport",
    "EvidenceReference",
    "MetricAssessment",
    "MetricEvidence",
    "PortfolioInsight",
    "StakeholderReport",
]
