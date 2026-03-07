import os

from dotenv import load_dotenv

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


def chat_completion(client, system_text, user_text):
    """Small wrapper for chat.completions.create."""
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ],
        temperature=0.2,
    )
