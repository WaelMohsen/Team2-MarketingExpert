from src.evaluation.analysis_judge import AnalysisJudge
from src.evaluation.evaluation_pipeline import EvaluationPipeline
from src.evaluation.recommendation.evaluator import RecommendationEvaluator
from src.evaluation.services.ground_truth_loader import FileGroundTruthLoader

DEFAULT_GT_PATH = "data/benchmark/recommendation_GT.json"


def build_default_evaluation_pipeline(
    llm_callable,
    embedding_callable,
    timestamp,
    analysis_model,
    analysis_temp,
    recommendation_model,
    recommendation_temp,
) -> EvaluationPipeline:
    return EvaluationPipeline(
        recommendation_evaluator=RecommendationEvaluator(
            llm=llm_callable,
            embed=embedding_callable,
            timestamp=timestamp,
        ),
        ground_truth_loader=FileGroundTruthLoader(DEFAULT_GT_PATH),
        analysis_evaluator_factory=AnalysisJudge,
        analysis_model=analysis_model,
        analysis_temp=analysis_temp,
        recommendation_model=recommendation_model,
        recommendation_temp=recommendation_temp,
    )
