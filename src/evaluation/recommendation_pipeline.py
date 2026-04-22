from src.evaluation.evaluation_pipeline import EvaluationPipeline


class RecommendationPipeline:

    def __init__(self, llm_callable, embedding_callable):
        self._pipeline = EvaluationPipeline(llm_callable, embedding_callable)

    def run(
        self,
        campaign_id: str,
        target: str,
        analysis_output: dict,
        recommendation_output: list,
        kpis: list,
        category: str = None,
    ):

        return self._pipeline.run_recommendation(
            campaign_id=campaign_id,
            target=target,
            analysis_output=analysis_output,
            recommendation_output=recommendation_output,
            kpis=kpis,
            category=category or target,
        )
