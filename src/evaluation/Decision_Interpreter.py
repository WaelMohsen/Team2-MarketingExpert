from typing import Dict, List


class DecisionInterpreter:

    def __init__(self):
        # thresholds (you can tune later)
        self.accept_threshold = 0.8
        self.partial_threshold = 0.7
        self.gt_strong_threshold = 0.7
        self.rec_strong_threshold = 0.8
        self.rec_weak_threshold = 0.6

    # =========================================================
    # 🔹 MAIN ENTRY
    # =========================================================

    def interpret(self, evaluation_output: Dict) -> Dict:

        final_score = evaluation_output.get("final_score", 0)
        business = evaluation_output.get("business", {})
        compliance = evaluation_output.get("compliance", {})
        gt = evaluation_output.get("ground_truth", {})

        # ---------------------------
        # 1. Decision
        # ---------------------------
        decision = self._build_decision(final_score, gt,business, compliance)

        # ---------------------------
        # 2. Summary
        # ---------------------------
        summary = self._build_summary(business, compliance, gt)

        # ---------------------------
        # 3. Recommendation Actions
        # ---------------------------
        rec_actions = self._classify_recommendations(business)

        # ---------------------------
        # 4. GT Insights
        # ---------------------------
        gt_insights = self._build_gt_insights(gt)

        # ---------------------------
        # Final Output
        # ---------------------------
        return {
            "final_score": final_score,
            "decision": decision,
            "summary": summary,
            "recommendation_actions": rec_actions,
            "ground_truth_insights": gt_insights,
            "diagnostics": evaluation_output  # keep original
        }
    def _compute_confidence(self, final_score, business, compliance, gt):

        signals = []

        # =========================================================
        # 1. Agreement Between Evaluators
        # =========================================================
        business_score = business.get("score", 0)
        compliance_score = compliance.get("score", 0)
        gt_score = gt.get("score", 0) if gt else 0

        scores = [business_score, compliance_score, gt_score]

        # variance-based agreement
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)

        agreement = 1 - min(variance, 1)  # normalize
        signals.append(agreement)

        # =========================================================
        # 2. Recommendation Consistency
        # =========================================================
        recs = business.get("per_recommendation", [])
        if recs:
            rec_avgs = [
                sum(r["scores"].values()) / len(r["scores"])
                for r in recs
            ]
            rec_mean = sum(rec_avgs) / len(rec_avgs)
            rec_variance = sum((r - rec_mean) ** 2 for r in rec_avgs) / len(rec_avgs)

            consistency = 1 - min(rec_variance, 1)
            signals.append(consistency)

        # =========================================================
        # 3. Ground Truth Reliability
        # =========================================================
        if gt:
            coverage = gt.get("coverage", 0)
            avg_similarity = gt.get("avg_similarity", 0)

            gt_reliability = (coverage + avg_similarity) / 2
            signals.append(gt_reliability)

        # =========================================================
        # 4. Evaluation Noise (LLM usage)
        # =========================================================
        if gt:
            llm_calls = gt.get("llm_calls", 0)
            total_recs = gt.get("total_recommendations", 1)

            noise_ratio = llm_calls / total_recs if total_recs else 1
            noise_penalty = 1 - min(noise_ratio, 1)

            signals.append(noise_penalty)

        # =========================================================
        # Final Confidence
        # =========================================================
        confidence = sum(signals) / len(signals)

        return round(confidence, 3) , signals
    # =========================================================
    # 🔹 Decision Logic
    # =========================================================

    def _build_decision(self, final_score: float, gt: Dict,business, compliance) -> Dict:

        gt_score = gt.get("score", 0) if gt else 0

        if final_score >= self.accept_threshold and gt_score >= self.gt_strong_threshold:
            status = "ACCEPT"
        elif final_score >= self.partial_threshold:
            status = "PARTIAL_ACCEPT"
        else:
            status = "REJECT"

        confidence , signals = self._compute_confidence(
            final_score, business, compliance, gt
        )

        reason = self._decision_reason(final_score, gt_score)

        return {
            "status": status,
            "confidence": confidence,
            "reason": reason,
            "signals" : signals
        }

    def _decision_reason(self, final_score, gt_score):

        if final_score > 0.8 and gt_score < 0.7:
            return "High quality recommendations but weak alignment with expert strategy"

        if final_score < 0.7:
            return "Overall recommendation quality is insufficient"

        if gt_score < 0.6:
            return "Recommendations miss key expert-level strategies"

        return "Strong recommendations aligned with expected strategy"

    # =========================================================
    # 🔹 Summary
    # =========================================================

    def _build_summary(self, business: Dict, compliance: Dict, gt: Dict) -> Dict:

        strengths = []
        weaknesses = []

        # Business strengths
        overall_scores = business.get("overall", {}).get("scores", {})

        for k, v in overall_scores.items():
            if v >= 0.9:
                strengths.append(f"Strong {k.replace('_', ' ')}")
            elif v < 0.7:
                weaknesses.append(f"Weak {k.replace('_', ' ')}")

        # Compliance
        if compliance.get("score", 0) == 1:
            strengths.append("Fully compliant with prompt rules")

        # GT
        if gt:
            if gt.get("score", 0) < 0.6:
                weaknesses.append("Low alignment with expert ground truth")

            if gt.get("missed_ground_truth"):
                weaknesses.append("Missing important expert strategies")

        return {
            "strengths": list(set(strengths)),
            "weaknesses": list(set(weaknesses))
        }

    # =========================================================
    # 🔹 Recommendation Classification
    # =========================================================

    def _classify_recommendations(self, business: Dict) -> Dict:

        keep, review, revise = [], [], []

        for rec in business.get("per_recommendation", []):
            scores = rec.get("scores", {})
            avg_score = sum(scores.values()) / len(scores) if scores else 0

            rec_id = rec.get("id")

            if avg_score >= self.rec_strong_threshold:
                keep.append(rec_id)
            elif avg_score >= self.rec_weak_threshold:
                review.append(rec_id)
            else:
                revise.append(rec_id)

        return {
            "keep": keep,
            "review": review,
            "revise": revise
        }

    # =========================================================
    # 🔹 Ground Truth Insights
    # =========================================================

    def _build_gt_insights(self, gt: Dict) -> Dict:

        if not gt:
            return {}

        missed = gt.get("missed_ground_truth", [])

        insights = []

        for m in missed:
            insights.append({
                "id": m,
                "importance": "high",
                "suggestion": "Add strategy aligned with this missing expert recommendation"
            })

        return {
            "coverage": gt.get("coverage"),
            "avg_similarity": gt.get("avg_similarity"),
            "missing": insights
        }