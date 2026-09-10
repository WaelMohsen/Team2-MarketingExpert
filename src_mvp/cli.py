"""Command-line entry point for the minimal objective-only pipeline."""

import argparse
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from .config import load_budget_policy
from .pipeline import run_mvp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--signals-path", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--budget", type=float)
    parser.add_argument("--currency")
    parser.add_argument("--with-llm", action="store_true")
    parser.add_argument("--model")
    return parser


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()
    policy = load_budget_policy()
    updates = {}
    if args.budget is not None:
        updates["budget_units"] = args.budget
    if args.currency is not None:
        updates["currency"] = args.currency
    if updates:
        policy = policy.model_copy(update=updates)
    result = run_mvp(
        input_directory=args.input_dir,
        signals_path=args.signals_path,
        output_directory=args.output_dir,
        policy=policy,
        with_llm=args.with_llm,
        model=args.model,
    )
    actions = Counter(
        item.action.value for item in result.allocations
    )
    allocated = sum(item.recommended_budget_units for item in result.allocations)
    print(f"Paid conversations: {len(result.data.conversations)}")
    print(
        "Semantic conversations: "
        f"{result.recommendation_input.data_scope.semantic_conversations}"
    )
    print(f"Campaign actions: {dict(actions)}")
    print(f"Allocated budget: {allocated:.2f}")
    print(
        "Unallocated budget: "
        f"{result.recommendation_input.unallocated_budget_units:.2f}"
    )
    print(f"Outputs: {result.output_directory}")


if __name__ == "__main__":
    main()
