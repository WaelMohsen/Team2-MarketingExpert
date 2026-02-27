import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CATEGORIES = [
    "Customer Acquisition",
    "Customer Satisfaction",
    "Revenue Growth",
    "Customer Retention"
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
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error loading target prompt: {e}")
        return ""


def generate_response(df, _query, category, metrics):
    """
    Generates a response based on the category using a specific prompt file.
    Uses the new system_prompt and build_user_prompt structure while adapting to available metrics.
    """
    # Map category to specific prompt file (Target Explanation)
    category_map = {
        "Customer Acquisition": "customer_acquisition.md",
        "Customer Satisfaction": "customer_satisfaction.md",
        "Revenue Growth": "revenue_growth.md",
        "Customer Retention": "customer_retention.md"
    }

    # Get the correct filename, default to generic response_generation.md if not found
    prompt_file = category_map.get(category, "response_generation.md")

    # Construct absolute path for load_target_prompt
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_prompt_path = os.path.join(base_dir, "prompts", prompt_file)

    # 1. Build System Prompt
    sys_prompt = system_prompt(category, target_prompt_path)

    # 2. Build User Prompt (business-first, plain-language metrics)
    user_prompt_str = build_user_prompt(category, df, metrics)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt_str}
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating response: {e}"


def system_prompt(target, target_prompt_path):
    # Load target campaign explanation prompt
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
        4) Give one clear decision and one clear next action.
        5) Keep each field concise and understandable to a non-marketer.
        6) Think step-by-step internally, but never reveal internal reasoning.

        OUTPUT RULES:
        - Return ONLY valid JSON
        - No markdown
        - No explanation outside JSON
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


def build_user_prompt(category, df, metrics):
    # Build business-first context to reduce technical/jargon-heavy output.
    campaign = df.iloc[0].to_dict() if not df.empty else {}

    business_metrics = {
        "campaign_name": metrics.get("Campaign Name", "Unknown"),
        "total_spend": metrics.get("Total Spend", "N/A"),
        "total_revenue": metrics.get("Total Revenue", "N/A"),
        "sales": metrics.get("Total Conversions", "N/A"),
        "new_customers": metrics.get("Total New Customers", "N/A"),
        "click_through_rate_percent": metrics.get("CTR", "N/A"),
        "conversion_rate_percent": metrics.get("Conversion Rate", "N/A"),
        "return_on_ad_spend": metrics.get("ROAS", "N/A"),
        "cost_per_customer": metrics.get("CPA", "N/A"),
    }

    business_context = ""
    if metrics.get("Campaign Goal"):
        business_context = f"""
            CAMPAIGN CONTEXT:
            - Ad format: {metrics.get('Ad Format', 'N/A')}
            - Campaign goal: {metrics.get('Campaign Goal', 'N/A')}

            BUSINESS CONTEXT:
            - Average order value: ${metrics.get('AOV', 'N/A')}
            - Annual customer value: ${metrics.get('Annual Customer Value', 'N/A')}
            - Profit margin percent: {metrics.get('Product Profit Margin', 'N/A')}%
            """

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

            Return JSON:
            {{
            "headline": "",
            "analysis": "",
            "core_issue": "",
            "why_it_matters": "",
            "recommended_action": "",
            "expected_outcome": "",
            "detected_issues": [],
            "confidence_score": 0
            }}
            Please audit this performance based on the metrics above.
        """
