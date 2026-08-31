"""Basic source inventory checks before canonical normalization."""

from dataclasses import dataclass

from src_2.contracts.cycle import DataQualityReport
from src_2.domain.models import EvidenceStatus

from .loaders import RawCyclePayload
from .normalizer import CanonicalCycleData

REQUIRED_META_COLLECTIONS = ("campaigns", "adsets", "ads", "creatives", "insights")


@dataclass(frozen=True)
class SourceInventory:
    campaigns: int
    adsets: int
    ads: int
    creatives: int
    insights: int
    conversations: int
    products: int


def inventory(payload: RawCyclePayload) -> SourceInventory:
    missing = [key for key in REQUIRED_META_COLLECTIONS if key not in payload.meta]
    if missing:
        raise ValueError(f"Missing Meta collections: {', '.join(missing)}")
    for key in REQUIRED_META_COLLECTIONS:
        if not isinstance(payload.meta[key], list):
            raise ValueError(f"Meta collection {key!r} must be a JSON array")
    return SourceInventory(
        campaigns=len(payload.meta["campaigns"]),
        adsets=len(payload.meta["adsets"]),
        ads=len(payload.meta["ads"]),
        creatives=len(payload.meta["creatives"]),
        insights=len(payload.meta["insights"]),
        conversations=len(payload.conversations),
        products=len(payload.products),
    )


def build_data_quality_report(data: CanonicalCycleData) -> DataQualityReport:
    """Reconcile source coverage and hierarchy joins without assuming event parity."""

    meta_starts = int(round(float(data.media_daily["meta_conversation_starts"].sum())))
    observed = data.conversations[
        data.conversations["source_platform"].eq("meta_ctwa")
    ].copy()
    observed_count = int(observed["conversation_id"].nunique())
    ratio = observed_count / meta_starts if meta_starts else None

    campaign_ids = set(data.campaigns["campaign_id"])
    adset_ids = set(data.adsets["adset_id"])
    ad_ids = set(data.ads["ad_id"])
    unmatched_campaigns = int((~observed["campaign_id"].isin(campaign_ids)).sum())
    unmatched_adsets = int((~observed["adset_id"].isin(adset_ids)).sum())
    unmatched_ads = int((~observed["ad_id"].isin(ad_ids)).sum())
    open_or_pending = int(data.conversations["is_open_or_pending"].sum())
    repeated_customers = int(
        data.conversations.loc[
            data.conversations["is_repeated_customer_in_cycle"], "customer_id"
        ].nunique()
    )
    organic_direct = int(
        data.conversations["source_platform"].isin({"organic", "direct"}).sum()
    )
    invalid_reach_rows = int(data.media_daily["reach_exceeds_impressions"].sum())

    warnings: list[str] = []
    if ratio is not None and ratio < 0.8:
        warnings.append(
            "Meta-attributed conversation starts and supplied WhatsApp records are not reconciled populations; outcome rankings describe the observed sample."
        )
    if unmatched_campaigns or unmatched_adsets or unmatched_ads:
        warnings.append(
            "Some supplied Meta-sourced conversations could not be joined to the Meta hierarchy."
        )
    if open_or_pending:
        warnings.append(
            f"{open_or_pending} active or stuck-pending conversations are unresolved and are excluded from mature-outcome rate denominators."
        )
    if repeated_customers:
        warnings.append(
            f"{repeated_customers} customers occur more than once; customer-level rates are reported alongside conversation-level rates."
        )
    if organic_direct:
        warnings.append(
            f"{organic_direct} organic/direct conversations are retained as context and excluded from paid-campaign scoring."
        )
    if invalid_reach_rows:
        warnings.append(
            f"{invalid_reach_rows} Meta insight rows report reach greater than impressions; reach-dependent metrics are not decision-grade."
        )
    warnings.append(
        "Daily reach is non-additive across dates; summed daily reach is retained only as a diagnostic proxy, not unique cycle reach."
    )
    if ratio is None:
        status = EvidenceStatus.DATA_NOT_READY
        warnings.append("No Meta conversation-start denominator is available.")
    else:
        # The supplied files do not establish that Meta actions and WhatsApp rows
        # use compatible event definitions, windows, and deduplication rules.
        status = EvidenceStatus.LIMITED

    return DataQualityReport(
        status=status,
        meta_conversation_starts=meta_starts,
        observed_meta_whatsapp_conversations=observed_count,
        reconciliation_ratio=ratio,
        event_definitions_reconciled=False,
        unmatched_campaigns=unmatched_campaigns,
        unmatched_adsets=unmatched_adsets,
        unmatched_ads=unmatched_ads,
        open_or_pending_conversations=open_or_pending,
        repeated_customers=repeated_customers,
        organic_direct_conversations=organic_direct,
        reach_exceeds_impressions_rows=invalid_reach_rows,
        daily_reach_is_non_additive=True,
        warnings=warnings,
    )
