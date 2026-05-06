import json
import sys
from typing import List

from dotenv import load_dotenv

from src.evaluation.run_config import DEFAULT_CONFIG_PATH, load_run_config
from src.evaluation.run_orchestrator import run_all_targets, run_target


def run_from_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict:
    load_dotenv()
    run_config = load_run_config(config_path)
    runtime = run_config.runtime

    if runtime.category:
        return run_target(
            campaign_name=runtime.campaign_id,
            category=runtime.category,
            context_rows=runtime.context_rows,
            run_config=run_config,
            run_id=None,
        )

    return run_all_targets(
        campaign_name=runtime.campaign_id,
        context_rows=runtime.context_rows,
        config_path=config_path,
    )


def _config_path_from_argv(argv: List[str]) -> str:
    if len(argv) <= 1:
        return DEFAULT_CONFIG_PATH
    if len(argv) == 2:
        return argv[1]

    raise SystemExit("Usage: python -m src.evaluation.run_evaluation [config_path]")


def main() -> None:
    try:
        result = run_from_config(_config_path_from_argv(sys.argv))
    except Exception as exc:
        print(f"Evaluation run failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
