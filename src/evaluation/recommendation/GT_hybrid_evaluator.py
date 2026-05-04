from typing import Dict, List

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class HybridEvaluator:
    """
    Hybrid Ground Truth Evaluator

    Combines:
    - Embedding similarity (fast)
    - LLM comparison (fallback)
    - Coverage scoring
    - Explainability (matches + missed GT)
    """

    def __init__(self, embedding_callable, llm_callable):
        self.embed = embedding_callable
        self.llm = llm_callable

        # thresholds
        self.high_threshold = 0.75
        self.low_threshold = 0.60

    # =========================================================
    # 🔹 Convert recommendation to text
    # =========================================================

    def _to_text(self, rec: dict) -> str:
        return f"""
        Title: {rec.get("title", "")}
        Problem: {rec.get("whats_happening", "")}
        Actions: {[step.get("step") for step in rec.get("what_you_should_do", [])]}
        KPI: {rec.get("expected_impact", {}).get("primary_kpi", "")}
        """

    # =========================================================
    # 🔹 Embedding
    # =========================================================

    def _embed_batch(self, texts: List[str]) -> np.ndarray:
        return np.array([self.embed(t) for t in texts])

    def _similarity_matrix(self, A: np.ndarray, B: np.ndarray) -> np.ndarray:
        return cosine_similarity(A, B)

    # =========================================================
    # 🔹 LLM fallback comparison
    # =========================================================

    def _llm_compare(
        self, rec: List[dict], gt: List[dict], model: str, temp: float
    ) -> float:
        prompt = f"""
Compare these two marketing recommendations:

A (Model Output):
{rec}

B (Expert Ground Truth):
{gt}

Score similarity from 0 to 1 based on:
- business intent
- target outcome
- action similarity

Return ONLY a number.
"""
        try:
            return float(self.llm(prompt, model, temp))
        except:
            return 0.0

    # =========================================================
    # 🔹 MAIN Evaluation
    # =========================================================

    def evaluate(
        self,
        recommendations: List[dict],
        ground_truth: List[dict],
        model: str,
        temp: float,
    ) -> Dict:

        # ---------------------------
        # Input validation
        # ---------------------------
        if not recommendations or not ground_truth:
            return {"score": 0, "error": "missing_data"}

        # ---------------------------
        # Prepare text
        # ---------------------------
        rec_texts = [self._to_text(r) for r in recommendations]
        gt_texts = [self._to_text(g) for g in ground_truth]

        rec_vecs = self._embed_batch(rec_texts)
        gt_vecs = self._embed_batch(gt_texts)

        sim_matrix = self._similarity_matrix(rec_vecs, gt_vecs)

        # ---------------------------
        # Tracking
        # ---------------------------
        final_scores = []
        total_llm_calls = 0

        matches = []
        matched_gt_indices = set()

        # ---------------------------
        # Matching loop
        # ---------------------------
        for i, rec in enumerate(recommendations):

            best_idx = int(np.argmax(sim_matrix[i]))
            sim_score = float(sim_matrix[i][best_idx])
            gt = ground_truth[best_idx]

            # Initialize llm_score
            llm_score = None

            # Decide scoring strategy
            if sim_score >= self.high_threshold:
                final_score = sim_score

            elif self.low_threshold <= sim_score < self.high_threshold:
                llm_score = self._llm_compare(rec, gt, model, temp)
                total_llm_calls += 1
                final_score = (sim_score + llm_score) / 2

            else:
                llm_score = self._llm_compare(rec, gt, model, temp)
                total_llm_calls += 1
                final_score = llm_score

            final_scores.append(final_score)

            # Track match
            matches.append(
                {
                    "rec_id": rec.get("id"),
                    "matched_gt_id": gt.get("id"),
                    "similarity": round(sim_score, 3),
                    "llm_score": round(llm_score, 3) if llm_score is not None else None,
                }
            )

            matched_gt_indices.add(best_idx)

        # ---------------------------
        # Coverage
        # ---------------------------
        coverage_scores = sim_matrix.max(axis=0)
        coverage = float(np.mean(coverage_scores))

        # ---------------------------
        # Averages
        # ---------------------------
        avg_similarity = float(np.mean(final_scores))

        final_score = (0.6 * avg_similarity) + (0.4 * coverage)

        # ---------------------------
        # Duplicate penalty
        # ---------------------------
        matched_ids = [m["matched_gt_id"] for m in matches]

        if len(set(matched_ids)) < len(matched_ids):
            final_score -= 0.05  # small penalty

        final_score = max(final_score, 0.0)

        # ---------------------------
        # Missed GT insights
        # ---------------------------
        missed_gt = [
            ground_truth[i].get("id")
            for i in range(len(ground_truth))
            if i not in matched_gt_indices
        ]

        # ---------------------------
        # Flags
        # ---------------------------
        flags = []

        if coverage < 0.6:
            flags.append("missing_key_expert_insights")

        if avg_similarity < 0.6:
            flags.append("low_similarity_to_expert")

        if len(missed_gt) >= 2:
            flags.append(f"missing_key_GT_Recommendations : {len(missed_gt)}")

        # ---------------------------
        # Final output
        # ---------------------------
        return {
            "score": round(final_score, 3),
            "avg_similarity": round(avg_similarity, 3),
            "coverage": round(coverage, 3),
            "llm_calls": total_llm_calls,
            # Explainability
            "matches": matches,
            "missed_ground_truth": missed_gt,
            # Diagnostics
            "flags": flags,
            "total_recommendations": len(recommendations),
            "total_ground_truth": len(ground_truth),
        }
