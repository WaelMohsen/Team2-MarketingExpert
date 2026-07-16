"""Extract per-campaign and per-campaign-type KPIs from the raw JSON data.

Joins data/meta_data.json (campaigns, adsets, ads, creatives, daily insights)
with data/conversations.json (CTWA/organic/direct WhatsApp conversations and
order outcomes) and data/products.json.

Outputs (data/processed/):
  campaign_kpis.csv / .json          one row per campaign, all KPIs
  campaign_type_kpis.csv / .json     one row per campaign_type, aggregated KPIs
  campaign_type_summary.json         rubric (target_job / success_question /
                                     primary_kpis) merged with the computed
                                     values of each type's primary KPIs

Run:  python scripts/extract_campaign_kpis.py
"""

import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
OUT_DIR = DATA_DIR / "processed"
RUBRIC_PATH = REPO_ROOT / "config" / "campaign_type_rubric.json"

NEGATIVE_OUTCOMES = {"ghosted", "cancelled", "refunded", "stuck_pending", "adversarial"}

# Rubric aligned with the campaign-type framework table (screenshot),
# shared with the LLM pipeline via config/campaign_type_rubric.json.
with open(RUBRIC_PATH, encoding="utf-8") as _f:
    CAMPAIGN_TYPE_RUBRIC = json.load(_f)


def load_json(name):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def final_status(outcome):
    history = outcome.get("status_history") or []
    return history[-1]["status"] if history else None


def safe_div(num, den):
    return round(num / den, 4) if den else None


def mark_repeat_conversations(conversations):
    """A conversation is 'repeat' when the same customer already had an
    earlier conversation in the dataset (any source), ordered by started_at."""
    by_customer = defaultdict(list)
    for conv in conversations:
        by_customer[conv["customer"]["id"]].append(conv)
    repeat_ids = set()
    for convs in by_customer.values():
        convs.sort(key=lambda c: c["started_at"])
        for conv in convs[1:]:
            repeat_ids.add(conv["id"])
    return repeat_ids


def aggregate_insights(insights, key="campaign_id"):
    """Sum daily insight rows per campaign (or per ad with key='ad_id').
    Note: 'reach' is a sum of daily reach values, so cross-day dedup is not
    applied (raw data limitation)."""
    agg = defaultdict(lambda: defaultdict(float))
    days = defaultdict(set)
    for row in insights:
        cid = row[key]
        agg[cid]["impressions"] += float(row["impressions"])
        agg[cid]["reach"] += float(row["reach"])
        agg[cid]["clicks"] += float(row["clicks"])
        agg[cid]["link_clicks"] += float(row["link_clicks"])
        agg[cid]["spend"] += float(row["spend"])
        for action in row.get("actions", []):
            if action["action_type"] == "onsite_conversion.messaging_conversation_started_7d":
                agg[cid]["ctwa_conversations_meta"] += float(action["value"])
        days[cid].add(row["date_start"])
    for cid in agg:
        agg[cid]["active_days"] = len(days[cid])
    return agg


def aggregate_conversations(conversations, repeat_ids, key="campaign_id"):
    agg = defaultdict(lambda: defaultdict(float))
    products_by_campaign = defaultdict(set)
    for conv in conversations:
        cid = conv["source"].get(key)
        if not cid:
            continue  # organic / direct conversations are not ad-attributable
        a = agg[cid]
        a["ctwa_conversations"] += 1
        if conv["id"] in repeat_ids:
            a["repeat_conversations"] += 1

        outcome = conv.get("outcome") or {}
        otype = outcome.get("type")
        if otype in NEGATIVE_OUTCOMES:
            a["negative_outcomes"] += 1
        if outcome.get("order_id"):
            a["orders_created"] += 1
            a["gross_revenue"] += outcome.get("total", 0)
        if otype == "delivered":
            a["delivered_orders"] += 1
            a["net_revenue"] += outcome.get("total", 0)
            if conv["id"] in repeat_ids:
                a["repeat_delivered_orders"] += 1
            for item in outcome.get("line_items", []):
                products_by_campaign[cid].add(item["product_id"])
    for cid, prods in products_by_campaign.items():
        agg[cid]["unique_products_ordered"] = len(prods)
    return agg


def aggregate_structure(meta):
    ads_per_campaign = defaultdict(int)
    creatives_per_campaign = defaultdict(set)
    for ad in meta["ads"]:
        cid = ad["campaign_id"]
        ads_per_campaign[cid] += 1
        creative_id = (ad.get("creative") or {}).get("id")
        if creative_id:
            creatives_per_campaign[cid].add(creative_id)
    return ads_per_campaign, creatives_per_campaign


def derive_kpis(base):
    """Compute ratio KPIs from summed components. Works for a single campaign
    or for components summed across a campaign type."""
    impressions = base.get("impressions", 0)
    reach = base.get("reach", 0)
    spend = base.get("spend", 0)
    convs = base.get("ctwa_conversations", 0)
    orders = base.get("orders_created", 0)
    delivered = base.get("delivered_orders", 0)
    net_rev = base.get("net_revenue", 0)
    days = base.get("active_days", 0)
    return {
        "frequency": safe_div(impressions, reach),
        "cpm": safe_div(spend * 1000, impressions),
        "link_ctr_pct": safe_div(base.get("link_clicks", 0) * 100, impressions),
        "net_roas": safe_div(net_rev, spend),
        "delivered_rate": safe_div(delivered, orders),
        "cost_per_delivered_order": safe_div(spend, delivered),
        "cost_per_ctwa": safe_div(spend, convs),
        "order_creation_rate": safe_div(orders, convs),
        "aov": safe_div(net_rev, delivered),
        "negative_outcome_rate": safe_div(base.get("negative_outcomes", 0), convs),
        "net_revenue_per_day": safe_div(net_rev, days),
        "ctwa_conversations_per_day": safe_div(convs, days),
        "repeat_conversation_rate": safe_div(base.get("repeat_conversations", 0), convs),
    }


def build_ad_rows(meta, conversations, repeat_ids):
    """One row per ad: insight + conversation KPIs plus adset/creative context."""
    insight_agg = aggregate_insights(meta["insights"], key="ad_id")
    conv_agg = aggregate_conversations(conversations, repeat_ids, key="ad_id")
    campaigns = {c["id"]: c for c in meta["campaigns"]}
    adsets = {a["id"]: a for a in meta["adsets"]}
    creatives = {c["id"]: c for c in meta["creatives"]}

    rows = []
    for ad in meta["ads"]:
        ad_id = ad["id"]
        campaign = campaigns.get(ad["campaign_id"], {})
        adset = adsets.get(ad["adset_id"], {})
        creative = creatives.get((ad.get("creative") or {}).get("id"), {})
        link_data = (creative.get("object_story_spec") or {}).get("link_data", {})

        base = {}
        base.update(insight_agg.get(ad_id, {}))
        base.update(conv_agg.get(ad_id, {}))
        rows.append({
            "ad_id": ad_id,
            "ad_name": ad["name"],
            "campaign_id": ad["campaign_id"],
            "campaign_name": campaign.get("name"),
            "campaign_type": campaign.get("campaign_type"),
            "adset_name": adset.get("name"),
            "audience_type": adset.get("audience_type"),
            "optimization_goal": adset.get("optimization_goal"),
            "creative_id": creative.get("id"),
            "creative_theme": creative.get("theme"),
            "creative_angle": creative.get("angle"),
            "creative_headline": link_data.get("name"),
            "creative_message": link_data.get("message"),
            "start_date": ad["start_date"],
            "end_date": ad["end_date"],
            "status": ad["status"],
            **{k: round(v, 2) if isinstance(v, float) else v for k, v in base.items()},
            **derive_kpis(base),
        })
    return rows


def main():
    meta = load_json("meta_data.json")
    conversations = load_json("conversations.json")

    repeat_ids = mark_repeat_conversations(conversations)
    insight_agg = aggregate_insights(meta["insights"])
    conv_agg = aggregate_conversations(conversations, repeat_ids)
    ads_per_campaign, creatives_per_campaign = aggregate_structure(meta)

    campaign_rows = []
    for campaign in meta["campaigns"]:
        cid = campaign["id"]
        base = {}
        base.update(insight_agg.get(cid, {}))
        base.update(conv_agg.get(cid, {}))
        base["ads_tested"] = ads_per_campaign.get(cid, 0)
        base["unique_creatives"] = len(creatives_per_campaign.get(cid, set()))
        row = {
            "campaign_id": cid,
            "campaign_name": campaign["name"],
            "campaign_type": campaign["campaign_type"],
            "objective": campaign["objective"],
            "start_date": campaign["start_date"],
            "end_date": campaign["end_date"],
            "status": campaign["status"],
            **{k: round(v, 2) if isinstance(v, float) else v for k, v in base.items()},
            **derive_kpis(base),
        }
        campaign_rows.append(row)

    campaign_df = pd.DataFrame(campaign_rows)

    # Aggregate raw components per campaign type, then recompute ratio KPIs
    # (never average ratios across campaigns).
    component_cols = [
        "impressions", "reach", "clicks", "link_clicks", "spend", "active_days",
        "ctwa_conversations_meta", "ctwa_conversations", "repeat_conversations",
        "negative_outcomes", "orders_created", "gross_revenue", "delivered_orders",
        "net_revenue", "repeat_delivered_orders", "unique_products_ordered",
        "ads_tested", "unique_creatives",
    ]
    type_rows = []
    for ctype, group in campaign_df.groupby("campaign_type"):
        sums = {col: group[col].fillna(0).sum() for col in component_cols if col in group}
        row = {
            "campaign_type": ctype,
            "num_campaigns": len(group),
            "campaigns": ", ".join(group["campaign_name"]),
            **{k: round(v, 2) for k, v in sums.items()},
            **derive_kpis(sums),
        }
        type_rows.append(row)

    type_order = list(CAMPAIGN_TYPE_RUBRIC)
    type_df = pd.DataFrame(type_rows)
    type_df["__order"] = type_df["campaign_type"].map(type_order.index)
    type_df = type_df.sort_values("__order").drop(columns="__order").reset_index(drop=True)

    # Screenshot-aligned summary: rubric + computed values of the primary KPIs.
    summary = []
    type_lookup = {row["campaign_type"]: row for row in type_df.to_dict("records")}
    for ctype, rubric in CAMPAIGN_TYPE_RUBRIC.items():
        computed = type_lookup.get(ctype, {})
        summary.append({
            "campaign_type": ctype,
            "target_job": rubric["target_job"],
            "success_question": rubric["success_question"],
            "primary_kpis": rubric["primary_kpis"],
            "num_campaigns": computed.get("num_campaigns", 0),
            "campaigns": computed.get("campaigns", ""),
            "primary_kpi_values": {k: computed.get(k) for k in rubric["primary_kpis"]},
        })

    ad_df = pd.DataFrame(build_ad_rows(meta, conversations, repeat_ids))

    OUT_DIR.mkdir(exist_ok=True)
    ad_df.to_csv(OUT_DIR / "ad_kpis.csv", index=False)
    ad_df.to_json(OUT_DIR / "ad_kpis.json", orient="records", indent=2)
    campaign_df.to_csv(OUT_DIR / "campaign_kpis.csv", index=False)
    campaign_df.to_json(OUT_DIR / "campaign_kpis.json", orient="records", indent=2)
    type_df.to_csv(OUT_DIR / "campaign_type_kpis.csv", index=False)
    type_df.to_json(OUT_DIR / "campaign_type_kpis.json", orient="records", indent=2)
    with open(OUT_DIR / "campaign_type_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    pd.set_option("display.width", 200)
    print(
        f"Wrote {len(ad_df)} ads / {len(campaign_df)} campaigns / "
        f"{len(type_df)} campaign types to {OUT_DIR}"
    )
    print("\n=== Campaign-type summary (screenshot-aligned) ===")
    for row in summary:
        kpis = ", ".join(f"{k}={v}" for k, v in row["primary_kpi_values"].items())
        print(f"\n[{row['campaign_type']}] ({row['num_campaigns']} campaigns: {row['campaigns']})")
        print(f"  job: {row['target_job']}")
        print(f"  question: {row['success_question']}")
        print(f"  kpis: {kpis}")


if __name__ == "__main__":
    main()
