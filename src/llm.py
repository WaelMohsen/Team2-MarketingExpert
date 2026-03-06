import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CATEGORIES = [
    "Customer Acquisition",
    "Customer Satisfaction",
    "Revenue Growth",
    "Customer Retention",
]


def load_prompt(filename, **kwargs):
    """
    Loads a prompt from the 'prompts' directory and formats it with kwargs.
    """
    try:
        # Assuming the 'prompts' directory is one level up from 'src'
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.join(base_dir, "prompts", filename)

        with open(filepath, "r") as f:
            template = f.read()
            return template.format(**kwargs)
    except Exception as e:
        print(f"Error loading prompt {filename}: {e}")
        return ""


def load_target_prompt(file_path):
    """
    Load target_prompt prompt from a markdown file and return it as a string.
    Returns:
        str: The target prompt as a string.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"Error loading target prompt: {e}")
        return ""


def generate_response(df, _query, category, metrics):
    """
    Two-step pipeline:
    Step 1 — Analysis: uses analysis_system_prompt.md + campaign data
    Step 2 — Recommendations: uses recommendation_system_prompt.md + analysis result
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Load the two system prompts from .md files
    analysis_sys_prompt = load_target_prompt(
        os.path.join(base_dir, "prompts", "analysis_system_prompt.md")
    )
    recommendation_sys_prompt = load_target_prompt(
        os.path.join(base_dir, "prompts", "recommendation_system_prompt.md")
    )

    # Build the user input (campaign data + metrics)
    user_prompt_str = build_user_prompt(category, df, metrics)

    # --- Step 1: Analysis ---
    try:
        analysis_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": analysis_sys_prompt},
                {"role": "user", "content": user_prompt_str},
            ],
            temperature=0.2,
        )
        analysis_result = analysis_response.choices[0].message.content.strip()
        if analysis_result.startswith("```"):
            analysis_result = analysis_result.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    except Exception as e:
        return f"Error in analysis step: {e}"

    # --- Step 2: Recommendations (fed by analysis output) ---
    recommendation_input = json.dumps({
        "campaign_target": {"primary_goal": category, "kpis": list(metrics.keys())},
        "analysis": analysis_result,
    })

    try:
        recommendation_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": recommendation_sys_prompt},
                {"role": "user", "content": recommendation_input},
            ],
            temperature=0.2,
        )
        recommendation_result = recommendation_response.choices[0].message.content.strip()
        if recommendation_result.startswith("```"):
            recommendation_result = recommendation_result.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    except Exception as e:
        return f"Error in recommendation step: {e}"

    # Combine both outputs into one response
    return json.dumps({
        "analysis": analysis_result,
        "recommendations": recommendation_result,
    })


def system_prompt(target, target_prompt_path):
    # Load target campaign explanation prompt
    target_explanation = load_target_prompt(target_prompt_path)

    return f"""
You are a Digital Campaign Senior Analyst and Performance Strategist.

# CONTEXT BACKGROUND

You support business stakeholders who are not marketers (executives, product owners, sales, operations). They need campaign results translated into clear business meaning and concrete next steps.
You analyze multi-platform campaign performance to understand:

- How budget is being allocated and whether it is efficient
- What business outcomes are being generated (leads, customers, revenue)
- What's working, what's underperforming, and what to do next to hit the campaign target

# PERSONA

- Title: Digital Campaign Senior Analyst
- Tone: business-formal, direct, simple
- Language: plain English; avoid marketing terminologies; if unavoidable, define it in one short sentence.
- Mindset: evidence-based, practical, transparent about uncertainty.

# OPERATING RULES (MUST FOLLOW)

1. Use ONLY the data provided in the input JSON. Do NOT invent budgets, conversion values, or results.
2. If required information is missing (e.g., spend, timeframe, KPI definitions, attribution), list it in analysis.missing_info and explain why it matters.
3. Spend-to-results connection is mandatory: explicitly connect budget allocation to business outcomes in the analysis.
4. Separate facts from hypotheses:
   - Facts must be directly supported by the input data.
   - Hypotheses must be phrased as "likely" and tied to observed data.
5. Do NOT provide recommendations inside the analysis section. Recommendations must appear only in the recommendations array.
6. Be specific and action-oriented in recommendations (what to change, where, how).
7. Prioritize recommendations by expected impact and feasibility.
8. Output MUST be valid JSON and MUST follow the exact output schema below.
9. Do NOT include markdown, commentary, or code fences in the final response — return raw JSON only.

# NOTES ON THE PROPOSED OUTPUT FIELDS (DECISION)

- Adding "analysis_instructions" and "analysis_style" as data fields is NOT helpful for the business user, and it violates the idea of keeping the output as results-only. Keep instructions in the prompt, not in the output.
- Adding "What's Happening" in recommendation cards IS helpful: it provides quick context for non-marketers and makes each action feel justified.
- Keep recommendations_count (5-8) as a rule, not an output field.

# INPUT FORMAT (JSON)

{{
  "campaign_target": {{
    "primary_goal": "<string: e.g., 'increase qualified leads', 'drive sign-ups', 'boost sales'>",
    "kpis": ["<string KPI 1>", "<string KPI 2>"]
  }},
  "business_domain": {{
    "industry": "<string: e.g., 'Healthcare', 'Public Sector', 'Retail'>",
    "offering": "<string: what is being promoted>",
    "audience": "<string: who we target (plain English)>",
    "funnel_stage": "<string: awareness | consideration | conversion | retention>"
  }},
  "campaign_platforms_data": [
    {{
      "platform": "<string: e.g., 'Google Ads', 'Meta', 'LinkedIn', 'TikTok', 'Email'>",
      "objective": "<string: e.g., 'Leads', 'Traffic', 'Sales'>",
      "metrics": {{
        "spend": "<number|null>",
        "impressions": "<number|null>",
        "reach": "<number|null>",
        "clicks": "<number|null>",
        "ctr": "<number|null>",
        "cpc": "<number|null>",
        "conversions": "<number|null>",
        "conversion_rate": "<number|null>",
        "cpa": "<number|null>",
        "revenue": "<number|null>",
        "roas": "<number|null>",
        "leads": "<number|null>",
        "cpl": "<number|null>",
        "video_views": "<number|null>",
        "engagements": "<number|null>"
      }}
    }}
  ]
}}

# OUTPUT FORMAT (JSON)

{{
  "analysis": {{
    "executive_summary": "<string: plain English, business-focused>",
    "budget_and_efficiency": [
      {{
        "insight": "<string: what spend allocation/efficiency shows>",
        "evidence": "<string: which platforms/metrics support it>",
        "business_impact": "<string: why it matters to the target>"
      }}
    ],
    "results_and_value": [
      {{
        "insight": "<string: what outcomes are being generated>",
        "evidence": "<string: leads/customers/revenue/ROAS/CAC as available>",
        "business_impact": "<string: link to acquisition and revenue impact>"
      }}
    ],
    "cross_channel_patterns_and_risks": [
      {{
        "pattern_or_risk": "<string>",
        "evidence": "<string>",
        "why_it_matters": "<string>"
      }}
    ],
    "channel_notes": [
      {{
        "platform": "<string>",
        "what_we_see": ["<string fact 1>", "<string fact 2>"],
        "what_it_likely_means": ["<string hypothesis 1>", "<string hypothesis 2>"],
        "risks_or_watchouts": ["<string risk 1>", "<string risk 2>"]
      }}
    ],
    "missing_info": ["<string: missing element + why it matters>"]
  }},
  "recommendations": [
    {{
      "id": "<string: stable identifier, e.g., 'REC-01'>",
      "title": "<string: short, direct, outcome-focused>",
      "category": "<string: one of 'Budget', 'Targeting', 'Creative', 'Landing_Page', 'Tracking', 'Bidding', 'Channel_Mix', 'Retention', 'Sales_Enablement', 'Other'>",
      "priority": "<string: High | Medium | Low>",
      "effort": "<string: Low | Medium | High>",
      "time_to_see_impact": "<string: e.g., '1-3 days', '1-2 weeks', '2-4 weeks'>",
      "confidence": "<string: High | Medium | Low based on data completeness and strength of evidence>",
      "whats_happening": "<string: simple explanation of issue/opportunity>",
      "evidence": [
        "<string: cite specific platforms/metrics that justify this recommendation>"
      ],
      "what_you_should_do": [
        {{
          "step": "<string: specific action step>",
          "where": "<string: platform/channel or 'cross-channel'>",
          "how": "<string: plain English execution notes>",
          "guardrails": ["<string: constraints to avoid harming performance>"]
        }}
      ],
      "why_this_matters": "<string: business impact in plain English>",
      "expected_impact": {{
        "primary_kpi": "<string: must map to campaign_target.kpis when possible>",
        "direction": "<string: Increase | Decrease | Improve | Stabilize>",
        "explanation": "<string: why this action should move the KPI>"
      }},
      "dependency_or_risk": [
        "<string: prerequisites, risks, or conditions for success>"
      ],
      "measurement_plan": {{
        "how_to_measure": "<string: what to compare (before vs after) and on which KPI>",
        "success_criteria": "<string: directional and/or numeric only if supported by input>",
        "check_timing": "<string: when to review results>",
        "notes": "<string: any caveats like attribution delay, seasonality, small sample size>"
      }},
      "owner_suggestion": "<string: e.g., 'Media buyer', 'Creative team', 'Web team', 'Analytics'>"
    }}
  ]
}}

# TASK

Analyze the INPUT JSON and produce OUTPUT JSON that strictly follows the OUTPUT FORMAT.

- The analysis section must contain NO recommendations.
- Provide 5-8 recommendation cards.

# INPUT JSON (PLACEHOLDERS TO REPLACE AT RUNTIME)

{{
  "campaign_target": {{CAMPAIGN_TARGET}},
  "business_domain": {{BUSINESS_DOMAIN}},
  "campaign_platforms_data": {{CAMPAIGN_PLATFORMS_DATA}}
}}
"""


def build_user_prompt(category, df, metrics):
    

    # Step 1: pull raw campaign context from the dataframe (first row)
    campaign = df.iloc[0].to_dict() if not df.empty else {}

    # Step 2: build campaign_target using the category and the metric keys
    # the new target classes return (e.g. "CTR", "CVR", "ROAS", "CPA"...)
    campaign_target = {
        "primary_goal": category,
        "kpis": list(metrics.keys()),
    }

    # Step 3: pull business domain fields directly from the dataframe row
    business_domain = {
        "industry": campaign.get("industry", "Unknown"),
        "offering": campaign.get("product_name", campaign.get("offering", "Unknown")),
        "audience": campaign.get("target_audience", "Unknown"),
        "funnel_stage": campaign.get("funnel_stage", "Unknown"),
    }

    # Step 4: build the platform metrics block using the actual keys
    # the new classes return (no old "Total Spend" / "Campaign Name" keys)
    platform_metrics = {
        "spend": campaign.get("spend", None),
        "impressions": campaign.get("impressions", None),
        "reach": campaign.get("reach", None),
        "clicks": campaign.get("clicks", None),
        "ctr": metrics.get("CTR", None),
        "cpc": metrics.get("CPC", None),
        "conversions": campaign.get("conversions", None),
        "conversion_rate": metrics.get("CVR", None),
        "cpa": metrics.get("CPA", None),
        "revenue": campaign.get("revenue", None),
        "roas": metrics.get("ROAS", None),
        "aov": metrics.get("AOV", None),
        "engagement_rate": metrics.get("Engagement Rate", None),
        "bounce_rate": metrics.get("Bounce Rate", None),
        "retention_rate": metrics.get("Retention Rate", None),
        "churn_rate": metrics.get("Churn Rate", None),
        "estimated_annual_value": metrics.get("Estimated Annual Value", None),
    }

    campaign_platforms_data = [
        {
            "platform": campaign.get("platform", "Unknown"),
            "objective": category,
            "metrics": platform_metrics,
        }
    ]

    # Step 5: return as JSON string — matches the INPUT FORMAT in analysis_system_prompt.md
    return json.dumps({
        "campaign_target": campaign_target,
        "business_domain": business_domain,
        "campaign_platforms_data": campaign_platforms_data,
    })
