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


def chat_completion(client, system_text, user_text, response_format):
    """Wrapper around the OpenAI structured-outputs beta endpoint.

    `response_format` should be a **Pydantic model class** (e.g. AnalysisOutput).
    The SDK automatically generates the JSON schema with additionalProperties: false,
    sends it with strict: true, and parses the response into a Pydantic instance
    accessible via `response.choices[0].message.parsed`.
    """

    return client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ],
        temperature=0.2,
        response_format=response_format,
    )

# ANALYSIS: "gpt-4o-mini",
# RECOMMENDATION: "gpt-4o"
