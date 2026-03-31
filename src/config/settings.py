"""Configuration models for the Marketing Expert application."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class PathSettings:
    """Filesystem locations used by the application."""

    repo_root: Path
    data_file: Path
    benchmark_file: Path
    prompt_dir: Path
    output_log_dir: Path


@dataclass(frozen=True)
class LLMSettings:
    """LLM configuration values kept outside orchestration logic."""

    analysis_model: str = "gpt-4o-mini"
    recommendation_model: str = "gpt-4o-mini"
    analysis_temperature: float = 0.2
    recommendation_temperature: float = 0.2


@dataclass(frozen=True)
class AppSettings:
    """Top-level immutable application settings."""

    paths: PathSettings
    llm: LLMSettings = field(default_factory=LLMSettings)

    @classmethod
    def default(cls) -> "AppSettings":
        """Build settings from repository defaults and optional env vars."""

        repo_root = _repo_root()
        data_file = Path(os.getenv("MARKETING_DATA_FILE", repo_root / "data" / "all_campaigns_data.csv"))
        benchmark_file = Path(
            os.getenv(
                "MARKETING_RECOMMENDATION_BENCHMARK_FILE",
                repo_root / "data" / "benchmarks" / "recommendation_cases.json",
            )
        )
        prompt_dir = Path(os.getenv("MARKETING_PROMPT_DIR", repo_root / "prompts"))
        output_log_dir = Path(os.getenv("MARKETING_OUTPUT_LOG_DIR", repo_root / "output_log"))

        llm = LLMSettings(
            analysis_model=os.getenv("OPENAI_ANALYSIS_MODEL", "gpt-4o-mini"),
            recommendation_model=os.getenv("OPENAI_RECOMMENDATION_MODEL", "gpt-4o-mini"),
            analysis_temperature=float(os.getenv("OPENAI_ANALYSIS_TEMPERATURE", "0.2")),
            recommendation_temperature=float(os.getenv("OPENAI_RECOMMENDATION_TEMPERATURE", "0.2")),
        )

        return cls(
            paths=PathSettings(
                repo_root=repo_root,
                data_file=data_file,
                benchmark_file=benchmark_file,
                prompt_dir=prompt_dir,
                output_log_dir=output_log_dir,
            ),
            llm=llm,
        )
