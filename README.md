# Team2-MarketingExpert

Marketing Expert is a Streamlit application that analyzes campaign performance and generates business-friendly recommendations using OpenAI.

The system is built around four goals:

- Customer Acquisition
- Customer Satisfaction
- Revenue Growth
- Customer Retention

## Application Purpose

This project helps non-marketers understand campaign outcomes using:

1. Validated CSV campaign data.
2. Deterministic KPI calculation (base metrics + category-specific metrics).
3. A two-step LLM flow (analysis JSON -> recommendation JSON).
4. UI rendering of metrics and recommendations.

## Architecture Overview

### Entry Point

- `app.py`
  - Owns Streamlit UI, user interaction, and page rendering.
  - Calls metric computation and LLM generation.

### Core Modules

- `src/metrics_engine/router.py`
  - `load_data(...)`: read CSV + validate against `CampaignInput`.
  - `calculate_metrics(...)`: compute base metrics and dispatch category-specific logic.
- `src/metrics_engine/base_metrics.py`
  - Shared KPI aggregation (spend, revenue, clicks, conversions, CTR, conversion rate, CPA, ROAS).
- `src/metrics_engine/registry.py`
  - Registry decorator (`@register_target`) for category calculators.
- `src/metrics_engine/acquisition.py`
- `src/metrics_engine/satisfaction.py`
- `src/metrics_engine/revenue.py`
- `src/metrics_engine/retention.py`
  - Category-specific KPI enrichments registered at import time.

- `src/llm/client.py`
  - Lazy OpenAI client construction (`get_client`) and completion wrapper.
- `src/llm/prompts.py`
  - Prompt builders and context construction.
- `src/llm/pipeline.py`
  - Orchestrates two-step generation.
  - Validates final recommendations schema.
  - Saves debug output into `output_log/`.

- `src/schemas/input_schema.py`
  - `CampaignInput` pydantic model for input validation.
- `src/schemas/Recommendation_schema.py`
  - `RecommendationResponse` and nested pydantic models for output validation.
- `src/schemas/__init__.py`
  - Lightweight input-schema exports.

## Execution Flow

1. Streamlit starts in `app.py`.
2. User selects one business category.
3. `load_data("data/all_campaigns_data.csv")` loads and validates records.
4. `calculate_metrics(df, category)` returns:
   - base metrics from `base_metrics.py`
   - plus category metrics from the registry.
5. `generate_response(df, category, metrics)` in `src/llm/pipeline.py`:
   - builds context and prompts,
   - calls the model for analysis,
   - calls the model for recommendations,
   - validates recommendations with `RecommendationResponse`.
6. `app.py` parses the returned JSON and renders recommendation cards.
7. Pipeline writes debug artifact JSON to `output_log/pipeline_output_<timestamp>.json`.

## Class/Module Interaction Summary

### Orchestrators

- `app.py` orchestrates user flow and rendering.
- `src/llm/pipeline.py` orchestrates model interaction flow.
- `src/metrics_engine/router.py` orchestrates metric computation flow.

### Data Models

- `CampaignInput` in `src/schemas/input_schema.py`.
- `ActionStep`, `ExpectedImpact`, `MeasurementPlan`, `Recommendation`, `RecommendationResponse` in `src/schemas/Recommendation_schema.py`.

### Infrastructure/Utility Support

- `src/llm/client.py` for OpenAI connectivity.
- `src/llm/prompts.py` for prompt assembly.
- `src/metrics_engine/registry.py` for pluggable category handlers.

## Folder and File Roles

```text
.
|-- app.py                         # Streamlit UI entry point
|-- requirements.txt               # Python dependencies
|-- README.md
|-- data/                          # Input datasets
|-- prompts/                       # Prompt templates and target guides
|-- src/
|   |-- llm/                       # Client, prompt builders, generation pipeline
|   |-- metrics_engine/            # KPI engine and registry-based category calculators
|   `-- schemas/                   # Input/output pydantic schemas
`-- output_log/                    # Runtime debug outputs from LLM pipeline
```

## Configuration

### Required Environment Variable

- `OPENAI_API_KEY`

Create `.env` at repo root:

```env
OPENAI_API_KEY=your_key_here
```

## How to Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Developer Onboarding Notes

1. Start in `app.py` to understand user interaction and rendering flow.
2. Review `src/metrics_engine/router.py` + category modules for metric logic.
3. Review `src/llm/pipeline.py` + `src/llm/prompts.py` for generation behavior.
4. Keep prompt schema and pydantic schema aligned when modifying LLM outputs.
5. Validate imports/typing with:

```bash
.\.venv\Scripts\python.exe -m compileall app.py src
```

## Extension Guide

### Add a New Category

1. Add UI selection in `app.py`.
2. Add a new calculator module under `src/metrics_engine/` and decorate with `@register_target("Category Name")`.
3. Import that module in `src/metrics_engine/__init__.py`.
4. Add prompt file in `prompts/`.
5. Map category to prompt in `src/llm/pipeline.py` (`_CATEGORY_PROMPT_FILES`).

### Change Recommendation Output Structure

1. Update recommendation instructions in prompt sources (`prompts/` and/or `src/llm/prompts.py`).
2. Update models in `src/schemas/Recommendation_schema.py`.
3. Update rendering in `app.py` (`_render_recommendations`).

## Constraints and Assumptions

- Primary runtime data source is `data/all_campaigns_data.csv`.
- Category routing depends on exact string labels.
- The app currently runs synchronously in a single Streamlit request path.
- No automated tests are currently included in the repository.
- Prompt quality and schema consistency directly affect runtime stability.

