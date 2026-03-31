# Domain Contracts Layer Design

## Scope

The domain contracts layer defines the stable typed shapes that move through the application. Its job is to make interfaces explicit and prevent silent drift between modules.

Owned files and packages:

- `src/schemas/input_schema.py`
- `src/schemas/analysis_output_schema.py`
- `src/schemas/recommendation_output_schema.py`
- `src/reporting/models.py`
- `src/metrics/models.py`
- `src/validation/models.py`
- `src/pipelines/models.py`

## Conceptual Role

Conceptually, this layer represents the shared language of the application.

Examples:

- what counts as one canonical campaign row
- what a metric bundle looks like
- what an LLM analysis is allowed to contain
- what a recommendation card must contain
- what a validation issue means
- what one pipeline result contains

Without this layer, the application would fall back to anonymous dictionaries and hidden assumptions.

## Logical Responsibilities

### Input Contract

`CampaignInput` defines the canonical row shape for marketing data after preprocessing.

Key value:

- converts inconsistent CSV rows into one stable internal representation
- centralizes row-level validation rules
- prevents downstream services from guessing field names or types

### Analysis Contract

`AnalysisOutput` defines the structured output of the LLM analysis step.

Typical fields:

- narrative analysis
- key signals
- detected issues
- root-cause hypothesis
- business risks
- confidence score

### Recommendation Contract

The recommendation schema is intentionally rich enough to support both UI rendering and evaluation.

Main models:

- `RecommendationActionStep`
- `ExpectedImpact`
- `MeasurementPlan`
- `RecommendationCard`
- `RecommendationOutput`

These models capture not only recommendation text, but also evidence, action structure, measurement plans, and ownership.

### Reporting Contract

`MarketingReport` combines:

- one `AnalysisOutput`
- one tuple of `RecommendationCard`
- the selected category

It acts as the durable report object passed from the AI service to the pipeline and UI.

### Operational Result Contracts

Operational dataclasses support clean boundaries between services.

Important examples:

- `MetricsBundle`
- `ValidationIssue`
- `ValidationResult`
- `PreprocessingResult`
- `MarketingPipelineResult`
- evaluation result dataclasses in `src/evaluation/`

## Design Rationale

Why strongly typed contracts matter here:

- they make failure modes explicit
- they make serialization predictable
- they reduce coupling between services
- they improve editor support and test readability
- they help the team evolve the app without breaking interfaces silently

This is practical OOP and data modeling, not abstraction for its own sake.

## Serialization Boundaries

Important serialization points:

- `MarketingReport.to_response_dict()` for UI and API-style responses
- `CriterionScore.to_dict()` and related evaluation serializers
- output-log JSON payloads produced by `OutputLogWriter`

The rule is simple:

Inside the application, prefer typed objects. At the system boundary, serialize deliberately.

## Validation Strategy

Contracts are enforced in two ways:

- explicit service-level validation for business-facing failure scenarios
- schema-level validation for canonical row and structured output correctness

That split is intentional. A user-friendly error like "Clicks exceed impressions" is easier to act on than a generic schema failure.

## Extension Guidelines

Use this layer when:

- a boundary needs a stable reusable shape
- an LLM output needs stronger structure
- a pipeline stage needs a durable result object

Do not create new models when:

- a value is purely local to one function
- a simple helper return tuple would be clearer
- the added model would not be shared across a module boundary

## Testing Strategy

Contract-focused tests should cover:

- valid and invalid input rows
- valid and invalid analysis outputs
- valid and invalid recommendation outputs
- serialization stability for output logs and evaluation results
- backward compatibility where legacy wrappers still depend on existing shapes

## Physical Design Notes

Physical placement:

- schema modules under `src/schemas/`
- reporting and operational models under their owning packages

These contracts are pure Python objects and Pydantic models. They have no independent runtime process and no storage of their own.
