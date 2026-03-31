"""Run recommendation benchmarks against saved reports or sample candidates."""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config import AppSettings
from src.evaluation import RecommendationBenchmarkRepository, RecommendationBenchmarkRunner
from src.evaluation.benchmarks import RecommendationBenchmarkCandidate, RecommendationBenchmarkCase
from src.evaluation.report_loader import build_candidate_from_report_file, select_benchmark_cases
from src.reporting import MarketingReport
from src.schemas.analysis_output_schema import AnalysisOutput
from src.schemas.recommendation_output_schema import (
    ExpectedImpact,
    MeasurementPlan,
    RecommendationActionStep,
    RecommendationCard,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    command_group = parser.add_mutually_exclusive_group(required=True)
    command_group.add_argument("--list-cases", action="store_true", help="List available benchmark cases.")
    command_group.add_argument(
        "--sample-report",
        action="store_true",
        help="Evaluate a built-in sample report against the selected case or category.",
    )
    command_group.add_argument(
        "--latest-output",
        action="store_true",
        help="Evaluate the most recent pipeline output JSON in the configured output_log directory.",
    )
    command_group.add_argument(
        "--report-json",
        nargs="+",
        metavar="PATH",
        help="Evaluate one or more saved report JSON files.",
    )

    parser.add_argument("--case", dest="case_id", help="Evaluate against one specific benchmark case id.")
    parser.add_argument(
        "--parameter",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Attach parameter metadata such as temperature=0.2 to the evaluated candidates.",
    )
    parser.add_argument(
        "--output",
        help="Optional path to save the JSON benchmark result. Defaults to stdout only.",
    )
    return parser.parse_args(argv)


def parse_parameter_settings(values: Iterable[str]) -> dict[str, Any]:
    """Parse repeated ``KEY=VALUE`` arguments into a dictionary."""

    parameter_settings: dict[str, Any] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Invalid parameter '{item}'. Expected KEY=VALUE.")

        key, raw_value = item.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key:
            raise ValueError(f"Invalid parameter '{item}'. Expected KEY=VALUE.")

        try:
            parameter_settings[key] = json.loads(raw_value)
        except json.JSONDecodeError:
            parameter_settings[key] = raw_value

    return parameter_settings


def expand_report_paths(paths: Iterable[str]) -> list[Path]:
    """Expand report path inputs, including wildcard patterns."""

    expanded_paths: list[Path] = []
    for raw_path in paths:
        matched_paths = sorted(Path(path).resolve() for path in glob.glob(raw_path))
        if matched_paths:
            expanded_paths.extend(path for path in matched_paths if path.is_file())
            continue

        literal_path = Path(raw_path).resolve()
        if not literal_path.is_file():
            raise FileNotFoundError(f"Report file not found: {raw_path}")
        expanded_paths.append(literal_path)

    deduplicated_paths: list[Path] = []
    seen_paths: set[Path] = set()
    for path in expanded_paths:
        if path not in seen_paths:
            seen_paths.add(path)
            deduplicated_paths.append(path)
    return deduplicated_paths


def resolve_latest_output_file(settings: AppSettings | None = None) -> Path:
    """Return the most recent saved pipeline output file."""

    active_settings = settings or AppSettings.default()
    output_directory = active_settings.paths.output_log_dir
    candidates = sorted(output_directory.glob("pipeline_output_*.json"))
    if not candidates:
        raise FileNotFoundError(f"No pipeline output files found in {output_directory}")
    return candidates[-1].resolve()


def build_sample_report(case: RecommendationBenchmarkCase) -> MarketingReport:
    """Create a deterministic sample report aligned with a benchmark case."""

    primary_problem_terms = list(case.expected_problem_terms[:3]) or ["performance", "conversion", "efficiency"]
    evidence_terms = list(case.expected_evidence_terms[:3]) or ["signal", "trend", "metric"]
    action_terms = list(case.required_action_terms) or ["targeting", "creative", "budget", "landing page", "segment"]
    preferred_kpi = case.preferred_primary_kpis[0] if case.preferred_primary_kpis else "conversion rate"
    recommendation_count = min(max(case.min_recommendations, 5), 6)

    recommendations = []
    for index in range(recommendation_count):
        action_term = action_terms[index % len(action_terms)].replace("-", " ")
        recommendations.append(
            RecommendationCard(
                id=f"{case.case_id}-sample-{index + 1}",
                title=f"Improve {action_term} execution",
                category=case.category,
                priority="High" if index == 0 else "Medium",
                effort="Medium",
                time_to_see_impact="2-4 weeks",
                confidence="High",
                whats_happening=(
                    f"{case.category} performance is showing issues around "
                    f"{', '.join(primary_problem_terms[:2])}."
                ),
                evidence=[
                    f"Observed evidence includes {evidence_terms[0]}.",
                    f"Benchmark focus highlights {', '.join(primary_problem_terms[:2])}.",
                ],
                what_you_should_do=[
                    RecommendationActionStep(
                        step=f"Improve {action_term}",
                        where="Campaign workflow",
                        how=f"Run a focused change on {action_term} and track the response.",
                        guardrails=["Keep the test isolated to one campaign segment."],
                    )
                ],
                why_this_matters=f"It directly supports better {preferred_kpi}.",
                expected_impact=ExpectedImpact(
                    primary_kpi=preferred_kpi,
                    direction="Increase",
                    explanation=f"Better {action_term} execution should improve {preferred_kpi}.",
                ),
                dependency_or_risk=[f"Requires coordination on {action_term} changes."],
                measurement_plan=MeasurementPlan(
                    how_to_measure=f"Compare {preferred_kpi} before and after the change.",
                    success_criteria=f"{preferred_kpi.title()} improves versus the previous baseline.",
                    check_timing="2 weeks",
                    notes="Review by segment to avoid masking weak cohorts.",
                ),
                owner_suggestion="Marketing operations",
            )
        )

    return MarketingReport(
        category=case.category,
        analysis=AnalysisOutput(
            analysis=(
                f"{case.category} results indicate pressure around "
                f"{', '.join(primary_problem_terms[:2])}."
            ),
            key_signals=[
                f"Primary concern terms: {', '.join(primary_problem_terms)}.",
                f"Supporting evidence terms: {', '.join(evidence_terms)}.",
            ],
            detected_issues=[f"The benchmark expects better handling of {primary_problem_terms[0]}."],
            root_cause_hypothesis=(
                f"The current execution is not responding strongly enough to {primary_problem_terms[0]}."
            ),
            business_risks=[f"We may miss the expected {preferred_kpi} target if no action is taken."],
            confidence_score=82.0,
        ),
        recommendations=tuple(recommendations),
    )


def assign_candidates_to_cases(
    cases: tuple[RecommendationBenchmarkCase, ...],
    candidates: Iterable[RecommendationBenchmarkCandidate],
) -> dict[str, list[RecommendationBenchmarkCandidate]]:
    """Group candidates by the benchmark cases that match their category."""

    candidates_by_case: dict[str, list[RecommendationBenchmarkCandidate]] = {case.case_id: [] for case in cases}
    for candidate in candidates:
        matching_cases = [case for case in cases if case.category == candidate.report.category]
        if not matching_cases:
            raise ValueError(
                f"No selected benchmark cases match candidate '{candidate.candidate_id}' "
                f"with category '{candidate.report.category}'."
            )

        for case in matching_cases:
            candidates_by_case[case.case_id].append(candidate)

    return {case_id: grouped_candidates for case_id, grouped_candidates in candidates_by_case.items() if grouped_candidates}


def run_cli(argv: list[str] | None = None) -> int:
    """Execute the benchmark CLI."""

    args = parse_args(argv)
    repository = RecommendationBenchmarkRepository()
    cases = repository.load_cases()

    if args.list_cases:
        for case in cases:
            print(f"{case.case_id}: {case.category} -> {case.description}")
        return 0

    parameter_settings = parse_parameter_settings(args.parameter)
    selected_cases = select_benchmark_cases(cases, case_id=args.case_id)

    if args.sample_report:
        candidates_by_case = {
            case.case_id: [
                RecommendationBenchmarkCandidate(
                    candidate_id=f"sample-{case.case_id}",
                    report=build_sample_report(case),
                    parameter_settings=dict(parameter_settings),
                )
            ]
            for case in selected_cases
        }
    elif args.latest_output:
        latest_output_path = resolve_latest_output_file()
        candidates = [build_candidate_from_report_file(latest_output_path, parameter_settings=parameter_settings)]
        candidates_by_case = assign_candidates_to_cases(selected_cases, candidates)
    else:
        report_paths = expand_report_paths(args.report_json or ())
        candidates = [
            build_candidate_from_report_file(report_path, parameter_settings=parameter_settings)
            for report_path in report_paths
        ]
        candidates_by_case = assign_candidates_to_cases(selected_cases, candidates)

    suite_result = RecommendationBenchmarkRunner().run_suite(selected_cases, candidates_by_case)
    payload = suite_result.to_dict()
    rendered_payload = json.dumps(payload, indent=2, ensure_ascii=False)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered_payload, encoding="utf-8")

    print(rendered_payload)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run_cli())
    except Exception as exc:
        print(f"Benchmark runner failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
