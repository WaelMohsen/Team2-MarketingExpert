# evaluation/recommendation/prompt_compliance_evaluator.py

from statistics import mean
from typing import Dict, List

from .parsing import parse_llm_mapping


class PromptComplianceEvaluator:

    def __init__(self, llm_callable):
        self.llm = llm_callable

    # =========================================================
    # 🔹 STRUCTURAL RULES (Former rule_checks)
    # =========================================================

    def _count_check(self, recs: List[dict]) -> float:
        return 1.0 if 5 <= len(recs) <= 8 else 0.0

    def _required_fields(self, recs: List[dict]) -> float:
        required_fields = ["title", "priority", "what_you_should_do", "evidence"]

        for r in recs:
            for f in required_fields:
                if f not in r:
                    return 0.0
        return 1.0

    def _priority_order(self, recs: List[dict]) -> float:
        priority_map = {"High": 0, "Medium": 1, "Low": 2}
        priorities = [priority_map.get(r.get("priority"), 3) for r in recs]
        return 1.0 if priorities == sorted(priorities) else 0.0

    # =========================================================
    # 🔹 LLM COMPLIANCE JUDGE
    # =========================================================

    def _llm_compliance(
        self, recs: List[dict], analysis: dict, kpis, model: str, temp: float
    ) -> Dict:

        prompt = f"""
Evaluate if these recommendations follow the system rules:

RULES:
1. Use ONLY provided data
2. Be action-oriented
3. Do not repeat analysis and recommendation
4. Be clear for non-marketers
5. Each recommendation must map to KPI

KPIs: {kpis}

ANALYSIS:
{analysis}

RECOMMENDATIONS:
{recs}

Score from 0 to 1:
- no_hallucination
- clarity
- non_repetition

RETURN STRICT JSON:

```json
{{
    "no_hallucination": float,
    "clarity": float,
    "non_repetition": float

 }}
```
"""
        try:
            return parse_llm_mapping(self.llm(prompt, model, temp))
        except Exception:
            return {}

    # =========================================================
    # 🔹 MAIN
    # =========================================================

    def evaluate(
        self,
        recommendations: List[dict],
        analysis: dict,
        kpis: List[str],
        model: str,
        temp: float,
    ) -> Dict:

        # ---------------------------
        # Structural checks
        # ---------------------------
        count_score = self._count_check(recommendations)
        fields_score = self._required_fields(recommendations)
        priority_score = self._priority_order(recommendations)

        # ---------------------------
        # LLM judgment
        # ---------------------------
        llm_scores = self._llm_compliance(recommendations, analysis, kpis, model, temp)

        # ---------------------------
        # Combine
        # ---------------------------
        final_scores = {
            # structural
            "count_valid": count_score,
            "required_fields": fields_score,
            "priority_order": priority_score,
            # llm
            "no_hallucination": llm_scores.get("no_hallucination", 0),
            "clarity": llm_scores.get("clarity", 0),
            "non_repetition": llm_scores.get("non_repetition", 0),
        }

        overall = mean(final_scores.values())

        # ---------------------------
        # Flags
        # ---------------------------
        flags = []

        if count_score == 0:
            flags.append("invalid_recommendation_count")

        if fields_score == 0:
            flags.append("missing_required_fields")

        if priority_score == 0:
            flags.append("priority_not_sorted")

        if final_scores.get("no_hallucination", 0) < 0.7:
            flags.append("hallucination_detected")

        if final_scores.get("non_repetition", 0) < 0.7:
            flags.append("repetition_detected")

        return {"score": round(overall, 3), "dimensions": final_scores, "flags": flags}
