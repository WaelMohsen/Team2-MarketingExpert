"""Build an objective-only learning notebook for the OUTCOME_LEADS MVP."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "CAPI_OUTCOME_LEADS_Objective_Only_Learning.ipynb"


def markdown(value: str):
    return nbf.v4.new_markdown_cell(dedent(value).strip())


def code(value: str):
    return nbf.v4.new_code_cell(dedent(value).strip())


cells = [
    markdown(
        """
        # Objective-Only MVP: OUTCOME_LEADS From Raw Evidence To Recommendation

        This notebook intentionally uses **Meta objective only**. It does not use any
        additional campaign taxonomy to choose a KPI, form a peer group, calculate a
        benchmark, make a decision, allocate illustrative budget, or instruct the LLM.

        The worked example is **Post-Eid Lookalike Test**, and its peers are the other
        campaigns whose objective is `OUTCOME_LEADS`.

        The notebook keeps every important number visible:

        1. raw records and eligible records;
        2. numerator, denominator, and raw rate;
        3. peer evidence before and after the half-count adjustment;
        4. Empirical-Bayes prior and corrected score;
        5. uncertainty ranges and the range-based decision;
        6. campaign, ad set, ad, creative, and audience scorecards;
        7. conversation semantics as diagnostic evidence;
        8. a deterministic 70/30 scenario and optional structured LLM narration.
        """
    ),
    markdown(
        """
        ## 0. End-To-End Logic

        ```text
        Sample 2 JSON files
              |
              v
        Canonical media + WhatsApp outcome tables
              |
              v
        Select one objective and its KPI contract
              |
              v
        Aggregate campaign / ad set / ad / creative / audience
              |
              v
        Raw rate + same-objective peer evidence
              |
              v
        Empirical-Bayes corrected score + uncertainty range
              |
              v
        SCALE / HOLD / KILL from the lift range
              |
              +--> conversation semantics explain possible reasons
              |
              v
        70 exploit / 30 named exploration tests
              |
              v
        Optional LLM explanation of locked evidence
        ```

        **Statistical engine owns:** calculations, ranges, decisions, and budget units.

        **LLM owns:** interpretation in plain language, hypotheses, and narration. It is
        not allowed to change the locked values.
        """
    ),
    markdown(
        """
        ## 1. Load The Real Pipeline And Data

        The notebook uses the production normalizer and aggregations. The statistical
        comparison is defined locally so its objective-only behavior is easy to audit.
        Optional LLM calls are off by default.
        """
    ),
    code(
        """
        import hashlib
        import json
        import os
        from math import sqrt
        from pathlib import Path
        from typing import List, Optional

        import altair as alt
        import pandas as pd
        from dotenv import load_dotenv
        from IPython.display import JSON, Markdown, display
        from pydantic import BaseModel

        from src_2.analytics import build_scorecards
        from src_2.analytics.empirical_bayes import fit_beta_prior, score_beta_binomial
        from src_2.application import load_conversation_signal_records
        from src_2.ingestion import build_data_quality_report, load_sample2, normalize_cycle

        pd.set_option("display.max_columns", 180)
        pd.set_option("display.max_colwidth", 180)
        pd.set_option("display.float_format", lambda value: f"{value:,.6f}")
        alt.data_transformers.disable_max_rows()

        ROOT = Path.cwd()
        if not (ROOT / "src_2").exists():
            raise RuntimeError("Run this notebook from the Team2-MarketingExpert repository root.")

        load_dotenv(ROOT / ".env")
        INPUT = ROOT / "src_2" / "data" / "input" / "sampe_2"
        SIGNALS = ROOT / "src_2" / "artifacts" / "conversation_signals.jsonl"
        LLM_CACHE = ROOT / "outputs" / "objective_leads_learning_llm"
        FOCUS_OBJECTIVE = "OUTCOME_LEADS"
        POST_EID_NAME = "Post-Eid Lookalike Test"
        """
    ),
    markdown(
        """
        ## 2. See The Objectives Before Choosing A KPI

        An objective is the outcome Meta was asked to optimize delivery toward. For this
        MVP, it is also the only grouping field used to define comparable campaigns.

        This avoids intersecting two classification systems. A campaign enters the
        `OUTCOME_LEADS` analysis because its objective is `OUTCOME_LEADS`, and for no
        other reason.
        """
    ),
    code(
        """
        canonical = normalize_cycle(load_sample2(INPUT))
        quality = build_data_quality_report(canonical)
        signal_records = load_conversation_signal_records(SIGNALS) if SIGNALS.exists() else []

        objective_meanings = {
            "OUTCOME_AWARENESS": "Reach people and create visibility; business outcomes are supporting evidence.",
            "OUTCOME_ENGAGEMENT": "Generate interaction with the ad or content.",
            "OUTCOME_LEADS": "Generate leads or conversations that can progress toward an order.",
            "OUTCOME_SALES": "Generate purchase-related outcomes and delivered customer value.",
        }

        objective_map = canonical.campaigns.groupby("objective", as_index=False).agg(
            campaign_count=("campaign_name", "nunique"),
            campaigns=("campaign_name", lambda values: "\\n".join(sorted(values))),
        )
        objective_map["business meaning"] = objective_map["objective"].map(objective_meanings)
        objective_map = objective_map[["objective", "business meaning", "campaign_count", "campaigns"]]
        display(objective_map.style.set_properties(
            subset=["campaigns"], **{"white-space": "pre-wrap", "text-align": "left"}
        ))
        """
    ),
    markdown(
        """
        ## 3. The Objective-To-KPI Contract

        The lookup below is an explicit MVP assumption. The objective chooses one primary
        statistical score; the other metrics stay visible as supporting evidence and
        guardrails. No weighted composite score is created.

        | Objective | Primary statistical score | Why |
        |---|---|---|
        | Awareness | Link responses / impressions | Available media response proxy; not proof of awareness lift |
        | Engagement | Link responses / impressions | Available interaction proxy in this sample |
        | Leads | Mature conversations with an order / mature conversations | Uses WhatsApp progression after unresolved cases are removed |
        | Sales | Delivered unique customers / mature unique customers | Uses completed customer-level delivery outcome |

        This notebook calculates only the `OUTCOME_LEADS` row.
        """
    ),
    code(
        """
        OBJECTIVE_KPI_LOOKUP = {
            "OUTCOME_AWARENESS": {
                "metric": "link_ctr",
                "numerator": "link_clicks",
                "denominator": "impressions",
                "business_job": "Create visibility and measurable response.",
                "success_question": "Did the campaign create more link response than comparable awareness campaigns?",
            },
            "OUTCOME_ENGAGEMENT": {
                "metric": "link_ctr",
                "numerator": "link_clicks",
                "denominator": "impressions",
                "business_job": "Generate interaction with the ad or content.",
                "success_question": "Did the campaign create more link response than comparable engagement campaigns?",
            },
            "OUTCOME_LEADS": {
                "metric": "order_creation_rate",
                "numerator": "mature_orders_created",
                "denominator": "mature_conversations",
                "business_job": "Generate WhatsApp leads that progress to a created order.",
                "success_question": "Did mature WhatsApp conversations progress to orders better than comparable lead campaigns?",
            },
            "OUTCOME_SALES": {
                "metric": "customer_delivered_rate",
                "numerator": "delivered_customers",
                "denominator": "mature_unique_customers",
                "business_job": "Generate delivered customer outcomes.",
                "success_question": "Did mature unique customers reach delivery better than comparable sales campaigns?",
            },
        }

        objective_spec = OBJECTIVE_KPI_LOOKUP[FOCUS_OBJECTIVE]
        display(pd.DataFrame([
            ["Objective", FOCUS_OBJECTIVE],
            ["Business job", objective_spec["business_job"]],
            ["Success question", objective_spec["success_question"]],
            ["Primary score", objective_spec["metric"]],
            ["Numerator", objective_spec["numerator"]],
            ["Denominator", objective_spec["denominator"]],
            ["Better direction", "higher"],
        ], columns=["contract element", "value"]))
        """
    ),
    markdown(
        """
        ## 4. Build Raw Aggregates At Five Levels

        The aggregation layer keeps media facts and observed WhatsApp outcomes at their
        correct grains. It does not multiply daily media rows by conversation rows.

        The score uses `mature_orders_created / mature_conversations`. Spend, delivered
        revenue, return on ad spend, cancellation, refund, and media response remain
        supporting evidence. They are not mixed into the score with arbitrary weights.
        """
    ),
    code(
        """
        raw_scorecards = build_scorecards(canonical, signal_records)
        levels = ["campaign", "adset", "ad", "creative", "audience"]

        inventory_rows = []
        for level in levels:
            frame = raw_scorecards.by_level(level)
            focused = frame.loc[frame["objective"].eq(FOCUS_OBJECTIVE)]
            inventory_rows.append({
                "level": level,
                "all entities": len(frame),
                "same-objective entities": len(focused),
                "mature conversations": int(focused["mature_conversations"].sum()),
                "mature orders": int(focused["mature_orders_created"].sum()),
            })
        display(pd.DataFrame(inventory_rows))
        """
    ),
    markdown(
        """
        ## 5. Define The Objective-Only Empirical-Bayes Scorer

        For each entity:

        1. keep entities at the same hierarchy level;
        2. keep only `OUTCOME_LEADS`;
        3. remove the entity being scored from its peer evidence;
        4. require at least two valid peers;
        5. fit a Beta prior from peer successes and trials;
        6. update it with the entity's evidence;
        7. compare posterior draws with peer benchmark draws;
        8. decide from the 95% favorable-lift range.

        This is partial pooling: a small sample leans more toward its objective peer
        benchmark, while a large sample is driven more by its own evidence.
        """
    ),
    code(
        """
        def stable_seed(level, entity_id, metric):
            raw = f"{level}|{entity_id}|{metric}".encode("utf-8")
            return int(hashlib.sha256(raw).hexdigest()[:8], 16)


        def score_objective_level(frame, level, objective, spec):
            scoped = frame.loc[frame["objective"].eq(objective)].copy()
            results = []
            for _, row in scoped.iterrows():
                peers = scoped.loc[scoped["entity_id"].ne(row["entity_id"])].copy()
                peers["_successes"] = pd.to_numeric(peers[spec["numerator"]], errors="coerce")
                peers["_trials"] = pd.to_numeric(peers[spec["denominator"]], errors="coerce")
                peers = peers.loc[
                    peers["_trials"].gt(0)
                    & peers["_successes"].ge(0)
                    & peers["_successes"].le(peers["_trials"])
                ]
                if len(peers) < 2:
                    results.append({
                        "entity_id": row["entity_id"],
                        "raw_score": row[spec["numerator"]] / row[spec["denominator"]]
                        if row[spec["denominator"]] else None,
                        "corrected_score": None,
                        "corrected_score_low": None,
                        "corrected_score_high": None,
                        "benchmark_score": None,
                        "expected_lift": None,
                        "lift_low": None,
                        "lift_high": None,
                        "probability_better": None,
                        "decision": "insufficient_evidence",
                        "benchmark_peer_count": len(peers),
                        "benchmark_source": "insufficient same-objective peers",
                        "prior_alpha": None,
                        "prior_beta": None,
                        "prior_strength": None,
                    })
                    continue

                prior = fit_beta_prior(
                    peers["_successes"], peers["_trials"],
                    source="current-cycle same-objective empirical prior",
                )
                score = score_beta_binomial(
                    metric=spec["metric"],
                    numerator=spec["numerator"],
                    denominator=spec["denominator"],
                    direction="higher",
                    successes=float(row[spec["numerator"]]),
                    trials=float(row[spec["denominator"]]),
                    prior=prior,
                    practical_lift_threshold=0.0,
                    seed=stable_seed(level, row["entity_id"], spec["metric"]),
                    samples=5000,
                )
                payload = score.model_dump(mode="json")
                payload["decision"] = score.decision.value
                payload["entity_id"] = row["entity_id"]
                results.append(payload)
            return scoped.merge(pd.DataFrame(results), on="entity_id", how="left")


        objective_scorecards = {
            level: score_objective_level(
                raw_scorecards.by_level(level), level, FOCUS_OBJECTIVE, objective_spec
            )
            for level in levels
        }
        """
    ),
    markdown(
        """
        ## 6. Campaign-Level Result For All Lead Campaigns

        Raw score answers: *what fraction progressed in this observed mature sample?*

        Corrected score answers: *after accounting for sample size and peer evidence,
        what underlying rate is most plausible?*

        Decision answers: *does the full favorable-lift range support better, worse, or
        uncertain performance?*
        """
    ),
    code(
        """
        campaign_scores = objective_scorecards["campaign"].copy()
        campaign_view_columns = [
            "campaign_id", "campaign_name", "observed_conversations",
            "open_or_pending_conversations", "mature_orders_created",
            "mature_conversations", "raw_score", "corrected_score",
            "corrected_score_low", "corrected_score_high", "benchmark_score",
            "lift_low", "lift_high", "probability_better", "decision",
            "spend", "net_revenue", "net_roas",
        ]
        campaign_view = campaign_scores[campaign_view_columns].sort_values(
            "corrected_score", ascending=False
        )
        display(campaign_view.style.format({
            "raw_score": "{:.2%}", "corrected_score": "{:.2%}",
            "corrected_score_low": "{:.2%}", "corrected_score_high": "{:.2%}",
            "benchmark_score": "{:.2%}", "lift_low": "{:+.2%}",
            "lift_high": "{:+.2%}", "probability_better": "{:.2%}",
            "spend": "{:,.2f}", "net_revenue": "{:,.2f}", "net_roas": "{:.2f}",
        }))
        """
    ),
    markdown(
        """
        ## 7. Visualize Corrected Campaign Scores And Their Ranges

        A point alone can make small differences look decisive. The horizontal line is
        the corrected-score range. Overlap means the ranking is uncertain, even if one
        point is numerically larger.
        """
    ),
    code(
        """
        plot_frame = campaign_view.copy()
        base = alt.Chart(plot_frame).encode(
            y=alt.Y("campaign_name:N", sort="-x", title=None),
            tooltip=[
                alt.Tooltip("campaign_name:N", title="Campaign"),
                alt.Tooltip("mature_orders_created:Q", title="Orders"),
                alt.Tooltip("mature_conversations:Q", title="Mature conversations"),
                alt.Tooltip("raw_score:Q", format=".2%", title="Raw"),
                alt.Tooltip("corrected_score:Q", format=".2%", title="Corrected"),
                alt.Tooltip("decision:N", title="Decision"),
            ],
        )
        ranges = base.mark_rule(strokeWidth=4, color="#68737d").encode(
            x=alt.X("corrected_score_low:Q", axis=alt.Axis(format="%"), title="Order creation rate"),
            x2="corrected_score_high:Q",
        )
        points = base.mark_point(filled=True, size=120, color="#176b87").encode(
            x="corrected_score:Q"
        )
        display((ranges + points).properties(height=190, title="Lead campaigns: corrected score with 95% range"))
        """
    ),
    markdown(
        """
        # Worked Example: Post-Eid Lookalike Test

        The next sections reconstruct the Post-Eid result from raw rows. Nothing is hidden
        behind the final percentage.
        """
    ),
    markdown(
        """
        ## 8. Raw Outcome Ledger

        `active` and `stuck_pending` are unresolved. They are not counted as failures.
        The score denominator includes only mature conversations.
        """
    ),
    code(
        """
        post_row = campaign_scores.loc[campaign_scores["campaign_name"].eq(POST_EID_NAME)].iloc[0]
        post_id = str(post_row["campaign_id"])
        post_conversations = canonical.conversations.loc[
            canonical.conversations["campaign_id"].eq(post_id)
        ].copy()

        outcome_ledger = post_conversations.groupby("outcome_type", as_index=False).agg(
            conversations=("conversation_id", "nunique"),
            mature=("is_mature_outcome", "sum"),
            created_orders=("has_mature_order", "sum"),
            delivered=("is_delivered", "sum"),
            cancelled=("is_cancelled", "sum"),
            refunded=("is_refunded", "sum"),
        )
        display(outcome_ledger)

        observed = int(len(post_conversations))
        unresolved = int(post_conversations["is_open_or_pending"].sum())
        mature = int(post_conversations["is_mature_outcome"].sum())
        successes = int(post_conversations["has_mature_order"].sum())
        print(f"Observed = {observed}")
        print(f"Unresolved = {unresolved}")
        print(f"Mature denominator = {observed} - {unresolved} = {mature}")
        print(f"Created-order numerator = {successes}")
        """
    ),
    markdown(
        """
        ## 9. Raw Rate And Its Raw Confidence Interval

        The raw rate is descriptive:

        ```text
        raw rate = created-order conversations / mature conversations
                 = 38 / 52
        ```

        The Wilson interval shows how uncertain that raw sample proportion is without
        using peer information. It is preferred to the simple normal approximation for
        binary rates, especially with small samples or rates near 0% or 100%.
        """
    ),
    code(
        """
        def wilson_interval(success_count, trial_count, z=1.959963984540054):
            if trial_count <= 0:
                return None, None
            rate = success_count / trial_count
            denominator = 1 + z * z / trial_count
            center = (rate + z * z / (2 * trial_count)) / denominator
            margin = z * sqrt(
                rate * (1 - rate) / trial_count + z * z / (4 * trial_count * trial_count)
            ) / denominator
            return center - margin, center + margin

        raw_rate = successes / mature
        raw_low, raw_high = wilson_interval(successes, mature)
        print(f"Raw rate = {successes} / {mature} = {raw_rate:.4%}")
        print(f"Raw 95% Wilson interval = [{raw_low:.4%}, {raw_high:.4%}]")
        assert abs(raw_rate - post_row["raw_score"]) < 1e-12
        """
    ),
    markdown(
        """
        ## 10. Build The Benchmark From Same-Objective Peers

        The campaign is removed from its own benchmark. The two remaining lead campaigns
        provide the comparison evidence. Their raw rates stay visible so we can see where
        the benchmark came from.
        """
    ),
    code(
        """
        peer_rows = campaign_scores.loc[campaign_scores["campaign_id"].ne(post_id)].copy()
        peer_rows = peer_rows[[
            "campaign_name", "mature_orders_created", "mature_conversations", "order_creation_rate"
        ]]
        display(peer_rows.style.format({"order_creation_rate": "{:.2%}"}))

        peer_successes = int(peer_rows["mature_orders_created"].sum())
        peer_trials = int(peer_rows["mature_conversations"].sum())
        pooled_peer_rate = peer_successes / peer_trials
        print(f"Pooled raw peer rate = {peer_successes} / {peer_trials} = {pooled_peer_rate:.4%}")
        """
    ),
    markdown(
        """
        ## 11. Why Add 0.5 And 1?

        The benchmark uses a half-success continuity adjustment:

        ```text
        adjusted peer rate = (peer successes + 0.5) / (peer trials + 1)
                           = (58 + 0.5) / (77 + 1)
                           = 75.00%
        ```

        The `+1` is one tiny synthetic observation split into `0.5` success and `0.5`
        failure. It prevents an all-success or all-failure peer sample from claiming the
        true rate is exactly 100% or 0%. It is a numerical stabilization convention, not
        a real customer and not a hidden business target. With 77 peer observations its
        effect is small: 75.32% becomes 75.00%.
        """
    ),
    code(
        """
        adjusted_peer_rate = (peer_successes + 0.5) / (peer_trials + 1.0)
        adjustment_effect = adjusted_peer_rate - pooled_peer_rate
        print(f"Before adjustment = {pooled_peer_rate:.4%}")
        print(f"After adjustment  = ({peer_successes} + 0.5) / ({peer_trials} + 1) = {adjusted_peer_rate:.4%}")
        print(f"Effect             = {adjustment_effect:+.4%}")
        assert abs(adjusted_peer_rate - post_row["benchmark_score"]) < 1e-12
        """
    ),
    markdown(
        """
        ## 12. Convert The Benchmark Into An Empirical Prior

        A prior needs two things:

        - **center:** the typical peer rate, 75.00%;
        - **strength:** how many equivalent observations the peer information should
          contribute.

        We do not simply inject all 77 peer conversations into every campaign. That would
        make the benchmark too powerful and pretend the campaigns are identical.

        The strength calculation is deliberately conservative:

        1. average peer size = `77 / 2 = 38.5`;
        2. estimate a strength implied by how much the two peer rates differ;
        3. use the smaller of those values, with a minimum of 1.

        If peers disagree strongly, the variance-implied strength becomes smaller and the
        prior has less influence. Here the average peer size, 38.5, is the limiting value.
        """
    ),
    code(
        """
        fitted_prior = fit_beta_prior(
            peer_rows["mature_orders_created"],
            peer_rows["mature_conversations"],
            source="current-cycle same-objective empirical prior",
        )
        prior_table = pd.DataFrame([
            ["Prior center", fitted_prior.mean, "Typical adjusted peer rate"],
            ["Prior strength", fitted_prior.strength, "Equivalent evidence allowed from peers"],
            ["Prior alpha", fitted_prior.alpha, "Prior success-shaped evidence"],
            ["Prior beta", fitted_prior.beta, "Prior failure-shaped evidence"],
            ["Peer count", fitted_prior.peer_count, "Independent peer campaign aggregates"],
        ], columns=["component", "value", "business interpretation"])
        display(prior_table)
        print(f"alpha = center x strength = {fitted_prior.mean:.6f} x {fitted_prior.strength:.4f} = {fitted_prior.alpha:.4f}")
        print(f"beta  = (1 - center) x strength = {(1-fitted_prior.mean):.6f} x {fitted_prior.strength:.4f} = {fitted_prior.beta:.4f}")
        """
    ),
    markdown(
        """
        ## 13. Update The Prior With Post-Eid Evidence

        A Beta prior is convenient because we can update it by adding observed successes
        and failures:

        ```text
        posterior alpha = prior alpha + observed successes
        posterior beta  = prior beta + observed failures
        corrected score = posterior alpha / (posterior alpha + posterior beta)
        ```

        The corrected score is a transparent weighted average of the 75.00% peer center
        and the 73.08% campaign raw rate. Post-Eid contributes 52 observations; the prior
        contributes 38.5 equivalent observations, so Post-Eid still has more influence.
        """
    ),
    code(
        """
        failures = mature - successes
        posterior_alpha = fitted_prior.alpha + successes
        posterior_beta = fitted_prior.beta + failures
        corrected_score = posterior_alpha / (posterior_alpha + posterior_beta)
        prior_weight = fitted_prior.strength / (fitted_prior.strength + mature)
        data_weight = mature / (fitted_prior.strength + mature)

        calculation = pd.DataFrame([
            ["Observed successes", successes],
            ["Observed failures", failures],
            ["Prior alpha", fitted_prior.alpha],
            ["Prior beta", fitted_prior.beta],
            ["Posterior alpha", posterior_alpha],
            ["Posterior beta", posterior_beta],
            ["Prior weight", prior_weight],
            ["Campaign-data weight", data_weight],
            ["Corrected score", corrected_score],
        ], columns=["quantity", "value"])
        display(calculation)
        print(f"Corrected score = {posterior_alpha:.3f} / ({posterior_alpha:.3f} + {posterior_beta:.3f}) = {corrected_score:.4%}")
        assert abs(corrected_score - post_row["corrected_score"]) < 1e-12
        """
    ),
    markdown(
        """
        ## 14. From A Corrected Point To A Decision Range

        The engine simulates plausible campaign rates from the posterior and plausible
        benchmark rates from the prior. For a higher-is-better metric:

        ```text
        favorable lift = campaign rate - benchmark rate
        ```

        - `SCALE`: the lower 95% lift bound is above zero.
        - `KILL`: the upper 95% lift bound is below zero.
        - `HOLD`: the range crosses zero.

        Post-Eid's range crosses zero. The data supports both a modestly worse and a
        modestly better underlying result, so the honest decision is HOLD.
        """
    ),
    code(
        """
        post_decision_table = pd.DataFrame([
            ["Raw score", post_row["raw_score"]],
            ["Corrected score", post_row["corrected_score"]],
            ["Corrected low", post_row["corrected_score_low"]],
            ["Corrected high", post_row["corrected_score_high"]],
            ["Benchmark", post_row["benchmark_score"]],
            ["Expected favorable lift", post_row["expected_lift"]],
            ["Lift low", post_row["lift_low"]],
            ["Lift high", post_row["lift_high"]],
            ["Probability better", post_row["probability_better"]],
        ], columns=["result", "value"])
        display(post_decision_table.style.format({"value": "{:.2%}"}))
        print(f"Decision = {post_row['decision'].upper()} because the lift range "
              f"[{post_row['lift_low']:+.2%}, {post_row['lift_high']:+.2%}] crosses zero.")
        assert post_row["decision"] == "hold"
        """
    ),
    markdown(
        """
        ## 15. Post-Eid Scorecards At Every Level

        The same objective KPI and same-objective peer rule are used at every level. This
        allows a campaign manager to inspect ad sets, ads, creatives, and audiences
        without trusting a small raw rate.

        Important reading rule: a numerically larger corrected score is a **leader to
        test**, not automatically a winner. The range-based decision remains authoritative.
        """
    ),
    code(
        """
        detail_rows = []
        for level, frame in objective_scorecards.items():
            selected = frame.loc[frame["campaign_id"].eq(post_id)].copy()
            for _, row in selected.iterrows():
                detail_rows.append({
                    "level": level,
                    "entity_id": row["entity_id"],
                    "entity": row["entity_name"],
                    "orders": row["mature_orders_created"],
                    "mature conversations": row["mature_conversations"],
                    "raw": row["raw_score"],
                    "corrected": row["corrected_score"],
                    "low": row["corrected_score_low"],
                    "high": row["corrected_score_high"],
                    "benchmark": row["benchmark_score"],
                    "lift low": row["lift_low"],
                    "lift high": row["lift_high"],
                    "probability better": row["probability_better"],
                    "decision": row["decision"],
                    "spend": row["spend"],
                    "net revenue": row["net_revenue"],
                })
        post_detail = pd.DataFrame(detail_rows)
        display(post_detail.style.format({
            "raw": "{:.2%}", "corrected": "{:.2%}", "low": "{:.2%}",
            "high": "{:.2%}", "benchmark": "{:.2%}",
            "lift low": "{:+.2%}", "lift high": "{:+.2%}",
            "probability better": "{:.2%}", "spend": "{:,.2f}",
            "net revenue": "{:,.2f}",
        }))
        """
    ),
    markdown(
        """
        ## 16. Compare Post-Eid Children Visually

        Post-Eid has two ad sets, two ads, and two creatives, but only one audience label
        after audience aggregation. We can compare the two configured lookalike widths at
        ad-set level; the audience-level label alone cannot distinguish 5% from 10%.
        """
    ),
    code(
        """
        child_plot = post_detail.loc[post_detail["level"].isin(["adset", "ad", "creative"])].copy()
        base = alt.Chart(child_plot).encode(
            y=alt.Y("entity:N", sort="-x", title=None),
            color=alt.Color("level:N", title="Level", scale=alt.Scale(
                domain=["adset", "ad", "creative"], range=["#176b87", "#c45a2a", "#5a6f3b"]
            )),
            tooltip=[
                alt.Tooltip("level:N"), alt.Tooltip("entity:N"),
                alt.Tooltip("orders:Q"), alt.Tooltip("mature conversations:Q"),
                alt.Tooltip("raw:Q", format=".2%"),
                alt.Tooltip("corrected:Q", format=".2%"),
                alt.Tooltip("decision:N"),
            ],
        )
        child_ranges = base.mark_rule(strokeWidth=3).encode(
            x=alt.X("low:Q", axis=alt.Axis(format="%"), title="Corrected order creation rate"),
            x2="high:Q",
        )
        child_points = base.mark_point(filled=True, size=90).encode(x="corrected:Q")
        display((child_ranges + child_points).properties(height=310, title="Post-Eid child entities"))
        """
    ),
    markdown(
        """
        ## 17. What Conversation Semantics Contributes

        Structured outcomes tell us **what happened**: order, delivery, cancellation,
        refund, unresolved, and revenue. Conversation semantics can suggest **why**:

        - customer goal and purchase intent;
        - barriers and whether the agent helped;
        - product demand;
        - urgency, price sensitivity, deals, agreement, and next steps;
        - alignment between the ad promise and the customer need.

        These are diagnostic signals, not funding-score ingredients. Otherwise subjective
        LLM labels could silently override real business outcomes.
        """
    ),
    code(
        """
        post_semantics = objective_scorecards["campaign"].loc[
            objective_scorecards["campaign"]["campaign_id"].eq(post_id)
        ].iloc[0]
        schema_versions = pd.Series(
            [record.signal_schema_version for record in signal_records], dtype="Int64"
        ).value_counts().sort_index()

        semantic_summary = pd.DataFrame([
            ["Semantic records", post_semantics["semantic_conversations"]],
            ["High purchase intent", post_semantics["high_purchase_intent_conversations"]],
            ["Conversation has a barrier", post_semantics["barrier_conversations"]],
            ["Agent rated helpful", post_semantics["agent_helpful_conversations"]],
            ["Top purpose", post_semantics["top_conversation_purpose"]],
            ["Top barrier", post_semantics["top_barrier"]],
            ["Top mentioned product", post_semantics["top_mentioned_product"]],
        ], columns=["signal", "raw evidence"])
        display(semantic_summary)
        print("Signal schema versions present:")
        display(schema_versions.rename("records").to_frame())
        print("The current 63 records use schema version 1. Newer high-value fields are "
              "present in the contract but were not extracted, so unknown must not be read as absence.")
        """
    ),
    markdown(
        """
        ## 18. Semantic Evidence By Post-Eid Ad Set

        The percentages are accompanied by counts. This avoids treating 19/25 and 22/38
        as equally precise. The signals generate hypotheses; they do not establish that
        an ad set caused the customer's intent or barrier.
        """
    ),
    code(
        """
        post_adsets = objective_scorecards["adset"].loc[
            objective_scorecards["adset"]["campaign_id"].eq(post_id)
        ].copy()
        semantic_adset_view = post_adsets[[
            "entity_name", "semantic_conversations", "high_purchase_intent_conversations",
            "high_purchase_intent_rate", "barrier_conversations", "barrier_conversation_rate",
            "agent_helpful_conversations", "agent_helpful_rate", "top_barrier",
            "top_mentioned_product", "mature_orders_created", "mature_conversations",
            "raw_score", "corrected_score", "decision",
        ]]
        display(semantic_adset_view.style.format({
            "high_purchase_intent_rate": "{:.2%}", "barrier_conversation_rate": "{:.2%}",
            "agent_helpful_rate": "{:.2%}", "raw_score": "{:.2%}",
            "corrected_score": "{:.2%}",
        }))
        """
    ),
    markdown(
        """
        ## 19. High-Value Semantic Fields Still To Extract

        Schema version 1 gives useful intent, barriers, products, and agent-evaluation
        evidence. The following fields can sharpen the next test once they are actually
        extracted. They must remain **unknown**, not zero, until then.

        | Signal | Business use |
        |---|---|
        | Urgency | Detect time-sensitive demand |
        | Price sensitivity and deal seeking | Separate normal price questions from price-driven abandonment |
        | Delivery intent and sales agreement | Detect checkout readiness and agreement |
        | Barrier severity and resolution | Separate minor questions from unresolved blockers |
        | Stated exit reason | Explain cancellation, ghosting, or abandonment |
        | Competitor mention and value driver | Understand alternatives and what customers value |
        | Ad-message alignment | Test whether the conversation need matches the ad promise |
        | Next-step completion | Test whether an agreed action actually progressed |

        Once available, aggregate each as `count / assessable conversations`, and always
        report unknown coverage beside it.
        """
    ),
    markdown(
        """
        ## 20. Data Quality Boundary

        The observed WhatsApp records are the business-outcome evidence, but they reconcile
        to only a small fraction of Meta-attributed conversation starts. Therefore this
        notebook can rank the observed supplied sample, but the budget scenario is not yet
        operational for the full population.
        """
    ),
    code(
        """
        quality_view = pd.DataFrame([
            ["Meta-attributed conversation starts", quality.meta_conversation_starts],
            ["Observed Meta-sourced WhatsApp conversations", quality.observed_meta_whatsapp_conversations],
            ["Observed / Meta reconciliation ratio", quality.reconciliation_ratio],
            ["Organic/direct conversations kept as context", quality.organic_direct_conversations],
            ["Open or pending outcomes", quality.open_or_pending_conversations],
            ["Repeated customers", quality.repeated_customers],
            ["Reach greater than impressions rows", quality.reach_exceeds_impressions_rows],
            ["Evidence status", quality.status.value],
        ], columns=["quality fact", "value"])
        display(quality_view)
        print(f"Coverage = {quality.observed_meta_whatsapp_conversations:,} / "
              f"{quality.meta_conversation_starts:,} = {quality.reconciliation_ratio:.2%}")
        """
    ),
    markdown(
        """
        ## 21. Deterministic 70/30 Objective Scenario

        The scenario uses 100 learning units:

        - **70 exploit units:** only campaigns with a statistically supported SCALE
          decision; allocation is weighted by `probability_better`.
        - **30 explore units:** HOLD campaigns become named controlled tests. With no
          business priority input, the MVP divides the reserve equally.
        - **KILL:** receives zero.
        - Unsupported exploit units remain unallocated rather than being forced into a
          weak campaign.

        All three lead campaigns are HOLD, so 70 exploit units remain unallocated and 30
        explore units are split into three 10-unit tests.
        """
    ),
    code(
        """
        TOTAL_UNITS = 100.0
        EXPLOIT_UNITS = 70.0
        EXPLORE_UNITS = 30.0

        scale_rows = campaign_scores.loc[campaign_scores["decision"].eq("scale")].copy()
        hold_rows = campaign_scores.loc[campaign_scores["decision"].eq("hold")].copy()
        allocation_rows = []

        if not scale_rows.empty:
            confidence_total = scale_rows["probability_better"].sum()
            for _, row in scale_rows.iterrows():
                units = EXPLOIT_UNITS * row["probability_better"] / confidence_total
                allocation_rows.append({
                    "campaign_id": row["campaign_id"], "campaign": row["campaign_name"],
                    "pool": "exploit", "decision": "scale", "budget_units": units,
                    "reason": "Supported positive lift; weighted by probability better.",
                })

        if not hold_rows.empty:
            units = EXPLORE_UNITS / len(hold_rows)
            for _, row in hold_rows.iterrows():
                allocation_rows.append({
                    "campaign_id": row["campaign_id"], "campaign": row["campaign_name"],
                    "pool": "explore", "decision": "hold", "budget_units": units,
                    "reason": "Uncertain lift; fund a named controlled test, not scaling.",
                })

        allocations = pd.DataFrame(allocation_rows)
        assigned_exploit = allocations.loc[allocations["pool"].eq("exploit"), "budget_units"].sum()
        assigned_explore = allocations.loc[allocations["pool"].eq("explore"), "budget_units"].sum()
        unallocated = TOTAL_UNITS - assigned_exploit - assigned_explore
        display(allocations)
        print(f"Exploit assigned = {assigned_exploit:.2f} / {EXPLOIT_UNITS:.2f}")
        print(f"Explore assigned = {assigned_explore:.2f} / {EXPLORE_UNITS:.2f}")
        print(f"Unallocated = {unallocated:.2f}")
        print("Operational = False because outcome reconciliation is limited.")
        """
    ),
    markdown(
        """
        ## 22. Turn Explore Units Into Named Tests

        Each HOLD campaign receives a concrete comparison, hypothesis, success rule,
        failure rule, and stop rule. The minimum 30 additional mature conversations per
        arm is an explicit POC assumption, not a universal marketing benchmark.

        The final comparison still uses ranges:

        - success: lower 95% direct lift bound above zero;
        - failure: upper 95% direct lift bound below zero;
        - otherwise: inconclusive and remain HOLD.
        """
    ),
    code(
        """
        test_rows = []
        adset_scores = objective_scorecards["adset"]
        for _, campaign in hold_rows.iterrows():
            children = adset_scores.loc[
                adset_scores["campaign_id"].eq(campaign["campaign_id"])
            ].sort_values("corrected_score", ascending=False)
            if len(children) >= 2:
                leader = children.iloc[0]
                challenger = children.iloc[1]
                comparison = f"{leader['entity_name']} vs {challenger['entity_name']}"
                hypothesis = (
                    f"{leader['entity_name']} will produce a higher mature order creation "
                    f"rate than {challenger['entity_name']} under matched conditions."
                )
            else:
                comparison = "Current setup vs one new controlled variant"
                hypothesis = "A single controlled variant will improve mature order creation."
            test_rows.append({
                "campaign_id": campaign["campaign_id"],
                "campaign": campaign["campaign_name"],
                "test": comparison,
                "hypothesis": hypothesis,
                "primary metric": objective_spec["metric"],
                "budget units": EXPLORE_UNITS / len(hold_rows),
                "success rule": "95% lower direct-lift bound > 0 after the stop rule.",
                "failure rule": "95% upper direct-lift bound < 0 after the stop rule.",
                "stop rule": "End of next cycle and at least 30 additional mature conversations per arm; otherwise inconclusive.",
            })
        exploration_tests = pd.DataFrame(test_rows)
        display(exploration_tests)
        """
    ),
    markdown(
        """
        ## 23. Build The Exact Objective-Only Evidence Payload

        The payload contains only the objective contract, deterministic scorecards,
        semantic aggregates, data limitations, and the locked budget scenario. Raw
        conversation text is not sent to the narrator.
        """
    ),
    code(
        """
        score_fields = [
            "entity_id", "entity_name", "campaign_id", "campaign_name", "objective",
            "mature_orders_created", "mature_conversations", "raw_score",
            "corrected_score", "corrected_score_low", "corrected_score_high",
            "benchmark_score", "benchmark_source", "benchmark_peer_count",
            "expected_lift", "lift_low", "lift_high", "probability_better", "decision",
            "spend", "net_revenue", "net_roas", "observed_conversations",
            "open_or_pending_conversations", "semantic_conversations",
            "high_purchase_intent_conversations", "barrier_conversations",
            "agent_helpful_conversations", "top_conversation_purpose", "top_barrier",
            "top_mentioned_product",
        ]

        def compact_records(frame):
            columns = [column for column in score_fields if column in frame.columns]
            clean = frame[columns].copy().where(pd.notna(frame[columns]), None)
            return clean.to_dict(orient="records")

        campaign_payloads = []
        for _, campaign in campaign_scores.iterrows():
            campaign_id = campaign["campaign_id"]
            campaign_payloads.append({
                "cycle_id": "sample2-completed-cycle",
                "objective": FOCUS_OBJECTIVE,
                "business_job": objective_spec["business_job"],
                "success_question": objective_spec["success_question"],
                "primary_metric": objective_spec["metric"],
                "campaign": compact_records(campaign_scores.loc[
                    campaign_scores["campaign_id"].eq(campaign_id)
                ])[0],
                "adsets": compact_records(objective_scorecards["adset"].loc[
                    objective_scorecards["adset"]["campaign_id"].eq(campaign_id)
                ]),
                "ads": compact_records(objective_scorecards["ad"].loc[
                    objective_scorecards["ad"]["campaign_id"].eq(campaign_id)
                ]),
                "creatives": compact_records(objective_scorecards["creative"].loc[
                    objective_scorecards["creative"]["campaign_id"].eq(campaign_id)
                ]),
                "audiences": compact_records(objective_scorecards["audience"].loc[
                    objective_scorecards["audience"]["campaign_id"].eq(campaign_id)
                ]),
                "limitations": quality.warnings + [
                    "Semantic schema version 1 is available only for the Post-Eid supplied sample.",
                    "Semantic signals are diagnostic and cannot override the outcome decision.",
                ],
            })

        post_payload = next(
            item for item in campaign_payloads if item["campaign"]["campaign_name"] == POST_EID_NAME
        )
        serialized_post_payload = json.dumps(post_payload, sort_keys=True, ensure_ascii=True, default=str)
        display(JSON(post_payload, expanded=False))
        print(f"Payload characters = {len(serialized_post_payload):,}")
        print(f"Payload SHA256 = {hashlib.sha256(serialized_post_payload.encode('utf-8')).hexdigest()}")
        """
    ),
    markdown(
        """
        ## 24. Optional Structured LLM Runs

        Five calls are available when `RUN_LLM = True`:

        1. one campaign analyst call for each of the three lead campaigns;
        2. one objective-level synthesis call;
        3. one stakeholder recommendation narrator call.

        All outputs use strict Pydantic contracts whose fields are required. The default
        execution makes no paid API calls. Outputs are cached by model, prompt hash, and
        payload hash.
        """
    ),
    code(
        """
        class ObjectiveEvidenceReference(BaseModel):
            entity_level: str
            entity_id: str
            metric: str
            actual: Optional[float]
            benchmark: Optional[float]


        class ObjectiveCampaignInsight(BaseModel):
            campaign_id: str
            objective: str
            target_assessment: str
            supporting_evidence: List[ObjectiveEvidenceReference]
            performance_drivers: List[str]
            audience_findings: List[str]
            creative_findings: List[str]
            risks_and_confounders: List[str]
            strategic_lesson: str
            next_controlled_test: Optional[str]
            evidence_status: str


        class ObjectivePortfolioInsight(BaseModel):
            cycle_id: str
            objective: str
            repeated_patterns: List[str]
            conflicting_results: List[str]
            strategic_lessons: List[str]
            portfolio_risks: List[str]
            tests_to_prioritize: List[str]


        class ObjectiveStakeholderReport(BaseModel):
            cycle_id: str
            objective: str
            executive_summary: str
            business_owner_sections: List[str]
            marketing_director_sections: List[str]
            performance_manager_sections: List[str]
            data_limitations: List[str]


        RUN_LLM = False
        FORCE_LLM_RERUN = False
        MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
        PROMPT_FILES = {
            "campaign": ROOT / "src_2" / "prompts" / "objective_campaign_analysis.md",
            "synthesis": ROOT / "src_2" / "prompts" / "objective_synthesis.md",
            "narrator": ROOT / "src_2" / "prompts" / "objective_recommendation_narrator.md",
        }
        prompts = {name: path.read_text(encoding="utf-8") for name, path in PROMPT_FILES.items()}
        display(pd.DataFrame([
            {"stage": name, "characters": len(text),
             "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
            for name, text in prompts.items()
        ]))
        print(f"RUN_LLM = {RUN_LLM}; model = {MODEL}")
        """
    ),
    markdown(
        """
        ## 25. Run, Validate, And Cache Campaign Analysis

        Pydantic validates structure. The grounding audit in the next cell validates that
        every numeric evidence reference maps back to the deterministic payload.
        """
    ),
    code(
        """
        def stable_json(value):
            return json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)


        def cached_parse(stage, prompt_key, payload, output_model):
            from openai import OpenAI

            prompt_sha = hashlib.sha256(prompts[prompt_key].encode("utf-8")).hexdigest()
            input_sha = hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()
            cache_key = hashlib.sha256(
                f"{MODEL}|{prompt_sha}|{input_sha}".encode("utf-8")
            ).hexdigest()[:20]
            path = LLM_CACHE / f"{stage}_{cache_key}.json"
            if path.exists() and not FORCE_LLM_RERUN:
                saved = json.loads(path.read_text(encoding="utf-8"))
                return output_model.model_validate(saved["output"]), "cache", path

            client = OpenAI()
            response = client.responses.parse(
                model=MODEL,
                instructions=prompts[prompt_key],
                input=stable_json(payload),
                text_format=output_model,
            )
            if response.output_parsed is None:
                raise RuntimeError("The model did not return a validated structured response")
            result = response.output_parsed
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(stable_json({
                "model": MODEL, "prompt_sha256": prompt_sha,
                "input_sha256": input_sha, "output": result.model_dump(mode="json"),
            }), encoding="utf-8")
            return result, "OpenAI", path


        campaign_insights = []
        llm_audit = []
        if RUN_LLM:
            for payload in campaign_payloads:
                result, source, path = cached_parse(
                    f"campaign_{payload['campaign']['campaign_id']}",
                    "campaign", payload, ObjectiveCampaignInsight,
                )
                campaign_insights.append(result)
                llm_audit.append({
                    "campaign": payload["campaign"]["campaign_name"],
                    "source": source, "cache": str(path.relative_to(ROOT)),
                })
            display(pd.DataFrame(llm_audit))
            display(JSON([item.model_dump(mode="json") for item in campaign_insights], expanded=True))
        else:
            print("Campaign LLM calls skipped. Set RUN_LLM = True and rerun from this cell.")
        """
    ),
    markdown(
        """
        ## 26. Grounding Audit

        Schema validation proves the output shape. Grounding validation proves that a
        cited entity, metric, actual value, and benchmark exist in the locked payload.
        """
    ),
    code(
        """
        payload_by_campaign = {
            item["campaign"]["campaign_id"]: item for item in campaign_payloads
        }

        def evidence_lookup(payload):
            lookup = {}
            for level_key, level_name in (
                ("campaign", "campaign"), ("adsets", "adset"), ("ads", "ad"),
                ("creatives", "creative"), ("audiences", "audience"),
            ):
                entities = [payload[level_key]] if level_key == "campaign" else payload[level_key]
                for entity in entities:
                    for metric in (
                        "raw_score", "corrected_score", "expected_lift", "lift_low",
                        "lift_high", "probability_better", "spend", "net_revenue", "net_roas",
                    ):
                        if metric in entity:
                            benchmark = entity.get("benchmark_score") if metric in {
                                "raw_score", "corrected_score"
                            } else (0.0 if metric in {"expected_lift", "lift_low", "lift_high"} else None)
                            lookup[(level_name, entity["entity_id"], metric)] = (
                                entity.get(metric), benchmark
                            )
            return lookup

        grounding_rows = []
        for insight in campaign_insights:
            payload = payload_by_campaign.get(insight.campaign_id)
            lookup = evidence_lookup(payload) if payload else {}
            for reference in insight.supporting_evidence:
                key = (reference.entity_level, reference.entity_id, reference.metric)
                expected = lookup.get(key)
                actual_ok = expected is not None and (
                    expected[0] is None and reference.actual is None
                    or expected[0] is not None and reference.actual is not None
                    and abs(expected[0] - reference.actual) < 1e-9
                )
                benchmark_ok = expected is not None and (
                    reference.benchmark is None
                    or expected[1] is not None
                    and abs(expected[1] - reference.benchmark) < 1e-9
                )
                grounding_rows.append({
                    "campaign_id": insight.campaign_id, "reference": key,
                    "exists": expected is not None, "actual matches": actual_ok,
                    "benchmark matches": benchmark_ok,
                })

        grounding_audit = pd.DataFrame(grounding_rows)
        if grounding_audit.empty:
            print("Grounding audit will run after campaign LLM calls.")
        else:
            display(grounding_audit)
            assert grounding_audit["exists"].all()
            assert grounding_audit["actual matches"].all()
            assert grounding_audit["benchmark matches"].all()
        """
    ),
    markdown(
        """
        ## 27. Objective Synthesis And Recommendation Narration

        The synthesis sees only deterministic decisions plus validated campaign insights.
        The narrator then sees the synthesis and the already-calculated budget scenario.
        Neither stage can create or alter budget numbers.
        """
    ),
    code(
        """
        objective_insight = None
        stakeholder_report = None
        if RUN_LLM:
            synthesis_payload = {
                "cycle_id": "sample2-completed-cycle",
                "objective": FOCUS_OBJECTIVE,
                "deterministic_campaign_results": compact_records(campaign_scores),
                "campaign_insights": [item.model_dump(mode="json") for item in campaign_insights],
            }
            objective_insight, synthesis_source, _ = cached_parse(
                "objective_synthesis", "synthesis", synthesis_payload,
                ObjectivePortfolioInsight,
            )
            narrator_payload = {
                "cycle_id": "sample2-completed-cycle",
                "objective": FOCUS_OBJECTIVE,
                "objective_insight": objective_insight.model_dump(mode="json"),
                "budget_scenario": {
                    "total_units": TOTAL_UNITS,
                    "exploit_units": EXPLOIT_UNITS,
                    "explore_units": EXPLORE_UNITS,
                    "allocations": allocations.to_dict(orient="records"),
                    "tests": exploration_tests.to_dict(orient="records"),
                    "unallocated_units": unallocated,
                    "operational": False,
                },
            }
            stakeholder_report, narrator_source, _ = cached_parse(
                "objective_report", "narrator", narrator_payload,
                ObjectiveStakeholderReport,
            )
            print(f"Synthesis source = {synthesis_source}; narrator source = {narrator_source}")
            display(JSON(objective_insight.model_dump(mode="json"), expanded=True))
            display(JSON(stakeholder_report.model_dump(mode="json"), expanded=True))
        else:
            print("Synthesis and recommendation narration skipped until RUN_LLM = True.")
        """
    ),
    markdown(
        """
        ## 28. Final Post-Eid Decision Card

        This table remains available offline. The optional LLM can explain it, but cannot
        replace it.
        """
    ),
    code(
        """
        final_post_eid = pd.DataFrame([{
            "campaign": POST_EID_NAME,
            "objective": FOCUS_OBJECTIVE,
            "raw evidence": f"{successes} created orders / {mature} mature conversations",
            "unresolved excluded": f"{unresolved} / {observed}",
            "raw score": post_row["raw_score"],
            "corrected score": post_row["corrected_score"],
            "corrected range": f"{post_row['corrected_score_low']:.2%} to {post_row['corrected_score_high']:.2%}",
            "same-objective benchmark": post_row["benchmark_score"],
            "favorable lift range": f"{post_row['lift_low']:+.2%} to {post_row['lift_high']:+.2%}",
            "probability better": post_row["probability_better"],
            "decision": post_row["decision"].upper(),
            "next action": "Run the named 5% versus 10% lookalike test; do not scale yet.",
            "semantic evidence": "41/63 high intent; 30/63 had barriers; schema v1 only.",
            "data status": "Illustrative, non-operational until population reconciliation is understood.",
        }])
        display(final_post_eid.style.format({
            "raw score": "{:.2%}", "corrected score": "{:.2%}",
            "same-objective benchmark": "{:.2%}", "probability better": "{:.2%}",
        }))

        if stakeholder_report is not None:
            display(Markdown("### LLM Executive Summary"))
            display(Markdown(stakeholder_report.executive_summary))
        """
    ),
    markdown(
        """
        ## 29. Calculation And Responsibility Ledger

        | Stage | Evidence | Post-Eid output | Why it matters | Owner |
        |---|---|---|---|---|
        | Eligibility | 63 observed, 11 unresolved | 52 mature | Avoids false failures | Deterministic |
        | Raw score | 38 / 52 | 73.08% | Describes observed sample | Deterministic |
        | Raw interval | 38 successes, 52 trials | 59.75% to 83.23% | Shows raw uncertainty | Deterministic |
        | Peer evidence | 58 / 77 from two other lead campaigns | 75.32% raw | Adds objective-specific context | Deterministic |
        | Half-count adjustment | +0.5 success, +0.5 failure | 75.00% | Avoids degenerate 0% or 100% prior | Deterministic |
        | Empirical prior | peer center and conservative strength | alpha 28.875, beta 9.625 | Controls how much peers contribute | Deterministic |
        | Corrected score | prior + Post-Eid counts | 73.90% | Reduces small-sample overreaction | Deterministic |
        | Corrected range | posterior simulation | about 64.6% to 82.2% | Shows plausible campaign rate | Deterministic |
        | Favorable lift | campaign draws minus peer draws | range crosses zero | Prevents a noisy winner call | Deterministic |
        | Decision | full lift range | HOLD | Connects uncertainty to action | Deterministic |
        | Conversation semantics | 63 schema-v1 records | intent, barriers, products, helpfulness | Suggests why and what to test | LLM extraction + deterministic aggregation |
        | Budget | locked decisions and 70/30 policy | 70 unallocated, 30 explore | Avoids forced scaling | Deterministic |
        | Campaign explanation | exact evidence payload | structured insight | Makes evidence understandable | Optional LLM |
        | Objective synthesis | validated campaign insights | patterns and tests | Builds strategy across lead campaigns | Optional LLM |
        | Stakeholder report | synthesis + locked budget | role-specific narrative | Communicates without changing numbers | Optional LLM |

        ## Final Reading Rule

        Do not start with the largest raw rate. Start with eligible evidence, then read the
        corrected score, benchmark, lift range, and range-based decision. Use conversation
        semantics to form a hypothesis and design the next test. Use the LLM only to
        explain the locked result.
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
