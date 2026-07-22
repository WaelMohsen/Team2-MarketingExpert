"""Typed objects exchanged between pipeline stages."""

from .assessment import CampaignAssessment, MetricAssessment
from .cycle import CycleManifest, DataQualityReport
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
    "CampaignEvidencePack",
    "CampaignInsight",
    "CampaignTypeLesson",
    "CycleManifest",
    "DataQualityReport",
    "EntityEvidence",
    "EvidenceReference",
    "MetricAssessment",
    "MetricEvidence",
    "PortfolioInsight",
    "StakeholderReport",
]
