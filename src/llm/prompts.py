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
        You are advising a business lead who is not a marketing expert.

        TARGET:
        {target}

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


def analysis_system_prompt(target: str, target_prompt_path: str) -> str:
    return f"""
        {_common_system_instructions(target, target_prompt_path)}

        STEP 1 (ANALYSIS ONLY):
                - Your job is to analyze the situation.
                    Do NOT propose the final recommendation.
                - Identify what is working, what is not working,
                    and the likely root cause.
        - Extract the most important signals from the provided metrics.

        OUTPUT RULES:
        - Return ONLY valid JSON
        - No markdown
        - No text outside JSON
        - Match the exact schema below:
        {{
            "analysis": "Plain-English analysis (no recommendation yet)",
            "key_signals": ["Signal 1", "Signal 2"],
            "detected_issues": ["Issue 1", "Issue 2"],
            "root_cause_hypothesis": "Most likely root cause",
            "business_risks": ["Risk 1", "Risk 2"],
            "confidence_score": 0
        }}
"""


def recommendation_system_prompt(target: str, target_prompt_path: str) -> str:
    return f"""
        {_common_system_instructions(target, target_prompt_path)}

        STEP 2 (RECOMMENDATION):
        - You will be given the analysis JSON from Step 1.
                - Use it as your primary input to produce ONE clear decision,
                    and ONE clear next action.
        - Your final output must match the report schema exactly.

        OUTPUT RULES:
        - Return ONLY valid JSON
        - No markdown
        - No text outside JSON
        - Match the exact schema below:
        {{
            "headline": "Short punchy headline summary",
            "analysis": "Plain-English business analysis with minimal jargon",
            "core_issue": "The one main problem",
            "why_it_matters": "Business impact explanation",
            "recommended_action": "Specific action to take",
            "expected_outcome": "What will happen after fix",
            "detected_issues": ["Issue 1", "Issue 2"],
            "confidence_score": 85
        }}
"""


def build_context_block(category: str, df, metrics: dict) -> str:
    """Build shared business-first context.

    No schemas, and no step instructions.
    """
    def _is_missing(value) -> bool:
        return value is None or value == "" or value == "N/A"

    def _pick(metric_key: str, default="N/A"):
        return metrics.get(metric_key, default)

    def _base_business_metrics() -> dict:
        return {
            "campaign_name": _pick("Campaign Name", "Unknown"),
            "total_spend": _pick("Total Spend"),
            "total_revenue": _pick("Total Revenue"),
            "sales": _pick("Total Conversions"),
            "new_customers": _pick("Total New Customers"),
            # Keep keys business-friendly (avoid marketing acronyms).
            "click_rate_percent": _pick("CTR"),
            "purchase_rate_percent": _pick("Conversion Rate"),
            "revenue_return_per_ad_dollar": _pick("ROAS"),
            "cost_per_new_customer": _pick("CPA"),
        }

    def _category_business_metrics() -> dict:
        if category == "Customer Satisfaction":
            return {
                "engagement_rate_percent": _pick("Engagement Rate"),
                "average_bounce_rate_percent": _pick("Average Bounce Rate"),
                "average_ad_frequency": _pick("Average Frequency"),
            }

        if category == "Revenue Growth":
            return {
                "average_order_value": _pick("AOV"),
                "annual_value_per_customer": _pick("Annual Customer Value"),
                # Use plain terms for ratios/benchmarks.
                "annual_value_to_cost_ratio": _pick("LTV:CAC Ratio"),
                "break_even_revenue_return": _pick("Break-Even ROAS"),
                "revenue_per_total_ad_spend": _pick("MER"),
                "profit_margin_percent": _pick("Product Profit Margin"),
                "ad_format": _pick("Ad Format"),
                "campaign_goal": _pick("Campaign Goal"),
            }

        if category == "Customer Retention":
            return {
                "retained_customers": _pick("Retained Customers"),
                "churn_rate_percent": _pick("Churn Rate"),
                "retention_rate_percent": _pick("Retention Rate"),
                "retained_customer_share_percent": _pick(
                    "Retained Customer Share"
                ),
                "repeat_purchases_per_year": _pick(
                    "Repeat Purchases Per Year"
                ),
                "estimated_annual_value_per_customer": _pick(
                    "Estimated Annual Value Per Customer"
                ),
                "customer_satisfaction_score": _pick(
                    "Customer Satisfaction Score"
                ),
            }

        # Customer Acquisition (and default)
        return {}

    campaign = df.iloc[0].to_dict() if df is not None and not df.empty else {}

    # Build a single metrics block: base + category-specific,
    # then drop missing values.
    business_metrics = {
        **_base_business_metrics(),
        **_category_business_metrics(),
    }
    business_metrics = {
        key: value
        for key, value in business_metrics.items()
        if not _is_missing(value)
    }

    # Optional: include small context block only when those fields exist.
    business_context_lines = []
    for label, key in (
        ("Channel", "channel"),
        ("Date", "date"),
    ):
        if key in campaign and not _is_missing(campaign.get(key)):
            business_context_lines.append(f"- {label}: {campaign.get(key)}")

    business_context = ""
    if business_context_lines:
        business_context = (
            "CAMPAIGN CONTEXT:\n" + "\n".join(business_context_lines)
        )

    return f"""
        BUSINESS:
        (Infer business type from campaign data)
        Goal: {category}

        CAMPAIGN RAW DATA:
        {campaign}

        PLAIN BUSINESS METRICS:
        {business_metrics}

        {business_context}

        IMPORTANT:
        - Write for a business lead with no marketing background.
        - Keep wording simple and practical.
        - Avoid abbreviations in the final JSON text.
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
