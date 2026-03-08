import os
import re
import sys

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from prompts.loader import (
    load_prompt,
    build_insight_user_prompt,
    build_recommendations_user_prompt,
    build_recommendations_sys_prompt,
)

INSIGHT_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "analysis_prompt.md")


def clean_llm_output(text: str) -> str:
    """Strip markdown code blocks, JSON fences, and extra whitespace."""
    # Remove ```json ... ``` or ``` ... ``` blocks
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = text.replace("```", "")
    # Remove leading/trailing whitespace
    text = text.strip()
    return text

class ContentGenerator:

    def __init__(self, insight_model="gpt-4o", recommendations_model="gpt-4o"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.insight_model = insight_model
        self.recommendations_model = recommendations_model

    def generate_insights(self, metrics, business_domain, canonical_data):
        insight_system_prompt = load_prompt(INSIGHT_PROMPT_PATH)
        user_prompt = build_insight_user_prompt(business_domain, canonical_data, metrics)

        response = self.client.chat.completions.create(
            model=self.insight_model,
            messages=[
                {"role": "system", "content": insight_system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return clean_llm_output(response.choices[0].message.content)

    def generate_recommendations(self, business_domain, metrics, target, insights):
        recommendations_user_prompt = build_recommendations_user_prompt(business_domain, insights, target, metrics)
        recommendations_system_prompt = build_recommendations_sys_prompt(target)

        response = self.client.chat.completions.create(
            model=self.recommendations_model,
            messages=[
                {"role": "system", "content": recommendations_system_prompt},
                {"role": "user", "content": recommendations_user_prompt},
            ],
        )
        return clean_llm_output(response.choices[0].message.content)