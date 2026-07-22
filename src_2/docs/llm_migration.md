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
