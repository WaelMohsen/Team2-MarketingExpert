# Marketing Engine — Project Documentation

## Overview

This project is an AI-powered marketing campaign analysis engine. It reads raw campaign data from a CSV file, calculates a set of marketing KPIs, and then uses an LLM pipeline (OpenAI GPT) to produce a structured diagnostic analysis followed by a set of prioritized, actionable recommendations — all scoped to a specific business target (revenue, acquisition, retention, or satisfaction).

---

## How to Run

1. Create a `.env` file in the project root with your OpenAI key:
   ```
   OPENAI_API_KEY=your_key_here
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run from the project root:
   ```bash
   python main.py
   ```

4. Output is printed to the terminal and saved as a JSON file in `output_log/`.

---

## Project Structure

```
├── main.py                          # Entry point
├── data/
│   └── all_campaigns_data.csv       # Raw campaign data input
├── prompts/
│   ├── analysis_prompt.md           # System prompt for Step 1 (analysis)
│   ├── recommendation_prompt.md     # System prompt for Step 2 (recommendations)
│   ├── customer_acquisition.md      # Target-specific rules: acquisition
│   ├── customer_retention.md        # Target-specific rules: retention
│   ├── customer_satisfaction.md     # Target-specific rules: satisfaction
│   └── revenue_growth.md            # Target-specific rules: revenue
├── output_log/                      # Auto-saved JSON outputs from each run
├── src_2/
│   ├── DTOs/
│   │   ├── campaign.py              # Campaign DTO (raw row from CSV)
│   │   └── metrics.py               # Metrics DTOs (calculated KPIs)
│   ├── readers/
│   │   └── campaign_reader.py       # Reads CSV and returns list of Campaign DTOs
│   ├── calculators/
│   │   └── metrics_calculator.py    # Calculates KPIs and returns target metric DTOs
│   ├── targets/
│   │   ├── base_target.py           # Abstract base class for targets
│   │   ├── acquisition_target.py    # Selects acquisition KPIs from metric DTOs
│   │   ├── revenue_target.py        # Selects revenue KPIs from metric DTOs
│   │   ├── retention_target.py      # Selects retention KPIs from metric DTOs
│   │   └── satisfaction_target.py   # Selects satisfaction KPIs from metric DTOs
│   ├── schemas/
│   │   ├── analysis_output_schema.py       # Pydantic model + validator for analysis output
│   │   └── recommendation_output_schema.py # Pydantic model + validator for recommendations
│   └── services/
│       ├── llm_client.py            # Wraps the OpenAI API call
│       ├── prompt_builder.py        # Loads prompt files from disk
│       ├── base_llm_service.py      # Abstract base class for LLM services
│       ├── llm_analysis_service.py  # Step 1: sends data to LLM for analysis
│       ├── llm_recommendation_service.py  # Step 2: sends analysis to LLM for recommendations
│       └── llm_orchestrator.py      # Runs Step 1 → Step 2, saves output
└── tests_2/
    ├── test_metrics_calculator.py   # Unit tests for KPI calculations
    ├── test_targets.py              # Unit tests for target selectors
    ├── test_services.py             # Unit tests for LLM and prompt services
    └── test_campaign_reader.py      # Unit tests for CSV reader
```

---

## Data Flow

```
CSV file
   │
   ▼
Campaign_Reader                           → list of Campaign objects (one per CSV row)
   │
   ▼
MetricsCalculator.run(campaigns, target)  → (Base_Metrics, <Target>_Metrics)
   │
   ▼
target.select_target()                    → dict of KPIs relevant to the chosen target
   │
   ▼
LLMOrchestrator
   ├── Step 1: LLMAnalysisService   → AnalysisOutput (JSON)
   └── Step 2: LLMRecommendationService (receives Step 1 output) → RecommendationOutput (JSON)
   │
   ▼
output_log/output_<timestamp>.json
```

---

## Components

### `models/campaign.py` — `Campaign`

Holds one row of raw campaign data as read from the CSV.

| Field | Description |
|---|---|
| `campaign_name` | Name of the campaign |
| `date` | Campaign date |
| `channel` | Marketing channel (e.g. social, search) |
| `impressions` | Number of times the ad was shown |
| `clicks` | Number of clicks |
| `conversions` | Number of completed goals |
| `spend` | Ad spend (currency) |
| `revenue` | Revenue generated |
| `new_customers` | New customers acquired |
| `reach` | Unique users reached |
| `likes`, `comments`, `shares` | Engagement signals |
| `bounce_rate` | Bounce rate (0–1 or 0–100) |
| `frequency` | Average times ad was shown per user |
| `retained_customers` | Customers who returned |
| `churn_rate` | Rate of customer loss |
| `purchases_per_year` | Average purchases per customer per year |
| `product_profit_margin` | Profit margin of the product |

---

### `models/metrics.py` — `Metrics`

Holds all calculated KPIs aggregated across campaigns.

| Group | Fields |
|---|---|
| Base | `campaign_name`, `total_spend`, `total_revenue`, `total_impressions`, `total_clicks`, `total_conversions`, `total_new_customers` |
| Acquisition | `ctr`, `conversion_rate`, `cpa` |
| Revenue | `roas`, `aov`, `annual_customer_value`, `marketing_roi`, `revenue_per_click`, `ltv_cac_ratio` |
| Retention | `retained_customers`, `churn_rate`, `retention_rate`, `purchases_per_year` |
| Satisfaction | `total_reach`, `engagement_rate`, `avg_bounce_rate`, `avg_frequency` |

---

### `readers/campaign_reader.py` — `Campaign_Reader`

Reads the CSV and returns a list of `Campaign` objects.

```python
reader = Campaign_Reader("data/all_campaigns_data.csv")
campaigns = reader.read_campaign()  # → list[Campaign]
```

---

### `calculators/metrics_calculator.py` — `MetricsCalculator`

Aggregates all campaigns and computes every KPI.

```python
calculator = MetricsCalculator()
metrics = calculator.run(campaigns)  # → Metrics
```

Key formulas:

| KPI | Formula |
|---|---|
| CTR | `clicks / impressions × 100` |
| Conversion Rate | `conversions / clicks × 100` |
| CPA | `spend / new_customers` |
| ROAS | `revenue / spend` |
| AOV | `revenue / conversions` |
| Annual Customer Value | `AOV × avg purchases_per_year` |
| Marketing ROI | `(revenue - spend) / spend × 100` |
| LTV:CAC | `annual_customer_value / CPA` |
| Retention Rate | `100 - churn_percent` |
| Engagement Rate | `(likes + comments + shares) / reach × 100` |

---

### `targets/` — Target Classes

Each target filters `Metrics` down to only the KPIs relevant to the business goal.

| Class | `select()` returns |
|---|---|
| `AcquisitionTarget` | `ctr`, `cpa`, `conversion_rate`, `total_new_customers` |
| `RevenueTarget` | `roas`, `aov`, `annual_customer_value`, `marketing_roi`, `revenue_per_click`, `ltv_cac_ratio` |
| `RetentionTarget` | `retained_customers`, `churn_rate`, `retention_rate`, `purchases_per_year` |
| `SatisfactionTarget` | `engagement_rate`, `avg_bounce_rate`, `avg_frequency` |

Usage:
```python
target_map = {
    "revenue": RevenueTarget(),
    "acquisition": AcquisitionTarget(),
    "retention": RetentionTarget(),
    "satisfaction": SatisfactionTarget(),
}
selected_metrics = target_map["revenue"].select(metrics)
```

---

### `services/llm_client.py` — `LLMClient`

Wraps `openai.beta.chat.completions.parse` (structured output mode). Requires `OPENAI_API_KEY` in the environment.

```python
client.chat_completion(system_text, user_text, response_format, model)
```

---

### `services/prompt_builder.py` — `PromptBuilder`

Loads prompt `.md` files from the `prompts/` directory. Returns `""` silently on failure.

```python
builder = PromptBuilder("prompts/")
builder.load("analysis_prompt.md")           # generic system prompt
builder.load_target_prompt("revenue")        # loads revenue_growth.md
```

---

### `services/llm_analysis_service.py` — `LLMAnalysisService` (Step 1)

Sends the full metrics + selected target metrics to `gpt-4o-mini` and returns a structured diagnostic analysis.

- **System prompt:** `analysis_prompt.md` + target-specific prompt
- **User prompt:** target name, full metrics context, selected KPIs
- **Model:** `gpt-4o-mini`
- **Output:** `AnalysisOutput` (see Schemas section)

---

### `services/llm_recommendation_service.py` — `LLMRecommendationService` (Step 2)

Receives the Step 1 analysis JSON and generates actionable recommendation cards.

- **System prompt:** `recommendation_prompt.md` + target-specific prompt
- **User prompt:** target name, full metrics context, selected KPIs, Step 1 analysis JSON
- **Model:** `gpt-4o`
- **Output:** `RecommendationOutput` containing 5–8 `RecommendationCard` objects

---

### `services/llm_orchestrator.py` — `LLMOrchestrator`

Runs the full two-step pipeline and saves the result.

```python
orchestrator = LLMOrchestrator("prompts/", "output_log")
result = orchestrator.run(target, metrics, selected_metrics)
# result = { "analysis": {...}, "recommendations": [...] }
```

Saves output to `output_log/output_<YYYYMMDD_HHMMSS>.json`.

---

## Schemas

### `AnalysisOutput`

| Field | Type | Description |
|---|---|---|
| `analysis` | `str` | Plain-English diagnostic summary |
| `key_signals` | `list[str]` | Most important observed signals |
| `detected_issues` | `list[str]` | Identified problems |
| `root_cause_hypothesis` | `str` | Most likely root cause |
| `business_risks` | `list[str]` | Risks if issues go unaddressed |
| `confidence_score` | `float` | Confidence 0–100 (auto-normalized from 0–1 if needed) |

### `RecommendationCard`

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Stable identifier (e.g. `REC-01`) |
| `title` | `str` | Short outcome-focused title |
| `category` | `str` | e.g. Budget, Targeting, Creative, Retention |
| `priority` | `str` | High / Medium / Low |
| `effort` | `str` | Low / Medium / High |
| `time_to_see_impact` | `str` | e.g. `1-3 days`, `2-4 weeks` |
| `confidence` | `str` | High / Medium / Low |
| `whats_happening` | `str` | Plain-English issue description |
| `evidence` | `list[str]` | Metrics that justify this recommendation |
| `what_you_should_do` | `list[RecommendationActionStep]` | Step-by-step actions |
| `why_this_matters` | `str` | Business impact |
| `expected_impact` | `ExpectedImpact` | KPI, direction, explanation |
| `dependency_or_risk` | `list[str]` | Prerequisites or risks |
| `measurement_plan` | `MeasurementPlan` | How to measure success |
| `owner_suggestion` | `str` | Suggested owner (e.g. Media buyer) |

---

## Prompts

| File | Used by | Purpose |
|---|---|---|
| `analysis_prompt.md` | `LLMAnalysisService` | Instructs the LLM to act as a diagnostic analyst — no recommendations, only root cause identification |
| `recommendation_prompt.md` | `LLMRecommendationService` | Instructs the LLM to produce 5–8 structured recommendation cards |
| `customer_acquisition.md` | Both services | KPI benchmarks and rules for the acquisition target |
| `revenue_growth.md` | Both services | KPI benchmarks and rules for the revenue target |
| `customer_retention.md` | Both services | KPI benchmarks and rules for the retention target |
| `customer_satisfaction.md` | Both services | KPI benchmarks and rules for the satisfaction target |

---

## Tests

Located in `tests/test_schema_validation.py`. Run with:

```bash
pytest
```

| Test | What it checks |
|---|---|
| `test_analysis_valid_strict_json_scales_confidence_fraction_to_percent` | A confidence score of `0.72` is normalized to `72.0` |
| `test_analysis_missing_required_text_fields_raises_value_error` | Empty `analysis` field raises `ValueError` |
| `test_analysis_broken_json_is_rejected_in_strict_json_mode` | Malformed JSON raises `JSONDecodeError` |
| `test_analysis_output_to_json_returns_valid_json_and_preserves_unicode` | Unicode characters are preserved in serialization |
| `test_recommendations_valid_5_cards_passes` | 5 recommendation cards pass validation |
| `test_recommendations_wrong_count_raises_value_error` | Fewer than 5 cards raises `ValueError` |
| `test_recommendations_empty_evidence_raises_value_error` | Empty `evidence` list raises `ValueError` |
| `test_recommendations_broken_json_python_dict_repr_is_rejected_in_strict_json_mode` | Python dict string (single quotes) raises `JSONDecodeError` |

---

## Dependencies

| Package | Purpose |
|---|---|
| `openai` | LLM API client (GPT-4o / GPT-4o-mini) |
| `pydantic` | Schema validation and structured output models |
| `pandas` | CSV reading |
| `python-dotenv` | Load `OPENAI_API_KEY` from `.env` |
| `streamlit` | UI (reserved for app interface, not used in `main.py`) |
