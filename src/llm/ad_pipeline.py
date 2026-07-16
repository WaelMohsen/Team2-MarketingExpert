"""Per-ad analysis -> recommendation pipeline, driven by the parent
campaign's type.

Same two-step flow as src/llm/campaign_pipeline.py, one level down:
  data/processed/ad_kpis.csv        (one row per ad, from scripts/extract_campaign_kpis.py)
  data/processed/campaign_kpis.csv  (parent-campaign baseline)
  data/processed/campaign_type_kpis.csv (type baseline)
  config/campaign_type_rubric.json  (rubric keyed by the parent campaign's type)

Usage:
  python -m src.llm.ad_pipeline 120209876543210025
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
from .campaign_pipeline import (
    COMPONENT_COLS,
    OUTPUT_LOG_DIR,
    _derive_kpis,
    _processed_path,
    _repo_root_dir,
    _row_to_clean_dict,
    load_rubric,
)

# Campaign-structure KPIs that do not exist for a single ad.
NOT_AD_LEVEL = {"ads_tested", "unique_creatives"}

AD_IDENTITY_COLS = {
    "ad_id", "ad_name", "campaign_id", "campaign_name", "campaign_type",
    "adset_name", "audience_type", "optimization_goal", "creative_id",
    "creative_theme", "creative_angle", "creative_headline", "creative_message",
    "start_date", "end_date", "status",
}


def build_ad_context(ad_id: str) -> Dict[str, Any]:
    """Assemble everything the LLM needs to judge one ad."""
    ads = pd.read_csv(_processed_path("ad_kpis.csv"), dtype={"ad_id": str, "campaign_id": str})
    campaigns = pd.read_csv(_processed_path("campaign_kpis.csv"), dtype={"campaign_id": str})
    types = pd.read_csv(_processed_path("campaign_type_kpis.csv"))
    rubric = load_rubric()

    match = ads[ads["ad_id"] == str(ad_id)]
    if match.empty:
        known = ", ".join(ads["ad_id"])
        raise ValueError(f"Ad not found: {ad_id}. Known ids: {known}")
    ad = _row_to_clean_dict(match.iloc[0])

    ctype = ad["campaign_type"]
    type_rubric = rubric.get(ctype)
    if type_rubric is None:
        raise ValueError(f"No rubric entry for campaign_type: {ctype}")

    campaign_match = campaigns[campaigns["campaign_id"] == ad["campaign_id"]]
    campaign_baseline = (
        _row_to_clean_dict(campaign_match.iloc[0]) if not campaign_match.empty else {}
    )
    type_match = types[types["campaign_type"] == ctype]
    type_baseline = _row_to_clean_dict(type_match.iloc[0]) if not type_match.empty else {}

    account_components = {
        col: float(campaigns[col].fillna(0).sum()) for col in COMPONENT_COLS if col in campaigns
    }
    account_baseline = {**account_components, **_derive_kpis(account_components)}

    # Primary KPIs come from the parent campaign's type; drop the ones that only
    # exist at campaign level (e.g. ads_tested for experimental campaigns).
    primary = [k for k in type_rubric["primary_kpis"] if k not in NOT_AD_LEVEL]
    skipped = [k for k in type_rubric["primary_kpis"] if k in NOT_AD_LEVEL]

    # An ad is always smaller than its campaign — absolute volumes only make
    # sense as a share of the parent, so precompute those shares.
    def _share(field):
        total = campaign_baseline.get(field) or 0
        return round((ad.get(field) or 0) / total, 4) if total else None

    share_of_campaign = {
        "spend": _share("spend"),
        "ctwa_conversations": _share("ctwa_conversations"),
        "orders_created": _share("orders_created"),
        "delivered_orders": _share("delivered_orders"),
        "net_revenue": _share("net_revenue"),
    }

    return {
        "ad_id": ad["ad_id"],
        "ad_name": ad["ad_name"],
        "campaign_type": ctype,
        "rubric": type_rubric,
        "identity": {k: ad.get(k) for k in AD_IDENTITY_COLS},
        "primary_kpis": {k: ad.get(k) for k in primary},
        "skipped_campaign_level_kpis": skipped,
        "supporting_kpis": {
            k: v for k, v in ad.items() if k not in AD_IDENTITY_COLS and k not in primary
        },
        "share_of_campaign": share_of_campaign,
        "campaign_baseline": campaign_baseline,
        "type_baseline": type_baseline,
        "account_baseline": account_baseline,
    }


def build_context_block(context: Dict[str, Any]) -> str:
    rubric = context["rubric"]
    skipped = context["skipped_campaign_level_kpis"]
    skipped_note = (
        f"\n        (These rubric KPIs exist only at campaign level and are skipped"
        f" for a single ad: {skipped})\n" if skipped else ""
    )
    return f"""
        BUSINESS:
        Egyptian online grocery selling via Meta click-to-WhatsApp ads.
        Orders are created and delivered through WhatsApp conversations.

        UNIT UNDER ANALYSIS: a SINGLE AD inside a campaign.
        {json.dumps(context['identity'], ensure_ascii=False)}

        CAMPAIGN TYPE RUBRIC (the parent campaign's type defines success):
        - campaign_type: {context['campaign_type']}
        - target_job: {rubric['target_job']}
        - success_question: {rubric['success_question']}
        - primary_kpis (judge on these): {list(context['primary_kpis'])}{skipped_note}
        PRIMARY KPI VALUES (this ad):
        {json.dumps(context['primary_kpis'], ensure_ascii=False)}

        SUPPORTING KPIs (context only — do not judge success on these):
        {json.dumps(context['supporting_kpis'], ensure_ascii=False)}

        THIS AD'S SHARE OF ITS PARENT CAMPAIGN (fraction of the campaign's total):
        {json.dumps(context['share_of_campaign'], ensure_ascii=False)}

        PEER BASELINE — the ad's parent campaign as a whole:
        {json.dumps(context['campaign_baseline'], ensure_ascii=False)}

        PEER BASELINE — all '{context['campaign_type']}' campaigns combined:
        {json.dumps(context['type_baseline'], ensure_ascii=False)}

        PEER BASELINE — whole account (all 12 campaigns combined):
        {json.dumps(context['account_baseline'], ensure_ascii=False)}

        IMPORTANT:
        - Judge the ad primarily against its PARENT CAMPAIGN baseline (is this
          ad pulling the campaign up or dragging it down?), then the wider ones.
        - NEVER compare the ad's absolute volumes (conversations, orders,
          revenue, spend) against the campaign's totals as if they were peers —
          an ad is a PART of its campaign. For volumes, use the share figures
          above (e.g. a 0.60 conversation share on a 0.45 spend share means the
          ad over-delivers). For rates and costs, compare values directly.
        - Use the creative theme/angle/headline and audience targeting to explain
          WHY the numbers look the way they do.
        - Write for a business lead with no marketing background.
        - Keep wording simple and practical.
        - Avoid abbreviations in the final JSON text.
    """


def save_output(output: dict, ad_id: str):
    os.makedirs(OUTPUT_LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(OUTPUT_LOG_DIR, f"ad_pipeline_{ad_id}_{timestamp}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
    print(f"Output saved to {filename}")
    return filename


def generate_ad_response(
    ad_id: str,
    analysis_model: Optional[str] = None,
    analysis_temp: Optional[float] = None,
    rec_model: Optional[str] = None,
    rec_temp: Optional[float] = None,
) -> Dict[str, Any]:
    """Two-step flow for one ad: analysis JSON -> recommendation JSON."""
    # Imported lazily to avoid a circular import (src.evaluation imports
    # src.llm at module load).
    from src.evaluation.run_config import load_run_config

    generation = load_run_config().generation
    analysis_model = analysis_model or generation.analysis_model
    analysis_temp = generation.analysis_temp if analysis_temp is None else analysis_temp
    rec_model = rec_model or generation.recommendation_model
    rec_temp = generation.recommendation_temp if rec_temp is None else rec_temp

    client = get_client()
    context = build_ad_context(ad_id)
    context_block = build_context_block(context)

    # Step 1: type-aware diagnostic analysis (same system prompt as campaigns;
    # the context block declares the unit is a single ad).
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

    # Step 2: recommendations for this specific ad.
    rec_sys = load_target_prompt(
        os.path.join(_repo_root_dir(), "prompts", "recommendation_system_prompt.md")
    )
    rec_user = f"""
        You are in Step 2 (Recommendation).

        Use the context below PLUS the Step 1 analysis JSON
        to produce the final report JSON.

        Recommendations must be about THIS SINGLE AD (its creative, audience,
        budget share, or whether to scale/pause it) and must serve the parent
        campaign's target job by moving its primary KPIs:
        {list(context['primary_kpis'])}

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
        "ad_id": context["ad_id"],
        "ad_name": context["ad_name"],
        "campaign_id": context["identity"]["campaign_id"],
        "campaign_name": context["identity"]["campaign_name"],
        "campaign_type": context["campaign_type"],
        "rubric": context["rubric"],
        "primary_kpis": context["primary_kpis"],
        "analysis": analysis_parsed.model_dump(),
        "recommendations": [rec.model_dump() for rec in rec_parsed.recommendations],
    }
    save_output(combined, context["ad_id"])
    return combined


if __name__ == "__main__":
    target_id = sys.argv[1] if len(sys.argv) > 1 else "120209876543210025"
    result = generate_ad_response(target_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))
