from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from ..llm.client import chat_completion, get_client
from ..schemas.analysis_output_schema import AnalysisOutput

# ─────────────────────────────────────────────
# 1. STATUS ENUM
# ─────────────────────────────────────────────


class EvaluationStatus(str, Enum):
    PASS = "pass"
    BORDERLINE = "borderline"
    FAIL = "fail"


# ─────────────────────────────────────────────
# 2. JUDGE VERDICT (Pydantic — LLM output)
# ─────────────────────────────────────────────


class DimensionScores(BaseModel):
    quantitative_grounding: float = Field(..., ge=0.0, le=1.0)
    benchmark_anchoring: float = Field(..., ge=0.0, le=1.0)
    coverage: float = Field(..., ge=0.0, le=1.0)
    no_recommendation: float = Field(..., ge=0.0, le=1.0)


class DimensionExplanations(BaseModel):
    quantitative_grounding: str
    benchmark_anchoring: str
    coverage: str
    no_recommendation: str


class JudgeVerdict(BaseModel):
    scores: DimensionScores
    explanations: DimensionExplanations


# ─────────────────────────────────────────────
# 3. JUDGE PROMPTS
# ─────────────────────────────────────────────

JUDGE_SYSTEM_PROMPT = """# Analysis Quality Judge — System Prompt

## Role

You are an expert evaluator of marketing campaign analysis outputs. Your job is to score the quality of an analysis across four well-defined dimensions, anchored to the campaign goal's industry benchmarks.

## Scoring Rules

- Score each dimension from 0.0 to 1.0 (decimals allowed).
  - 0.0 = the dimension is completely absent or factually wrong.
  - 0.5 = acceptable but missing depth, anchoring, or concrete numbers.
  - 1.0 = excellent — must be truly earned, not given for being "well written".
- Be strict. Do not inflate scores. A flowery, jargon-free analysis with no numbers does NOT earn 1.0 on data grounding.

## Communication Rules

- Write explanations in plain business English.
- Focus reasoning on money impact, growth impact, and risk.

## Dimensions

1. **quantitative_grounding** — Every claim cites a specific number from the campaign data: counts, percentages, dollars (e.g. "Google Ads received 52% of total spend, $895 of $1,720"). Penalize generic statements like "performance is poor" with no figures.

2. **benchmark_anchoring** — Every performance claim is compared to a benchmark from the GOAL BENCHMARKS section provided below, with the magnitude of the gap stated (e.g. "1.1% conversion rate is 21% below the 1.4% Shopify floor"). Penalize numbers stated without a reference point.

3. **coverage** — The analysis addresses every KPI listed in the GOAL BENCHMARKS section — none are silently skipped. Penalize analyses that discuss only a subset of the relevant KPIs while leaving important ones unmentioned.

4. **no_recommendation** — The analysis is diagnostic only. Score low if the analysis uses recommendation language such as: should, need to, recommend, increase, optimize, launch, consider, improve, ensure, invest, reduce, focus on, adjust. Recommendations belong in the recommendation step, not the analysis.
"""

JUDGE_USER_PROMPT = """# Analysis Quality Judge — User Prompt Template

Evaluate the following marketing campaign analysis against the GOAL BENCHMARKS provided. Use the benchmarks to verify whether each numerical claim in the analysis is correctly anchored.

## Campaign Goal

{goal}

## Goal Benchmarks (use these to verify benchmark_anchoring)

{benchmarks}

## Original Campaign Context

{context}

## Analysis Output to Score

- Analysis: {analysis}
- Key Signals: {key_signals}
- Detected Issues: {detected_issues}
- Root Cause Hypothesis: {root_cause_hypothesis}
- Business Risks: {business_risks}
- Confidence Score: {confidence_score}

## Output Format

Return a JSON object with this exact structure:

```json
{{
  "scores": {{
    "quantitative_grounding": <float 0.0-1.0>,
    "benchmark_anchoring": <float 0.0-1.0>,
    "coverage": <float 0.0-1.0>,
    "no_recommendation": <float 0.0-1.0>
  }},
  "explanations": {{
    "quantitative_grounding": "<brief explanation citing specific examples from the analysis>",
    "benchmark_anchoring": "<brief explanation noting which claims were/were not anchored to a benchmark above>",
    "coverage": "<brief explanation of which KPIs from GOAL BENCHMARKS were addressed and which were skipped>",
    "no_recommendation": "<brief explanation of whether the analysis stayed diagnostic>"
  }}
}}
```
"""


# ─────────────────────────────────────────────
# 4. ANALYSIS JUDGE CLASS
# ─────────────────────────────────────────────


class AnalysisJudge:
    def __init__(self) -> None:
        self._client = get_client()

    def evaluate(
        self,
        analysis: AnalysisOutput,
        context: str,
        model: Optional[str] = None,
        temp: Optional[float] = None,
        goal: str = "",
        benchmarks: str = "",
    ) -> JudgeVerdict:
        formatted_signals = (
            "\n- ".join(analysis.key_signals) if analysis.key_signals else "None"
        )
        formatted_issues = (
            "\n- ".join(analysis.detected_issues)
            if analysis.detected_issues
            else "None"
        )
        formatted_risks = (
            "\n- ".join(analysis.business_risks) if analysis.business_risks else "None"
        )

        user_prompt = JUDGE_USER_PROMPT.format(
            goal=goal,
            benchmarks=benchmarks,
            context=context,
            analysis=analysis.analysis,
            key_signals=formatted_signals,
            detected_issues=formatted_issues,
            root_cause_hypothesis=analysis.root_cause_hypothesis,
            business_risks=formatted_risks,
            confidence_score=analysis.confidence_score,
        )

        response = chat_completion(
            client=self._client,
            system_text=JUDGE_SYSTEM_PROMPT,
            user_text=user_prompt,
            response_format=JudgeVerdict,
            model=model,
            temp=temp,
        )

        return response.choices[0].message.parsed
