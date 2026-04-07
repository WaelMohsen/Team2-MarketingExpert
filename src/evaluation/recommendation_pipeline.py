from src.evaluation.recommendation.evaluator import RecommendationEvaluator
import json
import os 


class RecommendationPipeline:

    def __init__(self, llm_callable, embedding_callable):

        self.evaluator = RecommendationEvaluator(
            llm=llm_callable,
            embed=embedding_callable
        )

        self.gt_path =os.path.join("data","benchmark","recommendation_GT.json")
    
    def  load_ground_truth(self, path, campaign_id, target):

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for campaign in data:
            if campaign["campaign_id"] == campaign_id:
                return campaign["ground_truth"].get(target, [])

        return []
    def run(
        self,
        campaign_id: str,
        target: str,
        analysis_output: dict,
        recommendation_output:list,
        kpis: list
    ):

        # ---------------------------
        # 🔹 Load Ground Truth
        # ---------------------------
        gt_data = self.load_ground_truth(
            self.gt_path,
            campaign_id,
            target
        )

        # ---------------------------
        # 🔹 Build Evaluation Input
        # ---------------------------
        eval_input = {
            "output": recommendation_output,
            "analysis": analysis_output,
            "kpis": kpis,
            "ground_truth": gt_data
        }

        # ---------------------------
        # 🔹 Run Evaluation
        # ---------------------------
        result = self.evaluator.evaluate(eval_input)

        return result