# Recommendation Evaluation Framework

## Purpose

This framework gives the team one repeatable way to evaluate recommendation outputs across prompt changes, model changes, temperature changes, and future recommendation engines.

It is designed for practical development use:

- simple enough for everyday reviews
- structured enough for regression testing
- traceable enough for audits and debugging

The implementation lives in `src/evaluation/recommendation_framework.py`.

## Evaluation Principles

- Evaluate recommendation quality, not just JSON validity.
- Use both hard gates and weighted overall scoring.
- Keep the rubric stable across experiments so results stay comparable.
- Store parameter settings with every evaluation result.
- Capture rationale and evidence for every score.
- Use benchmark data that includes normal, edge, and failure cases.

These principles align with OpenAI's guidance to evaluate with representative datasets, include typical, edge, and adversarial cases, use clear rubrics, and compare runs continuously over time.[1] They also align with recommender-systems research that accuracy alone is not enough; practical evaluation also needs beyond-accuracy dimensions such as diversity, coverage, and usefulness.[2][3]

## Core Criteria

Use a 0-5 score for each criterion.

### Recommended criteria

| Criterion | What it checks | Suggested weight | Pass | Borderline | Fail |
| --- | --- | ---: | ---: | ---: | ---: |
| `problem_relevance` | The recommendation addresses the actual business issue in the input. | 0.20 | >= 4.0 | 3.0-3.99 | < 3.0 |
| `evidence_grounding` | Claims are supported by metrics, observations, or explicit signals. | 0.20 | >= 4.0 | 3.0-3.99 | < 3.0 |
| `actionability` | The team can execute the recommendation without guessing. | 0.15 | >= 4.0 | 3.0-3.99 | < 3.0 |
| `expected_impact` | The output states what should improve and why. | 0.15 | >= 4.0 | 3.0-3.99 | < 3.0 |
| `feasibility_and_risk` | Dependencies, constraints, or tradeoffs are acknowledged. | 0.10 | >= 4.0 | 3.0-3.99 | < 3.0 |
| `measurability` | The recommendation includes a concrete measurement plan. | 0.10 | >= 4.0 | 3.0-3.99 | < 3.0 |
| `clarity` | A non-specialist stakeholder can understand it quickly. | 0.05 | >= 4.0 | 3.0-3.99 | < 3.0 |
| `non_duplication` | Recommendation cards are not repetitive or redundant. | 0.05 | >= 4.0 | 3.0-3.99 | < 3.0 |

### Hard-fail threshold

Any criterion below `2.0` is a hard fail.

This is especially important for:

- `problem_relevance`
- `evidence_grounding`
- `actionability`
- `measurability`

If any of those collapse, the recommendation should not be accepted even if the average score still looks reasonable.

## How to Score Each Criterion

### `problem_relevance`

- `5`: directly addresses the dominant business problem in the metrics and context
- `3`: partly related, but still misses an important aspect of the problem
- `1`: generic advice with weak relation to the input

### `evidence_grounding`

- `5`: recommendation cites specific evidence from metrics or validated analysis
- `3`: generally plausible, but evidence is partial or weak
- `1`: unsupported or contradictory to the available data

### `actionability`

- `5`: includes clear steps, owners, or implementation guidance
- `3`: directionally useful but still vague
- `1`: abstract advice that a team cannot operationalize

### `expected_impact`

- `5`: identifies the expected business effect and the mechanism behind it
- `3`: states expected impact but weakly explains why
- `1`: no impact path is described

### `feasibility_and_risk`

- `5`: realistic for the likely team context and names major dependencies or risks
- `3`: mostly feasible, but constraints are underexplained
- `1`: unrealistic, unsafe, or ignores obvious blockers

### `measurability`

- `5`: includes success criteria, timing, and a measurement method
- `3`: partially measurable, but success criteria are incomplete
- `1`: no clear way to verify outcome

### `clarity`

- `5`: concise plain language with little ambiguity
- `3`: understandable but verbose or jargon-heavy
- `1`: confusing or difficult for a business stakeholder to interpret

### `non_duplication`

- `5`: recommendation set covers distinct actions
- `3`: some overlap exists
- `1`: several cards repeat the same action in different words

## Overall Outcome Rules

### Pass

- weighted overall score >= `4.0`
- no hard failures
- no critical missing evidence

### Borderline

- weighted overall score between `3.0` and `3.99`
- no hard failures
- useful enough to inspect, but not ready to ship without revision

### Fail

- weighted overall score < `3.0`
- or any hard-fail criterion < `2.0`
- or recommendation violates a mandatory contract such as missing evidence or missing action plan

## Borderline Cases

Mark as borderline when:

- the recommendation is directionally right but too generic
- evidence exists but is too weak to justify confidence
- the action is useful but the measurement plan is incomplete
- the recommendation duplicates another card
- output quality varies too much across nearby parameter settings

## Benchmark Dataset Design

Build a benchmark set that contains:

- high-signal examples with obvious problems
- ambiguous examples with competing interpretations
- sparse-data examples where the correct response is cautious
- contradictory-data examples to test hallucination resistance
- edge cases such as missing channels, zero spend, or zero conversions
- adversarial or noisy cases such as malformed text or misleading ratios

For each benchmark case store:

- `case_id`
- input dataset snapshot or fixture
- category
- expected dominant issue
- allowed recommendation families
- banned recommendations if relevant
- rubric notes for evaluators

Prefer JSONL or fixture-based storage so the same cases can be reused in CI, local tests, and offline experiments.[1]

## Temperature Sensitivity Evaluation

Run the same benchmark cases across a small fixed sweep such as:

- `temperature=0.0`
- `temperature=0.2`
- `temperature=0.5`
- `temperature=0.7`

For each case compare:

- overall score range
- status changes (`pass`, `borderline`, `fail`)
- criterion drift, especially `evidence_grounding` and `problem_relevance`

Suggested interpretation:

- stable: score range <= `0.5` and no status change
- moderate drift: score range `0.51-1.0`
- unstable: score range > `1.0` or status changes across runs

This follows OpenAI's recommendation to compare eval runs across changes and continuously monitor nondeterministic behavior.[1]

## Output Representation

Use a structured result with:

- candidate id
- parameter settings
- per-criterion score
- per-criterion rationale
- per-criterion evidence
- overall weighted score
- overall status
- trace metadata

The current code representation is:

```python
RecommendationEvaluationResult(
    candidate_id="rec-set-temp-0.2",
    criteria=(...),
    overall_score=4.15,
    overall_status=EvaluationStatus.PASS,
    parameter_settings={"temperature": 0.2, "model": "gpt-4o-mini"},
    trace={"benchmark_case_id": "retention-003"}
)
```

## Comparing Multiple Recommendation Outputs

Use the same benchmark case and rubric, then compare candidates in this order:

1. overall status
2. overall weighted score
3. `evidence_grounding`
4. `problem_relevance`

This prevents a stylistically polished but weakly grounded candidate from outranking a better-supported one.

## Failure Conditions

Treat the result as failed when any of the following occur:

- recommendation set has missing required fields
- recommendation conflicts with the validated metrics
- evidence is absent or misleading
- measurement plan is missing for important actions
- recommendations are nearly duplicates
- a low-temperature and medium-temperature run produce materially different business advice without a clear reason

## Team Workflow

### During development

- run unit tests for calculation and evaluation modules
- sample a small benchmark subset locally
- inspect any borderline or failed cases before merging

### During review

- compare new outputs against the current baseline
- inspect score deltas by criterion, not only overall score
- confirm that trace metadata explains why scores changed

### In CI or scheduled evaluation

- run the full benchmark set
- persist evaluation results
- alert on hard-fail regressions
- trend overall score and criterion-level score over time

## Sources

[1] OpenAI, "Evaluation best practices" and "Working with evals":
https://developers.openai.com/api/docs/guides/evaluation-best-practices
https://developers.openai.com/api/docs/guides/evals

[2] Ge, Delgado-Battenfeld, and Jannach, "Beyond accuracy: Evaluating recommender systems by coverage and serendipity":
https://dl.acm.org/doi/10.1145/1864708.1864761

[3] Kunaver and Pozrl, "Diversity in recommender systems - A survey":
https://link.springer.com/article/10.1007/s10462-015-9462-6
