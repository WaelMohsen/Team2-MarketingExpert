# Presentation Layer Design

## Scope

The presentation layer is responsible for turning pipeline results into an interactive Streamlit experience without embedding business rules in the UI. In the current version, this layer is intentionally thin and function-oriented.

Owned files:

- `app.py`
- `src/presentation/streamlit_dashboard.py`

## Conceptual Role

Conceptually, this layer sits between the business user and the application runtime.

Its responsibilities are to:

- collect the user intent, which is currently the selected marketing category
- trigger the end-to-end application workflow
- render metrics, analysis, recommendations, warnings, and trace metadata
- expose light debug affordances such as the raw-data preview

It does not own data validation rules, metric formulas, prompt construction, or recommendation scoring.

## Logical Responsibilities

### `app.py`

`app.py` is the Streamlit entrypoint and composition root for the interactive application.

Primary responsibilities:

- load environment variables
- configure logging through `configure_logging()`
- create the shared `CampaignDataService`
- create the shared `MarketingPipeline`
- initialize the page and delegate rendering to the presentation helpers
- translate user button clicks into `MarketingPipeline.run(...)` calls
- catch application exceptions and display user-friendly error messages

This file should remain small. It should compose services, not implement domain logic.

### `src/presentation/streamlit_dashboard.py`

This module contains pure UI-oriented helpers.

Important functions:

- `apply_page_style()`
- `render_header()`
- `render_sidebar(data_service)`
- `initialize_session_state()`
- `render_category_selector(on_select)`
- `render_analysis_result(result)`
- `render_overall_metric_cards(metrics_overall)`
- `render_analysis_summary(analysis)`
- `render_validation_warnings(warnings)`
- `render_recommendations(recommendations)`

These are functions instead of classes because:

- they are stateless
- they are tightly tied to Streamlit's rendering model
- they do not benefit from object lifecycle management
- they are easiest to understand as direct view helpers

## Input and Output Contracts

Inputs accepted by this layer:

- user category selection from the button grid
- `MarketingPipelineResult` from the orchestration layer
- `MarketingExpertError` subclasses surfaced from downstream services

Outputs produced by this layer:

- rendered Streamlit components
- displayed warnings and errors
- a visible run ID that maps to logs and output payloads

The key rule is that this layer receives already-processed information. It should not need to inspect raw CSV files or reconstruct business decisions.

## Request Flow

1. Streamlit starts `app.py`.
2. The app builds shared services and the pipeline once for the process.
3. UI helpers render the header, selector, and sidebar.
4. A category button click updates session state.
5. `MarketingPipeline.run(category)` is called.
6. The returned `MarketingPipelineResult` is rendered by `render_analysis_result(...)`.
7. Errors are caught and translated into Streamlit error components.

## Error Handling

The presentation layer should only handle errors at a user-communication level.

Current behavior:

- data load or validation failures are shown as friendly messages
- pipeline exceptions stop the current render cycle cleanly
- warnings are shown separately from blocking errors

This layer should not recover from corrupted data internally. Recovery decisions belong in the service and orchestration layers.

## Extension Guidelines

Use this layer for:

- new layout sections
- improved charts or visual summaries
- additional debug panels
- different entrypoints built on the same pipeline contract

Do not place the following here:

- metric calculations
- input validation rules
- prompt-generation logic
- OpenAI request code
- benchmark scoring rules

If the UI needs new information, extend the pipeline result contract first and then render that information here.

## Testing Strategy

The current automated tests do not deeply test Streamlit rendering. That is acceptable for this stage because the real value lies in the pipeline and service tests.

Recommended test focus for this layer:

- smoke tests for app startup
- snapshot-style tests if the UI becomes more complex
- regression tests for helper formatting functions such as currency formatting

## Physical Design Notes

Physical placement:

- `app.py` at the repository root for `streamlit run app.py`
- `src/presentation/` as the UI support package

Runtime dependencies:

- `streamlit`
- the shared application service graph built in `app.py`

This layer has no persistence of its own. It depends on the pipeline and logging infrastructure for traceable outputs.
