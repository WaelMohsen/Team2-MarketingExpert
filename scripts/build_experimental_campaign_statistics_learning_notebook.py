"""Build the experimental-campaign statistics and LLM learning notebook."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "CAPI_Experimental_Campaign_Statistics_Learning.ipynb"


def markdown(value: str):
    return nbf.v4.new_markdown_cell(dedent(value).strip())


def code(value: str):
    return nbf.v4.new_code_cell(dedent(value).strip())


cells = [
    markdown(
        """
        # Experimental Campaigns: Learn Every Number From Raw Evidence To LLM Report

        This notebook is a learning version of the completed-cycle pipeline. It uses the
        `experimental` campaign type and works through the **Post-Eid Lookalike Test** in
        detail.

        Every important result follows the same pattern:

        1. Business question and why the calculation is needed.
        2. Raw records included and excluded.
        3. Numerator, denominator, and formula with actual numbers.
        4. Manual result compared with the production pipeline.
        5. What the result contributes to the decision.
        6. What cannot be concluded.

        The statistical engine owns all numbers, decisions, and budget units. Optional
        structured LLM calls explain those locked results in business language.
        """
    ),
    markdown(
        """
        ## 0. The Complete Decision Story

        ```text
        Raw Meta and WhatsApp records
                    |
                    v
        Mature structured outcomes
                    |
                    v
        Raw rate and raw uncertainty
                    |
                    v
        Compatible peer benchmark
                    |
                    v
        Empirical-Bayes corrected score
                    |
                    v
        Favorable lift range
                    |
                    v
        SCALE / HOLD / KILL
                    |
                    +---- Conversation semantics explain possible reasons
                    |
                    v
        Deterministic 70/30 scenario and named test
                    |
                    v
        LLM campaign analysis, synthesis, and stakeholder narration
        ```

        A raw rate answers **what happened in the observed sample**. The benchmark adds
        **compared with what**. Empirical Bayes adds **how much to trust the result**.
        The lift range adds **whether better or worse is sufficiently supported**.
        Conversation semantics adds **why it may have happened and what to test next**.
        """
    ),
    markdown(
        """
        ## 1. Load The Production Pipeline

        The notebook calculates each worked example manually for learning, then compares
        it with the real `src_2` output. An assertion fails if the learning arithmetic and
        production result disagree.
        """
    ),
    code(
        """
        import hashlib
        import json
        import os
        from math import sqrt
        from pathlib import Path
        from random import Random
        from statistics import variance

        import altair as alt
        import pandas as pd
        from dotenv import load_dotenv
        from IPython.display import JSON, Markdown, display

        from src_2.analytics import (
            DeterministicBudgetAllocator,
            DeterministicCampaignAssessor,
            add_empirical_bayes_scores,
            build_evidence_packs,
            build_scorecards,
        )
        from src_2.application import load_conversation_signal_records
        from src_2.contracts import CampaignInsight, PortfolioInsight, StakeholderReport
        from src_2.domain.models import CampaignType
        from src_2.infrastructure.configuration import (
            load_budget_policy,
            load_campaign_type_registry,
        )
        from src_2.ingestion import (
            build_data_quality_report,
            load_sample2,
            normalize_cycle,
        )
        from src_2.intelligence import (
            OpenAICampaignAnalyst,
            OpenAIPortfolioSynthesizer,
            OpenAIReportNarrator,
            load_prompt,
        )

        pd.set_option("display.max_columns", 220)
        pd.set_option("display.max_colwidth", 180)
        pd.set_option("display.float_format", lambda value: f"{value:,.6f}")
        alt.data_transformers.disable_max_rows()

        ROOT = Path.cwd()
        if not (ROOT / "src_2").exists():
            raise RuntimeError("Run this notebook from the Team2-MarketingExpert repository root.")

        load_dotenv(ROOT / ".env")
        INPUT = ROOT / "src_2" / "data" / "input" / "sampe_2"
        SIGNALS = ROOT / "src_2" / "artifacts" / "conversation_signals.jsonl"
        LLM_CACHE = ROOT / "outputs" / "experimental_learning_llm"
        """
    ),
    markdown(
        """
        ## 2. Establish The Data Boundary

        **Why needed:** before calculating a rate, we must know the grain and whether the
        supplied WhatsApp outcomes represent the Meta-attributed population.

        Organic/direct conversations remain available as context but do not enter paid
        campaign scoring. The `0.53%` population ratio is a reconciliation warning; it is
        different from semantic coverage inside Post-Eid.
        """
    ),
    code(
        """
        canonical = normalize_cycle(load_sample2(INPUT))
        quality = build_data_quality_report(canonical)
        signal_records = load_conversation_signal_records(SIGNALS) if SIGNALS.exists() else []

        objective_meanings = {
            "OUTCOME_AWARENESS": "Meta optimizes delivery for visibility and awareness.",
            "OUTCOME_ENGAGEMENT": "Meta optimizes delivery for interactions and engagement.",
            "OUTCOME_LEADS": "Meta optimizes delivery for leads or conversations.",
            "OUTCOME_SALES": "Meta optimizes delivery for purchase-related outcomes.",
        }
        campaign_objective_rows = canonical.campaigns[
            ["objective", "campaign_name", "campaign_type"]
        ].copy()
        campaign_objective_rows["campaign_label"] = (
            campaign_objective_rows["campaign_name"]
            + " [" + campaign_objective_rows["campaign_type"].str.replace("_", " ").str.title() + "]"
        )
        objective_campaign_map = campaign_objective_rows.groupby(
            "objective", as_index=False
        ).agg(
            campaign_count=("campaign_name", "nunique"),
            campaigns=("campaign_label", lambda values: "\\n".join(sorted(values))),
        )
        objective_campaign_map["objective_meaning"] = objective_campaign_map[
            "objective"
        ].map(objective_meanings)
        objective_campaign_map = objective_campaign_map[
            ["objective", "objective_meaning", "campaign_count", "campaigns"]
        ].rename(columns={
            "objective": "Meta objective",
            "objective_meaning": "What Meta optimizes for",
            "campaign_count": "Campaign count",
            "campaigns": "Campaigns [campaign type]",
        })

        display(Markdown("### Campaigns Grouped By Meta Objective"))
        display(objective_campaign_map.style.set_properties(
            subset=["Campaigns [campaign type]"],
            **{"white-space": "pre-wrap", "text-align": "left"},
        ).set_properties(
            subset=["What Meta optimizes for"],
            **{"white-space": "normal", "text-align": "left"},
        ))

        inventory = pd.DataFrame({
            "canonical table": [
                "campaigns", "adsets", "ads", "creatives",
                "daily Meta rows", "all WhatsApp conversations",
            ],
            "rows": [
                len(canonical.campaigns), len(canonical.adsets), len(canonical.ads),
                len(canonical.creatives), len(canonical.media_daily),
                len(canonical.conversations),
            ],
            "grain": [
                "one campaign", "one adset", "one ad", "one creative",
                "one ad-day", "one conversation",
            ],
        })
        display(inventory)

        quality_ledger = pd.DataFrame([
            ["Meta-attributed conversation starts", quality.meta_conversation_starts],
            ["Supplied Meta-sourced WhatsApp conversations", quality.observed_meta_whatsapp_conversations],
            ["Observed / Meta ratio", quality.reconciliation_ratio],
            ["Organic/direct conversations kept for context", quality.organic_direct_conversations],
            ["Open or pending outcomes", quality.open_or_pending_conversations],
            ["Repeated customers in cycle", quality.repeated_customers],
            ["Rows where reach exceeds impressions", quality.reach_exceeds_impressions_rows],
        ], columns=["quality fact", "raw value"])
        display(quality_ledger)
        print(f"Population reconciliation ratio = {quality.observed_meta_whatsapp_conversations:,} / "
              f"{quality.meta_conversation_starts:,} = {quality.reconciliation_ratio:.2%}")
        """
    ),
    markdown(
        """
        ## 3. Select One Campaign Type And Its Business Contract

        The **objective KPI** and the **statistical funding score** are related but not the
        same thing:

        - Objective KPI: did the experiment generate enough useful evidence?
        - Funding score: did mature conversations progress to a created order?

        `order_creation_rate` is a POC decision assumption. It is useful because it is a
        binary WhatsApp business outcome available at every hierarchy level, but it does
        not mean the order was delivered or profitable. Delivery, cancellation, refund,
        and revenue remain visible as supporting evidence and guardrails.
        """
    ),
    code(
        """
        registry = load_campaign_type_registry()
        policy = load_budget_policy()
        experimental_config = registry.campaign_types[CampaignType.EXPERIMENTAL]
        score_spec = experimental_config.score_metric

        contract = pd.DataFrame([
            ["Business job", experimental_config.business_job],
            ["Success question", experimental_config.success_question],
            ["Objective KPI", ", ".join(experimental_config.primary_kpis)],
            ["Funding score", score_spec.metric],
            ["Funding numerator", score_spec.numerator],
            ["Funding denominator", score_spec.denominator],
            ["Better direction", score_spec.direction],
            ["POC practical lift threshold", score_spec.practical_lift_threshold],
        ], columns=["contract element", "configured value"])
        display(contract)

        experimental_campaigns = canonical.campaigns[
            canonical.campaigns["campaign_type"].eq("experimental")
        ][["campaign_id", "campaign_name", "objective", "start_date", "end_date"]]
        display(experimental_campaigns)
        """
    ),
    markdown(
        """
        ## 4. Build Scorecards, But Do Not Hide The Raw Evidence

        The production scorecards are created now. The following sections reconstruct the
        Post-Eid values directly from conversation rows before reading the final score.
        """
    ),
    code(
        """
        raw_scorecards = build_scorecards(canonical, signal_records)
        scored = add_empirical_bayes_scores(raw_scorecards, registry)

        POST_EID_NAME = "Post-Eid Lookalike Test"
        post_campaign = experimental_campaigns.loc[
            experimental_campaigns["campaign_name"].eq(POST_EID_NAME)
        ].iloc[0]
        post_id = str(post_campaign["campaign_id"])
        post_score = scored.campaign.loc[
            scored.campaign["campaign_id"].eq(post_id)
        ].iloc[0]

        post_conversations = canonical.conversations.loc[
            canonical.conversations["campaign_id"].eq(post_id)
        ].copy()
        raw_columns = [
            "conversation_id", "outcome_type", "is_mature_outcome",
            "is_open_or_pending", "has_mature_order", "is_delivered",
            "is_cancelled", "is_refunded", "is_negative",
        ]
        display(post_conversations[raw_columns].head(12))
        print(f"Post-Eid raw conversation rows: {len(post_conversations)}")
        """
    ),
    markdown(
        """
        ## 5. From Raw Outcomes To Eligible Evidence

        **Business question:** which conversations have had enough time to produce a final
        outcome?

        `active` and `stuck_pending` are unresolved, not failures. Removing them prevents
        the campaign from being punished for outcomes that are not finished.
        """
    ),
    code(
        """
        outcome_order = [
            "delivered", "cancelled", "refunded", "ghosted",
            "adversarial", "active", "stuck_pending",
        ]
        outcome_ledger = post_conversations.groupby("outcome_type", as_index=False).agg(
            conversations=("conversation_id", "nunique"),
            mature=("is_mature_outcome", "sum"),
            orders_created=("has_mature_order", "sum"),
            delivered=("is_delivered", "sum"),
        )
        outcome_ledger["sort"] = outcome_ledger["outcome_type"].map(
            {name: index for index, name in enumerate(outcome_order)}
        )
        outcome_ledger = outcome_ledger.sort_values("sort").drop(columns="sort")
        display(outcome_ledger)

        outcome_chart = alt.Chart(outcome_ledger).mark_bar().encode(
            x=alt.X("conversations:Q", title="Conversation rows"),
            y=alt.Y("outcome_type:N", title="Outcome", sort=outcome_order),
            color=alt.Color("outcome_type:N", legend=None, scale=alt.Scale(scheme="tableau10")),
            tooltip=["outcome_type", "conversations", "mature", "orders_created"],
        ).properties(height=250)
        outcome_chart
        """
    ),
    code(
        """
        observed = int(post_conversations["conversation_id"].nunique())
        unresolved = int(post_conversations["is_open_or_pending"].sum())
        mature = int(post_conversations["is_mature_outcome"].sum())
        successes = int(post_conversations["has_mature_order"].sum())
        failures = mature - successes

        maturity_ledger = pd.DataFrame([
            ["Observed conversations", observed, "raw unique conversation IDs"],
            ["Unresolved", unresolved, "active + stuck_pending"],
            ["Mature", mature, f"{observed} - {unresolved}"],
            ["Mature orders created", successes, "delivered + cancelled + refunded"],
            ["Mature without an order", failures, f"{mature} - {successes}"],
        ], columns=["evidence", "raw count", "calculation"])
        display(maturity_ledger)

        assert observed == 63
        assert unresolved == 11
        assert mature == 52
        assert successes == 38
        """
    ),
    markdown(
        """
        ## 6. Why The Maturity Filter Changes The Business Conclusion

        Without the maturity rule, all unresolved outcomes would silently enter the
        denominator as failures. The comparison below makes the contribution visible.
        """
    ),
    code(
        """
        naive_rate = successes / observed
        mature_raw_rate = successes / mature
        maturity_impact = mature_raw_rate - naive_rate

        maturity_comparison = pd.DataFrame([
            ["Incorrect: all observed rows", successes, observed, naive_rate],
            ["Correct: mature outcomes only", successes, mature, mature_raw_rate],
        ], columns=["method", "numerator", "denominator", "order creation rate"])
        display(maturity_comparison.style.format({"order creation rate": "{:.2%}"}))
        print(f"Excluding unresolved outcomes changes the rate by {maturity_impact:+.2%}.")
        """
    ),
    markdown(
        """
        ## 7. Separate Order Creation From Final Order Quality

        A cancelled or refunded outcome proves that an order was created, so it enters the
        experimental order-creation numerator. It does not count as a delivered order.
        This is why one score cannot tell the entire business story.
        """
    ),
    code(
        """
        delivered = int(post_conversations["is_delivered"].sum())
        cancelled = int(post_conversations["is_cancelled"].sum())
        refunded = int(post_conversations["is_refunded"].sum())

        outcome_quality = pd.DataFrame([
            ["Order creation rate", successes, mature, successes / mature,
             "Did a mature conversation progress to any order?"],
            ["Delivered outcome rate", delivered, mature, delivered / mature,
             "Did a mature conversation become a delivered order?"],
            ["Created-order delivery rate", delivered, successes, delivered / successes,
             "How many created orders were delivered?"],
            ["Cancellation rate", cancelled, mature, cancelled / mature,
             "How many mature conversations ended cancelled?"],
            ["Refund rate", refunded, mature, refunded / mature,
             "How many mature conversations ended refunded?"],
        ], columns=["metric", "numerator", "denominator", "result", "business question"])
        display(outcome_quality.style.format({"result": "{:.2%}"}))
        print(f"Order-created check: {delivered} delivered + {cancelled} cancelled + "
              f"{refunded} refunded = {successes}.")
        """
    ),
    markdown(
        """
        ## 8. Calculate The Raw Score And Its Wilson Interval

        The raw score answers: **what happened in the supplied mature sample?**

        A point estimate hides sampling uncertainty. The Wilson interval gives a stable
        raw-data range for a binomial proportion, including small samples. It is different
        from the Empirical-Bayes credible range calculated later.
        """
    ),
    code(
        """
        manual_raw = successes / mature
        pipeline_raw = float(post_score["raw_score"])

        z = 1.959963984540054
        z2 = z * z
        wilson_denominator = 1 + z2 / mature
        wilson_centre = (manual_raw + z2 / (2 * mature)) / wilson_denominator
        wilson_margin = (
            z * sqrt(manual_raw * (1 - manual_raw) / mature + z2 / (4 * mature**2))
            / wilson_denominator
        )
        manual_wilson_low = wilson_centre - wilson_margin
        manual_wilson_high = wilson_centre + wilson_margin

        raw_check = pd.DataFrame([
            ["Raw score", manual_raw, pipeline_raw, manual_raw - pipeline_raw],
            ["Raw Wilson low", manual_wilson_low, post_score["order_creation_rate_ci_low"],
             manual_wilson_low - post_score["order_creation_rate_ci_low"]],
            ["Raw Wilson high", manual_wilson_high, post_score["order_creation_rate_ci_high"],
             manual_wilson_high - post_score["order_creation_rate_ci_high"]],
        ], columns=["value", "manual", "pipeline", "difference"])
        display(raw_check.style.format({"manual": "{:.4%}", "pipeline": "{:.4%}", "difference": "{:+.8f}"}))

        assert abs(manual_raw - pipeline_raw) < 1e-12
        assert abs(manual_wilson_low - post_score["order_creation_rate_ci_low"]) < 1e-12
        assert abs(manual_wilson_high - post_score["order_creation_rate_ci_high"]) < 1e-12
        """
    ),
    markdown(
        """
        ## 9. Build The Compatible Peer Benchmark From Raw Counts

        **Why needed:** `73.08%` is an isolated number until we answer **compared with
        what?**

        Post-Eid has two other `OUTCOME_LEADS` campaigns with usable order-creation
        sufficient statistics. The benchmark is learned from their pooled counts; it is
        not an approved business target. The current entity is excluded from its own
        benchmark.
        """
    ),
    code(
        """
        peer_rows = raw_scorecards.campaign.loc[
            raw_scorecards.campaign["objective"].eq(post_score["objective"])
            & raw_scorecards.campaign["campaign_id"].ne(post_id)
        ].copy()
        peer_rows["peer_order_creation_rate"] = (
            peer_rows[score_spec.numerator] / peer_rows[score_spec.denominator]
        )
        peer_evidence = peer_rows[[
            "campaign_name", "campaign_type", "objective",
            score_spec.numerator, score_spec.denominator, "peer_order_creation_rate",
        ]]
        display(peer_evidence.style.format({"peer_order_creation_rate": "{:.2%}"}))

        peer_successes = float(peer_rows[score_spec.numerator].sum())
        peer_trials = float(peer_rows[score_spec.denominator].sum())
        peer_failures = peer_trials - peer_successes
        raw_peer_rate = peer_successes / peer_trials

        print(f"Pooled peer evidence = {peer_successes:.0f} successes + "
              f"{peer_failures:.0f} failures = {peer_trials:.0f} trials")
        print(f"Raw pooled peer rate = {peer_successes:.0f} / {peer_trials:.0f} "
              f"= {raw_peer_rate:.2%}")
        """
    ),
    markdown(
        """
        ## 10. Explain The `+0.5` And `+1` Instead Of Hiding Them

        The engine uses a **Jeffreys-style symmetric half-count safeguard**:

        ```text
        add 0.5 equivalent success
        add 0.5 equivalent failure
        total added evidence = 1
        ```

        It prevents a peer rate from becoming exactly `0%` or `100%`, which would imply
        false certainty. These are not observed conversations. The adjustment is shown
        separately so its effect can be audited.
        """
    ),
    code(
        """
        adjusted_peer_successes = peer_successes + 0.5
        adjusted_peer_failures = peer_failures + 0.5
        adjusted_peer_trials = peer_trials + 1.0
        adjusted_peer_mean = adjusted_peer_successes / adjusted_peer_trials

        smoothing_ledger = pd.DataFrame([
            ["Observed peer successes", peer_successes, 0.5, adjusted_peer_successes],
            ["Observed peer failures", peer_failures, 0.5, adjusted_peer_failures],
            ["Total peer trials", peer_trials, 1.0, adjusted_peer_trials],
        ], columns=["quantity", "observed", "safeguard added", "adjusted"])
        display(smoothing_ledger)

        smoothing_comparison = pd.DataFrame([
            ["Raw pooled peer rate", peer_successes, peer_trials, raw_peer_rate],
            ["Half-count adjusted peer rate", adjusted_peer_successes,
             adjusted_peer_trials, adjusted_peer_mean],
        ], columns=["benchmark version", "success evidence", "total evidence", "rate"])
        display(smoothing_comparison.style.format({"rate": "{:.4%}"}))
        print(f"Smoothing changes the benchmark by {adjusted_peer_mean - raw_peer_rate:+.4%}.")
        """
    ),
    markdown(
        """
        ## 11. Convert The Benchmark Into An Empirical Prior

        A benchmark rate alone does not specify how strongly it should influence the
        campaign. The prior strength is no larger than the average peer sample and is
        reduced when peers disagree strongly.

        The prior counts are **equivalent statistical evidence**, not extra WhatsApp
        rows. Small campaigns are pulled more toward this typical value; large campaigns
        are controlled mostly by their own evidence.
        """
    ),
    code(
        """
        peer_rates = peer_rows["peer_order_creation_rate"].tolist()
        peer_rate_variance = variance(peer_rates) if len(peer_rates) > 1 else 0.0
        average_peer_trials = peer_trials / len(peer_rows)
        implied_strength = (
            adjusted_peer_mean * (1 - adjusted_peer_mean) / peer_rate_variance - 1
            if peer_rate_variance > 0 else float("inf")
        )
        manual_prior_strength = max(min(average_peer_trials, implied_strength), 1.0)
        manual_prior_alpha = adjusted_peer_mean * manual_prior_strength
        manual_prior_beta = (1 - adjusted_peer_mean) * manual_prior_strength

        prior_ledger = pd.DataFrame([
            ["Adjusted peer mean", adjusted_peer_mean, post_score["benchmark_score"]],
            ["Average peer trials", average_peer_trials, None],
            ["Strength implied by peer disagreement", implied_strength, None],
            ["Prior strength used", manual_prior_strength, post_score["prior_strength"]],
            ["Prior equivalent successes (alpha)", manual_prior_alpha, post_score["prior_alpha"]],
            ["Prior equivalent failures (beta)", manual_prior_beta, post_score["prior_beta"]],
        ], columns=["prior component", "manual", "pipeline where applicable"])
        display(prior_ledger)

        assert abs(manual_prior_alpha - post_score["prior_alpha"]) < 1e-12
        assert abs(manual_prior_beta - post_score["prior_beta"]) < 1e-12
        """
    ),
    markdown(
        """
        ## 12. Calculate The Empirical-Bayes Corrected Score

        **Contribution:** this step controls small-sample overreaction. It combines the
        campaign's real observations with the compatible peer prior while preserving the
        raw score beside it.
        """
    ),
    code(
        """
        posterior_alpha = manual_prior_alpha + successes
        posterior_beta = manual_prior_beta + failures
        posterior_strength = posterior_alpha + posterior_beta
        manual_corrected = posterior_alpha / posterior_strength

        eb_ledger = pd.DataFrame([
            ["Peer prior", manual_prior_alpha, manual_prior_beta,
             manual_prior_strength, adjusted_peer_mean],
            ["Observed Post-Eid", successes, failures, mature, manual_raw],
            ["Combined posterior", posterior_alpha, posterior_beta,
             posterior_strength, manual_corrected],
        ], columns=["stage", "success evidence", "failure evidence", "total evidence", "rate"])
        display(eb_ledger.style.format({"rate": "{:.4%}"}))

        correction_check = pd.DataFrame([
            ["Raw campaign score", manual_raw],
            ["Peer benchmark", adjusted_peer_mean],
            ["Corrected campaign score", manual_corrected],
            ["Pipeline corrected score", post_score["corrected_score"]],
            ["Correction applied", manual_corrected - manual_raw],
        ], columns=["quantity", "value"])
        display(correction_check.style.format({"value": "{:+.4%}"}))

        assert abs(manual_corrected - post_score["corrected_score"]) < 1e-12
        """
    ),
    markdown(
        """
        ## 13. Sensitivity: What If We Removed The Half-Count?

        A modeling safeguard should never be hidden. This sensitivity check quantifies
        whether it materially changes the score or decision for Post-Eid.
        """
    ),
    code(
        """
        raw_implied_strength = (
            raw_peer_rate * (1 - raw_peer_rate) / peer_rate_variance - 1
            if peer_rate_variance > 0 else float("inf")
        )
        no_smoothing_strength = max(min(average_peer_trials, raw_implied_strength), 1.0)
        no_smoothing_alpha = raw_peer_rate * no_smoothing_strength
        no_smoothing_beta = (1 - raw_peer_rate) * no_smoothing_strength
        corrected_without_smoothing = (
            no_smoothing_alpha + successes
        ) / (no_smoothing_strength + mature)

        sensitivity = pd.DataFrame([
            ["No half-count", raw_peer_rate, corrected_without_smoothing],
            ["Current half-count", adjusted_peer_mean, manual_corrected],
        ], columns=["method", "benchmark", "corrected score"])
        display(sensitivity.style.format({"benchmark": "{:.4%}", "corrected score": "{:.4%}"}))
        print(f"Corrected-score difference = "
              f"{manual_corrected - corrected_without_smoothing:+.4%}.")
        """
    ),
    markdown(
        """
        ## 14. Calculate The Credible Range, Lift, And Probability Better

        The point estimate is not enough for a funding decision.

        1. Draw 5,000 plausible campaign rates from the posterior.
        2. Draw 5,000 plausible benchmark rates from the prior.
        3. Subtract benchmark from campaign for every pair.
        4. Summarize the distribution of those 5,000 lift values.

        The simulation uses a stable entity-specific seed, so this notebook reproduces
        the production values exactly.
        """
    ),
    code(
        """
        def quantile(values, probability):
            ordered = sorted(values)
            position = (len(ordered) - 1) * probability
            lower = int(position)
            upper = min(lower + 1, len(ordered) - 1)
            fraction = position - lower
            return ordered[lower] * (1 - fraction) + ordered[upper] * fraction

        seed_bytes = hashlib.sha256(
            f"campaign|{post_score['entity_id']}|{score_spec.metric}".encode("utf-8")
        ).digest()
        simulation_seed = int.from_bytes(seed_bytes[:8], "big")
        rng = Random(simulation_seed)
        simulation_count = 5000
        campaign_draws = [
            rng.betavariate(posterior_alpha, posterior_beta)
            for _ in range(simulation_count)
        ]
        benchmark_draws = [
            rng.betavariate(manual_prior_alpha, manual_prior_beta)
            for _ in range(simulation_count)
        ]
        lift_draws = [
            campaign_value - benchmark_value
            for campaign_value, benchmark_value in zip(campaign_draws, benchmark_draws)
        ]

        manual_corrected_low = quantile(campaign_draws, 0.025)
        manual_corrected_high = quantile(campaign_draws, 0.975)
        manual_benchmark_low = quantile(benchmark_draws, 0.025)
        manual_benchmark_high = quantile(benchmark_draws, 0.975)
        manual_expected_lift = sum(lift_draws) / simulation_count
        manual_lift_low = quantile(lift_draws, 0.025)
        manual_lift_high = quantile(lift_draws, 0.975)
        positive_lifts = sum(value > 0 for value in lift_draws)
        manual_probability_better = positive_lifts / simulation_count

        simulation_check = pd.DataFrame([
            ["Corrected score low", manual_corrected_low, post_score["corrected_score_low"]],
            ["Corrected score high", manual_corrected_high, post_score["corrected_score_high"]],
            ["Benchmark low", manual_benchmark_low, post_score["benchmark_low"]],
            ["Benchmark high", manual_benchmark_high, post_score["benchmark_high"]],
            ["Expected favorable lift", manual_expected_lift, post_score["expected_lift"]],
            ["Lift low", manual_lift_low, post_score["lift_low"]],
            ["Lift high", manual_lift_high, post_score["lift_high"]],
            ["Probability better", manual_probability_better, post_score["probability_better"]],
        ], columns=["quantity", "manual", "pipeline"])
        display(simulation_check.style.format({"manual": "{:+.4%}", "pipeline": "{:+.4%}"}))
        print(f"Positive lift draws = {positive_lifts:,} / {simulation_count:,} "
              f"= {manual_probability_better:.2%}")

        for _, item in simulation_check.iterrows():
            assert abs(item["manual"] - item["pipeline"]) < 1e-12
        """
    ),
    code(
        """
        interval_data = pd.DataFrame([
            ["Raw Wilson", manual_raw, manual_wilson_low, manual_wilson_high],
            ["EB corrected", manual_corrected, manual_corrected_low, manual_corrected_high],
            ["Peer benchmark", adjusted_peer_mean, manual_benchmark_low, manual_benchmark_high],
        ], columns=["estimate", "point", "low", "high"])

        interval_rules = alt.Chart(interval_data).mark_rule(strokeWidth=5).encode(
            x=alt.X("low:Q", title="Rate", axis=alt.Axis(format=".0%"), scale=alt.Scale(domain=[0.45, 1.0])),
            x2="high:Q",
            y=alt.Y("estimate:N", title=None, sort=["Raw Wilson", "EB corrected", "Peer benchmark"]),
            color=alt.Color("estimate:N", legend=None, scale=alt.Scale(scheme="tableau10")),
            tooltip=["estimate", alt.Tooltip("low:Q", format=".2%"),
                     alt.Tooltip("point:Q", format=".2%"), alt.Tooltip("high:Q", format=".2%")],
        )
        interval_points = alt.Chart(interval_data).mark_point(filled=True, size=110).encode(
            x="point:Q", y=alt.Y("estimate:N", sort=["Raw Wilson", "EB corrected", "Peer benchmark"]),
            color=alt.Color("estimate:N", legend=None, scale=alt.Scale(scheme="tableau10")),
        )
        (interval_rules + interval_points).properties(height=180)
        """
    ),
    code(
        """
        lift_frame = pd.DataFrame({"favorable_lift": lift_draws})
        lift_histogram = alt.Chart(lift_frame).mark_bar(color="#3D8DFF", opacity=0.8).encode(
            x=alt.X("favorable_lift:Q", bin=alt.Bin(maxbins=55), title="Campaign rate - benchmark rate", axis=alt.Axis(format="+.0%")),
            y=alt.Y("count():Q", title="Simulation draws"),
            tooltip=[alt.Tooltip("favorable_lift:Q", bin=True, format="+.2%"), "count():Q"],
        )
        zero_line = alt.Chart(pd.DataFrame({"zero": [0]})).mark_rule(
            color="#C94C4C", strokeWidth=3
        ).encode(x="zero:Q")
        (lift_histogram + zero_line).properties(height=280)
        """
    ),
    markdown(
        """
        ## 15. Turn The Lift Range Into A Decision

        ```text
        SCALE: the complete favorable-lift range is above zero
        KILL:  the complete favorable-lift range is below zero
        HOLD:  the range includes zero
        ```

        `probability_better` is supporting evidence, not the decision rule. For example,
        `43.54% probability better` does not mean `43.54% performance improvement`.
        """
    ),
    code(
        """
        threshold = score_spec.practical_lift_threshold
        if manual_lift_low > threshold:
            manual_decision = "scale"
        elif manual_lift_high < -threshold:
            manual_decision = "kill"
        else:
            manual_decision = "hold"

        decision_ledger = pd.DataFrame([
            ["Expected favorable lift", manual_expected_lift],
            ["95% lift lower bound", manual_lift_low],
            ["95% lift upper bound", manual_lift_high],
            ["Probability better", manual_probability_better],
            ["Practical threshold", threshold],
        ], columns=["decision evidence", "value"])
        display(decision_ledger.style.format({"value": "{:+.2%}"}))
        print(f"The range [{manual_lift_low:+.2%}, {manual_lift_high:+.2%}] "
              f"crosses zero, so the manual decision is {manual_decision.upper()}.")
        print(f"Pipeline decision: {post_score['statistical_decision'].upper()}.")
        assert manual_decision == post_score["statistical_decision"]
        """
    ),
    markdown(
        """
        ## 16. Compare Both Experimental Campaigns

        January has only 15 mature observations, so peer evidence contributes more to its
        corrected score. Post-Eid has 52 mature observations, so its own evidence carries
        more weight. Neither lift range supports a decisive winner or loser.
        """
    ),
    code(
        """
        experimental_scores = scored.campaign.loc[
            scored.campaign["campaign_type"].eq("experimental")
        ].copy()
        experiment_columns = [
            "campaign_name", "observed_conversations", "open_or_pending_conversations",
            "score_successes", "score_trials", "raw_score", "benchmark_score",
            "corrected_score", "corrected_score_low", "corrected_score_high",
            "expected_lift", "lift_low", "lift_high", "probability_better",
            "statistical_decision", "benchmark_source",
        ]
        display(experimental_scores[experiment_columns].style.format({
            "raw_score": "{:.2%}", "benchmark_score": "{:.2%}",
            "corrected_score": "{:.2%}", "corrected_score_low": "{:.2%}",
            "corrected_score_high": "{:.2%}", "expected_lift": "{:+.2%}",
            "lift_low": "{:+.2%}", "lift_high": "{:+.2%}",
            "probability_better": "{:.2%}",
        }))
        """
    ),
    markdown(
        """
        ## 17. Apply The Same Evidence Contract To Adsets, Ads, Creatives, And Audience

        Child rows use the same raw, corrected, range, and lift logic. The intervals help
        limit the winner's curse when many entities are compared. This is conservative
        evidence handling, but it is not a formal false-discovery-rate correction; child
        rankings remain exploratory.
        """
    ),
    code(
        """
        child_frames = []
        for level in ("adset", "ad", "creative", "audience"):
            frame = scored.by_level(level)
            subset = frame.loc[frame["campaign_id"].eq(post_id)].copy()
            subset["level"] = level
            child_frames.append(subset)
        post_children = pd.concat(child_frames, ignore_index=True)

        child_columns = [
            "level", "entity_name", "score_successes", "score_trials", "raw_score",
            "corrected_score", "corrected_score_low", "corrected_score_high",
            "benchmark_score", "lift_low", "lift_high", "probability_better",
            "statistical_decision",
        ]
        display(post_children[child_columns].style.format({
            "raw_score": "{:.2%}", "corrected_score": "{:.2%}",
            "corrected_score_low": "{:.2%}", "corrected_score_high": "{:.2%}",
            "benchmark_score": "{:.2%}", "lift_low": "{:+.2%}",
            "lift_high": "{:+.2%}", "probability_better": "{:.2%}",
        }))

        forest = post_children.copy()
        forest["label"] = forest["level"].str.title() + ": " + forest["entity_name"]
        forest_rules = alt.Chart(forest).mark_rule(strokeWidth=4).encode(
            x=alt.X("corrected_score_low:Q", title="Corrected order-creation score", axis=alt.Axis(format=".0%")),
            x2="corrected_score_high:Q",
            y=alt.Y("label:N", title=None, sort="-x"),
            color=alt.Color("level:N", title="Level", scale=alt.Scale(scheme="tableau10")),
            tooltip=["level", "entity_name", alt.Tooltip("raw_score:Q", format=".2%"),
                     alt.Tooltip("corrected_score:Q", format=".2%"),
                     alt.Tooltip("lift_low:Q", format="+.2%"),
                     alt.Tooltip("lift_high:Q", format="+.2%")],
        )
        forest_points = alt.Chart(forest).mark_point(filled=True, size=90).encode(
            x="corrected_score:Q", y=alt.Y("label:N", sort="-x"),
            color=alt.Color("level:N", scale=alt.Scale(scheme="tableau10")),
        )
        (forest_rules + forest_points).properties(height=max(260, len(forest) * 34))
        """
    ),
    markdown(
        """
        ### Important Confounder

        The 5% audience used Creative A and the 10% audience used Creative B. Audience and
        creative changed together, so the observed difference cannot be attributed to one
        of them. The next design should cross both audiences with both creatives.

        | | Creative A | Creative B |
        |---|---|---|
        | 5% Lookalike | Test | Test |
        | 10% Lookalike | Test | Test |
        """
    ),
    markdown(
        """
        ## 18. Conversation Semantics: A Separate Diagnostic Layer

        The semantic LLM sees redacted messages, not outcomes, revenue, campaign success,
        or budget. Its validated records are joined back to deterministic attribution and
        outcome facts afterward.

        ```text
        Statistical scorecard -> what happened and how certain are we?
        Conversation semantics -> what needs, intent, and barriers may explain it?
        ```

        Semantics does not override the funding decision. It contributes an explanation
        and a testable hypothesis.
        """
    ),
    code(
        """
        post_signal_records = [
            record for record in signal_records
            if record.attribution.campaign_id == post_id
        ]
        semantic_rows = []
        for record in post_signal_records:
            signals = record.signals
            semantic_rows.append({
                "conversation_id": record.conversation_id,
                "schema_version": record.signal_schema_version,
                "purpose": signals.conversation_purpose.value,
                "purchase_intent": signals.purchase_intent.level.value,
                "purchase_intent_evidence_indexes": signals.purchase_intent.evidence_message_indexes,
                "barrier_present": bool(signals.barriers),
                "barriers": [item.barrier_type.value for item in signals.barriers],
                "barrier_evidence_indexes": sorted({
                    index for item in signals.barriers for index in item.evidence_message_indexes
                }),
                "agent_helpful": signals.agent_evaluation.helpfulness.value in {"good", "strong"},
            })
        semantic_raw = pd.DataFrame(semantic_rows)

        print(f"Validated Post-Eid semantic records: {len(semantic_raw)}")
        print(f"Schema versions present: {sorted(semantic_raw['schema_version'].unique()) if not semantic_raw.empty else []}")
        display(semantic_raw.head(12))
        """
    ),
    markdown(
        """
        ## 19. Calculate Semantic Aggregates From Raw Classifications

        Semantic coverage here is `validated semantic records / supplied Post-Eid
        conversations`. It is not the account-level `617 / 116,098` reconciliation ratio.
        """
    ),
    code(
        """
        semantic_count = int(semantic_raw["conversation_id"].nunique())
        high_intent_count = int(semantic_raw["purchase_intent"].eq("high").sum())
        barrier_count = int(semantic_raw["barrier_present"].sum())
        helpful_count = int(semantic_raw["agent_helpful"].sum())

        semantic_ledger = pd.DataFrame([
            ["Semantic coverage", semantic_count, observed, semantic_count / observed],
            ["High purchase intent", high_intent_count, semantic_count, high_intent_count / semantic_count],
            ["Barrier present", barrier_count, semantic_count, barrier_count / semantic_count],
            ["Helpful agent", helpful_count, semantic_count, helpful_count / semantic_count],
        ], columns=["semantic metric", "numerator", "denominator", "rate"])
        display(semantic_ledger.style.format({"rate": "{:.2%}"}))

        pipeline_semantic = pd.DataFrame([
            ["High purchase intent", high_intent_count / semantic_count, post_score["high_purchase_intent_rate"]],
            ["Barrier present", barrier_count / semantic_count, post_score["barrier_conversation_rate"]],
            ["Helpful agent", helpful_count / semantic_count, post_score["agent_helpful_rate"]],
            ["Semantic coverage", semantic_count / observed, post_score["semantic_coverage_rate"]],
        ], columns=["metric", "manual", "pipeline"])
        display(pipeline_semantic.style.format({"manual": "{:.2%}", "pipeline": "{:.2%}"}))
        assert all(abs(row.manual - row.pipeline) < 1e-12 for row in pipeline_semantic.itertuples())

        intent_counts = semantic_raw.groupby("purchase_intent", as_index=False).agg(
            conversations=("conversation_id", "nunique")
        ).sort_values("conversations", ascending=False)
        display(intent_counts)
        """
    ),
    markdown(
        """
        ## 20. Join Semantics To Mature Outcomes Without Mixing Their Roles

        This join is diagnostic. It can reveal associations, but it does not prove that a
        semantic label caused an order. `high` purchase intent may describe behavior close
        to checkout, so it should not be mistaken for a pre-campaign causal feature.

        Unknown and unresolved outcomes remain visible rather than silently becoming
        failures.
        """
    ),
    code(
        """
        semantic_outcomes = semantic_raw.merge(
            post_conversations[[
                "conversation_id", "adset_id", "ad_id", "creative_id",
                "is_mature_outcome", "has_mature_order", "is_open_or_pending",
            ]],
            on="conversation_id",
            how="left",
            validate="one_to_one",
        )

        intent_outcome = semantic_outcomes.groupby("purchase_intent", as_index=False).agg(
            all_conversations=("conversation_id", "nunique"),
            mature_conversations=("is_mature_outcome", "sum"),
            mature_orders=("has_mature_order", "sum"),
        )
        intent_outcome["mature_order_rate"] = (
            intent_outcome["mature_orders"] / intent_outcome["mature_conversations"]
        )
        display(intent_outcome.style.format({"mature_order_rate": "{:.2%}"}))

        barrier_outcome = semantic_outcomes.groupby("barrier_present", as_index=False).agg(
            all_conversations=("conversation_id", "nunique"),
            mature_conversations=("is_mature_outcome", "sum"),
            mature_orders=("has_mature_order", "sum"),
        )
        barrier_outcome["mature_order_rate"] = (
            barrier_outcome["mature_orders"] / barrier_outcome["mature_conversations"]
        )
        display(barrier_outcome.style.format({"mature_order_rate": "{:.2%}"}))
        """
    ),
    markdown(
        """
        ## 21. Compare Semantic Evidence By Adset And Creative Combination

        The raw counts come first. Rates are calculated only after the numerator and
        denominator are visible.
        """
    ),
    code(
        """
        adset_names = canonical.adsets.set_index("adset_id")["adset_name"].to_dict()
        semantic_by_adset = semantic_outcomes.groupby("adset_id", as_index=False).agg(
            semantic_conversations=("conversation_id", "nunique"),
            mature_conversations=("is_mature_outcome", "sum"),
            mature_orders=("has_mature_order", "sum"),
            high_intent=("purchase_intent", lambda values: values.eq("high").sum()),
            barrier_conversations=("barrier_present", "sum"),
            helpful_conversations=("agent_helpful", "sum"),
        )
        semantic_by_adset["adset_name"] = semantic_by_adset["adset_id"].map(adset_names)
        semantic_by_adset["mature_order_rate"] = (
            semantic_by_adset["mature_orders"] / semantic_by_adset["mature_conversations"]
        )
        semantic_by_adset["high_intent_rate"] = (
            semantic_by_adset["high_intent"] / semantic_by_adset["semantic_conversations"]
        )
        semantic_by_adset["barrier_rate"] = (
            semantic_by_adset["barrier_conversations"] / semantic_by_adset["semantic_conversations"]
        )
        semantic_by_adset["helpful_rate"] = (
            semantic_by_adset["helpful_conversations"] / semantic_by_adset["semantic_conversations"]
        )
        display(semantic_by_adset[[
            "adset_name", "semantic_conversations", "mature_conversations", "mature_orders",
            "high_intent", "barrier_conversations", "helpful_conversations",
            "mature_order_rate", "high_intent_rate", "barrier_rate", "helpful_rate",
        ]].style.format({
            "mature_order_rate": "{:.2%}", "high_intent_rate": "{:.2%}",
            "barrier_rate": "{:.2%}", "helpful_rate": "{:.2%}",
        }))
        """
    ),
    markdown(
        """
        ### What Semantics Contributes

        - The statistical score says the 5%/Creative A combination is more promising but
          still uncertain.
        - Semantic counts show more high-intent conversations in that combination and a
          different barrier pattern.
        - Together they justify a controlled follow-up test.
        - They do **not** prove whether audience or creative caused the difference.

        Current records are V1. New V2 fields such as urgency, barrier resolution, and
        ad-message match remain unknown until the governed extraction is deliberately
        rerun. The notebook does not present missing V2 fields as observed evidence.
        """
    ),
    markdown(
        """
        ## 22. Build The Exact Deterministic Handoff To The LLM

        The `CampaignEvidencePack` is the boundary between the data/statistics half and
        the interpretation half. It contains objective KPIs, score details, child entities,
        semantic aggregates, guardrails, and limitations. It contains no raw customer PII.
        """
    ),
    code(
        """
        cycle_id = f"cycle_{canonical.cycle_start.date()}_{canonical.cycle_end.date()}"
        evidence_packs = build_evidence_packs(cycle_id, scored, registry, quality)
        experimental_packs = [
            pack for pack in evidence_packs
            if pack.campaign_type is CampaignType.EXPERIMENTAL
        ]
        assessor = DeterministicCampaignAssessor()
        experimental_assessments = [
            assessor.assess(pack, experimental_config)
            for pack in experimental_packs
        ]
        post_pack = next(pack for pack in experimental_packs if pack.campaign_id == post_id)
        post_assessment = next(
            item for item in experimental_assessments if item.campaign_id == post_id
        )

        handoff_summary = {
            "campaign": post_pack.campaign_name,
            "campaign_type": post_pack.campaign_type.value,
            "business_job": post_pack.business_job,
            "success_question": post_pack.success_question,
            "evidence_status": post_pack.evidence_status.value,
            "decision_score": post_pack.decision_score.model_dump(mode="json"),
            "deterministic_assessment": post_assessment.model_dump(mode="json"),
            "child_counts": {
                "adsets": len(post_pack.adsets),
                "ads": len(post_pack.ads),
                "creatives": len(post_pack.creatives),
                "audiences": len(post_pack.audiences),
            },
            "limitations": post_pack.limitations,
        }
        display(JSON(handoff_summary, expanded=True))
        """
    ),
    markdown(
        """
        ## 23. Calculate The Experimental-Type Budget Scenario Before Narration

        This is a **type-scoped learning scenario**, not the full production portfolio.
        The allocator remains deterministic:

        - 70 units exploit only statistically supported `SCALE` decisions.
        - 30 units explore named tests for eligible `HOLD` decisions.
        - Unsupported units stay unallocated.
        - The LLM receives this scenario after the numbers are locked.
        """
    ),
    code(
        """
        experimental_campaign_scorecard = scored.campaign.loc[
            scored.campaign["campaign_type"].eq("experimental")
        ].copy()
        type_budget = DeterministicBudgetAllocator().allocate(
            cycle_id,
            experimental_campaign_scorecard,
            experimental_assessments,
            registry,
            policy,
            quality,
        )

        budget_allocations = pd.DataFrame([
            item.model_dump(mode="json") for item in type_budget.allocations
        ])
        exploration_tests = pd.DataFrame([
            item.model_dump(mode="json") for item in type_budget.exploration_tests
        ])
        display(budget_allocations)
        display(exploration_tests)
        print(f"Assigned units = {budget_allocations['budget_units'].sum():.2f}")
        print(f"Unallocated units = {type_budget.unallocated_units:.2f}")
        print(f"Operational = {type_budget.operational}")
        """
    ),
    markdown(
        """
        ## 24. LLM Safety Boundary And Execution Controls

        Four structured calls are available:

        1. Campaign analyst for January.
        2. Campaign analyst for Post-Eid.
        3. Experimental campaign-type synthesis.
        4. Stakeholder recommendation narrator.

        The default is `RUN_LLM = False`, so a full notebook execution makes no paid API
        calls. Review the displayed evidence and then deliberately change it to `True`.
        Validated outputs are cached by model, prompt hash, and input hash.
        """
    ),
    code(
        """
        RUN_LLM = False
        FORCE_LLM_RERUN = False
        MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")

        prompt_rows = []
        for prompt_name in (
            "campaign_analysis", "portfolio_synthesis", "recommendation_narrator"
        ):
            prompt_text = load_prompt(prompt_name)
            prompt_rows.append({
                "prompt": prompt_name,
                "sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
                "characters": len(prompt_text),
            })
        display(pd.DataFrame(prompt_rows))
        print(f"RUN_LLM = {RUN_LLM}")
        print(f"Model = {MODEL}")
        """
    ),
    markdown(
        """
        ## 25. Preview The Exact Campaign-Analysis Payload

        This is the full structured input, not a hand-written summary. Conversation text
        is absent; only aggregated diagnostic evidence is present.
        """
    ),
    code(
        """
        campaign_payload = post_pack.model_dump(mode="json")
        serialized_campaign_payload = json.dumps(
            campaign_payload, sort_keys=True, ensure_ascii=True, default=str
        )
        print(f"Payload characters: {len(serialized_campaign_payload):,}")
        print(f"Payload SHA256: {hashlib.sha256(serialized_campaign_payload.encode('utf-8')).hexdigest()}")
        display(JSON(campaign_payload, expanded=False))
        """
    ),
    markdown(
        """
        ## 26. Run And Cache The Two Campaign Analysts

        `CampaignInsight` is a strict Pydantic output. It can explain target achievement,
        drivers, audience/creative findings, confounders, strategic lessons, and the next
        controlled test. It has no budget field and cannot replace the deterministic
        action.
        """
    ),
    code(
        """
        def stable_json(value):
            return json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)

        def cache_path(stage, prompt_name, payload):
            prompt_sha = hashlib.sha256(load_prompt(prompt_name).encode("utf-8")).hexdigest()
            input_sha = hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()
            key = hashlib.sha256(f"{MODEL}|{prompt_sha}|{input_sha}".encode("utf-8")).hexdigest()[:20]
            return LLM_CACHE / f"{stage}_{key}.json", prompt_sha, input_sha

        def save_cache(path, prompt_sha, input_sha, output):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(stable_json({
                "model": MODEL,
                "prompt_sha256": prompt_sha,
                "input_sha256": input_sha,
                "output": output,
            }), encoding="utf-8")

        campaign_insights = []
        campaign_cache_audit = []
        if RUN_LLM:
            analyst = OpenAICampaignAnalyst(model=MODEL)
            for pack in experimental_packs:
                payload = pack.model_dump(mode="json")
                path, prompt_sha, input_sha = cache_path(
                    f"campaign_{pack.campaign_id}", "campaign_analysis", payload
                )
                if path.exists() and not FORCE_LLM_RERUN:
                    cached = json.loads(path.read_text(encoding="utf-8"))
                    insight = CampaignInsight.model_validate(cached["output"])
                    source = "cache"
                else:
                    insight = analyst.analyze(pack)
                    save_cache(path, prompt_sha, input_sha, insight.model_dump(mode="json"))
                    source = "OpenAI"
                campaign_insights.append(insight)
                campaign_cache_audit.append({
                    "campaign": pack.campaign_name,
                    "source": source,
                    "cache": str(path.relative_to(ROOT)),
                    "input_sha256": input_sha,
                    "prompt_sha256": prompt_sha,
                })
            display(pd.DataFrame(campaign_cache_audit))
            display(JSON([item.model_dump(mode="json") for item in campaign_insights], expanded=True))
        else:
            print("Campaign LLM calls skipped. Set RUN_LLM = True and rerun from this cell.")
        """
    ),
    markdown(
        """
        ## 27. Grounding Audit For Campaign LLM Outputs

        Pydantic validates the shape. This cell additionally checks that campaign IDs and
        quantitative evidence references exist and that referenced values match the
        deterministic evidence.
        """
    ),
    code(
        """
        def evidence_lookup(pack):
            entities = [pack.campaign, *pack.adsets, *pack.ads, *pack.creatives, *pack.audiences]
            lookup = {}
            for entity in entities:
                for metric in entity.metrics:
                    lookup[(entity.entity_level.value, entity.entity_id, metric.metric)] = (
                        metric.actual, metric.benchmark
                    )
                if entity.decision_score is not None:
                    score = entity.decision_score
                    prefix = (entity.entity_level.value, entity.entity_id)
                    lookup[(*prefix, score.metric)] = (
                        score.corrected_score, score.benchmark_score
                    )
                    lookup[(*prefix, "raw_score")] = (
                        score.raw_score, score.benchmark_score
                    )
                    lookup[(*prefix, "corrected_score")] = (
                        score.corrected_score, score.benchmark_score
                    )
                    lookup[(*prefix, "expected_lift")] = (
                        score.expected_lift, 0.0
                    )
                    lookup[(*prefix, "lift_low")] = (score.lift_low, 0.0)
                    lookup[(*prefix, "lift_high")] = (score.lift_high, 0.0)
                    lookup[(*prefix, "probability_better")] = (
                        score.probability_better, 0.5
                    )
            return lookup

        grounding_rows = []
        pack_by_id = {pack.campaign_id: pack for pack in experimental_packs}
        for insight in campaign_insights:
            pack = pack_by_id.get(insight.campaign_id)
            lookup = evidence_lookup(pack) if pack else {}
            if not insight.supporting_evidence:
                grounding_rows.append({
                    "campaign_id": insight.campaign_id,
                    "reference": "no quantitative references returned",
                    "exists": False,
                    "value_matches": False,
                })
            for reference in insight.supporting_evidence:
                key = (reference.entity_level.value, reference.entity_id, reference.metric)
                expected = lookup.get(key)
                actual = expected[0] if expected is not None else None
                benchmark = expected[1] if expected is not None else None
                value_matches = (
                    actual is None and reference.actual is None
                    or actual is not None and reference.actual is not None
                    and abs(actual - reference.actual) < 1e-9
                )
                benchmark_matches = (
                    reference.benchmark is None
                    or benchmark is not None
                    and abs(benchmark - reference.benchmark) < 1e-9
                )
                grounding_rows.append({
                    "campaign_id": insight.campaign_id,
                    "reference": key,
                    "exists": key in lookup,
                    "evidence_actual": actual,
                    "LLM_actual": reference.actual,
                    "value_matches": value_matches,
                    "evidence_benchmark": benchmark,
                    "LLM_benchmark": reference.benchmark,
                    "benchmark_matches": benchmark_matches,
                })

        grounding_audit = pd.DataFrame(grounding_rows)
        if grounding_audit.empty:
            print("Grounding audit will run after the campaign LLM calls.")
        else:
            display(grounding_audit)
            assert grounding_audit["exists"].all()
            assert grounding_audit["value_matches"].all()
            assert grounding_audit["benchmark_matches"].all()
        """
    ),
    markdown(
        """
        ## 28. Run The Experimental Campaign-Type Synthesizer

        The synthesizer receives only deterministic assessments and validated campaign
        insights. It identifies repeated patterns, conflicts, risks, type lessons, and
        tests to prioritize. It cannot change decisions or calculate budget.
        """
    ),
    code(
        """
        portfolio_insight = None
        if RUN_LLM:
            synthesis_payload = {
                "cycle_id": cycle_id,
                "assessments": [item.model_dump(mode="json") for item in experimental_assessments],
                "insights": [item.model_dump(mode="json") for item in campaign_insights],
            }
            path, prompt_sha, input_sha = cache_path(
                "experimental_synthesis", "portfolio_synthesis", synthesis_payload
            )
            if path.exists() and not FORCE_LLM_RERUN:
                cached = json.loads(path.read_text(encoding="utf-8"))
                portfolio_insight = PortfolioInsight.model_validate(cached["output"])
                synthesis_source = "cache"
            else:
                synthesizer = OpenAIPortfolioSynthesizer(model=MODEL)
                portfolio_insight = synthesizer.synthesize(
                    experimental_assessments, campaign_insights
                )
                save_cache(
                    path, prompt_sha, input_sha,
                    portfolio_insight.model_dump(mode="json"),
                )
                synthesis_source = "OpenAI"
            print(f"Synthesis source: {synthesis_source}")
            display(JSON(portfolio_insight.model_dump(mode="json"), expanded=True))
        else:
            print("Campaign-type synthesis skipped until RUN_LLM = True.")
        """
    ),
    markdown(
        """
        ## 29. Run The Recommendation Narrator

        The final narrator receives the validated synthesis plus the already-calculated
        budget scenario. Its Pydantic output has separate sections for the business owner,
        marketing director, and performance marketing manager.

        The prompt explicitly forbids changing actions, units, shares, eligibility, or
        unallocated budget.
        """
    ),
    code(
        """
        stakeholder_report = None
        if RUN_LLM and portfolio_insight is not None:
            narrator_payload = {
                "portfolio": portfolio_insight.model_dump(mode="json"),
                "budget": type_budget.model_dump(mode="json"),
            }
            path, prompt_sha, input_sha = cache_path(
                "stakeholder_report", "recommendation_narrator", narrator_payload
            )
            if path.exists() and not FORCE_LLM_RERUN:
                cached = json.loads(path.read_text(encoding="utf-8"))
                stakeholder_report = StakeholderReport.model_validate(cached["output"])
                report_source = "cache"
            else:
                narrator = OpenAIReportNarrator(model=MODEL)
                stakeholder_report = narrator.narrate(portfolio_insight, type_budget)
                save_cache(
                    path, prompt_sha, input_sha,
                    stakeholder_report.model_dump(mode="json"),
                )
                report_source = "OpenAI"
            print(f"Narrator source: {report_source}")
            display(JSON(stakeholder_report.model_dump(mode="json"), expanded=True))
        else:
            print("Recommendation narration skipped until RUN_LLM = True.")
        """
    ),
    markdown(
        """
        ## 30. Present The Final Full Picture

        The deterministic scorecard remains visible even when LLM execution is disabled.
        When enabled, the validated stakeholder report is rendered below without replacing
        the numeric evidence.
        """
    ),
    code(
        """
        final_scorecard = pd.DataFrame([{
            "campaign": POST_EID_NAME,
            "objective evidence": f"{observed} observed / {mature} mature",
            "raw score": manual_raw,
            "corrected score": manual_corrected,
            "corrected low": manual_corrected_low,
            "corrected high": manual_corrected_high,
            "benchmark": adjusted_peer_mean,
            "lift low": manual_lift_low,
            "lift high": manual_lift_high,
            "probability better": manual_probability_better,
            "statistical decision": manual_decision.upper(),
            "operational action": post_assessment.next_cycle_action.value,
            "semantic evidence": f"{high_intent_count}/{semantic_count} high intent; "
                                 f"{barrier_count}/{semantic_count} with barriers",
        }])
        display(final_scorecard.style.format({
            "raw score": "{:.2%}", "corrected score": "{:.2%}",
            "corrected low": "{:.2%}", "corrected high": "{:.2%}",
            "benchmark": "{:.2%}", "lift low": "{:+.2%}",
            "lift high": "{:+.2%}", "probability better": "{:.2%}",
        }))

        if stakeholder_report is not None:
            display(Markdown("### Executive Summary"))
            display(Markdown(stakeholder_report.executive_summary))
            sections = [
                ("Business Owner", stakeholder_report.business_owner_sections),
                ("Marketing Director", stakeholder_report.marketing_director_sections),
                ("Performance Marketing Manager", stakeholder_report.performance_manager_sections),
                ("Data Limitations", stakeholder_report.data_limitations),
            ]
            for heading, items in sections:
                display(Markdown(f"### {heading}"))
                for item in items:
                    display(Markdown(f"- {item}"))
        else:
            display(Markdown(
                "**LLM narrative not run.** The complete deterministic result above is "
                "available offline. Set `RUN_LLM = True` and rerun cells 26-30 to add "
                "the validated narrative."
            ))
        """
    ),
    markdown(
        """
        ## 31. End-To-End Calculation And Responsibility Ledger

        | Stage | Raw evidence | Output | Why it contributes | Owner |
        |---|---|---|---|---|
        | Maturity | 63 total, 11 unresolved | 52 mature | Avoids false failures | Deterministic |
        | Raw score | 38 created orders / 52 mature | 73.08% | Describes observed sample | Deterministic |
        | Raw interval | 38 successes, 52 trials | 59.75%-83.23% | Shows raw sampling uncertainty | Deterministic |
        | Peer benchmark | 58 peer successes / 77 trials | 75.00% adjusted | Adds comparison context | Deterministic |
        | EB correction | prior + campaign counts | 73.90% | Reduces small-sample overreaction | Deterministic |
        | Credible range | Beta posterior draws | 64.56%-82.23% | Shows plausible underlying rates | Deterministic |
        | Favorable lift | campaign draw - benchmark draw | -16.93%-16.14% | Connects uncertainty to funding | Deterministic |
        | Decision | lift range crosses zero | HOLD | Prevents a noisy winner call | Deterministic |
        | Semantics | 63 validated classifications | intent/barrier patterns | Explains and generates hypotheses | LLM classification + deterministic aggregation |
        | Budget | locked decisions and 70/30 policy | units and named tests | Turns evidence into a scenario | Deterministic |
        | Campaign interpretation | complete evidence pack | `CampaignInsight` | Explains one campaign | Structured LLM |
        | Type synthesis | assessments + insights | `PortfolioInsight` | Finds patterns and conflicts | Structured LLM |
        | Stakeholder report | synthesis + locked budget | `StakeholderReport` | Makes the result easy to act on | Structured LLM |

        ## Final Reading Rule

        Do not start with the largest rate. Start with the eligible raw evidence, then read
        the corrected score, uncertainty, benchmark, lift range, and decision. Use
        conversation semantics to explain the result and design the next test. Use the LLM
        to communicate the locked evidence, never to replace it.
        """
    ),
]


notebook = nbf.v4.new_notebook(
    cells=cells,
    metadata={
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.9"},
    },
)
nbf.write(notebook, OUTPUT)
print(OUTPUT)
