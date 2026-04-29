from __future__ import annotations


def load_target_prompt(file_path: str) -> str:
    """Load a category target prompt (markdown) and return it as a string."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as exc:
        # Keep behavior simple: return empty prompt rather than crashing.
        print(f"Error loading target prompt: {exc}")
        return ""


def _common_system_instructions(target: str, target_prompt_path: str) -> str:
    target_explanation = load_target_prompt(target_prompt_path)

    return f"""
        Important Note : Take in mind to perform your role based on this marketing campaign target below
        TARGET: {target}
        TARGET EXPLANATION:
        {target_explanation}

        COMMUNICATION STYLE (STRICT):
        1) Use simple business language.
          2) Avoid abbreviations in final text (do NOT use CTR, ROAS, CPA, CAC,
              LTV, MER). Spell terms out in plain English instead.
        3) Focus on money impact, growth impact, and risk.
        4) Keep each field concise and understandable to a non-marketer.
        5) Think step-by-step internally, but never reveal internal reasoning.
"""


def analysis_system_prompt(
    target: str, target_prompt_path: str, analysis_prompt_path: str
) -> str:
    analysis_prompt = load_target_prompt(analysis_prompt_path)
    return f"""{analysis_prompt}
        {_common_system_instructions(target, target_prompt_path)}
"""


def recommendation_system_prompt(
    target: str, target_prompt_path: str, rec_prompt_path: str
) -> str:
    rec_prompt = load_target_prompt(rec_prompt_path)
    return f"""{rec_prompt}
        {_common_system_instructions(target, target_prompt_path)}

    """


def _parse_numeric(value):
    """Strip % signs, handle None, return float."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).replace("%", "").replace("$", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


# -------------------------------
# Category-aware ranking config
# -------------------------------
# What metric to rank by for each category. This aligns the ranking with
# the campaign's actual goal instead of defaulting to ROAS everywhere.
_RANKING_CONFIG = {
    "Customer Acquisition": {
        "metric_key": "CPA",
        "direction": "asc",  # lower is better
        "label": "cost-per-customer",
        "format": "${:.2f}",
    },
    "Revenue Growth": {
        "metric_key": "ROAS",
        "direction": "desc",
        "label": "return-per-dollar",
        "format": "{:.2f}",
    },
    "Customer Satisfaction": {
        "metric_key": "Engagement Rate",
        "direction": "desc",
        "label": "engagement rate",
        "format": "{:.2f}%",
    },
    "Customer Retention": {
        "metric_key": "Retention Rate",
        "direction": "desc",
        "label": "retention rate",
        "format": "{:.2f}%",
    },
}


def build_channel_ranking(metrics: dict, category: str) -> str:
    """Pre-compute per-channel ranking using a metric aligned with the category."""
    per_channel = metrics.get("per_channel", {}) or {}
    if not per_channel:
        return "CHANNEL PERFORMANCE: (not available)"

    config = _RANKING_CONFIG.get(category)
    if config is None:
        # Safe fallback: rank by ROAS but tell the LLM we fell back
        config = _RANKING_CONFIG["Revenue Growth"]
        fallback_note = f"(Category '{category}' not recognized; ranking by return-per-dollar as fallback.)"
    else:
        fallback_note = None

    metric_key = config["metric_key"]
    reverse = config["direction"] == "desc"
    label = config["label"]
    fmt = config["format"]

    rows = []
    for channel, m in per_channel.items():
        value = _parse_numeric(m.get(metric_key))
        rows.append(
            {
                "channel": channel,
                "ranking_value": value,
                "spend": _parse_numeric(m.get("Total Spend")),
                "roas": _parse_numeric(m.get("ROAS")),
                "cac": _parse_numeric(m.get("CPA")),
            }
        )

    # If the ranking metric returned all zeros (metric not tracked), warn the LLM
    if all(r["ranking_value"] == 0.0 for r in rows):
        return (
            f"CHANNEL PERFORMANCE: ranking metric '{metric_key}' is not available "
            f"per channel for this campaign. Cannot rank channels by {label}."
        )

    rows.sort(key=lambda r: r["ranking_value"], reverse=reverse)
    total_spend = sum(r["spend"] for r in rows) or 1.0

    header = f"CHANNEL PERFORMANCE for {category} (ranked by {label}, best to worst):"
    lines = [header]
    if fallback_note:
        lines.append(f"  Note: {fallback_note}")

    for i, r in enumerate(rows, 1):
        spend_pct = r["spend"] / total_spend * 100
        lines.append(
            f"  {i}. {r['channel']:12s} "
            f"{label} {fmt.format(r['ranking_value']):>10s}  "
            f"spend ${r['spend']:>6.0f} ({spend_pct:4.1f}% of budget)"
        )

    top2 = sum(r["spend"] for r in rows[:2])
    bot2 = sum(r["spend"] for r in rows[-2:])
    lines.append("")
    lines.append(f"BUDGET vs {label.upper()}:")
    lines.append(
        f"  Top-2 channels by {label} get ${top2:.0f} "
        f"({top2/total_spend*100:.0f}% of budget)"
    )
    lines.append(
        f"  Bottom-2 channels by {label} get ${bot2:.0f} "
        f"({bot2/total_spend*100:.0f}% of budget)"
    )
    return "\n".join(lines)


def build_context_block(category: str, df, metrics: dict) -> str:
    """Build shared business-first context.

    No schemas, and no step instructions.
    """
    campaign_raw_data = df.to_dict("records")
    metrics_overall = metrics.get("overall")
    # metrics_per_channel = metrics.get("per_channel")
    ranking_block = build_channel_ranking(metrics, category)

    return f"""
        BUSINESS:
        (Infer business type from campaign data)
        Goal: {category}

        CHANNEL PERFORMANCE:
        {ranking_block}

        CAMPAIGN RAW DATA:
        {campaign_raw_data}

        PLAIN BUSINESS METRICS:
         - Across all channels (overall)
            {metrics_overall}


        IMPORTANT:
        - Write for a business lead with no marketing background.
        - Keep wording simple and practical.
        - Avoid abbreviations in the final JSON text.
        - When making channel-specific recommendations, cite the channel by name and
        reference specific numbers from the CHANNEL PERFORMANCE ranking above.
        - Only produce recommendations that are directly supported by the data shown.
    """


def build_analysis_user_prompt(context_block: str) -> str:
    return f"""
        You are in Step 1 (Analysis Only).

        Use the context below and return analysis JSON only.

        CONTEXT:
        {context_block}
    """


def build_recommendation_user_prompt(
    context_block: str,
    analysis_input: str,
) -> str:
    return f"""
        You are in Step 2 (Recommendation).

        Use the context below PLUS the Step 1 analysis JSON
        to produce the final report JSON.

        CONTEXT:
        {context_block}

        STEP 1 ANALYSIS JSON (input):
        {analysis_input}
    """
