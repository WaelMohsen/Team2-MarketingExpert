from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from ..llm.client import chat_completion, get_client
from ..schemas.analysis_output_schema import AnalysisOutput
import json
from pathlib import Path



# ─────────────────────────────────────────────
# 1. STATUS ENUM
# ─────────────────────────────────────────────


class EvaluationStatus(str, Enum):
    PASS = "pass"
    BORDERLINE = "borderline"
    FAIL = "fail"


# ─────────────────────────────────────────────
# 2. CRITERION DEFINITION
# ─────────────────────────────────────────────


@dataclass(frozen=True)
class CriterionDefinition:
    name: str
    description: str
    weight: float
    pass_threshold: float = 4.0
    borderline_threshold: float = 3.0
    hard_fail_threshold: float = 2.0

# ─────────────────────────────────────────────
# JUDGE ANCHOR REGISTRY
# ─────────────────────────────────────────────
# Reference 5/5 analyses, injected into JUDGE_SYSTEM_PROMPT
# so the judge calibrates against a concrete example, not just rubric prose.

_ANCHOR_DIR = Path(__file__).resolve().parents[2] / "prompts" / "judge_anchors"

ANCHOR_REGISTRY: Dict[str, str] = {
    "Customer Acquisition": "acquisition.json",
    "Customer Retention":   "retention.json",
}


def _load_anchor(target: str) -> str:
    """Load the 5/5 reference example for a target. Returns empty string if missing."""
    filename = ANCHOR_REGISTRY.get(target)
    if filename is None:
        return ""
    path = _ANCHOR_DIR / filename
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""

# ─────────────────────────────────────────────
# 3. CRITERIA — ACQUISITION
# ─────────────────────────────────────────────


DEFAULT_CRITERIA_ACQUISITION: Tuple[CriterionDefinition, ...] = (

    CriterionDefinition(
        name="bottleneck_identification",
        description="""
        Analysis correctly identifies the bottleneck type:
        - Pre-Click when CVR > 2.5% but acquisition cost is high
        - Post-Click when CVR < 1.4%
        - None when both are healthy
        Must cite actual CVR and compare to 1.4% benchmark.
        Must state what NOT to do based on bottleneck found.
        """,
        weight=0.30,
    ),

    CriterionDefinition(
        name="channel_diagnosis",
        description="""
        Analysis compares at least 2 channels by acquisition cost
        and conversion rate. Must identify:
        - Which channel has lowest acquisition cost and why
        - Which channel is wasting budget relative to performance
        - Whether budget allocation matches channel efficiency
        Generic statements without channel names and numbers score 1-2.
        """,
        weight=0.25,
    ),

    CriterionDefinition(
        name="metric_chain_reasoning",
        description="""
        Analysis connects the acquisition metric chain:
        Impressions → Clicks → Conversions → Acquisition Cost → Revenue
        Must show how weakness in one metric flows to business outcome.
        Jumping to conclusions without the chain scores 1-2.
        """,
        weight=0.20,
    ),

    CriterionDefinition(
        name="benchmark_usage",
        description="""
        Analysis uses correct industry benchmarks:
        - Conversion rate: 1.4% minimum, 2.5% good
        - Revenue return: 4x minimum spend
        Must state whether campaign is above or below benchmark.
        Scoring without any benchmark reference scores 1-2.
        """,
        weight=0.15,
    ),

    CriterionDefinition(
        name="actionable_diagnosis",
        description="""
        Analysis concludes with a diagnosis that enables action:
        - States the primary problem in one clear sentence
        - States what should NOT be done
        - Avoids vague conclusions like 'needs improvement'
        A diagnosis that could apply to any campaign scores 1-2.
        """,
        weight=0.10,
    ),
)


# ─────────────────────────────────────────────
# 4. CRITERIA — RETENTION
# ─────────────────────────────────────────────


DEFAULT_CRITERIA_RETENTION: Tuple[CriterionDefinition, ...] = (

    CriterionDefinition(
        name="churn_diagnosis",
        description="""
        Analysis correctly interprets churn rate across channels:
        - Identifies which channel has highest churn with its number
        - States financial impact in dollars (churning customers × AOV)
        - Compares retained vs churned customer value
        Generic statements like 'churn is a risk' score 1-2.
        """,
        weight=0.30,
    ),

    CriterionDefinition(
        name="leaky_bucket_detection",
        description="""
        Analysis checks for leaky bucket pattern:
        - High new customers but low retained = acquisition masking
          retention failure
        - Must state whether pattern is present or absent
        - If present must quantify revenue lost through churn
        Missing this check entirely scores 1-2.
        """,
        weight=0.25,
    ),

    CriterionDefinition(
        name="retention_channel_comparison",
        description="""
        Analysis compares retention across channels:
        - Which channel retains customers longest
        - Whether high acquisition cost channels also have high churn
        - Gap between owned channels (email, SMS) and paid channels
        Must reference at least 2 channels with specific numbers.
        """,
        weight=0.20,
    ),

    CriterionDefinition(
        name="ltv_cac_assessment",
        description="""
        Analysis evaluates long-term customer value vs acquisition cost:
        - Must reference or compute annual value to acquisition cost ratio
        - Healthy threshold is 3x or above
        - Must identify which channels produce most valuable customers
        Ignoring long-term value entirely scores 1-2.
        """,
        weight=0.15,
    ),

    CriterionDefinition(
        name="risk_quantification",
        description="""
        Business risks stated with specific financial figures:
        - Must include numeric estimate e.g.
          '250 churning customers × $22 average order = $5,500 at risk'
        - Not acceptable: 'revenue may decline'
        - Time horizon must be stated
        Any risk without a number scores 1-2.
        """,
        weight=0.10,
    ),
)


# ─────────────────────────────────────────────
# 5. CRITERIA REGISTRY
# ─────────────────────────────────────────────


CRITERIA_REGISTRY: Dict[str, Tuple[CriterionDefinition, ...]] = {
    "Customer Acquisition": DEFAULT_CRITERIA_ACQUISITION,
    "Customer Retention":   DEFAULT_CRITERIA_RETENTION,
}


# ─────────────────────────────────────────────
# 6. PYDANTIC OUTPUT SCHEMA FOR LLM
# ─────────────────────────────────────────────


class CriterionScoreSchema(BaseModel):
    name: str
    score: int = Field(..., ge=1, le=5)
    rationale: str


class JudgeVerdict(BaseModel):
    criteria_scores: List[CriterionScoreSchema]
    summary: str
    improvement_suggestions: List[str]


# ─────────────────────────────────────────────
# 7. PROMPTS
# ─────────────────────────────────────────────


# in analysis_judge.py — no dataclass change
JUDGE_SYSTEM_PROMPT_TEMPLATE = """
You are an expert evaluator of marketing campaign analysis outputs.

SCORING RULES:
- Score each criterion from 1 to 5 (integers only)
- 1=very poor  2=poor  3=acceptable  4=good  5=excellent
- A score of 4 or 5 must be earned with specific evidence.
- Reference actual numbers and channel names from the analysis.

COMMUNICATION RULES:
- Never use abbreviations like CTR, ROAS, CPA in your rationale.
- Focus on money impact, growth impact, and risk.
- Write for a business lead with no marketing background.

<<ANCHOR_BLOCK>>
"""

_ANCHOR_INSTRUCTION = """
REFERENCE EXAMPLE OF A 5/5 ANALYSIS FOR THIS TARGET:
The JSON below is the calibration anchor. It demonstrates the depth,
specificity, benchmark grounding, channel-level rigor, and quantification
that earn full marks on every criterion.

When scoring a candidate analysis:
- Match this depth on a criterion → score 5
- Materially shallower but rubric items present → score 3
- Generic, missing rubric items, or recommendation language → score 1-2

ANCHOR JSON:
{anchor_json}
"""


def _build_judge_system_prompt(target: str) -> str:
    """Inject the target's reference anchor into the system prompt template."""
    anchor = _load_anchor(target)
    if not anchor:
        return JUDGE_SYSTEM_PROMPT_TEMPLATE.replace("<<ANCHOR_BLOCK>>", "")
    anchor_block = _ANCHOR_INSTRUCTION.replace("{anchor_json}", anchor)
    return JUDGE_SYSTEM_PROMPT_TEMPLATE.replace("<<ANCHOR_BLOCK>>", anchor_block)

JUDGE_USER_PROMPT = """
CAMPAIGN CONTEXT:
{context}

ANALYSIS TO EVALUATE:
- Analysis:              {analysis}
- Key Signals:           {key_signals}
- Detected Issues:       {detected_issues}
- Root Cause:            {root_cause}
- Business Risks:        {business_risks}
- Confidence Score:      {confidence_score}

CRITERIA (score each 1-5):
{criteria_text}

Return JSON:
{{
  "criteria_scores": [
    {{"name": "<name>", "score": <int>, "rationale": "<text>"}}
  ],
  "summary": "<one sentence verdict>",
  "improvement_suggestions": ["<suggestion1>", "<suggestion2>"]
}}
"""


# ─────────────────────────────────────────────
# 8. ANALYSIS JUDGE
# ─────────────────────────────────────────────


class AnalysisJudge:

    def __init__(self, target: str) -> None:
        self._target = target
        self._criteria = CRITERIA_REGISTRY.get(
            target, DEFAULT_CRITERIA_ACQUISITION
        )
        self._client = get_client()

    def _weighted_score(self, verdict: JudgeVerdict) -> float:
        """Deterministic weighted score — never trust LLM overall_score."""
        weight_map = {c.name: c.weight for c in self._criteria}
        return round(
            sum(
                (cs.score / 5.0) * weight_map.get(cs.name, 0)
                for cs in verdict.criteria_scores
            ),
            3,
        )

    def _status(self, score: float) -> EvaluationStatus:
        if score >= 0.80:
            return EvaluationStatus.PASS
        if score >= 0.60:
            return EvaluationStatus.BORDERLINE
        return EvaluationStatus.FAIL

    def _format_analysis(self, analysis: AnalysisOutput) -> Dict[str, str]:
        """Format nested fields into readable strings for the prompt."""
        return {
            "key_signals": "\n".join(
                f"- {s.channel or 'Overall'}: {s.observation} "
                f"(actual={s.actual_value}, benchmark={s.benchmark_value})"
                for s in analysis.key_signals
            ),
            "detected_issues": "\n".join(
                f"- [{i.severity}] {i.affected_channel}: {i.issue} "
                f"| impact: {i.business_impact}"
                for i in analysis.detected_issues
            ),
            "business_risks": "\n".join(
                f"- [{r.likelihood}] {r.risk} "
                f"| financial: {r.financial_impact} "
                f"| horizon: {r.time_horizon}"
                for r in analysis.business_risks
            ),
            "root_cause": (
                f"{analysis.root_cause_hypothesis.hypothesis} "
                f"(bottleneck: {analysis.root_cause_hypothesis.bottleneck_type})"
            ),
        }

    def _criteria_text(self) -> str:
        return "\n".join(
            f"[{c.name}] weight={c.weight}\n{c.description}"
            for c in self._criteria
        )

    def evaluate(
        self,
        analysis: AnalysisOutput,
        context: str,
        model: str,
        temp: float,
    ) -> Dict[str, Any]:

        formatted = self._format_analysis(analysis)

        user_prompt = JUDGE_USER_PROMPT.format(
            context=context,
            analysis=analysis.analysis,
            key_signals=formatted["key_signals"],
            detected_issues=formatted["detected_issues"],
            root_cause=formatted["root_cause"],
            business_risks=formatted["business_risks"],
            confidence_score=analysis.confidence_score,
            criteria_text=self._criteria_text(),
        )

        response = chat_completion(
            client=self._client,
            system_text=_build_judge_system_prompt(self._target),
            user_text=user_prompt,
            response_format=JudgeVerdict,
            model=model,
            temp=temp,
        )
        verdict = response.choices[0].message.parsed

        # deterministic score and status — not from LLM
        score = self._weighted_score(verdict)
        status = self._status(score)

        return {
            "overall_score": score,
            "overall_status": status.value,
            "criteria_scores": [cs.dict() for cs in verdict.criteria_scores],
            "summary": verdict.summary,
            "improvement_suggestions": verdict.improvement_suggestions,
        }