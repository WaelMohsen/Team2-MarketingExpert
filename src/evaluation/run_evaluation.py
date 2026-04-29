import argparse
import json
import sys
from typing import Optional

from src.evaluation.services.evaluation_run_service import (
    CATEGORIES,
    run_evaluation_for_all_categories,
    run_evaluation_for_category,
)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run unified analysis + recommendation evaluation."
    )
    parser.add_argument(
        "--category",
        default=None,
        choices=CATEGORIES,
        help=(
            "Business category used for metric calculation and prompts. "
            "If omitted, all categories are evaluated."
        ),
    )
    parser.add_argument(
        "--campaign-id",
        default="Spring Launch",
        help="Campaign identifier used for ground-truth lookup.",
    )
    parser.add_argument(
        "--target",
        default=CATEGORIES[0],
        choices=CATEGORIES,
        help="Target used for recommendation ground-truth matching.",
    )
    parser.add_argument(
        "--context-rows",
        type=int,
        default=10,
        help=("Number of dataframe rows to include in analysis " "evaluation context."),
    )
    return parser


def run(
    category: str,
    campaign_id: str,
    target: str,
    context_rows: int,
) -> dict:
    return run_evaluation_for_category(
        campaign_id=campaign_id,
        target=target,
        category=category,
        context_rows=context_rows,
    )


def run_all_categories(
    campaign_id: str,
    context_rows: int,
    target_override: Optional[str] = None,
) -> dict:
    return run_evaluation_for_all_categories(
        campaign_id=campaign_id,
        context_rows=context_rows,
        target_override=target_override,
    )


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    try:
        if args.category:
            result = run(
                category=args.category,
                campaign_id=args.campaign_id,
                target=args.target,
                context_rows=args.context_rows,
            )
        else:
            result = run_all_categories(
                campaign_id=args.campaign_id,
                context_rows=args.context_rows,
            )
    except Exception as exc:
        print(f"Evaluation run failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
