"""Budget scenario and final report contracts."""

from pydantic import BaseModel, Field

from src_2.domain.assessment_rules import NextCycleAction
from src_2.domain.models import EntityLevel, EvidenceStatus


class BudgetAllocation(BaseModel):
    entity_level: EntityLevel
    entity_id: str
    entity_name: str
    action: NextCycleAction
    budget_units: float = Field(ge=0)
    budget_share_pct: float = Field(ge=0, le=100)
    reason: str


class BudgetScenario(BaseModel):
    cycle_id: str
    scenario_name: str
    total_budget_units: float = Field(gt=0)
    evidence_status: EvidenceStatus
    operational: bool
    assumptions: list[str]
    allocations: list[BudgetAllocation]
    unallocated_units: float = Field(default=0, ge=0)


class StakeholderReport(BaseModel):
    cycle_id: str
    executive_summary: str
    business_owner_sections: list[str] = Field(default_factory=list)
    marketing_director_sections: list[str] = Field(default_factory=list)
    performance_manager_sections: list[str] = Field(default_factory=list)
    data_limitations: list[str] = Field(default_factory=list)
