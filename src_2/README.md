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
- Campaign, adset, ad, creative, and audience scorecards without duplicated facts.
- Campaign-type primary KPI assessment, evidence guardrails, and child decisions.
- A historical campaign-type budget scenario with an experimental spend envelope.
- Deterministic reporting by default and optional structured OpenAI narration.
- A Streamlit report with stakeholder views, campaign drill-downs, and exports.

## Run the Application

From the repository root:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app_v2.py
```

The application opens at `http://localhost:8501`. It works without an API key.
To enable the optional AI campaign narrative, copy `.env.example` to `.env` and
set `OPENAI_API_KEY`.

Run the v2 tests with:

```bash
pytest tests/test_src_2_scaffold.py tests/test_src_2_pipeline.py -v
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
