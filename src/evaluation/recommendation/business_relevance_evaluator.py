from typing import List

from .config import BUSINESS_WEIGHTS


class BusinessRelevanceEvaluator:

    def __init__(self, llm_callable):
        self.llm = llm_callable

    # ---------------------------
    # 🔹 Prompt Builder
    # ---------------------------

    def _build_prompt(self, recs, analysis, kpis):

        return f"""
You are a senior marketing evaluator.

Evaluate the quality of the recommendations BOTH:
1) Overall recommendation quality
2) Each individual recommendation
---
SCORING (0 to 1):
0 = poor
0.5 = acceptable
1 = excellent
---
CRITERIA:

1. insight_quality
Does each recommendation clearly explain WHY (cause or opportunity)?

2. actionability
Are steps clear, specific, and executable (what, where, how)?

3. data_grounding
Are recommendations supported by the provided data (metrics, platforms)?

4. kpi_alignment
Do recommendations clearly link to campaign KPIs?

5. priority_accuracy
Are high-impact recommendations correctly prioritized first?

6. decision_quality
Are these strong and correct business decisions?

7. feasibility
Are these realistically implementable?

8. readability
Are they clear and simple for non-marketers?

IMPORTANT RULES:
- Use ONLY the provided analysis and recommendations
- Do NOT assume missing data
- Be strict in scoring
- Do NOT give all 1.0 unless truly perfect
---
TASK:

1. Score EACH recommendation individually
2. Score OVERALL performance
3. Provide short explanation ONLY if score < 0.7
---
KPIs: {kpis}
---
ANALYSIS:
{analysis}
---
RECOMMENDATIONS:
{recs}
---

RETURN STRICT JSON:

{{
  "overall": {{
    "scores": {{
      "insight_quality": float,
      "actionability": float,
      "data_grounding": float,
      "kpi_alignment": float,
      "priority_accuracy": float,
      "decision_quality": float,
      "feasibility": float,
      "readability": float
    }},
    "explanations": {{
      "insight_quality": "string",
      "actionability": "string",
      "data_grounding": "string",
      "kpi_alignment": "string",
      "priority_accuracy": "string",
      "decision_quality": "string",
      "feasibility": "string",
      "readability": "string"
    }}
  }},
  "per_recommendation": [
    {{
      "id": "<rec_id>",
      "scores": {{
        "insight_quality": float,
        "actionability": float,
        "data_grounding": float,
        "kpi_alignment": float,
        "decision_quality": float,
        "feasibility": float
      }},
      "issues": ["list of problems if any"]
    }}
  ]
}}
"""

    # ---------------------------
    # 🔹 Evaluate
    # ---------------------------

    def evaluate(self, recs: List[dict], analysis: dict, kpis):

        if not recs:
            return {"score": 0, "error": "no_recommendations"}

        prompt = self._build_prompt(recs, analysis, kpis)

        try:
            response = self.llm(prompt)
            result = eval(response) if isinstance(response, str) else response
        except Exception:
            return {"score": 0, "error": "llm_failed"}

        # ---------------------------
        # 🔹 Extract Scores
        # ---------------------------

        overall_scores = result.get("overall", {}).get("scores", {})
        
        final_score = sum(
            overall_scores.get(k, 0) * BUSINESS_WEIGHTS[k] for k in BUSINESS_WEIGHTS
        )

        # ---------------------------
        # 🔹 Flags
        # ---------------------------

        flags = []

        for k, v in overall_scores.items():
            if v < 0.6:
                flags.append(f"low_{k}")

        # ---------------------------
        # 🔹 Weak Recommendations Detection
        # ---------------------------

        weak_recs = []

        for rec in result.get("per_recommendation", []):
            avg = sum(rec["scores"].values()) / len(rec["scores"])
            if avg < 0.6:
                weak_recs.append(rec["id"])

        return {
            "score": round(final_score, 3),
            "overall": result.get("overall"),
            "per_recommendation": result.get("per_recommendation"),
            "flags": flags,
            "weak_recommendations": weak_recs,
        }
    