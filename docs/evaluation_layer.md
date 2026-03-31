# Evaluation Layer Design

## Scope

The evaluation layer provides a repeatable way to assess recommendation quality outside the main Streamlit flow. It is designed for regression checks, team review, and future CI automation.

Owned files:

- `src/evaluation/recommendation_framework.py`
- `src/evaluation/benchmarks.py`
- `data/benchmarks/recommendation_cases.json`

## Conceptual Role

Conceptually, this layer answers a different question from the main application.

The runtime pipeline asks:

What recommendation should we generate?

The evaluation layer asks:

How good is this recommendation output, and how does it compare to alternatives?

That separation is important because it keeps assessment logic independent from generation logic.

## Logical Responsibilities

### `RecommendationEvaluationFramework`

This class defines the evaluation rubric and scoring mechanics.

Core responsibilities:

- define the criteria and weights
- normalize scores to a 0 to 5 scale
- assign pass, borderline, or fail status
- aggregate weighted overall scores
- compare multiple results consistently
- summarize parameter sensitivity such as temperature changes

Primary result models:

- `CriterionDefinition`
- `CriterionScore`
- `RecommendationEvaluationResult`
- `ParameterSensitivitySummary`
- `EvaluationStatus`

### `RecommendationBenchmarkRepository`

This class loads benchmark cases from the JSON fixture file. It is deliberately simple so cases remain easy to version and review.

### `RecommendationBenchmarkRunner`

This class applies the rubric to a concrete benchmark case and one or more recommendation candidates.

Primary responsibilities:

- score each candidate against one case
- compare and rank candidates
- summarize score stability when multiple candidates represent different parameter settings
- return serializable suite results for logs, artifacts, or dashboards

Supporting models:

- `RecommendationBenchmarkCase`
- `RecommendationBenchmarkCandidate`
- `RecommendationBenchmarkCaseResult`
- `RecommendationBenchmarkSuiteResult`

## Current Scoring Approach

The current version uses deterministic heuristics built around:

- problem relevance
- evidence grounding
- actionability
- expected impact
- feasibility and risk
- measurability
- clarity
- non-duplication

Important note:

The benchmark runner currently uses rule-based text heuristics such as term coverage and field completeness. This is intentional for repeatability and speed, but it is not the final word on recommendation quality.

## Benchmark Fixture Design

Each benchmark case currently stores:

- `case_id`
- `category`
- `description`
- `expected_problem_terms`
- `expected_evidence_terms`
- `preferred_primary_kpis`
- `required_action_terms`
- `forbidden_terms`
- `min_recommendations`

This structure makes cases easy to extend without introducing a database or a more complex evaluation service.

## Evaluation Flow

1. Load benchmark cases from the fixture file.
2. Wrap one or more `MarketingReport` outputs as `RecommendationBenchmarkCandidate` objects.
3. Score each candidate with `RecommendationBenchmarkRunner`.
4. Compare ranked results.
5. Inspect criterion rationales and trace metadata.
6. Optionally summarize parameter sensitivity across candidates.

## Using the Layer in Practice

Recommended uses:

- compare prompt versions
- compare temperature settings
- compare different model outputs
- build regression checks before prompt changes are merged
- support structured review discussions with score traces

Non-goals for the current version:

- replacing human review for nuanced business judgment
- providing production-time online ranking
- modeling long-term recommendation business outcomes automatically

## Failure Modes and Caveats

Known caveats in the current implementation:

- text matching is heuristic and can over-match short substrings
- the fixture set is still small and should grow by category and difficulty
- deterministic scores are useful for regression, but they do not cover every qualitative dimension

These are acceptable tradeoffs for the current project stage.

## Testing Strategy

Primary tests should verify:

- fixture loading
- ranking order for stronger vs weaker candidates
- sensitivity summary behavior
- serializer output stability

As the benchmark library grows, add golden-result tests for representative cases.

## Physical Design Notes

Physical placement:

- source code under `src/evaluation/`
- fixture data under `data/benchmarks/`

Runtime characteristics:

- no external service dependency
- deterministic local execution
- JSON-serializable outputs suitable for CI artifacts

This layer is intentionally decoupled from Streamlit so it can be run from scripts, tests, or future automation jobs.
