from typing import Dict, Optional

from dotenv import load_dotenv

import src.llm as llm_handler
import src.metrics_engine as data_processor
from src.llm.pipeline import CATEGORIES

from .pipeline_factory import build_default_evaluation_pipeline
from .run_config import DEFAULT_CONFIG_PATH, RunConfig, load_run_config
from .services.campaign_data_service import CampaignDataService
from .services.evaluation_log_writer import EvaluationLogWriter
from .services.run_metadata_service import RunMetadataService


def _build_pipeline(
    run_config: RunConfig,
    timestamp_token: str,
):
    return build_default_evaluation_pipeline(
        llm_callable=llm_handler.llm_callable,
        embedding_callable=llm_handler.embedding_callable,
        timestamp=timestamp_token,
        analysis_model=run_config.evaluation.analysis_judge_model,
        analysis_temp=run_config.evaluation.analysis_judge_temp,
        recommendation_model=run_config.evaluation.recommendation_judge_model,
        recommendation_temp=run_config.evaluation.recommendation_judge_temp,
    )


def run_target(
    campaign_name: str,
    category: str,
    context_rows: int,
    run_config: RunConfig,
    run_id: Optional[str],
    source_df=None,
) -> Dict:
    load_dotenv()
    metadata_service = RunMetadataService()
    campaign_data_service = CampaignDataService(data_processor.load_data)
    log_writer = EvaluationLogWriter(run_config)

    if run_id is None:
        run_id = metadata_service.build_run_id()

    campaign_df = campaign_data_service.campaign_frame(
        campaign_name, source_df=source_df
    )
    metrics = data_processor.calculate_metrics_full(campaign_df, category)

    generation_output = llm_handler.generate_response(
        campaign_df,
        category,
        metrics,
        run_config.generation.analysis_model,
        run_config.generation.analysis_temp,
        run_config.generation.recommendation_model,
        run_config.generation.recommendation_temp,
    )
    if isinstance(generation_output, str):
        raise ValueError(generation_output)

    analysis_output = generation_output.get("analysis", {})
    recommendation_output = generation_output.get("recommendations", [])
    kpis = generation_output.get("kpis", [])

    if not analysis_output:
        raise ValueError("Missing analysis output from LLM response.")
    if not recommendation_output:
        raise ValueError("Missing recommendation output from LLM response.")

    event_now = metadata_service.utc_now()
    event_token = metadata_service.timestamp_token(event_now)
    event_iso = metadata_service.iso_utc(event_now)
    category_slug = metadata_service.slugify(category)

    pipeline_log_path = log_writer.write_pipeline_log(
        run_id=run_id,
        timestamp_utc=event_iso,
        campaign_name=campaign_name,
        category=category,
        category_slug=category_slug,
        event_token=event_token,
        generation_output=generation_output,
    )

    pipeline = _build_pipeline(run_config, event_token)
    campaign_context = campaign_df.head(max(context_rows, 1)).to_json(orient="records")
    evaluation_output = pipeline.run_all(
        campaign_id=campaign_name,
        target=category,
        analysis_output=analysis_output,
        recommendation_output=recommendation_output,
        kpis=kpis,
        campaign_context=campaign_context,
        category=category,
    )

    analysis_log_path = log_writer.write_analysis_log(
        run_id=run_id,
        timestamp_utc=event_iso,
        campaign_name=campaign_name,
        category=category,
        category_slug=category_slug,
        event_token=event_token,
        analysis_evaluation=evaluation_output.get("analysis_evaluation"),
        pipeline_log_path=pipeline_log_path,
    )

    recommendation_log_path = log_writer.write_recommendation_log(
        run_id=run_id,
        timestamp_utc=event_iso,
        campaign_name=campaign_name,
        category=category,
        category_slug=category_slug,
        event_token=event_token,
        recommendation_evaluation=evaluation_output.get("recommendation_evaluation"),
        pipeline_log_path=pipeline_log_path,
    )

    return {
        "run_id": run_id,
        "timestamp_utc": event_iso,
        "campaign_id": campaign_name,
        "campaign_name": campaign_name,
        "target": category,
        "category": category,
        "pipeline_log_path": pipeline_log_path,
        "analysis_log_path": analysis_log_path,
        "recommendation_log_path": recommendation_log_path,
        "analysis_evaluation": evaluation_output.get("analysis_evaluation"),
        "recommendation_evaluation": evaluation_output.get("recommendation_evaluation"),
    }


def run_all_targets(
    campaign_name: str,
    context_rows: int,
    config_path: str = DEFAULT_CONFIG_PATH,
    target_override: Optional[str] = None,
) -> Dict:
    metadata_service = RunMetadataService()
    campaign_data_service = CampaignDataService(data_processor.load_data)
    run_started = metadata_service.utc_now()
    run_id = metadata_service.build_run_id(run_started)
    run_config = load_run_config(config_path)

    df = campaign_data_service.load_all()

    targets = [target_override] if target_override else list(CATEGORIES)
    results = {}
    for category in targets:
        results[category] = run_target(
            campaign_name=campaign_name,
            category=category,
            context_rows=context_rows,
            run_config=run_config,
            run_id=run_id,
            source_df=df,
        )

    return {
        "run_id": run_id,
        "timestamp_utc": metadata_service.iso_utc(run_started),
        "campaign_id": campaign_name,
        "campaign_name": campaign_name,
        "targets": targets,
        "config_path": config_path,
        "results": results,
    }
