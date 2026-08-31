"""Build the all-level Empirical-Bayes scorecard walkthrough notebook."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "CAPI_Sample2_All_Level_Empirical_Bayes_Scorecards.ipynb"


def markdown(value: str):
    return nbf.v4.new_markdown_cell(dedent(value).strip())


def code(value: str):
    return nbf.v4.new_code_cell(dedent(value).strip())


cells = [
    markdown(
        """
        # Sample 2: Empirical-Bayes Scorecards At Every Marketing Level

        This notebook walks through the running POC from normalized Meta and WhatsApp
        facts to campaign, adset, ad, creative, and audience scorecards.

        For every entity it shows the raw rate, small-sample corrected score, learned
        peer benchmark, uncertainty range, favorable lift, probability of beating the
        benchmark, and `scale` / `hold` / `kill` statistical decision. Conversation
        signals remain an optional diagnostic explanation layer.
        """
    ),
    markdown(
        """
        ## 1. Load The Existing Pipeline

        All calculations call `src_2` services directly. The notebook does not recreate
        scoring formulas or use an LLM to calculate a decision.
        """
    ),
    code(
        """
        from pathlib import Path

        import altair as alt
        import pandas as pd
        from IPython.display import display

        from src_2.analytics import (
            DeterministicBudgetAllocator,
            DeterministicCampaignAssessor,
            add_empirical_bayes_scores,
            build_evidence_packs,
            build_scorecards,
            enrich_scorecards,
        )
        from src_2.application import load_conversation_signal_records
        from src_2.infrastructure.configuration import (
            load_budget_policy,
            load_campaign_type_registry,
        )
        from src_2.ingestion import (
            build_data_quality_report,
            load_sample2,
            normalize_cycle,
        )

        pd.set_option("display.max_columns", 200)
        pd.set_option("display.max_colwidth", 160)
        alt.data_transformers.disable_max_rows()

        ROOT = Path.cwd()
        INPUT = ROOT / "src_2" / "data" / "input" / "sampe_2"
        SIGNALS = ROOT / "src_2" / "artifacts" / "conversation_signals.jsonl"
        """
    ),
    markdown(
        """
        ## 2. Normalize Facts And Establish The Quality Boundary

        Active and stuck-pending conversations remain unresolved and are excluded from
        mature outcome rates. Customer-level rates ensure a customer with several chats
        does not silently receive several votes. Organic/direct chats remain available
        for context but are excluded from paid campaign scoring.
        """
    ),
    code(
        """
        canonical = normalize_cycle(load_sample2(INPUT))
        quality = build_data_quality_report(canonical)

        inventory = pd.DataFrame({
            "table": ["campaigns", "adsets", "ads", "creatives", "media_daily", "conversations"],
            "rows": [len(canonical.campaigns), len(canonical.adsets), len(canonical.ads),
                     len(canonical.creatives), len(canonical.media_daily), len(canonical.conversations)],
        })
        display(inventory)
        display(pd.DataFrame([quality.model_dump(mode="json")]))
        """
    ),
    markdown(
        """
        ## 3. Build Raw Sufficient Statistics

        Rates are calculated from summed numerators and denominators, never by averaging
        row-level percentages. The experimental order-creation score uses only mature
        conversations, so its numerator can never exceed its denominator.
        """
    ),
    code(
        """
        signal_records = load_conversation_signal_records(SIGNALS) if SIGNALS.exists() else []
        raw = build_scorecards(canonical, signal_records)

        raw.campaign[[
            "campaign_name", "campaign_type", "observed_conversations",
            "mature_conversations", "mature_unique_customers", "delivered_customers",
            "mature_orders_created", "open_or_pending_conversations",
        ]]
        """
    ),
    markdown(
        """
        ## 4. Objective-Specific Score Definitions

        The campaign type selects one decision rate. Sales-oriented types use delivered
        customers, experimental campaigns use mature order creation, retention uses
        returning-customer delivery, and awareness uses link click-through rate. Primary
        business KPIs such as revenue per day and return on ad spend remain visible as
        objective KPIs and guardrails; they are not mixed into an arbitrary weighted score.
        """
    ),
    code(
        """
        registry = load_campaign_type_registry()
        definitions = []
        for campaign_type, config in registry.campaign_types.items():
            score = config.score_metric
            definitions.append({
                "campaign_type": campaign_type.value,
                "business_job": config.business_job,
                "score_metric": score.metric,
                "numerator": score.numerator,
                "denominator": score.denominator,
                "direction": score.direction,
                "POC_lift_threshold": score.practical_lift_threshold,
            })
        display(pd.DataFrame(definitions))
        """
    ),
    markdown(
        """
        ## 5. Apply Empirical Bayes

        For a rate with `k` successes from `n` eligible observations, compatible peers
        provide an empirically fitted beta prior `(alpha, beta)`:

        `raw = k / n`

        `corrected = (k + alpha) / (n + alpha + beta)`

        The prior contributes more when `n` is small and less as evidence grows. The
        system samples both the entity posterior and peer benchmark distribution, then
        calculates favorable lift. A range crossing zero is `hold`; fully positive is
        `scale`; fully negative is `kill`.
        """
    ),
    code(
        """
        scored = add_empirical_bayes_scores(raw, registry)
        score_columns = [
            "entity_name", "campaign_name", "campaign_type", "score_metric",
            "score_successes", "score_trials", "raw_score", "corrected_score",
            "corrected_score_low", "corrected_score_high", "benchmark_score",
            "benchmark_source", "benchmark_peer_count", "expected_lift",
            "lift_low", "lift_high", "probability_better", "statistical_decision",
        ]
        display(scored.campaign[score_columns])
        """
    ),
    markdown(
        """
        ## 6. Review All Five Levels

        Use the selector to inspect any level. Child scores remain visible even when a
        parent campaign blocks funding, because their purpose is also to preserve what
        was learned for the next creative, audience, or execution test.
        """
    ),
    code(
        """
        LEVEL = "ad"  # campaign, adset, ad, creative, or audience
        level_scorecard = scored.by_level(LEVEL).copy()
        display(level_scorecard[score_columns].sort_values(
            ["campaign_name", "probability_better"], ascending=[True, False]
        ))

        chart = alt.Chart(level_scorecard).mark_point(filled=True, size=90).encode(
            x=alt.X("corrected_score:Q", title="Empirical-Bayes corrected score", axis=alt.Axis(format=".0%")),
            y=alt.Y("probability_better:Q", title="Probability better", axis=alt.Axis(format=".0%")),
            color=alt.Color("statistical_decision:N", title="Decision"),
            tooltip=["campaign_name", "entity_name", "score_metric", alt.Tooltip("raw_score:Q", format=".1%"),
                     alt.Tooltip("corrected_score:Q", format=".1%"), alt.Tooltip("lift_low:Q", format="+.1%"),
                     alt.Tooltip("lift_high:Q", format="+.1%"), "benchmark_source"],
        ).properties(height=420)
        chart
        """
    ),
    markdown(
        """
        ## 7. Attach Operational Actions And The 70/30 Scenario

        Statistical decisions describe the evidence. Operational actions additionally
        respect data quality and parent campaign rules. Budget is allocated only at
        campaign level: 70 units exploit supported winners and 30 units fund named tests
        for uncertain campaigns. Unused pools remain unallocated.
        """
    ),
    code(
        """
        cycle_id = f"cycle_{canonical.cycle_start.date()}_{canonical.cycle_end.date()}"
        packs = build_evidence_packs(cycle_id, scored, registry, quality)
        assessor = DeterministicCampaignAssessor()
        assessments = [
            assessor.assess(pack, registry.campaign_types[pack.campaign_type])
            for pack in packs
        ]
        enriched = enrich_scorecards(scored, assessments, registry, quality)
        budget = DeterministicBudgetAllocator().allocate(
            cycle_id, enriched.campaign, assessments, registry,
            load_budget_policy(), quality,
        )

        display(enriched.campaign[[
            "campaign_name", "raw_score", "corrected_score", "lift_low", "lift_high",
            "funding_decision", "next_cycle_action", "evidence_status",
        ]])
        display(pd.DataFrame([item.model_dump(mode="json") for item in budget.allocations]))
        display(pd.DataFrame([
            item.model_dump(mode="json") for item in budget.exploration_tests
        ]))
        print("Assigned:", sum(item.budget_units for item in budget.allocations))
        print("Unallocated:", budget.unallocated_units)
        """
    ),
    markdown(
        """
        ## 8. Conversation Diagnostics

        Version-2 signals explain why a corrected score may be strong, weak, or uncertain:
        urgency, price blocking, deal seeking, delivery readiness, agreement, barrier
        resolution, value drivers, stated exit reasons, and next-step completion. A
        version-1 artifact loads safely with new fields marked unknown. Semantic coverage
        must be shown, and these diagnostics do not change funding until human validation.
        Ad-message match is a separate comparison between the creative promise and the
        validated customer need; unknown comparisons are excluded from its denominator.
        """
    ),
    code(
        """
        semantic_columns = [
            "campaign_name", "semantic_conversations", "semantic_coverage_rate",
            "high_purchase_intent_rate", "high_urgency_rate", "price_blocking_rate",
            "deal_seeking_rate", "delivery_ready_rate", "sales_agreement_rate",
            "barrier_resolution_rate", "next_step_completion_rate",
            "ad_message_alignment_rate", "ad_message_mismatch_rate",
            "top_conversation_purpose", "top_barrier", "top_value_driver",
            "top_stated_exit_reason",
        ]
        available = [column for column in semantic_columns if column in enriched.campaign]
        display(enriched.campaign.loc[
            enriched.campaign.get("semantic_conversations", 0).gt(0), available
        ] if "semantic_conversations" in enriched.campaign else pd.DataFrame())
        """
    ),
    markdown(
        """
        ## Final Reading Rule

        Do not call the largest raw rate the winner. Read each row in this order:

        1. Objective and decision KPI.
        2. Eligible evidence count.
        3. Raw versus corrected score.
        4. Learned benchmark and peer source.
        5. Favorable lift range and probability better.
        6. Statistical decision and operational data-quality status.
        7. Conversation evidence explaining the result and the next controlled test.

        With the current Sample 2 evidence and 95% ranges, all campaign decisions are
        holds. The output still identifies which patterns are more promising, but it does
        not manufacture confident winners from sparse observations.
        """
    ),
]


notebook = nbf.v4.new_notebook(
    cells=cells,
    metadata={
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.9"},
    },
)
nbf.write(notebook, OUTPUT)
print(OUTPUT)
