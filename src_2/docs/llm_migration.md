# Migrating src_2 from Deterministic Logic to an LLM-Driven Pipeline

Status: design proposal (no code changes yet)

This document describes how to move src_2 from its deterministic default path
to an LLM-driven pipeline **end to end**, while preserving the hexagonal
architecture, the ability to fall back to deterministic behaviour, and the
existing UI/export/artifact surface.

## Guiding Principle: LLM Judges, Deterministic Code Measures

The one constraint to keep even in a "full LLM" pipeline: **the LLM must not do
the arithmetic.**

KPI aggregation in `analytics/aggregations.py` sums spend, revenue,
conversions, and orders across hundreds of fact rows and computes ~25 derived
ratios. LLMs are unreliable at multi-row arithmetic and are not reproducible, so
asking a model to compute `net_roas` from raw rows produces numbers that drift
silently between runs and cannot be audited.

Keep measurement deterministic and feed the *computed* numbers to the LLM as
evidence. Everything downstream of the raw math — evidence interpretation,
target classification, funding decisions, budget rationale, and narrative — is
delegated to the LLM.

> Full pipeline end to end, in practice, means: **deterministic measurement ->
> LLM does all judgment.**

## Method: Extend the Existing Port Pattern

src_2 already proves the ports-and-adapters pattern for the narrative layer:

- Protocol interfaces in `application/ports.py`
- Deterministic adapters in `intelligence/deterministic.py`
- OpenAI adapters in `intelligence/openai_adapters.py`
- Injection with deterministic fallback in `application/reporting.py`
  (`run_completed_cycle`)

The narrative ports (`CampaignAnalyst`, `PortfolioSynthesizer`,
`ReportNarrator`) are already swappable. The gap is that the two **decision**
stages are hardcoded calls inside `run_completed_cycle`, not ports:

- `application/reporting.py` -> `build_assessment_bundle(...)` decides
  `target_status` and `next_cycle_action`
- `application/reporting.py` -> `build_budget_scenario(...)` allocates the 100
  budget units

The migration applies the *same* port pattern to these two stages.

## Stage-by-Stage Map

| Stage | Module | LLM? | Notes |
|---|---|---|---|
| Load / normalize | `ingestion/loaders`, `ingestion/normalizer` | No | Deterministic parsing and PII stripping |
| KPI + scorecards | `analytics/aggregations` | No | Keep arithmetic deterministic |
| Data-quality / evidence status | `ingestion/data_quality` | Optional | LLM may interpret; keep ratio math deterministic |
| Target + funding assessment | `analytics/assessment_engine` | **Yes** | New `CampaignAssessor` port |
| Budget allocation | `analytics/allocation` | **Yes** | New `BudgetAllocator` port (see caveat) |
| Analyze / synthesize / narrate | `intelligence/` | **Yes** | Already swappable; inject OpenAI adapters |

## Implementation Steps

### Step 1 — Add two new ports

In `application/ports.py`:

```python
class CampaignAssessor(Protocol):
    def assess(self, evidence: CampaignEvidencePack,
               config: CampaignTypeConfig) -> CampaignAssessment: ...

class BudgetAllocator(Protocol):
    def allocate(self, cycle_id: str,
                 assessments: Sequence[CampaignAssessment],
                 policy: BudgetPolicy) -> BudgetScenario: ...
```

These output the **existing Pydantic contracts** (`CampaignAssessment` in
`contracts/assessment.py`, `BudgetScenario`). Because the contracts are already
defined, they double as the LLM structured-output schema
(`responses.parse(..., text_format=CampaignAssessment)`), so validation is free
and nothing downstream (Streamlit, export, artifacts) has to change.

### Step 2 — Wrap current logic as the default adapters

Repackage the existing `build_assessment_bundle` and `build_budget_scenario`
behind `DeterministicCampaignAssessor` and `DeterministicBudgetAllocator`. They
remain the default and the fallback (see Guardrails). No behaviour is lost.

### Step 3 — Add OpenAI adapters + prompts

Mirror `_StructuredOpenAI` from `intelligence/openai_adapters.py`. Add prompts
under `prompts/` (`campaign_assessment.md`, `budget_allocation.md`) that pass the
LLM:

- the evidence pack (computed KPIs, benchmarks, evidence status), and
- the campaign-type config from `config/campaign_types.yaml` (business job,
  primary KPI, guardrails, thresholds)

and ask it to classify and justify. The existing `reason_codes` / `reason`
contract fields become where the LLM explains itself.

### Step 4 — Inject in `run_completed_cycle`

Add `campaign_assessor` and `budget_allocator` parameters using the same
`or Deterministic...()` fallback pattern already used for the narrative ports,
and add a Streamlit sidebar toggle mirroring the existing narrative-engine
toggle.

## Guardrails (Non-Negotiable Once the LLM Makes Decisions)

The current code has none of these because the LLM only writes prose today. Once
it makes funding decisions they are required:

1. **Semantic post-validation** (beyond Pydantic types): allocations >= 0 and
   sum to `budget_units`; blocked campaigns receive 0; `next_cycle_action` is
   legal for the campaign's `budget_pool` per `budget_policy` `action_eligibility`.
   On failure, fall back to the deterministic adapter for that item and log it.
2. **Determinism controls**: `temperature=0`, pin the model
   (`openai_adapters.py` currently defaults to `gpt-5-mini` with default params),
   and cache responses keyed by an input hash so reruns on the same cycle are
   stable and free.
3. **Evaluation harness**: the deterministic implementations become the golden
   baseline. Run both paths on the sample cycle, diff decisions, and measure
   disagreement rate and defensibility. This closes the gap that src_2 has today
   (no evaluation layer, unlike `src`). The LLM-as-judge approach in
   `src/evaluation/` can be reused.
4. **Ground the LLM in config**: pass the YAML policy (primary KPI, guardrails,
   thresholds) into every decision prompt so the model applies *this* policy, not
   generic marketing intuition. Keeping policy in `config/` human-editable is the
   whole point — do not bake it into prose prompts.

## Allocation Caveat

Let the LLM decide allocation *strategy and rationale* (which campaigns are
funded, why, relative priority), but have it emit weights/priorities that a thin
deterministic step normalizes to exactly `budget_units`. Otherwise you will fight
the model to make the numbers sum correctly.

## Suggested Rollout Order

1. **Narrative layer** — no new code; inject the existing
   `OpenAICampaignAnalyst` / `OpenAIPortfolioSynthesizer` / `OpenAIReportNarrator`.
   Ships immediately; validate output quality.
2. **`CampaignAssessor` port** — highest-value judgment; contract already exists;
   deterministic fallback keeps it safe.
3. **Evaluation harness** — before trusting the assessor in front of anyone.
4. **`BudgetAllocator` port** — last, because it allocates money and is hardest to
   keep numerically sane.

## What Stays the Same

- All Pydantic contracts in `contracts/`
- The Streamlit UI, JSON export, and artifact store
- Deterministic measurement (`ingestion`, `analytics/aggregations`)
- The ability to run with no API key (deterministic remains the default and the
  fallback)

## Status Update (2026-07-23)

Two rollout items have since been implemented, which changes the baseline this
integration plan builds on:

- **Narrative layer is now LLM-only.** The deterministic narrative adapters were
  removed; `run_completed_cycle` defaults its narrative ports to the OpenAI
  adapters. There is no deterministic narrative fallback anymore — a missing key
  or a failed/invalid LLM response stops the run.
- **An evaluation subsystem exists** (`src_2/evaluation/`): a deterministic
  narrative consistency checker + local JSON history + a Streamlit dashboard
  (`app_eval.py`). This is the concrete form of the "evaluation harness" bullet
  above, and it is what the decision-consistency check (below) extends.

The `CampaignAssessor` / `BudgetAllocator` ports remain **not built** — the
sections below are the plan for that work.

## Integration: `CampaignAssessor` & `BudgetAllocator`

### The seam runs *through* the analytics functions, not around them

Neither decision function is a clean unit; each mixes deterministic measurement
with the decision:

- `build_assessment_bundle` → per campaign, `_campaign_pack_and_assessment` both
  **builds the `CampaignEvidencePack`** (metric evidence, benchmark resolution,
  child entities — deterministic, keep) **and calls** `classify_target` +
  `classify_next_cycle_action` (the decision — swap point).
- `build_budget_scenario` → **sizes type envelopes from historical spend share and
  normalizes to 100 units** (deterministic, keep) **and chooses within-envelope
  funding/priority + applies eligibility** (the decision — swap point).

So integration is not "wrap the two functions with a port"; it is **extract the
classification step behind a port and keep the measurement in place.**

### Refactor

```
build_assessment_bundle  →  split into:
   build_evidence_packs(...)            # deterministic packs + benchmarks   (KEEP)
   assessor.assess(pack, config)        # PORT -> CampaignAssessment
   _add_campaign/_child_decisions(...)  # deterministic enrichment           (KEEP)

build_budget_scenario    →  split into:
   compute_envelopes(...)               # deterministic spend-share sizing   (KEEP)
   allocator.allocate(assessments, envelopes, policy)   # PORT -> BudgetScenario
   normalize + apply_eligibility(...)   # deterministic: sum->100, blocked->0 (KEEP)
```

The existing rule bodies (`classify_target`, `classify_next_cycle_action`, the
allocation KPI weighting) become `DeterministicCampaignAssessor` /
`DeterministicBudgetAllocator` — moved behind the port, kept as the default and
per-item fallback. Nothing is lost.

### Ports (grounded in current types)

```python
class CampaignAssessor(Protocol):
    def assess(self, evidence: CampaignEvidencePack,
               config: CampaignTypeConfig) -> CampaignAssessment: ...

class BudgetAllocator(Protocol):
    def allocate(self, cycle_id: str, assessments: Sequence[CampaignAssessment],
                 envelopes: dict[str, float], policy: BudgetPolicy) -> BudgetScenario: ...
```

Both emit the existing `CampaignAssessment` / `BudgetScenario` contracts, so
scorecard enrichment, Streamlit, export, and the evaluator are unchanged, and the
contracts double as the OpenAI Structured Outputs schema.

### Two rules that must stay deterministic

If the LLM assesses each campaign independently, cross-campaign consistency cannot
be trusted to it:

- **Parent → child propagation** (`_add_child_decisions`: a child cannot override a
  blocked parent) — enforce deterministically *after* the port.
- **Budget eligibility** (action legal for the pool per `action_eligibility`,
  blocked → 0, units sum to `budget_units`) — enforce deterministically *around*
  the allocator.

Pattern: the LLM *proposes*, deterministic rules *constrain*.

### Wiring into `run_completed_cycle`

```python
def run_completed_cycle(..., *, campaign_assessor=None, budget_allocator=None,
                        campaign_analyst=None, ...):
    evidence_packs = build_evidence_packs(cycle_id, raw_scorecards, registry, quality)
    assessor = campaign_assessor or DeterministicCampaignAssessor()   # DETERMINISTIC default
    assessments = [assessor.assess(p, registry[p.campaign_type]) for p in evidence_packs]
    assessments = propagate_parent_child(assessments)                 # deterministic
    scorecards  = enrich_scorecards(raw_scorecards, assessments)      # deterministic

    envelopes = compute_envelopes(scorecards.campaign)                # deterministic
    allocator = budget_allocator or DeterministicBudgetAllocator()
    budget = normalize_and_gate(allocator.allocate(cycle_id, assessments, envelopes, policy))
    # ... existing narrative ports follow ...
```

Data-dependency order is unchanged: evidence → **assess** → propagate → envelopes →
**allocate** → gate → narrative → report.

**Default these two ports to deterministic** (unlike the narrative ports, which
default to OpenAI). They are money decisions, so safe-by-default matters; make the
LLM opt-in.

### Safety wrapper

A `ValidatedAssessor(llm, deterministic)` decorator: call the LLM, validate the
result (Pydantic covers schema; add semantic checks — action legal for pool, no
invented metrics), and fall back to the deterministic implementation per campaign
on any failure. Same for the allocator.

### How evaluation extends

The existing evaluator checks *narrative* faithfulness. When decisions move to the
LLM, add a **decision-consistency** check: `DeterministicCampaignAssessor` is the
regression oracle — diff LLM decision vs deterministic decision on the golden
cycle, and the existing history/trend view surfaces divergence over time. This is
what makes trusting an LLM decision defensible.

### Net

A refactor (split measurement from decision) + two ports + deterministic
guardrails, with **zero change to contracts or downstream consumers.**
