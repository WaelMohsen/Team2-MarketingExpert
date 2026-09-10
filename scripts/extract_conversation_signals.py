"""Extract privacy-safe, validated conversation signals to a resumable JSONL artifact."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src_2.application.conversation_signals import extract_conversation_signals
from src_2.intelligence import OpenAIAdMessageMatchEvaluator


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-directory")
    parser.add_argument("--output-path")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--paid-only",
        action="store_true",
        help="Select only conversations attributed to a paid campaign.",
    )
    campaign = parser.add_mutually_exclusive_group()
    campaign.add_argument("--campaign-id")
    campaign.add_argument("--campaign-name")
    parser.add_argument("--restart", action="store_true")
    parser.add_argument(
        "--with-ad-message-match",
        action="store_true",
        help="Run the separate ad-promise versus customer-need evaluator.",
    )
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    summary = extract_conversation_signals(
        args.input_directory,
        output_path=args.output_path,
        limit=args.limit,
        campaign_id=args.campaign_id,
        campaign_name=args.campaign_name,
        paid_only=args.paid_only,
        resume=not args.restart,
        ad_match_evaluator=(
            OpenAIAdMessageMatchEvaluator() if args.with_ad_message_match else None
        ),
        progress=lambda message: print(message, flush=True),
    )
    print(
        f"selected={summary.selected} extracted={summary.extracted} "
        f"skipped={summary.skipped} failed={summary.failed} "
        f"output={summary.output_path}"
    )
    usage = summary.total_usage
    cost = (
        f"${usage.estimated_cost_usd:.6f}"
        if usage.estimated_cost_usd is not None
        else "unavailable"
    )
    print(
        "current_run_usage "
        f"requests={usage.request_count} input_tokens={usage.input_tokens} "
        f"cached_input_tokens={usage.cached_input_tokens} "
        f"output_tokens={usage.output_tokens} "
        f"reasoning_output_tokens={usage.reasoning_output_tokens} "
        f"total_tokens={usage.total_tokens} estimated_cost_usd={cost} "
        f"usage_log={summary.usage_log_path}"
    )


if __name__ == "__main__":
    main()
