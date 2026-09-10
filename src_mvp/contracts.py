"""Small, strict contracts for scoring and the recommendation handoff."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EntityLevel(str, Enum):
    CAMPAIGN = "campaign"
    ADSET = "adset"
    AD = "ad"
    CREATIVE = "creative"
    AUDIENCE = "audience"


class EvidenceStatus(str, Enum):
    NONE = "none"
    LIMITED = "limited"
    SUFFICIENT = "sufficient"


class StatisticalDecision(str, Enum):
    SCALE = "scale"
    HOLD = "hold"
    KILL = "kill"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class NextCycleAction(str, Enum):
    SCALE = "scale"
    KEEP_AS_TEST = "keep_as_test"
    DO_NOT_FUND = "do_not_fund"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EfficiencyComparison(str, Enum):
    BETTER = "better_than_peer"
    EQUAL = "equal_to_peer"
    WORSE = "worse_than_peer"
    UNAVAILABLE = "unavailable"


class BenchmarkScope(str, Enum):
    SAME_OBJECTIVE = "same_objective"
    SHARED_PRIMARY_KPI_GROUP = "shared_primary_kpi_group"
    UNAVAILABLE = "unavailable"


class BenchmarkQuality(str, Enum):
    DECISION_GRADE = "decision_grade"
    PROVISIONAL = "provisional"
    UNAVAILABLE = "unavailable"


class SemanticContract(StrictModel):
    metric: Literal["ad_alignment", "meaningful_conversation", "qualified_conversation", "checkout_readiness"]
    definition: str
    minimum_customers: int = Field(default=10, ge=1)
    minimum_peers: int = Field(default=2, ge=2)


class ObjectiveContract(StrictModel):
    objective: str
    business_job: str
    success_question: str
    primary_metric: str
    primary_numerator: str
    primary_denominator: str
    primary_direction: Literal["higher", "lower"]
    efficiency_metric: str
    efficiency_direction: Literal["higher", "lower"]
    minimum_trials: int = Field(ge=1)
    minimum_peer_entities: int = Field(ge=1)
    fallback_benchmark_group: Optional[str] = None
    semantic: SemanticContract


class EvidenceSummary(StrictModel):
    successes: float = Field(ge=0)
    trials: float = Field(ge=0)
    observed_conversations: int = Field(ge=0)
    mature_conversations: int = Field(ge=0)
    unresolved_conversations: int = Field(ge=0)
    unique_customers: int = Field(ge=0)
    mature_unique_customers: int = Field(ge=0)
    evidence_status: EvidenceStatus


class PrimaryScore(StrictModel):
    metric: str
    numerator: str
    denominator: str
    direction: Literal["higher", "lower"]
    raw_rate: Optional[float] = Field(default=None, ge=0, le=1)
    corrected_rate: Optional[float] = Field(default=None, ge=0, le=1)
    range_low: Optional[float] = Field(default=None, ge=0, le=1)
    range_high: Optional[float] = Field(default=None, ge=0, le=1)
    benchmark: Optional[float] = Field(default=None, ge=0, le=1)
    benchmark_peer_count: int = Field(ge=0)
    same_objective_peer_count: int = Field(ge=0)
    benchmark_scope: BenchmarkScope
    benchmark_quality: BenchmarkQuality
    portfolio_context_benchmark: Optional[float] = Field(default=None, ge=0, le=1)
    portfolio_context_peer_count: int = Field(ge=0)
    expected_lift: Optional[float] = None
    lift_low: Optional[float] = None
    lift_high: Optional[float] = None
    probability_better: Optional[float] = Field(default=None, ge=0, le=1)
    statistical_decision: StatisticalDecision


class EfficiencyEvidence(StrictModel):
    metric: str
    direction: Literal["higher", "lower"]
    value: Optional[float] = None
    benchmark: Optional[float] = None
    benchmark_peer_count: int = Field(ge=0)
    comparison: EfficiencyComparison
    reliability: Literal["accepted_for_mvp"] = "accepted_for_mvp"


class DeliverySummary(StrictModel):
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    running_days: int = Field(ge=0)
    active_days: int = Field(ge=0)
    impressions: float = Field(ge=0)
    link_clicks: float = Field(ge=0)


class BusinessOutcomes(StrictModel):
    spend: float = Field(ge=0)
    created_orders: int = Field(ge=0)
    delivered_orders: int = Field(ge=0)
    net_revenue: float = Field(ge=0)


class ConversationDiagnostics(StrictModel):
    semantic_conversations: int = Field(ge=0)
    semantic_coverage_rate: Optional[float] = Field(default=None, ge=0, le=1)
    high_purchase_intent_rate: Optional[float] = Field(default=None, ge=0, le=1)
    price_blocking_rate: Optional[float] = Field(default=None, ge=0, le=1)
    barrier_resolution_rate: Optional[float] = Field(default=None, ge=0, le=1)
    ad_alignment_rate: Optional[float] = Field(default=None, ge=0, le=1)
    agent_helpful_rate: Optional[float] = Field(default=None, ge=0, le=1)
    next_step_agreement_rate: Optional[float] = Field(default=None, ge=0, le=1)
    next_step_order_progression_rate: Optional[float] = Field(
        default=None, ge=0, le=1
    )
    top_customer_need: Optional[str] = None
    top_barrier: Optional[str] = None
    top_value_driver: Optional[str] = None


class SemanticScore(StrictModel):
    metric: str
    definition: str
    unit: Literal["earliest_mature_conversation_per_customer"] = "earliest_mature_conversation_per_customer"
    eligible_customers: int = Field(ge=0)
    successes: int = Field(ge=0)
    trials: int = Field(ge=0)
    unknown_customers: int = Field(ge=0)
    missing_customers: int = Field(ge=0)
    raw_rate: Optional[float] = Field(default=None, ge=0, le=1)
    corrected_rate: Optional[float] = Field(default=None, ge=0, le=1)
    range_low: Optional[float] = Field(default=None, ge=0, le=1)
    range_high: Optional[float] = Field(default=None, ge=0, le=1)
    prior_alpha: float = Field(gt=0)
    prior_beta: float = Field(gt=0)
    posterior_alpha: float = Field(gt=0)
    posterior_beta: float = Field(gt=0)
    prior_source: Literal["same_objective_empirical", "jeffreys_no_peer_comparison"]
    benchmark: Optional[float] = None
    peer_count: int = Field(ge=0)
    lift_low: Optional[float] = None
    lift_high: Optional[float] = None
    probability_better: Optional[float] = None
    status: Literal["supportive", "neutral", "concerning", "insufficient_evidence", "no_peer_comparison"]
    evidence_status: EvidenceStatus
    validation_status: Literal["automated_labels_unreviewed"] = "automated_labels_unreviewed"


class EntityScore(StrictModel):
    entity_level: EntityLevel
    entity_id: str
    entity_name: str
    campaign_id: str
    parent_entity_id: Optional[str] = None
    objective: str
    attributes: Dict[str, Any]
    delivery: DeliverySummary
    evidence: EvidenceSummary
    primary_score: PrimaryScore
    efficiency: EfficiencyEvidence
    business_outcomes: BusinessOutcomes
    diagnostics: ConversationDiagnostics
    semantic_score: SemanticScore
    recommended_action: NextCycleAction
    reason_codes: List[str]


class BudgetAllocation(StrictModel):
    campaign_id: str
    campaign_name: str
    objective: str
    action: NextCycleAction
    budget_pool: Literal["score_based", "unallocated"]
    objective_envelope_units: float = Field(ge=0)
    allocation_weight: float = Field(ge=0, le=1)
    recommended_budget_units: float = Field(ge=0)
    recommended_budget_share: float = Field(ge=0, le=1)
    allocation_basis: str = "previous_cycle_spend"
    primary_probability_component: Optional[float] = Field(default=None, ge=0, le=1)
    semantic_priority: Optional[float] = None
    allocation_priority: Optional[float] = Field(default=None, ge=0)
    previous_spend_budget_units: float = Field(default=0, ge=0)
    reason_codes: List[str]


class ExplorationTest(StrictModel):
    campaign_id: str
    campaign_name: str
    objective: str
    assigned_budget_units: float = Field(ge=0)
    hypothesis: str
    primary_metric: str
    success_rule: str
    failure_rule: str
    stop_rule: str


class CycleSummary(StrictModel):
    cycle_id: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    currency: str
    budget_mode: Literal["normalized_units", "currency"]
    next_budget_amount: float = Field(ge=0)


class DecisionPolicy(StrictModel):
    allocation_mode: Literal["score_based"]
    objective_envelope_basis: Literal["previous_cycle_spend_share"]
    campaign_weight: Literal["primary_probability_x_semantic_lower_bound"]
    missing_component_rule: Literal["zero_allocation"]
    concentration_cap: Optional[float] = Field(default=None, ge=0, le=1)
    scale_rule: str
    kill_rule: str
    hold_rule: str


class DataScope(StrictModel):
    paid_attributed_conversations: int = Field(ge=0)
    semantic_conversations: int = Field(ge=0)
    semantic_coverage_rate: Optional[float] = Field(default=None, ge=0, le=1)
    outcome_data_assumption: Literal["complete_for_cycle"]
    financial_metrics_reliability: Literal["accepted_for_mvp"]
    conversation_prompt_version: Optional[str] = None
    ad_match_prompt_version: Optional[str] = None


class ChildEvidence(StrictModel):
    successes: float = Field(ge=0)
    trials: float = Field(ge=0)
    evidence_status: EvidenceStatus


class ChildPrimaryScore(StrictModel):
    raw_rate: Optional[float] = Field(default=None, ge=0, le=1)
    corrected_rate: Optional[float] = Field(default=None, ge=0, le=1)
    range_low: Optional[float] = Field(default=None, ge=0, le=1)
    range_high: Optional[float] = Field(default=None, ge=0, le=1)
    benchmark: Optional[float] = Field(default=None, ge=0, le=1)
    benchmark_peer_count: int = Field(ge=0)
    same_objective_peer_count: int = Field(ge=0)
    benchmark_scope: BenchmarkScope
    benchmark_quality: BenchmarkQuality
    portfolio_context_benchmark: Optional[float] = Field(default=None, ge=0, le=1)
    portfolio_context_peer_count: int = Field(ge=0)
    lift_low: Optional[float] = None
    lift_high: Optional[float] = None
    probability_better: Optional[float] = Field(default=None, ge=0, le=1)
    statistical_decision: StatisticalDecision


class ChildEfficiency(StrictModel):
    value: Optional[float] = None
    benchmark: Optional[float] = None
    comparison: EfficiencyComparison


class ChildEntityScore(StrictModel):
    entity_level: EntityLevel
    entity_id: str
    entity_name: str
    parent_entity_id: Optional[str] = None
    attributes: Dict[str, Any]
    evidence: ChildEvidence
    primary_score: ChildPrimaryScore
    efficiency: ChildEfficiency
    spend: float = Field(ge=0)
    diagnostics: ConversationDiagnostics
    semantic_score: SemanticScore
    recommended_action: NextCycleAction
    reason_codes: List[str]


class CampaignPackage(StrictModel):
    campaign: EntityScore
    allocation: BudgetAllocation
    child_entities: List[ChildEntityScore]


class RecommendationInput(StrictModel):
    schema_version: Literal["recommendation-input-v3"]
    generated_at: datetime
    cycle: CycleSummary
    decision_policy: DecisionPolicy
    data_scope: DataScope
    objective_contracts: List[ObjectiveContract]
    campaigns: List[CampaignPackage]
    exploration_tests: List[ExplorationTest]
    unallocated_budget_units: float = Field(ge=0)


class EvidenceReference(StrictModel):
    entity_level: EntityLevel
    entity_id: str
    statement: str


class CampaignNarrative(StrictModel):
    campaign_id: str
    action: NextCycleAction
    decision_explanation: str
    budget_explanation: str
    strongest_supported_entities: List[str]
    weakest_supported_entities: List[str]
    conversation_lessons: List[str]
    evidence_references: List[EvidenceReference]


class RecommendationReport(StrictModel):
    executive_summary: str
    budget_summary: str
    campaign_recommendations: List[CampaignNarrative]
    objective_lessons: List[str]
    strategic_lessons: List[str]
    test_plan_summary: List[str]
    assumptions: List[str]
