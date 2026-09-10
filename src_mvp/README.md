# Objective-Only Marketing MVP

This package scores one completed marketing cycle and prepares a compact, validated
input for a recommendation LLM. It is standalone and does not import `src_2`.

## Scope

- Meta `objective` is the only campaign taxonomy used for scoring.
- The 617 paid-attributed WhatsApp conversations are assumed complete for the MVP.
- Organic/direct conversations are excluded from paid campaign scoring.
- Active and `stuck_pending` conversations remain visible but are excluded from mature
  outcome denominators.
- Campaign, adset, and ad are the funding hierarchy. Creative and audience are
  diagnostic score views. Budget is allocated only to campaigns.
- Conversation quality has a separate score and range at all five levels. Together
  with primary `probability_better`, it allocates campaign budget within each objective.
  Primary outcome scores and final action labels remain intact.

## Objective Contracts

| Objective | Primary score | Efficiency |
|---|---|---|
| `OUTCOME_AWARENESS` | Link clicks / impressions | CPM |
| `OUTCOME_ENGAGEMENT` | Link clicks / impressions | CPC |
| `OUTCOME_LEADS` | Mature created orders / mature conversations | Cost per created order |
| `OUTCOME_SALES` | Delivered customers / mature unique customers | Net ROAS |

The primary score first uses same-objective Empirical Bayes. When Awareness or
Engagement lacks two same-objective peers, it falls back to their shared upper-funnel
Link CTR group. This fallback is explicitly marked provisional and its final action is
capped at `KEEP_AS_TEST`. The whole-portfolio same-metric benchmark is descriptive
context only. Efficiency is a separate same-objective peer comparison and acts as a
scale gate; effectiveness and efficiency are never blended into a weighted score.

## Run

From the repository root:

```bash
../.venv/bin/python -m src_mvp
```

Use a real next-cycle budget when it is known:

```bash
../.venv/bin/python -m src_mvp --budget 100000 --currency EGP
```

The default is 100 normalized units. Add `--with-llm` to make the optional, single
structured recommendation call after deterministic processing:

```bash
../.venv/bin/python -m src_mvp --with-llm --model gpt-5-mini
```

## Refresh Latest Assets

The MVP copies only the two required raw files, the latest schema-v3 paid semantic
artifact, and its two extraction prompts:

```bash
../.venv/bin/python -m src_mvp.sync_assets
```

Run this again after the full 617-conversation extraction finishes.

## Decision Logic

```text
SCALE: 95% favorable-lift lower bound > 0
KILL:  95% favorable-lift upper bound < 0
HOLD:  lift range crosses 0
```

At least two peers are required. Same-objective peers are decision-grade; the configured
Awareness plus Engagement Link CTR fallback is provisional and can fund only a test.
At least 10 primary trials are required for a funding action. With a decision-grade
benchmark, a statistical scale becomes a final scale only when efficiency is at least as
good as its same-objective peer median.

The budget preserves previous-cycle spend share by objective. The full objective
envelope is then allocated among its campaigns:

```text
allocation priority = primary probability_better x semantic range_low
campaign weight = allocation priority / sum of priorities in the objective
campaign budget = objective envelope x campaign weight
```

There is no concentration cap. Unsupported envelopes remain unallocated.

## Conversation Quality

Rules are explicit in `config/objectives.yaml` and `semantics.py`:

| Objective | Separate semantic score |
|---|---|
| Awareness | Central customer need aligned with the ad; partial/mismatch count as negative |
| Engagement | Commercial inquiry + medium/high specificity + consideration/checkout + aligned/partial ad match |
| Leads | Commercial inquiry + medium/high specificity + medium/high intent |
| Sales | Commercial inquiry + complete sales agreement + accepted next step |

Commercial inquiries are purchase, product information, promotion information, and
delivery information. Every required component must be known; missing components
produce unknown, not zero. Positive evidence-bearing fields need message indexes.
These are MVP definitions, not industry-standard qualification criteria.

Select the earliest mature conversation per customer within each entity before
inspecting labels, ordered by started_at then conversation ID (missing times last).
Unresolved conversations and subsequent mature conversations from that customer are
excluded. Selection happens before checking signal availability, so a later labelled
conversation cannot replace an earlier missing one. A customer can still appear in
different entities: their scores are not independent experimental treatment groups.

Raw semantic rate = successes / assessable selected customers. With two valid peers
under the same objective, use the existing leave-one-out Empirical-Bayes estimator.
Without two peers, show a weak Beta(0.5, 0.5) posterior and its 95% range, explicitly
without a benchmark, lift, or probability-better claim. The 0.5 values are Jeffreys
pseudocounts, not observed customers. No semantic cross-objective fallback is used.

For allocation, multiply each campaign's primary `probability_better` by its semantic
lower 95% bound and normalize the products within the objective. Example: `(0.50 x
0.20)=0.10` and `(0.25 x 0.60)=0.15` produce 40% and 60% of that objective's envelope.
Campaign actions do not gate this POC allocation. A missing component produces zero
allocation; if every campaign in an objective is missing a component, that envelope
remains unallocated. The packet retains the previous-spend scenario for comparison.

Objective envelopes still use previous-cycle spend shares because Awareness,
Engagement, Leads and Sales have different success definitions. Moving money between
objectives requires business strategy inputs; globally comparing their semantic rates
would favor objectives whose definitions naturally have higher base rates.

The allocation is an explicit experimental policy, not a joint probability, a learned
profit optimum, or proof that overlapping ranges identify a winner.

Automated labels are marked unreviewed. These retrospective signals may reflect an
agreement later cancelled; they do not predict future sales. Credible ranges represent
sampling uncertainty conditional on the labels, not model error or all peer-estimation
uncertainty. Review evidence against original transcripts and test outcome associations
before treating this experimental allocation as validated business policy.

## Outputs

`src_mvp/outputs/` contains:

- `entity_scorecards.jsonl`: one strict score record per entity.
- `semantic_evidence.jsonl`: local audit of selection, unknowns and semantic rule results
  linked by conversation ID, without transcript text or customer identities.
- `campaign_budget.json`: deterministic campaign allocations.
- `exploration_tests.json`: funded hypotheses and stop rules.
- `recommendation_input.json`: the compact LLM handoff.
- `recommendation_output.json`: created only when `--with-llm` succeeds.

Raw transcripts, customer identities, daily rows, and legacy
campaign-type calculations are not included in the recommendation packet.
The v2 packet includes separate semantic prior/posterior parameters for auditability.

## Objective Learning Notebooks

`src_mvp/notebooks/` contains one executed notebook per objective:

- `01_OUTCOME_AWARENESS_Analysis.ipynb`
- `02_OUTCOME_ENGAGEMENT_Analysis.ipynb`
- `03_OUTCOME_LEADS_Analysis.ipynb`
- `04_OUTCOME_SALES_Analysis.ipynb`

Each notebook shows raw evidence, peer evidence, prior and posterior calculations,
uncertainty, probability better, efficiency, campaign budget, child entities,
conversation diagnostics, named tests, and campaign-by-campaign recommendations.

Rebuild the notebook files after changing the shared methodology:

```bash
../.venv/bin/python -m src_mvp.build_notebooks
```

The generated notebooks use `run_mvp()` and do not make an LLM call.

## Streamlit Report

Run the dedicated MVP report from the repository root:

```bash
../.venv/bin/python -m streamlit run app_mvp.py
```

The report presents the portfolio, objective contracts, campaign and child scorecards,
conversation signals, ad-message alignment, budget scenario, named tests, and optional
structured recommendation narration. The presentation layer calls `run_mvp()` and does
not recalculate the scoring or budget rules.

The validated schema-v3 artifact lives at
`src_mvp/artifacts/conversation_signals_v3_paid.jsonl`. Both environment settings point
to that local copy. `MVP_CONVERSATION_SIGNALS_PATH` can be changed independently when
the MVP report should read another validated schema-v3 artifact.
