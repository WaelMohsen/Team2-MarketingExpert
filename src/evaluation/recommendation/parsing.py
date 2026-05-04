import ast
import json
from typing import Any, Dict


def _strip_code_fence(payload: str) -> str:
    text = payload.strip()
    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()

    return text


def parse_llm_mapping(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        return payload

    if not isinstance(payload, str):
        raise TypeError("Expected LLM payload to be a mapping or string")

    normalized = _strip_code_fence(payload)
    if not normalized:
        raise ValueError("LLM payload is empty")

    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError:
        parsed = ast.literal_eval(normalized)

    if not isinstance(parsed, dict):
        raise ValueError("Expected parsed LLM payload to be a mapping")

    return parsed
