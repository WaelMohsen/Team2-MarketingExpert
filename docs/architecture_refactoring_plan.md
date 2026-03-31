# Architecture Refactoring Plan

## Current State Review

### Main problems

- `app.py` mixes presentation, orchestration, data access, metric calculation, JSON parsing, and error handling.
- The legacy `metrics_engine` package relies on import side effects for calculator registration.
- The LLM flow bundles prompt lookup, client configuration, validation, persistence, and response assembly into one function.
- Input and output contracts are mostly loose dictionaries, which makes interfaces fragile and hard to test.
- Metric values are inconsistent across categories. Some percentages are strings, some are numeric, and some NumPy scalar types leak outward.
- There is duplicated schema logic in `src/schemas/Recommendation_schema.py` and `src/schemas/recommendation_output_schema.py`.
- Logging and traceability rely on `print` statements and ad hoc output files.

### Design smells

- God-function behavior in both `app.py` and `src/llm/pipeline.py`
- Hidden coupling through shared dictionaries and side-effect imports
- Weak separation between business logic and I/O
- Procedural flow with limited composability
- Low confidence in change safety because critical calculations were not isolated behind stable services

### Refactoring priorities

1. Introduce clear service boundaries around ingestion, metrics, orchestration, and AI reporting.
2. Replace side-effect-driven wiring with explicit composition.
3. Stabilize contracts with typed models for metrics bundles, reports, and evaluation results.
4. Move the Streamlit app to a thin UI role.
5. Expand tests around calculations, orchestration, and evaluation logic.

## Target Structure

```text
src/
  config/
    settings.py
  core/
    exceptions.py
  evaluation/
    recommendation_framework.py
  ingestion/
    service.py
  llm/
    client.py
    pipeline.py
    prompts.py
  metrics/
    calculators.py
    models.py
    registry.py
    service.py
  pipelines/
    marketing_pipeline.py
    models.py
  preprocessing/
    models.py
    service.py
  presentation/
    streamlit_dashboard.py
  reporting/
    models.py
  schemas/
    analysis_output_schema.py
    input_schema.py
    recommendation_output_schema.py
  validation/
    models.py
    service.py
```

## Responsibility Split

- `config`: immutable application settings and filesystem paths
- `core`: shared exceptions and cross-cutting primitives
- `ingestion`: data loading and schema validation
- `preprocessing`: lightweight normalization before validation and metric calculation
- `metrics`: pure calculations plus a coordinating metrics service
- `llm`: prompt construction, structured-output calls, and report persistence
- `reporting`: report-level contracts used by pipelines and UI
- `pipelines`: orchestration of ingestion, metrics, validation, analysis, and recommendations
- `presentation`: Streamlit-specific rendering helpers and page composition
- `evaluation`: reusable scoring framework for recommendation quality and parameter sensitivity
- `validation`: explicit input/output validation services with failure scenarios and warnings

## Pipeline Interaction Model

### Data ingestion pipeline

- Load CSV
- Preprocess into a stable shape
- Validate failure scenarios explicitly
- Validate with `CampaignInput`
- Produce canonical `DataFrame`

### Data preprocessing pipeline

- Keep preprocessing lightweight for now
- Normalize null values through schema validation
- Add future transformations as explicit services instead of inside calculators

### Metric calculation pipeline

- Calculate base metrics once
- Apply category-specific enrichments through an explicit registry
- Return `MetricsBundle` with overall and per-channel metrics

### Validation pipeline

- Validate input rows before any business logic
- Validate analysis output and recommendation output after each LLM step
- Surface explicit failure messages to the UI

### AI analysis pipeline

- Build context from canonical data plus metrics
- Generate structured analysis
- Validate and normalize confidence score

### Recommendation pipeline

- Use validated analysis as input
- Generate structured recommendations
- Validate count and required fields

### Evaluation pipeline

- Score recommendation outputs with a repeatable rubric
- Load benchmark fixtures from versioned JSON
- Run automated candidate comparisons against benchmark cases
- Track parameter settings such as temperature
- Compare candidates consistently using weighted thresholds and hard-fail gates

## Incremental Migration Strategy

### Step 1

- Add the new service-oriented packages.
- Keep `src.metrics_engine` and `src.llm.generate_response` as compatibility wrappers.

### Step 2

- Move the Streamlit app to the new pipeline and remove orchestration logic from the UI layer.

### Step 3

- Delete unused legacy schema modules and side-effect registration once downstream imports are confirmed.

### Step 4

- Add richer preprocessing and evaluation datasets without changing public pipeline contracts.
- Continue moving UI rendering helpers into dedicated modules when presentation complexity grows.
