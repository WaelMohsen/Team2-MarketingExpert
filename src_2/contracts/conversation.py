"""Strict contracts for privacy-safe conversation signal extraction."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MessageRole(str, Enum):
    CUSTOMER = "customer"
    AGENT = "agent"


class ConversationPurpose(str, Enum):
    PURCHASE = "purchase"
    PRODUCT_INFORMATION = "product_information"
    PROMOTION_INFORMATION = "promotion_information"
    DELIVERY_INFORMATION = "delivery_information"
    SUPPORT = "support"
    COMPLAINT = "complaint"
    RETURN_OR_REFUND = "return_or_refund"
    WRONG_NUMBER = "wrong_number"
    ADVERSARIAL = "adversarial"
    OTHER = "other"
    UNKNOWN = "unknown"


class PurchaseIntentLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class ConversationStage(str, Enum):
    DISCOVERY = "discovery"
    CONSIDERATION = "consideration"
    CHECKOUT = "checkout"
    POST_PURCHASE = "post_purchase"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class BarrierType(str, Enum):
    PRICE = "price"
    PRODUCT_AVAILABILITY = "product_availability"
    PRODUCT_QUALITY = "product_quality"
    PRODUCT_FIT = "product_fit"
    DELIVERY = "delivery"
    TIMING = "timing"
    PAYMENT = "payment"
    FINANCING = "financing"
    PROMOTION_CONFUSION = "promotion_confusion"
    TRUST = "trust"
    AGENT_EXPERIENCE = "agent_experience"
    OTHER = "other"


class UrgencyLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class PriceSensitivityLevel(str, Enum):
    NONE = "none"
    INTEREST = "interest"
    SENSITIVE = "sensitive"
    BLOCKING = "blocking"
    UNKNOWN = "unknown"


class DealSeekingLevel(str, Enum):
    NONE = "none"
    INTERESTED = "interested"
    REQUIRED = "required"
    UNKNOWN = "unknown"


class DeliveryIntentLevel(str, Enum):
    NONE = "none"
    QUESTION = "question"
    READINESS = "readiness"
    CHECKOUT_DETAILS = "checkout_details"
    UNKNOWN = "unknown"


class AgreementLevel(str, Enum):
    NONE = "none"
    PARTIAL = "partial"
    COMPLETE = "complete"
    UNKNOWN = "unknown"


class SpecificityLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class FinancingLevel(str, Enum):
    NONE = "none"
    INQUIRY = "inquiry"
    CONSIDERATION = "consideration"
    STRONG = "strong"
    UNKNOWN = "unknown"


class BarrierSeverity(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    BLOCKING = "blocking"
    UNKNOWN = "unknown"


class BarrierResolution(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    UNCLEAR = "unclear"
    NOT_APPLICABLE = "not_applicable"


class ValueDriver(str, Enum):
    PRICE = "price"
    QUALITY = "quality"
    GIFTING = "gifting"
    HEALTH = "health"
    CONVENIENCE = "convenience"
    DELIVERY_SPEED = "delivery_speed"
    TRUST = "trust"
    PRODUCT_FIT = "product_fit"
    OTHER = "other"


class StatedExitReason(str, Enum):
    PRICE = "price"
    AVAILABILITY = "availability"
    PRODUCT_FIT = "product_fit"
    DELIVERY = "delivery"
    PAYMENT = "payment"
    TRUST = "trust"
    CHOSE_ALTERNATIVE = "chose_alternative"
    CHANGED_MIND = "changed_mind"
    OTHER = "other"
    NOT_STATED = "not_stated"
    UNKNOWN = "unknown"


class AdMessageMatchLevel(str, Enum):
    ALIGNED = "aligned"
    PARTIAL = "partial"
    MISMATCH = "mismatch"
    UNKNOWN = "unknown"


class AgentRating(str, Enum):
    POOR = "poor"
    ADEQUATE = "adequate"
    GOOD = "good"
    STRONG = "strong"
    NOT_ASSESSABLE = "not_assessable"


class AgentToneLabel(str, Enum):
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    EMPATHETIC = "empathetic"
    NEUTRAL = "neutral"
    PERSUASIVE = "persuasive"
    CONCISE = "concise"
    INFORMATIVE = "informative"
    APOLOGETIC = "apologetic"
    IMPATIENT = "impatient"
    DISMISSIVE = "dismissive"
    AGGRESSIVE = "aggressive"
    CONFUSING = "confusing"
    OTHER = "other"


class AgentToneQuality(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"
    NOT_ASSESSABLE = "not_assessable"


class CommercialTrait(str, Enum):
    BRAND_PREFERENCE = "brand_preference"
    FEATURE_PRIORITY = "feature_priority"
    BULK_PURCHASE_INTEREST = "bulk_purchase_interest"
    CUSTOMIZATION_INTEREST = "customization_interest"


class CommercialTraitStrength(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class SemanticMessage(StrictModel):
    message_index: int = Field(ge=0)
    role: MessageRole
    relative_minute: float | None
    redacted_text: str
    product_references: list[str]


class SemanticConversationInput(StrictModel):
    language: str | None
    messages: list[SemanticMessage]


class PurchaseIntentSignal(StrictModel):
    level: PurchaseIntentLevel
    elicited_by_agent: bool
    evidence_message_indexes: list[int]


class BarrierSignal(StrictModel):
    barrier_type: BarrierType
    description: str
    evidence_message_indexes: list[int]
    severity: BarrierSeverity = BarrierSeverity.UNKNOWN
    resolution: BarrierResolution = BarrierResolution.UNCLEAR


class UrgencySignal(StrictModel):
    level: UrgencyLevel
    evidence_message_indexes: list[int]
    elicited_by_agent: bool | None = None


class PriceSensitivitySignal(StrictModel):
    level: PriceSensitivityLevel
    evidence_message_indexes: list[int]


class DealSeekingSignal(StrictModel):
    level: DealSeekingLevel
    evidence_message_indexes: list[int]


class DeliveryIntentSignal(StrictModel):
    level: DeliveryIntentLevel
    evidence_message_indexes: list[int]
    elicited_by_agent: bool | None = None


class SalesAgreementSignal(StrictModel):
    level: AgreementLevel
    agreed_elements: list[str]
    evidence_message_indexes: list[int]


class SpecificitySignal(StrictModel):
    level: SpecificityLevel
    evidence_message_indexes: list[int]


class FinancingSignal(StrictModel):
    level: FinancingLevel
    evidence_message_indexes: list[int]


class CommercialTraitSignal(StrictModel):
    trait: CommercialTrait
    strength: CommercialTraitStrength
    detail: str | None
    evidence_message_indexes: list[int]


class CompetitorMentionSignal(StrictModel):
    mentioned: bool
    reference: str | None
    evidence_message_indexes: list[int]


class ValueDriverSignal(StrictModel):
    driver: ValueDriver
    evidence_message_indexes: list[int]


class StatedExitReasonSignal(StrictModel):
    reason: StatedExitReason
    evidence_message_indexes: list[int]


class NextStepAgreementSignal(StrictModel):
    agreed: bool | None
    next_step: str | None
    evidence_message_indexes: list[int]


class AdMessageContext(StrictModel):
    creative_name: str | None
    headline: str | None
    message: str | None
    description: str | None
    theme: str | None
    angle: str | None


class AdMessageMatchSignal(StrictModel):
    level: AdMessageMatchLevel
    rationale: str | None
    evidence_message_indexes: list[int]


class MentionedProduct(StrictModel):
    product_reference: str
    canonical_product_id: str | None
    evidence_message_indexes: list[int]


class AgentEvaluation(StrictModel):
    helpfulness: AgentRating
    needs_discovery: AgentRating
    objection_handling: AgentRating
    progression: AgentRating
    tone: AgentRating
    evidence_message_indexes: list[int]


class AgentToneSignal(StrictModel):
    labels: list[AgentToneLabel]
    quality: AgentToneQuality
    evidence_message_indexes: list[int]


class ConversationSignals(StrictModel):
    conversation_purpose: ConversationPurpose
    customer_need: str | None
    purchase_intent: PurchaseIntentSignal
    barriers: list[BarrierSignal]
    mentioned_products: list[MentionedProduct]
    conversation_stage: ConversationStage
    agent_evaluation: AgentEvaluation
    conversation_summary: str
    not_assessable_reasons: list[str]
    urgency: UrgencySignal = Field(
        default_factory=lambda: UrgencySignal(
            level=UrgencyLevel.UNKNOWN, evidence_message_indexes=[]
        )
    )
    price_sensitivity: PriceSensitivitySignal = Field(
        default_factory=lambda: PriceSensitivitySignal(
            level=PriceSensitivityLevel.UNKNOWN, evidence_message_indexes=[]
        )
    )
    deal_seeking: DealSeekingSignal = Field(
        default_factory=lambda: DealSeekingSignal(
            level=DealSeekingLevel.UNKNOWN, evidence_message_indexes=[]
        )
    )
    delivery_intent: DeliveryIntentSignal = Field(
        default_factory=lambda: DeliveryIntentSignal(
            level=DeliveryIntentLevel.UNKNOWN, evidence_message_indexes=[]
        )
    )
    sales_agreement: SalesAgreementSignal = Field(
        default_factory=lambda: SalesAgreementSignal(
            level=AgreementLevel.UNKNOWN,
            agreed_elements=[],
            evidence_message_indexes=[],
        )
    )
    competitor_mention: CompetitorMentionSignal = Field(
        default_factory=lambda: CompetitorMentionSignal(
            mentioned=False, reference=None, evidence_message_indexes=[]
        )
    )
    value_drivers: list[ValueDriverSignal] = Field(default_factory=list)
    stated_exit_reason: StatedExitReasonSignal = Field(
        default_factory=lambda: StatedExitReasonSignal(
            reason=StatedExitReason.UNKNOWN, evidence_message_indexes=[]
        )
    )
    next_step_agreed: NextStepAgreementSignal = Field(
        default_factory=lambda: NextStepAgreementSignal(
            agreed=None, next_step=None, evidence_message_indexes=[]
        )
    )
    specificity: SpecificitySignal = Field(
        default_factory=lambda: SpecificitySignal(
            level=SpecificityLevel.UNKNOWN, evidence_message_indexes=[]
        )
    )
    financing: FinancingSignal = Field(
        default_factory=lambda: FinancingSignal(
            level=FinancingLevel.UNKNOWN, evidence_message_indexes=[]
        )
    )
    commercial_traits: list[CommercialTraitSignal] = Field(default_factory=list)
    agent_tone: AgentToneSignal = Field(
        default_factory=lambda: AgentToneSignal(
            labels=[],
            quality=AgentToneQuality.NOT_ASSESSABLE,
            evidence_message_indexes=[],
        )
    )


class ConversationAttribution(StrictModel):
    source_platform: str | None
    campaign_id: str | None
    adset_id: str | None
    ad_id: str | None
    creative_id: str | None
    audience_type: str | None


class LLMTokenUsage(StrictModel):
    """API-reported token usage plus an auditable pricing snapshot."""

    request_count: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    reasoning_output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    model: str | None = None
    input_usd_per_million: float | None = Field(default=None, ge=0)
    cached_input_usd_per_million: float | None = Field(default=None, ge=0)
    output_usd_per_million: float | None = Field(default=None, ge=0)
    pricing_as_of: str | None = None
    estimated_cost_usd: float | None = Field(default=None, ge=0)


class ConversationSignalRecord(StrictModel):
    conversation_id: str
    attribution: ConversationAttribution
    input_projection_version: str = "semantic-input-v1"
    prompt_version: str
    prompt_sha256: str
    model: str
    extracted_at: datetime
    signals: ConversationSignals
    signal_schema_version: int = Field(default=1, ge=1)
    ad_message_match: AdMessageMatchSignal = Field(
        default_factory=lambda: AdMessageMatchSignal(
            level=AdMessageMatchLevel.UNKNOWN,
            rationale=None,
            evidence_message_indexes=[],
        )
    )
    ad_match_prompt_version: str | None = None
    ad_match_prompt_sha256: str | None = None
    ad_match_model: str | None = None
    semantic_usage: LLMTokenUsage = Field(default_factory=LLMTokenUsage)
    ad_match_usage: LLMTokenUsage = Field(default_factory=LLMTokenUsage)
