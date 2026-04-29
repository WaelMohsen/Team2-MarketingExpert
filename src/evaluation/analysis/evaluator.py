"""LLM-as-a-judge quality evaluator for analysis output.

This evaluator is intentionally standalone and does not alter the existing
analysis_judge module.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from src.evaluation.services import EvaluationLogger
from src.llm.client import chat_completion, get_client
from src.schemas.analysis_output_schema import AnalysisOutput

QUALITY_WEIGHTS: Dict[str, float] = {
    "clarity": 0.18,
    "data_grounding": 0.20,
    "logic_coherence": 0.20,
    "business_focus": 0.15,
    "confidence_calibration": 0.12,
    "no_recommendation": 0.15,
}

LOW_SCORE_THRESHOLD = 0.6


class DimensionScores(BaseModel):
    clarity: float = Field(..., ge=0.0, le=1.0)
    data_grounding: float = Field(..., ge=0.0, le=1.0)
    logic_coherence: float = Field(..., ge=0.0, le=1.0)
    business_focus: float = Field(..., ge=0.0, le=1.0)
    confidence_calibration: float = Field(..., ge=0.0, le=1.0)
    no_recommendation: float = Field(..., ge=0.0, le=1.0)


class DimensionExplanations(BaseModel):
    clarity: str
    data_grounding: str
    logic_coherence: str
    business_focus: str
    confidence_calibration: str
    no_recommendation: str


class QualityVerdict(BaseModel):
    scores: DimensionScores
    explanations: DimensionExplanations


SYSTEM_PROMPT = """
You are an expert evaluator of marketing campaign analysis outputs.
Your task is to judge the quality of an analysis across 6 dimensions.

SCORING RULES:
- Score each dimension from 0.0 to 1.0 (decimals allowed).
- 0.0 = completely absent or wrong.
- 0.5 = acceptable but missing depth or clarity.
- 1.0 = excellent and must be truly earned.
- Be strict. Do not inflate scores.

COMMUNICATION RULES:
- Write explanations in plain business English.
- Never use abbreviations like CTR, ROAS, CPA, CPC.
- Focus reasoning on money impact, growth impact, and risk.

DIMENSIONS:
1. clarity: plain business language, no jargon or abbreviations.
2. data_grounding: references concrete data points from context.
3. logic_coherence: root cause follows from signals/issues.
4. business_focus: discusses money, growth, and risk impact.
5. confidence_calibration: confidence matches evidence strength.
6. no_recommendation: analysis is diagnostic only (no advice/prescriptions).

For no_recommendation, score low if analysis uses recommendation language
such as: should, need to, recommend, increase, optimize, launch, consider,
improve, ensure, invest, reduce, focus on, adjust.
"""

USER_PROMPT = """
Evaluate the following marketing campaign analysis.

ORIGINAL CAMPAIGN CONTEXT:
{context}

ANALYSIS OUTPUT:
Analysis: {analysis}
Key Signals: {key_signals}
Detected Issues: {detected_issues}
Root Cause Hypothesis: {root_cause_hypothesis}
Business Risks: {business_risks}
Confidence Score: {confidence_score}

Return a JSON object with this exact structure:
{{
  "scores": {{
    "clarity": <float 0.0-1.0>,
    "data_grounding": <float 0.0-1.0>,
    "logic_coherence": <float 0.0-1.0>,
    "business_focus": <float 0.0-1.0>,
    "confidence_calibration": <float 0.0-1.0>,
    "no_recommendation": <float 0.0-1.0>
  }},
  "explanations": {{
    "clarity": "<brief explanation>",
    "data_grounding": "<brief explanation>",
    "logic_coherence": "<brief explanation>",
    "business_focus": "<brief explanation>",
    "confidence_calibration": "<brief explanation>",
    "no_recommendation": "<brief explanation>"
  }}
}}
"""


class AnalysisQualityEvaluator:
    def __init__(self, client=None, logger=None) -> None:
        self._client = client or get_client()
        self.logger = logger or EvaluationLogger("analysis")

    def evaluate(
        self,
        analysis: AnalysisOutput,
        context: str,
        category: Optional[str] = None,
    ) -> dict:
        user_prompt = self._build_user_prompt(analysis, context)

        try:
            response = chat_completion(
                client=self._client,
                system_text=SYSTEM_PROMPT,
                user_text=user_prompt,
                response_format=QualityVerdict,
            )
            verdict: QualityVerdict = response.choices[0].message.parsed
        except Exception:
            result = {
                "category": category,
                "score": 0,
                "error": "llm_failed",
                "flags": ["llm_failed"],
            }
            result["log_file"] = self.logger.log(result)
            return result

        scores = verdict.scores.dict()
        explanations = verdict.explanations.dict()
        weighted_score = self._compute_weighted_score(scores)
        flags = self._compute_flags(scores)

        result = {
            "category": category,
            "score": round(weighted_score, 3),
            "dimensions": scores,
            "explanations": explanations,
            "flags": flags,
        }
        result["log_file"] = self.logger.log(result)
        return result

    def _build_user_prompt(self, analysis: AnalysisOutput, context: str) -> str:
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

        return USER_PROMPT.format(
            context=context,
            analysis=analysis.analysis,
            key_signals=formatted_signals,
            detected_issues=formatted_issues,
            root_cause_hypothesis=analysis.root_cause_hypothesis,
            business_risks=formatted_risks,
            confidence_score=analysis.confidence_score,
        )

    @staticmethod
    def _compute_weighted_score(scores: Dict[str, float]) -> float:
        return sum(
            scores.get(dimension, 0.0) * weight
            for dimension, weight in QUALITY_WEIGHTS.items()
        )

    @staticmethod
    def _compute_flags(scores: Dict[str, float]) -> List[str]:
        flags: List[str] = []

        for dimension, value in scores.items():
            if value < LOW_SCORE_THRESHOLD:
                flags.append(f"low_{dimension}")

        if scores.get("no_recommendation", 1.0) < LOW_SCORE_THRESHOLD:
            flags.append("analysis_contains_recommendations")

        return flags
