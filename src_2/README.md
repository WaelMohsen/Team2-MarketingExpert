# Marketing Expert v2 Completed-Cycle Report

`src_2` is a parallel, non-breaking implementation area for the completed-cycle
marketing report. The existing `src` application remains unchanged.

## Design Goals

- Keep all joins, KPIs, benchmarks, assessments, and budget math deterministic.
- Keep business policy human-readable in YAML.
- Keep prompts and methodology reviewable in Markdown.
- Validate stage boundaries with Pydantic and JSON Schema.
- Make prompt implementations replaceable by agents through stable ports.
- Persist machine-readable cycle artifacts for audit and evaluation.

## Directory Map

| Directory | Responsibility |
|---|---|
| `domain` | Marketing vocabulary, configuration models, formulas, and transparent rules |
| `ingestion` | Raw file loading and source validation |
| `analytics` | Aggregation, KPI, benchmark, evidence, assessment, and allocation logic |
| `application` | End-to-end use-case orchestration and replaceable ports |
| `intelligence` | Prompt implementations now and agent implementations later |
| `infrastructure` | Configuration, repositories, LLM clients, and artifact stores |
| `contracts` | Pydantic objects exchanged between pipeline stages |
| `presentation` | Streamlit and API adapters |
| `config` | Human-editable campaign and POC policies |
| `prompts` | Focused Markdown instructions for LLM or agent roles |
| `schemas` | Machine-readable interchange contracts |
| `data/input/sampe_2` | Copied Sample 2 source JSON files |
| `artifacts` | Generated, cycle-versioned outputs; not source code |

## Current Status

The runnable v2 application provides:

- The complete v2 package structure and stable intelligence ports.
- Typed campaign evidence, assessment, insight, budget, and report contracts.
- All eight campaign-type definitions without weighted composite scoring.
- The agreed normalized POC budget policy with no campaign concentration cap.
- Prompt contracts for campaign analysis, portfolio synthesis, and narration.
- Privacy-safe canonical media, conversation, order-line, and product facts.
- Mature-outcome and customer-level KPIs with corrected numerator/denominator definitions.
- Peer-fitted Empirical-Bayes raw/corrected scores, credible ranges, benchmark ranges, favorable lift, and probability better at all five levels.
- Data-quality blocking for invalid and non-additive daily reach.
- Optional versioned, redacted, Pydantic-validated conversation semantics with resumable extraction and high-value purchase-friction fields.
- Campaign, adset, ad, creative, and audience scorecards without duplicated facts.
- Campaign-type primary KPI assessment, evidence guardrails, and child decisions.
- An explicit 70% exploit / 30% explore campaign budget scenario with no double-counting across entity levels.
- Deterministic reporting by default and optional structured OpenAI narration.
- A Streamlit report with stakeholder views, campaign drill-downs, and exports.

## Run the Application

From the repository root:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app_v2.py
```

The application opens at `http://localhost:8501`. Copy `.env.example` to `.env`
and set `OPENAI_API_KEY` for the narrative pipeline.

To build a small stratified semantic POC artifact first:

```bash
python scripts/extract_conversation_signals.py --limit 40
```

For the Post-Eid walkthrough, target that campaign rather than taking a portfolio
sample:

```bash
python scripts/extract_conversation_signals.py \
  --campaign-name "Post-Eid Lookalike Test" \
  --limit 5 \
  --with-ad-message-match
```

After reviewing the five-record POC, rerun without `--limit`; extraction resumes
and completes the remaining campaign conversations. The optional
`--with-ad-message-match` flag runs a second structured call that compares the ad
promise with validated customer needs; it never receives the order outcome.

The command checkpoints validated records in
`src_2/artifacts/conversation_signals.jsonl`. Set
`CONVERSATION_SIGNALS_PATH` to that file before launching Streamlit to include the
aggregated diagnostics. Omit the variable to run the report without semantic data.

Run the v2 tests with:

```bash
pytest tests/test_src_2_scaffold.py tests/test_src_2_pipeline.py tests/test_src_2_conversation_signals.py -v
```

## Configuration Validation

Install project requirements, then load the policies through:

```python
from src_2.infrastructure.configuration import (
    load_budget_policy,
    load_campaign_type_registry,
)

campaign_types = load_campaign_type_registry()
budget_policy = load_budget_policy()
```

The YAML is validated by Pydantic before it reaches the analytics engine.
