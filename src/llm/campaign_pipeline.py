"""Per-campaign analysis -> recommendation pipeline, driven by campaign type.

Data flow:
  data/processed/campaign_kpis.csv       (one row per campaign, from scripts/extract_campaign_kpis.py)
  data/processed/campaign_type_kpis.csv  (one row per campaign type, peer baseline)
  config/campaign_type_rubric.json       (target job / success question / primary KPIs per type)
        |
        v
  build_campaign_context(campaign_id)    -> context block (rubric + campaign KPIs + baselines)
        |
        v
  Step 1: analysis LLM  (prompts/campaign_analysis_system_prompt.md)  -> AnalysisOutput JSON
  Step 2: recommendation LLM (prompts/recommendation_system_prompt.md) -> RecommendationOutput JSON

Usage:
  python -m src.llm.campaign_pipeline 120209876543220002
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from src.llm.client import chat_completion, get_client
from src.llm.prompts import load_target_prompt

from ..schemas.analysis_output_schema import AnalysisOutput, validate_analysis_output
from ..schemas.recommendation_output_schema import (
    RecommendationOutput,
    validate_recommendation_output,
)

OUTPUT_LOG_DIR = "output_log"

# Raw components summed to build the whole-account baseline.
COMPONENT_COLS = [
    "impressions", "reach", "clicks", "link_clicks", "spend", "active_days",
    "ctwa_conversations", "repeat_conversations", "negative_outcomes",
    "orders_created", "gross_revenue", "delivered_orders", "net_revenue",
    "repeat_delivered_orders", "unique_products_ordered", "ads_tested",
    "unique_creatives",
]


def _repo_root_dir() -> str:
    this_file = os.path.abspath(__file__)
    return os.path.dirname(os.path.dirname(os.path.dirname(this_file)))


def _processed_path(name: str) -> str:
    return os.path.join(_repo_root_dir(), "data", "processed", name)


def load_rubric() -> Dict[str, Any]:
    path = os.path.join(_repo_root_dir(), "config", "campaign_type_rubric.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _safe_div(num, den):
    return round(num / den, 4) if den else None


def _derive_kpis(base: Dict[str, float]) -> Dict[str, Optional[float]]:
    """Same ratio formulas as scripts/extract_campaign_kpis.py, applied to
    summed components (used here for the whole-account baseline)."""
    impressions = base.get("impressions", 0)
    spend = base.get("spend", 0)
    convs = base.get("ctwa_conversations", 0)
    delivered = base.get("delivered_orders", 0)
    net_rev = base.get("net_revenue", 0)
    return {
        "frequency": _safe_div(impressions, base.get("reach", 0)),
        "cpm": _safe_div(spend * 1000, impressions),
        "link_ctr_pct": _safe_div(base.get("link_clicks", 0) * 100, impressions),
        "net_roas": _safe_div(net_rev, spend),
        "delivered_rate": _safe_div(delivered, base.get("orders_created", 0)),
        "cost_per_delivered_order": _safe_div(spend, delivered),
        "cost_per_ctwa": _safe_div(spend, convs),
        "order_creation_rate": _safe_div(base.get("orders_created", 0), convs),
        "aov": _safe_div(net_rev, delivered),
        "negative_outcome_rate": _safe_div(base.get("negative_outcomes", 0), convs),
        "net_revenue_per_day": _safe_div(net_rev, base.get("active_days", 0)),
        "ctwa_conversations_per_day": _safe_div(convs, base.get("active_days", 0)),
        "repeat_conversation_rate": _safe_div(base.get("repeat_conversations", 0), convs),
    }


def _row_to_clean_dict(row: pd.Series) -> Dict[str, Any]:
    clean = {}
    for k, v in row.items():
        if pd.isna(v):
            clean[k] = None
        elif hasattr(v, "item"):  # numpy scalar -> native Python type
            clean[k] = v.item()
        else:
            clean[k] = v
    return clean


def build_campaign_context(campaign_id: str) -> Dict[str, Any]:
    """Assemble everything the LLM needs to judge one campaign."""
    campaigns = pd.read_csv(_processed_path("campaign_kpis.csv"), dtype={"campaign_id": str})
    types = pd.read_csv(_processed_path("campaign_type_kpis.csv"))
    rubric = load_rubric()

    match = campaigns[campaigns["campaign_id"] == str(campaign_id)]
    if match.empty:
        known = ", ".join(campaigns["campaign_id"])
        raise ValueError(f"Campaign not found: {campaign_id}. Known ids: {known}")
    campaign = _row_to_clean_dict(match.iloc[0])

    ctype = campaign["campaign_type"]
    type_rubric = rubric.get(ctype)
    if type_rubric is None:
        raise ValueError(f"No rubric entry for campaign_type: {ctype}")

    type_match = types[types["campaign_type"] == ctype]
    type_baseline = _row_to_clean_dict(type_match.iloc[0]) if not type_match.empty else {}

    account_components = {
        col: float(campaigns[col].fillna(0).sum()) for col in COMPONENT_COLS if col in campaigns
    }
    account_baseline = {**account_components, **_derive_kpis(account_components)}

    primary = type_rubric["primary_kpis"]
    identity_cols = {
        "campaign_id", "campaign_name", "campaign_type", "objective",
        "start_date", "end_date", "status",
    }
    return {
        "campaign_id": campaign["campaign_id"],
        "campaign_name": campaign["campaign_name"],
        "campaign_type": ctype,
        "rubric": type_rubric,
        "identity": {k: campaign[k] for k in identity_cols},
        "primary_kpis": {k: campaign.get(k) for k in primary},
        "supporting_kpis": {
            k: v for k, v in campaign.items() if k not in identity_cols and k not in primary
        },
        "type_baseline": type_baseline,
        "account_baseline": account_baseline,
    }


def build_context_block(context: Dict[str, Any]) -> str:
    rubric = context["rubric"]
    return f"""
        BUSINESS:
        Egyptian online grocery selling via Meta click-to-WhatsApp ads.
        Orders are created and delivered through WhatsApp conversations.

        CAMPAIGN UNDER ANALYSIS:
        {json.dumps(context['identity'], ensure_ascii=False)}

        CAMPAIGN TYPE RUBRIC (this defines success for this campaign):
        - campaign_type: {context['campaign_type']}
        - target_job: {rubric['target_job']}
        - success_question: {rubric['success_question']}
        - primary_kpis (judge on these): {rubric['primary_kpis']}

        PRIMARY KPI VALUES (this campaign):
        {json.dumps(context['primary_kpis'], ensure_ascii=False)}

        SUPPORTING KPIs (context only — do not judge success on these):
        {json.dumps(context['supporting_kpis'], ensure_ascii=False)}

        PEER BASELINE — all '{context['campaign_type']}' campaigns combined:
        {json.dumps(context['type_baseline'], ensure_ascii=False)}

        PEER BASELINE — whole account (all 12 campaigns combined):
        {json.dumps(context['account_baseline'], ensure_ascii=False)}

        IMPORTANT:
        - Write for a business lead with no marketing background.
        - Keep wording simple and practical.
        - Avoid abbreviations in the final JSON text.
    """


def save_output(output: dict, campaign_id: str):
    os.makedirs(OUTPUT_LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(
        OUTPUT_LOG_DIR, f"campaign_pipeline_{campaign_id}_{timestamp}.json"
    )
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
    print(f"Output saved to {filename}")
    return filename


def generate_campaign_response(
    campaign_id: str,
    analysis_model: Optional[str] = None,
    analysis_temp: Optional[float] = None,
    rec_model: Optional[str] = None,
    rec_temp: Optional[float] = None,
) -> Dict[str, Any]:
    """Two-step flow for one campaign: analysis JSON -> recommendation JSON."""
    # Imported lazily to avoid a circular import (src.evaluation imports
    # src.llm at module load).
    from src.evaluation.run_config import load_run_config

    generation = load_run_config().generation
    analysis_model = analysis_model or generation.analysis_model
    analysis_temp = generation.analysis_temp if analysis_temp is None else analysis_temp
    rec_model = rec_model or generation.recommendation_model
    rec_temp = generation.recommendation_temp if rec_temp is None else rec_temp

    client = get_client()
    context = build_campaign_context(campaign_id)
    context_block = build_context_block(context)

    # Step 1: type-aware diagnostic analysis.
    analysis_sys = load_target_prompt(
        os.path.join(_repo_root_dir(), "prompts", "campaign_analysis_system_prompt.md")
    )
    analysis_user = f"""
        You are in Step 1 (Analysis Only).

        Use the context below and return analysis JSON only.

        CONTEXT:
        {context_block}
    """
    analysis_resp = chat_completion(
        client,
        analysis_sys,
        analysis_user,
        response_format=AnalysisOutput,
        model=analysis_model,
        temp=analysis_temp,
    )
    analysis_parsed = analysis_resp.choices[0].message.parsed
    analysis_json_str = json.dumps(analysis_parsed.model_dump(), ensure_ascii=False)
    analysis_parsed = validate_analysis_output(analysis_json_str)
    analysis_json_str = json.dumps(analysis_parsed.model_dump(), ensure_ascii=False)

    # Step 2: recommendations grounded in the analysis and the same context.
    rec_sys = load_target_prompt(
        os.path.join(_repo_root_dir(), "prompts", "recommendation_system_prompt.md")
    )
    rec_user = f"""
        You are in Step 2 (Recommendation).

        Use the context below PLUS the Step 1 analysis JSON
        to produce the final report JSON.

        Recommendations must serve the campaign's target job and move its
        primary KPIs: {context['rubric']['primary_kpis']}

        CONTEXT:
        {context_block}

        STEP 1 ANALYSIS JSON (input):
        {analysis_json_str}
    """
    rec_resp = chat_completion(
        client,
        rec_sys,
        rec_user,
        response_format=RecommendationOutput,
        model=rec_model,
        temp=rec_temp,
    )
    rec_parsed = rec_resp.choices[0].message.parsed
    rec_json_str = json.dumps(rec_parsed.model_dump(), ensure_ascii=False)
    rec_parsed = validate_recommendation_output(rec_json_str)

    combined = {
        "campaign_id": context["campaign_id"],
        "campaign_name": context["campaign_name"],
        "campaign_type": context["campaign_type"],
        "rubric": context["rubric"],
        "primary_kpis": context["primary_kpis"],
        "analysis": analysis_parsed.model_dump(),
        "recommendations": [rec.model_dump() for rec in rec_parsed.recommendations],
    }
    save_output(combined, context["campaign_id"])
    return combined


if __name__ == "__main__":
    target_id = sys.argv[1] if len(sys.argv) > 1 else "120209876543220002"
    result = generate_campaign_response(target_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))
