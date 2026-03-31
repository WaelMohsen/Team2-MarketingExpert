# Orchestration Layer Design

## Scope

The orchestration layer coordinates the end-to-end application flow. It is the bridge between the user-facing entrypoint and the individual application services.

Owned files:

- `src/pipelines/marketing_pipeline.py`
- `src/pipelines/models.py`

## Conceptual Role

Conceptually, this layer answers one question:

How does one analysis request move through the system from input to report?

It is responsible for sequencing work, preserving traceability, and returning a complete runtime result object.

## Logical Responsibilities

### `MarketingPipeline`

`MarketingPipeline` is the main application orchestrator.

Responsibilities:

- load raw input datasets
- preprocess datasets
- validate datasets
- canonicalize validated data
- calculate metrics
- generate the AI report
- assign a correlation ID for the request
- return one `MarketingPipelineResult`

The constructor accepts service dependencies so the pipeline can be tested with fakes or alternate implementations.

### `MarketingPipelineResult`

This dataclass is the stable output contract for one run.

Current fields:

- `correlation_id`
- `raw_dataset`
- `dataset`
- `preprocessing`
- `input_validation`
- `metrics`
- `report`

This contract is important because it prevents the UI from needing to reassemble state from multiple sources.

## Stage-Level API

The pipeline exposes stage methods as well as the full `run(...)` method.

Available stage methods:

- `load_raw_dataset(...)`
- `preprocess_dataset(...)`
- `validate_dataset(...)`
- `canonicalize_dataset(...)`
- `calculate_metrics(...)`
- `generate_report(...)`
- `run(...)`

This design supports:

- integration testing at intermediate boundaries
- selective reuse in scripts or future APIs
- easier debugging when one stage fails

## Orchestration Flow

1. Enter `correlation_context()` and allocate a run ID.
2. Load the raw dataset.
3. Preprocess the dataset.
4. Validate the preprocessed dataset.
5. Stop early if blocking validation errors exist.
6. Canonicalize the dataset using the input schema.
7. Calculate metrics for the selected category.
8. Generate the validated LLM report.
9. Return the assembled `MarketingPipelineResult`.

## Failure Boundaries

The orchestration layer is where service failures become runtime workflow failures.

Important failure paths:

- `DataLoadError` when the input file cannot be read
- `DataValidationError` when explicit checks or schema canonicalization fail
- `ReportValidationError` when structured LLM output is invalid
- future `PipelineExecutionError` when more complex multi-step rollback or wrapping becomes necessary

The pipeline should not hide these failures. It should preserve meaningful exception types.

## Design Rationale

Why this is a class instead of a single function:

- it owns a dependency graph
- it provides reusable stage methods
- it gives us a stable seam for testing and future alternate entrypoints
- it keeps orchestration separate from both UI and business formulas

Why the result is a dataclass:

- immutable, easy-to-inspect contract
- clear field ownership
- straightforward serialization from nested types when needed

## Extension Guidelines

Good uses for this layer:

- adding a preprocessing or evaluation stage to the main runtime flow
- introducing alternate orchestration methods for batch mode or API mode
- adding retries or timing around LLM execution
- wrapping each stage with richer observability

Bad uses for this layer:

- embedding formula details
- embedding Streamlit presentation logic
- embedding prompt text or schema parsing rules

## Testing Strategy

Primary orchestration tests should verify:

- stage ordering
- correct stop behavior on validation errors
- propagation of warnings
- propagation of correlation IDs
- result contract completeness

This is the right layer for service-composition tests, but not for heavy formula-level assertions. Formula tests belong in the metrics layer.

## Physical Design Notes

Physical placement:

- `src/pipelines/` package

Runtime dependencies:

- `CampaignDataService`
- `CampaignPreprocessingService`
- `CampaignValidationService`
- `CampaignMetricsService`
- `LLMReportService`
- `correlation_context()`

The orchestration layer is process-local. It does not persist state beyond the returned result object and downstream output-log writes performed by the LLM service.
