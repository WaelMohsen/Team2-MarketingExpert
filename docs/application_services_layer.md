# Application Services Layer Design

## Scope

The application services layer contains the operational business services that perform work for the pipeline. These services are intentionally separated by responsibility so they can be tested and extended independently.

Owned packages:

- `src/ingestion/`
- `src/preprocessing/`
- `src/validation/`
- `src/metrics/`
- `src/llm/`

## Conceptual Role

Conceptually, this layer converts raw campaign input into validated, explainable business output.

It owns the main transformations of the system:

- file to dataframe
- raw dataframe to normalized dataframe
- normalized dataframe to validated/canonical dataframe
- canonical dataframe to metric bundle
- metric bundle to structured business report

## Service Inventory

| Service | Responsibility | Key Dependencies |
| --- | --- | --- |
| `CampaignDataService` | Read CSV data and produce canonical dataframes | `AppSettings`, preprocessing, validation, `CampaignInput` validation |
| `CampaignPreprocessingService` | Normalize strings, numerics, dates, and row order | `pandas` |
| `CampaignValidationService` | Detect explicit input failure and warning scenarios | validation models, `pandas` |
| `ReportValidationService` | Validate structured analysis and recommendation payloads | schema validators |
| `CampaignMetricsService` | Compute overall and per-channel metrics | registry and pure calculator functions |
| `LLMReportService` | Build prompt context, call the OpenAI API, validate outputs, persist logs | prompt helpers, OpenAI client, reporting model |

## Ingestion Service

### `CampaignDataService`

Primary responsibilities:

- load the configured CSV file
- provide a raw-data path for the sidebar and diagnostics
- orchestrate preprocessing plus validation for full data preparation
- canonicalize rows through the `CampaignInput` schema

Important methods:

- `load_raw_dataframe(...)`
- `preprocess_dataframe(...)`
- `validate_input_dataframe(...)`
- `prepare_dataframe(...)`
- `validate_dataframe(...)`
- `load_dataframe(...)`

Design note:

This service owns data access and canonicalization, but not metric logic and not UI rendering.

## Preprocessing Service

### `CampaignPreprocessingService`

Primary responsibilities:

- trim and normalize string values
- coerce numeric columns where possible
- normalize date values
- sort rows into a stable order
- return metadata about applied steps through `PreprocessingResult`

Why it exists as a separate service:

- preprocessing rules evolve independently from validation rules
- normalization is often useful even when validation eventually fails
- it improves observability by recording the steps that were applied

## Validation Services

### `CampaignValidationService`

Primary responsibilities:

- detect missing required columns
- detect nulls in required fields
- detect negative numeric values
- check funnel monotonicity such as clicks greater than impressions
- enforce supported rate ranges
- detect invalid dates
- warn on duplicate rows

It returns `ValidationResult` instead of raising immediately so the pipeline can preserve warnings and decide where to stop.

### `ReportValidationService`

Primary responsibilities:

- validate analysis payloads against `AnalysisOutput`
- validate recommendation payloads against `RecommendationOutput`
- accept string, dict, or already-built models behind one stable API

This prevents LLM parsing and schema enforcement from leaking into the orchestration or UI layers.

## Metrics Service

### `CampaignMetricsService`

Primary responsibilities:

- calculate base metrics for the full dataset
- calculate category-specific metrics for the selected business area
- calculate per-channel metric variants
- return a `MetricsBundle` with both overall and per-channel views

Supporting design:

- `MetricCalculatorRegistry` maps categories to calculator functions
- `src/metrics/calculators.py` keeps the formulas pure and testable
- `src/metrics_engine/` remains as a legacy compatibility wrapper

This design balances OOP and functional code. The service coordinates calculations, while formulas remain simple functions.

## LLM Service

### `LLMReportService`

Primary responsibilities:

- build shared prompt context from category, metrics, and dataset
- resolve prompt files through `PromptRepository`
- call the OpenAI API through `chat_completion(...)`
- validate both analysis and recommendation outputs
- assemble a `MarketingReport`
- persist one structured JSON payload through `OutputLogWriter`

Supporting classes:

- `PromptRepository`
- `OutputLogWriter`

Important design boundary:

This service owns AI orchestration, but it does not own the UI and it does not own benchmark scoring.

## Logical Data Flow

1. `CampaignDataService` reads the CSV.
2. `CampaignPreprocessingService` normalizes it.
3. `CampaignValidationService` checks explicit failure scenarios.
4. `CampaignDataService.validate_dataframe(...)` canonicalizes rows using the schema layer.
5. `CampaignMetricsService` computes the selected category metrics.
6. `LLMReportService` turns metrics into a validated `MarketingReport`.

## Extension Guidelines

Preferred extension patterns:

- add new preprocessing rules inside `CampaignPreprocessingService`
- add new validation rules inside `CampaignValidationService`
- add new business categories through `MetricCalculatorRegistry`
- add new prompt variants through prompt files and `PromptRepository`
- swap services during tests by constructor injection

Anti-patterns to avoid:

- mixing filesystem access into metrics or validation modules
- duplicating schemas inside service code
- returning loosely shaped dictionaries when a stable model already exists
- moving prompt text into orchestration code

## Testing Strategy

This layer should carry most of the unit-test weight.

Recommended focus:

- preprocessing normalization edge cases
- explicit validation failure scenarios
- metric correctness and rounding behavior
- prompt and LLM output validation boundaries
- output payload persistence contract

## Physical Design Notes

Physical placement:

- service packages live under `src/`
- prompt templates live under `prompts/`
- persisted outputs live under `output_log/`

External runtime dependencies:

- `pandas`
- `pydantic`
- `openai`
- local filesystem

This layer is where most CPU and I/O work occurs in the current version.
