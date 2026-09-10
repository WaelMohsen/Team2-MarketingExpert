"""Objective-specific conversation quality, kept separate from outcome scores."""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .config import ObjectiveRegistry
from .contracts import EvidenceStatus, SemanticScore
from .data import CanonicalData
from .scorecards import entity_ids
from .statistics import EmpiricalPrior, _score, _seed, fit_beta_prior


COMMERCIAL_PURPOSES = {
    "purchase", "product_information", "promotion_information", "delivery_information"
}
OTHER_PURPOSES = {
    "support", "complaint", "return_or_refund", "wrong_number", "adversarial", "other"
}


def _label(record: dict, field: str, positive: set, negative: set) -> Optional[bool]:
    signal = (record.get("signals") or {}).get(field) or {}
    value = signal.get("level")
    # A positive score requires traceable evidence in the extracted artifact.
    if value in positive and signal.get("evidence_message_indexes"):
        return True
    if value in negative:
        return False
    return None


def semantic_success(record: Optional[dict], metric: str) -> Optional[bool]:
    """Three-state rule: missing evidence never becomes a negative outcome."""
    if not record:
        return None
    signals = record.get("signals") or {}
    match = record.get("ad_message_match") or {}
    alignment = match.get("level")
    if metric == "ad_alignment":
        if alignment == "aligned" and match.get("evidence_message_indexes"):
            return True
        return False if alignment in {"partial", "mismatch"} else None

    purpose = signals.get("conversation_purpose")
    commercial = True if purpose in COMMERCIAL_PURPOSES else (
        False if purpose in OTHER_PURPOSES else None
    )
    specificity = _label(record, "specificity", {"medium", "high"}, {"none", "low"})
    if metric == "qualified_conversation":
        parts = [commercial, specificity, _label(
            record, "purchase_intent", {"medium", "high"}, {"none", "low"}
        )]
    elif metric == "meaningful_conversation":
        stage = signals.get("conversation_stage")
        progressed = True if stage in {"consideration", "checkout"} else (
            False if stage in {"discovery", "post_purchase", "not_applicable"} else None
        )
        aligned = True if alignment in {"aligned", "partial"} and match.get(
            "evidence_message_indexes"
        ) else (False if alignment == "mismatch" else None)
        parts = [commercial, specificity, progressed, aligned]
    elif metric == "checkout_readiness":
        step = signals.get("next_step_agreed") or {}
        agreed = step.get("agreed")
        if agreed is True and not step.get("evidence_message_indexes"):
            agreed = None
        parts = [commercial, _label(
            record, "sales_agreement", {"complete"}, {"none", "partial"}
        ), agreed]
    else:
        raise ValueError(f"Unknown semantic metric: {metric}")
    return None if any(part is None for part in parts) else all(parts)


def build_semantic_evidence(
    data: CanonicalData, records: List[Dict[str, Any]], registry: ObjectiveRegistry
) -> pd.DataFrame:
    """Select the first mature conversation before inspecting its semantic label."""
    lookup = {}
    for record in records:
        key = str(record["conversation_id"])
        if key in lookup:
            raise ValueError(f"Duplicate semantic conversation: {key}")
        lookup[key] = record
    conversations = data.conversations.merge(
        data.campaigns[["campaign_id", "objective"]], on="campaign_id", validate="many_to_one"
    )
    evidence = []
    for level in ("campaign", "adset", "ad", "creative", "audience"):
        frame = conversations.copy()
        frame["entity_id"] = entity_ids(frame, level)
        frame = frame.dropna(subset=["entity_id"])
        frame = frame.sort_values(["started_at", "conversation_id"], na_position="last")
        selected = frame[frame["is_mature"]].drop_duplicates(["entity_id", "customer_key"])
        selected_ids = set(zip(selected["entity_id"], selected["conversation_id"]))
        for _, row in frame.iterrows():
            key = str(row["conversation_id"])
            record = lookup.get(key)
            contract = registry.objectives[str(row["objective"])].semantic
            selected_row = (row["entity_id"], row["conversation_id"]) in selected_ids
            success = semantic_success(record, contract.metric)
            evidence.append({
                "entity_level": level, "entity_id": row["entity_id"],
                "campaign_id": row["campaign_id"], "objective": row["objective"],
                "conversation_id": key, "metric": contract.metric,
                "selected": selected_row,
                "exclusion_reason": None if selected_row else (
                    "unresolved" if not row["is_mature"] else "repeat_customer"
                ),
                "signal_available": record is not None,
                "success": success,
                "has_order": bool(row["has_order"]),
                "is_delivered": bool(row["is_delivered"]),
            })
    return pd.DataFrame(evidence)


def add_semantic_scores(
    frames: Dict[str, pd.DataFrame], data: CanonicalData,
    records: List[Dict[str, Any]], registry: ObjectiveRegistry,
) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:
    audit = build_semantic_evidence(data, records, registry)
    output = {}
    for level, frame in frames.items():
        selected = audit[audit["entity_level"].eq(level) & audit["selected"]]
        summaries = {}
        for entity_id, group in selected.groupby("entity_id"):
            known = group["success"].notna()
            summaries[entity_id] = {
                "eligible_customers": len(group),
                "successes": int(group.loc[known, "success"].sum()),
                "trials": int(known.sum()),
                "unknown_customers": int((~known & group["signal_available"]).sum()),
                "missing_customers": int((~group["signal_available"]).sum()),
            }
        scores = []
        for _, row in frame.iterrows():
            spec = registry.objectives[str(row["objective"])].semantic
            counts = summaries.get(row["entity_id"], dict(
                eligible_customers=0, successes=0, trials=0,
                unknown_customers=0, missing_customers=0,
            ))
            peers = [summaries[entity_id] for entity_id in frame.loc[
                frame["objective"].eq(row["objective"])
                & frame["entity_id"].ne(row["entity_id"]), "entity_id"
            ] if entity_id in summaries and summaries[entity_id]["trials"] > 0]
            empirical = len(peers) >= spec.minimum_peers
            prior = fit_beta_prior(
                [p["successes"] for p in peers], [p["trials"] for p in peers]
            ) if empirical else EmpiricalPrior(0.5, 0.5, 0)
            s, n = counts["successes"], counts["trials"]
            evidence_status = EvidenceStatus.NONE if not n else (
                EvidenceStatus.SUFFICIENT if n >= spec.minimum_customers else EvidenceStatus.LIMITED
            )
            values = {}
            status = "insufficient_evidence"
            if n:
                estimate = _score(s, n, prior, "higher", _seed(level, str(row["entity_id"]), spec.metric))
                values = {key: estimate[key] for key in (
                    "raw_rate", "corrected_rate", "range_low", "range_high"
                )}
                if empirical:
                    values.update({key: estimate[key] for key in (
                        "benchmark", "lift_low", "lift_high", "probability_better"
                    )})
                if evidence_status == EvidenceStatus.SUFFICIENT:
                    status = {"scale": "supportive", "hold": "neutral", "kill": "concerning"}[
                        estimate["statistical_decision"]
                    ] if empirical else "no_peer_comparison"
            scores.append(SemanticScore(
                metric=spec.metric, definition=spec.definition, **counts, **values,
                prior_alpha=prior.alpha, prior_beta=prior.beta,
                posterior_alpha=prior.alpha + s, posterior_beta=prior.beta + n - s,
                prior_source="same_objective_empirical" if empirical else "jeffreys_no_peer_comparison",
                peer_count=len(peers), status=status, evidence_status=evidence_status,
            ).model_dump(mode="json"))
        output[level] = frame.assign(semantic_score=scores)
    return output, audit
