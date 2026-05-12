from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional, Sequence

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
# 2. CRITERION DEFINITION (config/rubric)
# ─────────────────────────────────────────────


@dataclass(frozen=True)
class CriterionDefinition:
    name: str
    description: str
    weight: float
    pass_threshold: float
    borderline_threshold: float
    hard_fail_threshold: float
    rubric: str = ""


DEFAULT_CRITERIA: tuple[CriterionDefinition, ...] = (
    CriterionDefinition(
        name="analysis",
        description="Overall analysis is written in plain business language and directly addresses the campaign performance without using abbreviations",
        weight=0.30,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
         rubric=(
            "5: References actual metric values, compares to benchmarks, uses logical connectors (Consequently/Therefore/This indicates), no recommendations\n"
            "4: References metrics but benchmark comparison is implicit or partial\n"
            "3: Mentions metrics but draws no benchmark comparison\n"
            "2: Generic narrative with no specific numbers\n"
            "1: Vague, fluffy, or contains recommendations (strict violation)"
        ),
    ),
    CriterionDefinition(
        name="key_signals",
        description="Key signals are specific observations grounded in the raw campaign data, not generic statements",
        weight=0.10,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
        rubric=(
            "5: Each signal states actual metric value AND compares to benchmark (e.g. CVR of 1.1% is below the 1.4% industry benchmark)\n"
            "4: Signals cite metric values but skip explicit benchmark reference\n"
            "3: Signals present but values missing or only partially cited\n"
            "2: Generic observations not tied to actual data\n"
            "1: No signals or signals are copy-pasted from context without interpretation"
        ),
    ),
    CriterionDefinition(
        name="detected_issues",
        description="Detected issues are concrete problems with clear business impact, not vague or repetitive",
        weight=0.10,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
        rubric=(
            "5: Names specific issues with metric evidence AND classifies as Pre-Click or Post-Click bottleneck\n"
            "4: Names issues with metric evidence but bottleneck classification missing\n"
            "3: Issues mentioned but vague or without supporting metric values\n"
            "2: Only one issue named, or issues are generic\n"
            "1: No issues detected or section is empty"
        ),
    ),
    CriterionDefinition(
        name="root_cause_hypothesis",
        description="Root cause hypothesis logically follows from the detected issues and key signals with clear reasoning",
        weight=0.20,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
        rubric=(
            "5: Explicitly states Post-Click or Pre-Click bottleneck, connects CVR→CAC or CPC→CAC chain, cites benchmark\n"
            "4: Correct bottleneck direction but metric chain incomplete\n"
            "3: Plausible hypothesis but not grounded in benchmark comparison\n"
            "2: Hypothesis is speculative with no metric support\n"
            "1: Missing, generic, or contradicts the data"
        ),
    ),
    CriterionDefinition(
        name="business_risks",
        description="Business risks are specific with money or growth impact, written for a non-marketing audience",
        weight=0.15,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
        rubric=(
            "5: Risks are specific, quantified where possible, and tied to financial or growth impact\n"
            "4: Risks are specific and business-relevant but not quantified\n"
            "3: Risks mentioned but stated as possibilities without evidence\n"
            "2: Generic risks that apply to any campaign (e.g. performance may decline)\n"
            "1: No risks identified or risks are fabricated"
        ),
    ),
    CriterionDefinition(
        name="confidence_score",
        description="Confidence score is realistic and consistent with the strength of evidence provided in the analysis",
        weight=0.15,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
        rubric=(
            "5: Score is realistic (not 95%+ unless all metrics are strong) and analysis explains what drives the confidence level\n"
            "4: Score is realistic but no explanation of what supports it\n"
            "3: Score seems arbitrary with no connection to evidence quality\n"
            "2: Score is unrealistically high given weak or missing evidence\n"
            "1: Score is missing or nonsensical"
        ),
    ),
)


# ─────────────────────────────────────────────
# 3. CRITERION SCORE (result per criterion)
# ─────────────────────────────────────────────


@dataclass(frozen=True)
class CriterionScore:
    name: str
    score: int
    status: EvaluationStatus
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "status": self.status.value,
            "rationale": self.rationale,
        }


# ─────────────────────────────────────────────
# 4. JUDGE VERDICT (Pydantic — LLM output)
# ─────────────────────────────────────────────


class CriterionScoreSchema(BaseModel):
    name: str
    score: int = Field(..., ge=1, le=5)
    rationale: str


class JudgeVerdict(BaseModel):
    overall_score: int = Field(..., ge=1, le=5)
    overall_status: EvaluationStatus
    criteria_scores: List[CriterionScoreSchema]
    summary: str
    improvement_suggestions: List[str]


# ─────────────────────────────────────────────
# 5. JUDGE PROMPT
# ─────────────────────────────────────────────

JUDGE_SYSTEM_PROMPT = """
You are an expert evaluator of marketing campaign diagnostic analysis outputs.
Your job is to judge whether the analysis correctly applied a strict diagnostic framework.

DOMAIN KNOWLEDGE YOU MUST APPLY:
- CVR benchmark: 1.4%–2.5% (Shopify industry standard)
  - Below 1.4% = Post-Click bottleneck (landing page / checkout friction)
  - Above 2.5% = Pre-Click or Scale opportunity
- CPC threshold: above $2.00 indicates expensive traffic
- CAC is driven by EITHER poor CVR OR high CPC — the analysis must distinguish which
- The analysis step is DIAGNOSTIC ONLY — any recommendation or suggestion is a violation

SCORING RULES:
- Score each criterion from 1 to 5 (discrete integers only)
- Use the exact rubric provided per criterion — do not invent your own logic
- A score of 4 requires explicit metric values with benchmark comparison
- A score of 5 requires correct bottleneck classification AND metric correlation chain
- Never give 4 or 5 to vague text, even if it is well-written

COMMUNICATION RULES:
- Write rationale for a business lead with no marketing background
- Focus on money impact, growth impact, and risk
- Never accept vague language like "performance was moderate" as a score of 4 or 5
"""

JUDGE_USER_PROMPT = """
You are evaluating the following marketing analysis output.

ORIGINAL CAMPAIGN CONTEXT:
{context}

ANALYSIS OUTPUT TO JUDGE:
- Analysis: {analysis}
- Key Signals: {key_signals}
- Detected Issues: {detected_issues}
- Root Cause Hypothesis: {root_cause_hypothesis}
- Business Risks: {business_risks}
- Confidence Score: {confidence_score}

CRITERIA TO EVALUATE:
{criteria_text}

Return a JSON object with this exact structure:
{{
  "overall_score": <float 1-5>,
  "overall_status": <"pass" | "borderline" | "fail">,
  "criteria_scores": [
    {{"name": "<criterion_name>", "score": <int 1-5>, "rationale": "<explanation>"}}
  ],
  "summary": "<one sentence overall verdict>",
  "improvement_suggestions": ["<suggestion1>", "<suggestion2>"]
}}
"""


# ─────────────────────────────────────────────
# 6. ANALYSIS JUDGE CLASS
# ─────────────────────────────────────────────


class AnalysisJudge:
    def __init__(
        self,
        criteria: Optional[Sequence[CriterionDefinition]] = None,
        pass_threshold: float = 3.5,
    ) -> None:
        self._criteria = tuple(criteria or DEFAULT_CRITERIA)
        self._pass_threshold = pass_threshold
        self._client = get_client()

    def evaluate(
        self, analysis: AnalysisOutput, context: str, model: str, temp: float
    ) -> JudgeVerdict:
        criteria_text = self._build_criteria_text()

        formatted_issues = (
            "\n- ".join(analysis.detected_issues)
            if analysis.detected_issues
            else "None"
        )
        formatted_signals = (
            "\n- ".join(analysis.key_signals) if analysis.key_signals else "None"
        )
        formatted_risks = (
            "\n- ".join(analysis.business_risks) if analysis.business_risks else "None"
        )

        user_prompt = JUDGE_USER_PROMPT.format(
            context=context,
            analysis=analysis.analysis,
            key_signals=formatted_signals,
            detected_issues=formatted_issues,
            root_cause_hypothesis=analysis.root_cause_hypothesis,
            business_risks=formatted_risks,
            confidence_score=analysis.confidence_score,
            criteria_text=criteria_text,
        )

        response = chat_completion(
            client=self._client,
            system_text=JUDGE_SYSTEM_PROMPT,
            user_text=user_prompt,
            response_format=JudgeVerdict,
            model=model,
            temp=temp,
        )

        verdict = response.choices[0].message.parsed
        return verdict

    def _build_criteria_text(self) -> str:
        lines = []
        for criterion in self._criteria:
            lines.append(
                f"Criterion: {criterion.name} (weight={criterion.weight})\n"
                f"Description: {criterion.description}\n"
            f"Scoring rubric:\n{criterion.rubric}"
        )
    return "\n\n".join(lines)

    @staticmethod
    def _status_for_score(
        definition: CriterionDefinition,
        score: float,
    ) -> EvaluationStatus:
        if score >= definition.pass_threshold:
            return EvaluationStatus.PASS
        if score >= definition.borderline_threshold:
            return EvaluationStatus.BORDERLINE
        return EvaluationStatus.FAIL
