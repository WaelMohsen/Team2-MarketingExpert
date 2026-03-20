from functools import lru_cache
from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    load_dotenv()
    return OpenAI()

def run_insights(
    system: str,
    user: str,
    model: str = "gpt-4o",
    temperature: float = 0.2
) -> str:
    return get_client().chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
    ).choices[0].message.content


def run_recommendations(
    system: str,
    user: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7
) -> str:
    return get_client().chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
    ).choices[0].message.content