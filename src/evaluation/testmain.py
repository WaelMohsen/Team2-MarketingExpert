import argparse
import json
import sys
from typing import Optional

from dotenv import load_dotenv

import src.llm as llm_handler
import src.metrics_engine as data_processor
from src.evaluation.evaluation_pipeline import EvaluationPipeline

CATEGORIES = [
    "Customer Acquisition",
    "Customer Satisfaction",
    "Revenue Growth",
    "Customer Retention",
]


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


def run(category: str, campaign_id: str, target: str, context_rows: int) -> dict:
    load_dotenv()

    # 1) Load source data and compute metrics
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

    pipeline = EvaluationPipeline(
        llm_callable=llm_handler.llm_callable,
        embedding_callable=llm_handler.embedding_callable,
    )

    campaign_context = df.head(max(context_rows, 1)).to_json(orient="records")

    return pipeline.run_all(
        campaign_id=campaign_id,
        target=target,
        analysis_output=analysis_output,
        recommendation_output=recommendation_output,
        kpis=kpis,
        campaign_context=campaign_context,
        category=category,
    )


def run_all_categories(
    campaign_id: str,
    context_rows: int,
    target_override: Optional[str] = None,
) -> dict:
    """Run evaluation for every category.

    Returns a category-keyed mapping.
    """
    all_results = {}
    for category in CATEGORIES:
        target = target_override or category
        all_results[category] = run(
            category=category,
            campaign_id=campaign_id,
            target=target,
            context_rows=context_rows,
        )
    return all_results


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
