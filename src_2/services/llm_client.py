import os

from openai import OpenAI


class LLMClient:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing OPENAI_API_KEY in .env file.")
        self._client = OpenAI(api_key=api_key)

    def chat_completion(self, system_text, user_text, response_format, model):
        return self._client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            temperature=0.2,
            response_format=response_format,
        )
