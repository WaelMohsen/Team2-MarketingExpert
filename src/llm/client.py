import os
from typing import Optional, Tuple

from dotenv import load_dotenv

from src.evaluation.run_config import load_run_config

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

_client = None


def get_client():
    """Return a cached OpenAI client (lazy init)."""
    global _client
    if _client is not None:
        return _client

    # Load environment variables once at first use.
    load_dotenv()

    if OpenAI is None:
        raise RuntimeError(
            "Missing dependency: 'openai'. Install with "
            "`pip install -r requirements.txt`."
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Set it in your environment or .env file."
        )

    _client = OpenAI(api_key=api_key)
    return _client


def chat_completion(client, system_text, user_text, response_format, model, temp):
    """Wrapper around the OpenAI structured-outputs beta endpoint.

    `response_format` should be a **Pydantic model class** (e.g. AnalysisOutput).
    The SDK automatically generates the JSON schema with additionalProperties: false,
    sends it with strict: true, and parses the response into a Pydantic instance
    accessible via `response.choices[0].message.parsed`.
    """

    return client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ],
        temperature=temp,
        response_format=response_format,
    )


def _default_llm_settings() -> Tuple[str, float]:
    config = load_run_config()
    return (
        config.generation.recommendation_model,
        config.generation.recommendation_temp,
    )


def llm_callable(
    prompt: str,
    model: Optional[str] = None,
    temp: Optional[float] = None,
) -> str:
    if model is None or temp is None:
        default_model, default_temp = _default_llm_settings()
        model = model or default_model
        temp = default_temp if temp is None else temp

    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temp,
    )
    return response.choices[0].message.content


def embedding_callable(text: str) -> list[float]:
    client = get_client()
    response = client.embeddings.create(model="text-embedding-3-small", input=text)
    return response.data[0].embedding
