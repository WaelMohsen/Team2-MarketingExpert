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


DEFAULT_CRITERIA: tuple[CriterionDefinition, ...] = (
    CriterionDefinition(
        name="analysis",
        description="Overall analysis is written in plain business language and directly addresses the campaign performance without using abbreviations",
        weight=0.30,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
    ),
    CriterionDefinition(
        name="key_signals",
        description="Key signals are specific observations grounded in the raw campaign data, not generic statements",
        weight=0.10,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
    ),
    CriterionDefinition(
        name="detected_issues",
        description="Detected issues are concrete problems with clear business impact, not vague or repetitive",
        weight=0.10,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
    ),
    CriterionDefinition(
        name="root_cause_hypothesis",
        description="Root cause hypothesis logically follows from the detected issues and key signals with clear reasoning",
        weight=0.20,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
    ),
    CriterionDefinition(
        name="business_risks",
        description="Business risks are specific with money or growth impact, written for a non-marketing audience",
        weight=0.15,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
    ),
    CriterionDefinition(
        name="confidence_score",
        description="Confidence score is realistic and consistent with the strength of evidence provided in the analysis",
        weight=0.15,
        pass_threshold=4.0,
        borderline_threshold=3.0,
        hard_fail_threshold=2.0,
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
You are an expert evaluator of marketing campaign analysis outputs.
Your job is to judge the quality of an analysis based on specific criteria.

SCORING RULES:
- Score each criterion from 1 to 5 (discrete integers only)
- 1 = very poor, 2 = poor, 3 = acceptable, 4 = good, 5 = excellent
- Be strict. A score of 4 or 5 must be earned.
- Always explain your score in plain English in the rationale field.

COMMUNICATION RULES:
- Never use abbreviations like CTR, ROAS, CPA in your rationale.
- Focus on money impact, growth impact, and risk in your reasoning.
- Write for a business lead with no marketing background.
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
        self,
        analysis: AnalysisOutput,
        context: str,
        model :str ,
        temp : float
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
            model= model ,
            temp= temp 
        )

        verdict = response.choices[0].message.parsed
        return verdict

    def _build_criteria_text(self) -> str:
        lines = []
        for criterion in self._criteria:
            lines.append(
                f"- {criterion.name} (weight={criterion.weight}): {criterion.description}"
            )
        return "\n".join(lines)

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
