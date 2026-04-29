from src.evaluation.base_evaluator import BaseEvaluator
from src.evaluation.services import EvaluationLogger

from .business_relevance_evaluator import BusinessRelevanceEvaluator
from .config import FINAL_WEIGHTS
from .GT_hybrid_evaluator import HybridEvaluator
from .prompt_compliance_evaluator import PromptComplianceEvaluator


class RecommendationEvaluator(BaseEvaluator):

    def __init__(self, llm, embed):
        super().__init__("recommendation")

        self.business = BusinessRelevanceEvaluator(llm)
        self.gt = HybridEvaluator(embed, llm)
        self.compliance = PromptComplianceEvaluator(llm)

        self.logger = EvaluationLogger("recommendation")

    def compute_final(self, business, gt, compliance):

        return round(
            business["score"] * FINAL_WEIGHTS["business_relevance"]
            + (gt["score"] if gt else 0) * FINAL_WEIGHTS["ground_truth"]
            + compliance["score"] * FINAL_WEIGHTS["compliance"],
            3,
        )

    def evaluate(self, data):
        recs = data["output"]

        analysis = data["analysis"]
        kpis = data["kpis"]
        gt_data = data.get("ground_truth")
        category = data.get("category")
        campaign_id = data.get("campaign_id")
        target = data.get("target")
        # 1. Business relevance
        business = self.business.evaluate(recs, analysis, kpis)
        # 2. Rules check
        compliance = self.compliance.evaluate(recs, analysis, kpis)
        # 3. Ground truth (hybrid)
        gt_result = self.gt.evaluate(recs, gt_data) if gt_data else None
        # 4. Final aggregation
        final_score = self.compute_final(
            compliance=compliance, business=business, gt=gt_result
        )

        result = {
            "category": category,
            "campaign_id": campaign_id,
            "target": target,
            "final_score": final_score,
            "business": business,
            "compliance": compliance,
            "ground_truth": gt_result,
        }

        result["log_file"] = self.logger.log(result)

        return result
