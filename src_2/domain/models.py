"""Stable business vocabulary shared across the v2 pipeline."""

from enum import Enum


class CampaignType(str, Enum):
    AWARENESS = "awareness"
    ALWAYS_ON = "always_on"
    PROMOTIONAL = "promotional"
    SEASONAL = "seasonal"
    EXPERIMENTAL = "experimental"
    LAUNCH = "launch"
    SCALE = "scale"
    RETENTION = "retention"


class EntityLevel(str, Enum):
    CAMPAIGN = "campaign"
    ADSET = "adset"
    AD = "ad"
    CREATIVE = "creative"
    AUDIENCE = "audience"


class BudgetPool(str, Enum):
    CORE = "core"
    TEST = "test"


class EvidenceStatus(str, Enum):
    READY = "ready"
    LIMITED = "limited_evidence"
    INSUFFICIENT = "insufficient_evidence"
    DATA_NOT_READY = "data_not_ready"


class FundingDecision(str, Enum):
    """Three-way statistical recommendation for the next completed cycle."""

    SCALE = "scale"
    HOLD = "hold"
    KILL = "kill"
