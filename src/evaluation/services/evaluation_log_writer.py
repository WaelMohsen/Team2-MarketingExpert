import json
import os
from typing import Dict

from src.evaluation.run_config import RunConfig

BASE_EVALUATION_LOG_DIR = "evaluation_logs"
PIPELINE_LOG_DIR = os.path.join(BASE_EVALUATION_LOG_DIR, "pipeline")
ANALYSIS_LOG_DIR = os.path.join(BASE_EVALUATION_LOG_DIR, "analysis")
RECOMMENDATION_LOG_DIR = os.path.join(BASE_EVALUATION_LOG_DIR, "recommendation")


class EvaluationLogWriter:
    def __init__(self, run_config: RunConfig):
        self._run_config = run_config

    def generation_metadata(self) -> Dict:
        return {
            "analysis_generation_model": self._run_config.generation.analysis_model,
            "analysis_generation_temp": self._run_config.generation.analysis_temp,
            "recommendation_generation_model": self._run_config.generation.recommendation_model,
            "recommendation_generation_temp": self._run_config.generation.recommendation_temp,
        }

    def write_pipeline_log(
        self,
        *,
        run_id: str,
        timestamp_utc: str,
        campaign_name: str,
        category: str,
        category_slug: str,
        event_token: str,
        generation_output: Dict,
    ) -> str:
        payload = {
            "run_id": run_id,
            "timestamp_utc": timestamp_utc,
            "campaign_id": campaign_name,
            "campaign_name": campaign_name,
            "target": category,
            "category": category,
            **self.generation_metadata(),
            "payload": generation_output,
        }
        return self._write_json(
            PIPELINE_LOG_DIR,
            f"eval_{event_token}_{category_slug}.json",
            payload,
        )

    def write_analysis_log(
        self,
        *,
        run_id: str,
        timestamp_utc: str,
        campaign_name: str,
        category: str,
        category_slug: str,
        event_token: str,
        analysis_evaluation: Dict,
        pipeline_log_path: str,
    ) -> str:
        payload = {
            "run_id": run_id,
            "timestamp_utc": timestamp_utc,
            "campaign_id": campaign_name,
            "campaign_name": campaign_name,
            "target": category,
            "category": category,
            **self.generation_metadata(),
            "judge_model": self._run_config.evaluation.analysis_judge_model,
            "judge_temp": self._run_config.evaluation.analysis_judge_temp,
            **(analysis_evaluation or {}),
            "pipeline_log_path": pipeline_log_path,
        }
        return self._write_json(
            ANALYSIS_LOG_DIR,
            f"eval_{event_token}_{category_slug}.json",
            payload,
        )

    def write_recommendation_log(
        self,
        *,
        run_id: str,
        timestamp_utc: str,
        campaign_name: str,
        category: str,
        category_slug: str,
        event_token: str,
        recommendation_evaluation: Dict,
        pipeline_log_path: str,
    ) -> str:
        payload = {
            "run_id": run_id,
            "timestamp_utc": timestamp_utc,
            "campaign_id": campaign_name,
            "campaign_name": campaign_name,
            "target": category,
            "category": category,
            **self.generation_metadata(),
            "judge_model": self._run_config.evaluation.recommendation_judge_model,
            "judge_temp": self._run_config.evaluation.recommendation_judge_temp,
            **(recommendation_evaluation or {}),
            "pipeline_log_path": pipeline_log_path,
        }
        return self._write_json(
            RECOMMENDATION_LOG_DIR,
            f"eval_{event_token}_{category_slug}.json",
            payload,
        )

    @staticmethod
    def _write_json(directory: str, filename: str, payload: Dict) -> str:
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, filename)
        with open(path, "w", encoding="utf-8") as output_file:
            json.dump(payload, output_file, indent=2, ensure_ascii=False)
        return path
