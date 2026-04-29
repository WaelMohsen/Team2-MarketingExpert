from src.evaluation.orchestrator import EvaluationOrchestrator


class RecommendationPipeline:
    """Compatibility wrapper for recommendation-only evaluation calls."""

    def __init__(self, llm_callable, embedding_callable):
        self._orchestrator = EvaluationOrchestrator(llm_callable, embedding_callable)

    def run(
        self,
        campaign_id: str,
        target: str,
        analysis_output: dict,
        recommendation_output: list,
        kpis: list,
        category: str = None,
    ):

        return self._orchestrator.run_recommendation(
            campaign_id=campaign_id,
            target=target,
            analysis_output=analysis_output,
            recommendation_output=recommendation_output,
            kpis=kpis,
            category=category or target,
        )
