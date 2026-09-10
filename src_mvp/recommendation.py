"""Optional single-call structured recommendation narrator."""

import json
import os
from pathlib import Path
from typing import Optional

from .contracts import RecommendationInput, RecommendationReport
from .paths import PROMPT_DIR


def run_recommendation(
    packet: RecommendationInput,
    model: Optional[str] = None,
    prompt_path: Optional[Path] = None,
) -> RecommendationReport:
    from openai import OpenAI

    prompt = prompt_path or PROMPT_DIR / "recommendation.md"
    instructions = prompt.read_text(encoding="utf-8")
    response = OpenAI().responses.parse(
        model=model or os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        instructions=instructions,
        input=json.dumps(
            packet.model_dump(mode="json", exclude_none=True), ensure_ascii=True
        ),
        text_format=RecommendationReport,
    )
    if response.output_parsed is None:
        raise RuntimeError("The recommendation model returned no validated output")
    return response.output_parsed
