import ast
import json
from typing import Any, Dict


def parse_llm_dict_response(raw_response: Any) -> Dict[str, Any]:
    if isinstance(raw_response, dict):
        return raw_response

    if not isinstance(raw_response, str):
        raise ValueError("LLM response must be a dict or string")

    payload = raw_response.strip()
    if not payload:
        raise ValueError("LLM response is empty")

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        # Backward-compatible safe fallback for Python-literal dict strings.
        parsed = ast.literal_eval(payload)

    if not isinstance(parsed, dict):
        raise ValueError("LLM response did not parse into a dict")

    return parsed
