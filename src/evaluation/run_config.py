import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GenerationConfig:
    analysis_model: str
    analysis_temp: float
    recommendation_model: str
    recommendation_temp: float


@dataclass(frozen=True)
class EvaluationConfig:
    analysis_judge_model: str
    analysis_judge_temp: float
    recommendation_judge_model: str
    recommendation_judge_temp: float


@dataclass(frozen=True)
class RuntimeConfig:
    campaign_id: str
    category: Optional[str]
    context_rows: int
    experiment_tag: str = ""

@dataclass(frozen=True)
class RunConfig:
    runtime: RuntimeConfig
    generation: GenerationConfig
    evaluation: EvaluationConfig


DEFAULT_CONFIG_PATH = os.path.join("config", "evaluation_run_config.json")


def load_run_config(config_path: str = DEFAULT_CONFIG_PATH) -> RunConfig:
    with open(config_path, "r", encoding="utf-8") as config_file:
        raw = json.load(config_file)

    runtime = raw.get("runtime", {})
    generation = raw.get("generation", {})
    evaluation = raw.get("evaluation", {})

    return RunConfig(
        runtime=RuntimeConfig(
            campaign_id=runtime.get("campaign_id", "Spring Launch"),
            category=runtime.get("category"),
            context_rows=int(runtime.get("context_rows", 10)),
            experiment_tag=runtime.get("experiment_tag", ""),
        ),
        generation=GenerationConfig(
            analysis_model=generation["analysis_model"],
            analysis_temp=float(generation["analysis_temp"]),
            recommendation_model=generation["recommendation_model"],
            recommendation_temp=float(generation["recommendation_temp"]),
        ),
        evaluation=EvaluationConfig(
            analysis_judge_model=evaluation["analysis_judge_model"],
            analysis_judge_temp=float(evaluation["analysis_judge_temp"]),
            recommendation_judge_model=evaluation["recommendation_judge_model"],
            recommendation_judge_temp=float(evaluation["recommendation_judge_temp"]),
        ),
    )
