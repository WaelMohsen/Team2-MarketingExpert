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


def generate_response(query, category, metrics):
    """
    Generates a response based on the category using a specific prompt file.
    Uses the new system_prompt and build_user_prompt structure while adapting to available metrics.
    """
    metrics_str = json.dumps(metrics, indent=2)

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

    # 2. Build User Prompt (adapting strictly to available metrics)
    user_prompt_str = build_user_prompt(category, metrics)

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
    # Note: Using load_prompt helper to handle path resolution relative to workspace if needed, 
    # or the new load_target_prompt if path is absolute. Using load_target_prompt here as requested.
    target_explanation = load_target_prompt(target_prompt_path)

    return f"""
            You are a senior marketing performance auditor.

            Your job is to diagnose paid advertising campaigns and deliver a decisive business verdict.

            You think step-by-step internally but NEVER reveal your reasoning process.

            ------------------------------------------------------------
            STEP 1 — Diagnose Performance
            Evaluate every metric.
            Label each as STRONG, NORMAL, or WEAK based on industry standards.

            Do not analyze metrics in isolation.
            Identify relationships between them.
            Explain cause-and-effect chains.

            ------------------------------------------------------------
            STEP 2 — Identify Root Cause
            Go beyond surface metrics.
            Find the single biggest leverage point.
            Is the problem:
            - Audience
            - Message
            - Offer
            - Budget allocation
            - Landing page
            - Timing

            Choose ONE primary root cause.

            ------------------------------------------------------------
            STEP 3 — Make a Decision
            Give ONE clear verdict:
            - Continue
            - Fix
            - Cut

            Be decisive.

            ------------------------------------------------------------
            IMPORTANT CONTEXT

            The analysis MUST align with this campaign target:

            TARGET:
            {target}

            TARGET EXPLANATION:
            {target_explanation}

            ------------------------------------------------------------
            COMMUNICATION STYLE

            Write for a smart business owner.

            1) First explain in plain English (no acronyms).
            2) Then briefly reference technical metrics (CTR, ROAS, CAC).

            Be direct.
            Be blunt if money is being wasted.
            Never invent data.

            ------------------------------------------------------------
            OUTPUT RULES

            Return ONLY valid JSON.
            No markdown.
            No explanation outside JSON.
            Match the exact schema provided below:
            {{
            "headline": "Short punchy headline summary",
            "analysis": "Detailed analysis of the performance step-by-step",
            "core_issue": "The one main problem",
            "why_it_matters": "Business impact explanation",
            "recommended_action": "Specific action to take",
            "expected_outcome": "What will happen after fix",
            "detected_issues": ["Issue 1", "Issue 2"],
            "confidence_score": 85
            }}
            """


def build_user_prompt(category, metrics):
    # Constructing a simulated 'user_input' based on the metrics we have
    # Since we moved to a single row CSV, we can assume the metrics dictionary 
    # has the raw values passed from data.py (which I need to verify in data.py next)

    return f"""
            BUSINESS:
            (Infer business type from campaign data)
            Goal: {category}

            CAMPAIGN:
            Name: {metrics.get('Campaign Name', 'Unknown')}
            Spend: ${metrics.get('Total Spend', 0)}
            Revenue: ${metrics.get('Total Revenue', 0)}
            Sales: {metrics.get('Total Conversions', 0)}
            Impressions: {metrics.get('Total Impressions', 0)}
            Clicks: {metrics.get('Total Clicks', 0)}

            METRICS:
            Click-through rate: {metrics.get('CTR', 'N/A')}
            Conversion rate: {metrics.get('Conversion Rate', 'N/A')}
            Return on ad spend: {metrics.get('ROAS', 'N/A')}
            Cost per customer: ${metrics.get('CPA', 'N/A')} (CPA estimated as Cost per Customer)

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
