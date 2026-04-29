from typing import Optional

from dotenv import load_dotenv

import src.llm as llm_handler
import src.metrics_engine as data_processor
from src.evaluation.orchestrator import EvaluationOrchestrator

CATEGORIES = [
    "Customer Acquisition",
    "Customer Satisfaction",
    "Revenue Growth",
    "Customer Retention",
]


def _load_evaluation_inputs(category: str):
    df = data_processor.load_data()
    if df is None or df.empty:
        raise ValueError("No campaign data loaded. Check input data source.")

    metrics = data_processor.calculate_metrics_full(df, category)
    response_dict_data = llm_handler.generate_response(df, category, metrics)

    analysis_output = response_dict_data.get("analysis", {})
    recommendation_output = response_dict_data.get("recommendations", [])
    kpis = response_dict_data.get("kpis", [])

    if not analysis_output:
        raise ValueError("Missing analysis output from LLM response.")
    if not recommendation_output:
        raise ValueError("Missing recommendation output from LLM response.")

    return df, analysis_output, recommendation_output, kpis


def run_evaluation_for_category(
    campaign_id: str,
    target: str,
    category: str,
    context_rows: int,
) -> dict:
    load_dotenv()

    (
        df,
        analysis_output,
        recommendation_output,
        kpis,
    ) = _load_evaluation_inputs(category)

    orchestrator = EvaluationOrchestrator(
        llm_callable=llm_handler.llm_callable,
        embedding_callable=llm_handler.embedding_callable,
    )

    campaign_context = df.head(max(context_rows, 1)).to_json(orient="records")

    return orchestrator.run_all(
        campaign_id=campaign_id,
        target=target,
        analysis_output=analysis_output,
        recommendation_output=recommendation_output,
        kpis=kpis,
        campaign_context=campaign_context,
        category=category,
    )


def run_evaluation_for_all_categories(
    campaign_id: str,
    context_rows: int,
    target_override: Optional[str] = None,
) -> dict:
    all_results = {}
    for category in CATEGORIES:
        target = target_override or category
        all_results[category] = run_evaluation_for_category(
            campaign_id=campaign_id,
            target=target,
            category=category,
            context_rows=context_rows,
        )
    return all_results
