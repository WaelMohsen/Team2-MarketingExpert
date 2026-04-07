# evaluation/recommendation/prompt_compliance_evaluator.py

from typing import List, Dict
from statistics import mean


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
    """
    # =========================================================
    # 🔹 PROMPT RULE HEURISTICS
    # =========================================================

    def _kpi_mapping(self, recs: List[dict], kpis: List[str]) -> float:
        scores = []
        for r in recs:
            kpi = r.get("expected_impact", {}).get("primary_kpi")
            scores.append(1.0 if kpi in kpis else 0.0)
        return mean(scores) if scores else 0.0

    def _no_analysis_repetition(self, recs: List[dict], analysis: str) -> float:
        score = 1.0
        for r in recs:
            if r.get("whats_happening", "") in analysis:
                score -= 0.2
        return max(score, 0.0)

    def _action_orientation(self, recs: List[dict]) -> float:
        verbs = ["increase", "reduce", "optimize", "shift", "improve"]
        scores = []

        for r in recs:
            steps = r.get("what_you_should_do", [])
            text = " ".join([s.get("step", "") for s in steps]).lower()
            scores.append(1.0 if any(v in text for v in verbs) else 0.0)

        return mean(scores) if scores else 0.0
    """
    # =========================================================
    # 🔹 LLM COMPLIANCE JUDGE
    # =========================================================

    def _llm_compliance(self, recs: List[dict], analysis: dict, kpis) -> Dict:

        prompt = f"""
Evaluate if these recommendations follow the system rules:

RULES:
1. Use ONLY provided data
2. Be action-oriented
3. Do not repeat analysis
4. Be clear for non-marketers
5. Each recommendation must map to KPI

KPIs: {kpis}

ANALYSIS:
{analysis}

RECOMMENDATIONS:
{recs}

Score 0 to 1:
- no_hallucination
- clarity
- non_repetition

Return JSON.
"""
        try:
            return eval(self.llm(prompt))
        except:
            return {}

    # =========================================================
    # 🔹 MAIN
    # =========================================================

    def evaluate(
        self,
        recommendations: List[dict],
        analysis: dict,
        kpis: List[str]
    ) -> Dict:

        # ---------------------------
        # Structural checks
        # ---------------------------
        count_score = self._count_check(recommendations)
        fields_score = self._required_fields(recommendations)
        priority_score = self._priority_order(recommendations)
        """
        # ---------------------------
        # Prompt heuristics
        # ---------------------------
        kpi_score = self._kpi_mapping(recommendations, kpis)
        repetition_score = self._no_analysis_repetition(recommendations, str(analysis))
        action_score = self._action_orientation(recommendations)
        """
        # ---------------------------
        # LLM judgment
        # ---------------------------
        llm_scores = self._llm_compliance(recommendations, analysis, kpis)

        # ---------------------------
        # Combine
        # ---------------------------
        final_scores = {
            # structural
            "count_valid": count_score,
            "required_fields": fields_score,
            "priority_order": priority_score,
            """
            # heuristics
            "kpi_mapping": kpi_score,
            "no_repetition": repetition_score,
            "action_oriented": action_score,
            """
            # llm
            "no_hallucination": llm_scores.get("no_hallucination", 0),
            "clarity": llm_scores.get("clarity", 0),
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
        """
        if kpi_score < 0.6:
            flags.append("weak_kpi_mapping")
        """
        if llm_scores.get("no_hallucination", 1) < 0.7:
            flags.append("possible_hallucination")
        """
        if action_score < 0.5:
            flags.append("weak_actionability")
        """
        return {
            "score": round(overall, 3),
            "dimensions": final_scores,
            "flags": flags
        }