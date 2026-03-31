# Cross-Cutting Concerns Design

## Scope

Cross-cutting concerns are the pieces of the application that support every major layer without belonging to one business pipeline step.

Owned files:

- `src/config/settings.py`
- `src/core/exceptions.py`
- `src/core/observability.py`

## Conceptual Role

These modules provide the shared infrastructure vocabulary of the application:

- how configuration is resolved
- how failures are represented
- how runs are traced in logs and persisted outputs

They are deliberately isolated so every other layer can depend on them without creating circular ownership.

## Configuration Design

### `PathSettings`

Stores the resolved filesystem locations used by the app:

- repository root
- data file
- benchmark file
- prompt directory
- output-log directory

### `LLMSettings`

Stores the model and temperature configuration for both analysis and recommendation generation.

### `AppSettings`

Acts as the immutable top-level configuration object. The current default builder reads environment variables and falls back to repository defaults.

Design benefits:

- avoids scattering `os.getenv(...)` calls across the codebase
- makes configuration explicit at service-construction time
- simplifies future dependency injection for tests or deployments

## Exception Design

The custom exception types define meaningful failure categories.

Current exception types:

- `MarketingExpertError`
- `DataLoadError`
- `DataValidationError`
- `ReportValidationError`
- `CategoryNotSupportedError`
- `PipelineExecutionError`

Why this matters:

- the UI can catch application errors cleanly
- service tests can assert specific failure types
- orchestration code does not need to inspect brittle error strings

## Observability Design

### Correlation IDs

`correlation_context()` provides a request-scoped correlation ID.

This ID is:

- added to log records through `CorrelationIdFilter`
- returned in `MarketingPipelineResult`
- persisted in output payload traces
- shown in the Streamlit UI as the run ID

### Logging

`configure_logging()` configures the root logger once with a format that includes:

- timestamp
- log level
- correlation ID
- logger name
- message

This gives the current version enough traceability without requiring a full logging platform.

## Logical Responsibilities

These modules should provide infrastructure support, not domain policy.

Good uses:

- centralizing path defaults
- centralizing model settings
- centralizing exception taxonomy
- centralizing correlation ID behavior

Bad uses:

- embedding marketing formulas
- embedding benchmark criteria
- embedding UI details

## Extension Guidelines

Good future extensions:

- environment-specific settings loaders
- JSON or file-based logging handlers
- correlation ID propagation into external telemetry tools
- richer exception hierarchies when new integration types appear

Keep in mind:

These modules should stay stable and boring. If they grow quickly, it is usually a sign that unrelated logic is leaking into the infrastructure layer.

## Testing Strategy

The current tests already cover the most important observability behaviors.

Recommended focus:

- correlation ID creation and reset behavior
- logging configuration idempotency
- settings default resolution from environment variables
- exception propagation through service boundaries

## Physical Design Notes

Physical placement:

- `src/config/`
- `src/core/`

Runtime characteristics:

- process-local configuration and logging support
- no separate infrastructure process in the current version
- shared dependency surface used by nearly every other package

This layer is the foundation that keeps the rest of the architecture coherent and traceable.
