"""Generate one executed-ready learning notebook per Meta objective."""

from pathlib import Path
from textwrap import dedent
from typing import Dict

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

from .paths import PACKAGE_DIR


NOTEBOOK_DIR = PACKAGE_DIR / "notebooks"

OBJECTIVE_CONTENT: Dict[str, Dict[str, str]] = {
    "OUTCOME_AWARENESS": {
        "number": "01",
        "title": "Awareness Objective",
        "plain_job": "Create visibility and measurable response before expecting a sale.",
        "metric_note": (
            "Link click-through rate is an available response proxy. It does not prove "
            "brand awareness lift, which would require a brand-lift study or comparable survey."
        ),
        "semantic_note": (
            "Use message alignment, customer needs, and value drivers to learn whether the "
            "attention attracted by the ad matches its promise. Purchase intent is downstream "
            "diagnostic evidence, not the awareness score."
        ),
    },
    "OUTCOME_ENGAGEMENT": {
        "number": "02",
        "title": "Engagement Objective",
        "plain_job": "Generate measurable interaction with the ad or content.",
        "metric_note": (
            "The sample provides link clicks, so link click-through rate is the available "
            "interaction proxy. Richer reactions, saves, shares, and video completion are not "
            "available in this dataset."
        ),
        "semantic_note": (
            "Conversation purpose, customer need, and ad-message alignment help distinguish "
            "useful engagement from curiosity that does not match the advertised promise."
        ),
    },
    "OUTCOME_LEADS": {
        "number": "03",
        "title": "Leads Objective",
        "plain_job": "Generate WhatsApp conversations that progress to a created order.",
        "metric_note": (
            "Only mature conversations enter the denominator. A created order is progression, "
            "not proof of delivery or revenue. Those later outcomes remain supporting evidence."
        ),
        "semantic_note": (
            "Purchase intent, price blocking, barrier resolution, next-step agreement, and agent "
            "helpfulness can explain why conversations did or did not progress to an order."
        ),
    },
    "OUTCOME_SALES": {
        "number": "04",
        "title": "Sales Objective",
        "plain_job": "Generate delivered customer outcomes with acceptable revenue return.",
        "metric_note": (
            "The primary score is customer-level: each mature customer is counted once within an "
            "entity, even when that customer has multiple conversations. Net ROAS is kept separate "
            "to represent revenue efficiency."
        ),
        "semantic_note": (
            "Intent, delivery readiness, agreement, barriers, value drivers, and agent behavior "
            "help explain observed delivery performance. They cannot replace delivered outcomes."
        ),
    },
}


def markdown(value: str):
    return new_markdown_cell(dedent(value).strip())


def code(value: str):
    return new_code_cell(dedent(value).strip())


def semantic_learning_cells():
    return [
        markdown('''
            ### 12.1 Define Conversation Quality Before Counting

            Each objective has one explicit rule. These definitions are MVP assumptions that
            need transcript review. They do not combine labels using subjective weights.
            A positive evidence-bearing label must cite message indexes. All required components
            must be known; an unknown component leaves the combined result unknown.

            | Objective | Success definition |
            |---|---|
            | Awareness | Central need aligned with the ad; partial/mismatch are negative |
            | Engagement | Commercial inquiry, medium/high specificity, consideration/checkout, aligned/partial ad match |
            | Leads | Commercial inquiry, medium/high specificity and medium/high purchase intent |
            | Sales | Commercial inquiry, complete sales agreement and accepted next step |

            Commercial inquiry means purchase, product information, promotion information or
            delivery information. These semantic rates describe customers who chatted. They do
            not measure awareness lift or engagement among everyone who viewed an ad.
        '''),
        code('''
            display(Markdown(f"**This objective:** {contract.semantic.metric}: {contract.semantic.definition}"))
            objective_audit = result.semantic_evidence.loc[
                result.semantic_evidence["objective"].eq(FOCUS_OBJECTIVE)
            ].copy()
            display(objective_audit.groupby(["entity_level", "exclusion_reason"], dropna=False).size().rename("Records").reset_index())
        '''),
        markdown('''
            ### 12.2 Inspect Selection And Raw Evidence

            Choose the earliest mature conversation per customer within each entity, using
            started_at then conversation ID (missing timestamps last). Choose before checking
            labels. Later records do not replace an earlier unknown or missing result.
            This prevents repeat chats from multiplying a customer's weight. Open outcomes
            stay out of this completed-cycle score. A customer can still appear across entities.

            The local audit below connects every selection and exclusion to a conversation ID.
            No transcript or customer identity is passed to the recommendation model.
        '''),
        code('''
            campaign_audit = objective_audit[objective_audit["entity_level"].eq("campaign")].copy()
            display(campaign_audit[[
                "campaign_id", "conversation_id", "metric", "selected",
                "exclusion_reason", "signal_available", "success"
            ]])
            semantic_tables = {}
            for level, frame in result.scorecards.items():
                focused = frame[frame["objective"].eq(FOCUS_OBJECTIVE)].reset_index(drop=True)
                semantic_tables[level] = pd.concat([
                    focused[["entity_id", "entity_name", "campaign_name"]],
                    pd.json_normalize(focused["semantic_score"])
                ], axis=1)
            quality = semantic_tables["campaign"]
            display(quality[[
                "entity_name", "eligible_customers", "successes", "trials",
                "unknown_customers", "missing_customers", "raw_rate", "evidence_status"
            ]].style.format({"raw_rate": "{:.2%}"}, na_rep="Unknown"))
            assert (quality["trials"] + quality["unknown_customers"] + quality["missing_customers"]).equals(quality["eligible_customers"])
        '''),
        markdown('''
            ### 12.3 Calculate The Corrected Quality And Range

            With two valid same-objective peers, learn the prior with the same Empirical-Bayes
            method used earlier. Exclude the entity itself. Semantic metrics differ across
            objectives, so the shared Link CTR fallback does not apply here.

            With fewer peers, use Beta(0.5, 0.5), a weak Jeffreys prior: half a success and half a
            failure worth of mathematical smoothing, not real customer records. Show its range
            but no peer benchmark, lift or probability-better claim.

            ```text
            raw rate = successes / assessable customers
            posterior alpha = prior alpha + successes
            posterior beta = prior beta + assessable customers - successes
            corrected rate = posterior alpha / (posterior alpha + posterior beta)
            95% credible range = 2.5th and 97.5th percentiles of posterior draws
            ```

            The code uses 5,000 repeatable draws. With a valid peer prior, favorable lift above
            zero across the whole range means supportive; below zero means concerning; crossing
            zero means neutral. Fewer than 10 assessable customers means insufficient evidence.
            Ten is an MVP evidence floor, not a universal statistical guarantee.
        '''),
        code('''
            for level, table in semantic_tables.items():
                display(Markdown(f"**{level.title()}: raw evidence through posterior**"))
                display(table[[
                    "entity_name", "metric", "successes", "trials", "prior_source", "peer_count",
                    "prior_alpha", "prior_beta", "posterior_alpha", "posterior_beta",
                    "raw_rate", "corrected_rate", "range_low", "range_high",
                    "benchmark", "lift_low", "lift_high", "probability_better", "status"
                ]].style.format({
                    **{c: "{:.2%}" for c in ["raw_rate", "corrected_rate", "range_low", "range_high", "benchmark", "probability_better"]},
                    **{c: "{:.3f}" for c in ["prior_alpha", "prior_beta", "posterior_alpha", "posterior_beta"]},
                    "lift_low": "{:+.2%}", "lift_high": "{:+.2%}"
                }, na_rep="Not available"))
                available = table[table["trials"].gt(0)]
                calculated = available["posterior_alpha"] / (available["posterior_alpha"] + available["posterior_beta"])
                assert np.allclose(calculated, available["corrected_rate"])
        '''),
        markdown('''
            ### 12.4 Compare Quality Ranges

            Read the point together with the line. A high point with a wide range has limited
            evidence. These ranges assume the extracted labels are correct; they do not account
            for systematic LLM mistakes. Overlapping ranges should not be presented as proven
            winners. Primary outcome scores remain separate because their denominators and
            business meanings differ.
        '''),
        code('''
            plotted = quality.dropna(subset=["corrected_rate"])
            if not plotted.empty:
                base = alt.Chart(plotted).encode(y=alt.Y("entity_name:N", title=None))
                bounds = base.mark_rule(strokeWidth=4, color="#218380").encode(
                    x=alt.X("range_low:Q", title="Conversation quality", axis=alt.Axis(format=".0%"), scale=alt.Scale(domain=[0, 1])),
                    x2="range_high:Q",
                    tooltip=["entity_name", "successes", "trials", "prior_source", "status"]
                )
                points = base.mark_point(filled=True, color="#20262e", size=90).encode(x="corrected_rate:Q")
                display((bounds + points).properties(width=760, height=max(150, 45 * len(plotted))))
        '''),
        markdown('''
            ### 12.5 Check Whether Quality Is Associated With Outcomes

            The next table compares orders and deliveries between semantic-positive,
            semantic-negative and unknown selected conversations. It is a retrospective
            association, not causal evidence or an independent predictive evaluation: the
            extractor saw the full conversation, including historical checkout steps.
            This is a starting point for manually reviewing whether the definitions are useful.
            Small groups and missing labels can make the differences unstable.
        '''),
        code('''
            selected = campaign_audit[campaign_audit["selected"]].copy()
            selected["Semantic result"] = selected["success"].map({True: "positive", False: "negative"}).fillna("unknown")
            associations = selected.groupby(["campaign_id", "Semantic result"]).agg(
                customers=("conversation_id", "size"), orders=("has_order", "sum"), deliveries=("is_delivered", "sum")
            ).reset_index()
            associations["order_rate"] = associations["orders"] / associations["customers"]
            associations["delivery_rate"] = associations["deliveries"] / associations["customers"]
            display(associations.style.format({"order_rate": "{:.2%}", "delivery_rate": "{:.2%}"}))
        '''),
        markdown('''
            ### 12.6 How Primary And Conversation Evidence Allocate Budget

            Every campaign with both required components receives a share of its objective's
            full envelope:

            ```text
            priority = primary probability_better x semantic 95% lower bound
            weight = priority / sum of campaign priorities in the objective
            campaign budget = full objective envelope x weight
            ```

            Objective envelopes retain previous-cycle spend shares because their primary and
            semantic metrics are not comparable across objectives. Within an objective, action
            labels do not gate this POC allocation. Missing either component gives the campaign
            zero allocation. The priority product is a policy index, not a joint probability or
            a learned return-on-spend optimum.

            Review labels against transcripts before operational use. No manual validation is
            claimed here. The table shows exactly how much this assumption changes the budget.
        '''),
        code('''
            impact = pd.DataFrame([
                {"Campaign": item.campaign_name,
                 "Primary probability": item.primary_probability_component,
                 "Quality lower bound": item.semantic_priority,
                 "Priority product": item.allocation_priority,
                 "Normalized weight": item.allocation_weight,
                 "Basis": item.allocation_basis,
                 "Previous-spend scenario": item.previous_spend_budget_units,
                 "Two-factor scenario": item.recommended_budget_units,
                 "Change": item.recommended_budget_units - item.previous_spend_budget_units}
                for item in result.allocations if item.objective == FOCUS_OBJECTIVE
            ])
            display(impact.style.format({
                "Primary probability": "{:.2%}", "Quality lower bound": "{:.2%}",
                "Priority product": "{:.4f}", "Normalized weight": "{:.2%}",
                "Previous-spend scenario": "{:.3f}", "Two-factor scenario": "{:.3f}",
                "Change": "{:+.3f}"
            }, na_rep="Not available"))
        '''),
    ]


def build_notebook(objective: str, content: Dict[str, str]):
    cells = [
        markdown(
            f"""
            # {content['title']}: Completed-Cycle Learning Notebook

            **Business job:** {content['plain_job']}

            This notebook follows the objective from raw Meta and WhatsApp evidence through
            objective-specific KPIs, Empirical Bayes with an explicit benchmark hierarchy,
            efficiency, deterministic action, budget allocation, child-entity evidence, and
            conversation diagnostics.

            It is an explanatory report for a completed cycle. It does not optimize a live
            campaign and does not ask an LLM to calculate scores or budget.
            """
        ),
        markdown(
            """
            ## 1. Scope And Reading Rules

            1. `objective` is the only campaign grouping used for evaluation.
            2. Paid-attributed WhatsApp outcomes are treated as complete for this MVP.
            3. Organic/direct conversations are outside paid campaign scoring.
            4. Active and stuck-pending outcomes remain visible but are excluded from mature rates.
            5. The primary score measures outcome effectiveness; efficiency remains separate.
            6. Small samples lean toward selected peers and always show a range. Same-objective
               peers are preferred; Awareness and Engagement may share Link CTR evidence when
               their own objective has too few peers.
            7. Conversation signals create a separate quality score and can prioritize exploration.
               Primary outcome scores and final actions remain driven by structured evidence.
            8. Budget is assigned only to campaigns; child levels guide execution without
               double-counting the same money.
            """
        ),
        code(
            f"""
            from pathlib import Path
            import sys

            import altair as alt
            import numpy as np
            import pandas as pd
            from IPython.display import Markdown, display

            candidates = [Path.cwd(), *Path.cwd().parents]
            ROOT = next(path for path in candidates if (path / "src_mvp").exists())
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))

            from src_mvp.config import load_budget_policy, load_objectives
            from src_mvp.pipeline import run_mvp
            from src_mvp.statistics import fit_beta_prior

            FOCUS_OBJECTIVE = "{objective}"
            result = run_mvp(output_directory=ROOT / "src_mvp" / "outputs")
            registry = load_objectives()
            policy = load_budget_policy()
            contract = registry.objectives[FOCUS_OBJECTIVE]
            all_campaigns = result.scorecards["campaign"].copy()
            campaigns = all_campaigns.loc[
                all_campaigns["objective"].eq(FOCUS_OBJECTIVE)
            ].copy()
            allocations = {{item.campaign_id: item for item in result.allocations}}
            objective_tests = [
                item for item in result.exploration_tests
                if item.objective == FOCUS_OBJECTIVE
            ]

            DECISION_COLORS = {{
                "scale": "#16815d",
                "hold": "#d68c16",
                "kill": "#c44536",
                "insufficient_evidence": "#6b7280",
            }}
            alt.data_transformers.disable_max_rows()

            print(f"Repository: {{ROOT}}")
            print(f"Objective: {{FOCUS_OBJECTIVE}}")
            print(f"Campaigns in scope: {{len(campaigns)}}")
            """
        ),
        markdown(
            f"""
            ## 2. Objective Contract

            The objective determines the business question and the one primary statistical score.
            It also selects one efficiency metric, which remains a separate gate.

            **Important limitation:** {content['metric_note']}
            """
        ),
        code(
            """
            contract_table = pd.DataFrame([
                ["Business job", contract.business_job],
                ["Success question", contract.success_question],
                ["Primary metric", contract.primary_metric],
                ["Numerator", contract.primary_numerator],
                ["Denominator", contract.primary_denominator],
                ["Better primary direction", contract.primary_direction],
                ["Efficiency metric", contract.efficiency_metric],
                ["Better efficiency direction", contract.efficiency_direction],
                ["Minimum primary trials", contract.minimum_trials],
                ["Minimum peer entities", contract.minimum_peer_entities],
                ["Configured fallback group", contract.fallback_benchmark_group or "None"],
                ["Semantic metric", contract.semantic.metric],
                ["Semantic definition", contract.semantic.definition],
            ], columns=["Contract element", "Value"])
            display(contract_table.style.hide(axis="index"))
            """
        ),
        markdown(
            """
            ## 3. Campaign Inventory And Delivery

            Spend and delivery volume describe campaign size; they do not prove success. The
            primary outcome score below evaluates quality relative to the selected compatible
            benchmark. Portfolio-wide context remains descriptive only.
            """
        ),
        code(
            """
            inventory = campaigns[[
                "campaign_name", "entity_status", "media_start", "media_end",
                "running_days", "active_days", "spend", "impressions", "link_clicks",
                "observed_conversations", "mature_conversations",
                "unresolved_conversations",
            ]].rename(columns={
                "campaign_name": "Campaign", "entity_status": "Status",
                "media_start": "First delivery", "media_end": "Last delivery",
                "running_days": "Calendar days", "active_days": "Days with delivery",
                "spend": "Spend", "impressions": "Impressions",
                "link_clicks": "Link clicks",
                "observed_conversations": "Paid conversations",
                "mature_conversations": "Mature",
                "unresolved_conversations": "Unresolved",
            })
            display(inventory.style.format({"Spend": "{:,.2f}", "Impressions": "{:,.0f}"}))
            """
        ),
        markdown(
            """
            ## 4. Raw Primary Evidence

            The raw score is the directly observed rate:

            ```text
            raw rate = objective successes / eligible objective trials
            ```

            These counts remain beside every corrected score so the modeled result can always be
            audited back to real evidence.
            """
        ),
        code(
            """
            raw_evidence = campaigns[[
                "campaign_name", "score_successes", "score_trials", "raw_rate",
                "observed_conversations", "mature_conversations",
                "unresolved_conversations", "evidence_status",
            ]].rename(columns={
                "campaign_name": "Campaign", "score_successes": "Successes",
                "score_trials": "Eligible trials", "raw_rate": "Raw rate",
                "observed_conversations": "Observed conversations",
                "mature_conversations": "Mature conversations",
                "unresolved_conversations": "Unresolved conversations",
                "evidence_status": "Evidence status",
            })
            display(raw_evidence.style.format({"Raw rate": "{:.2%}"}, na_rep="Not available"))

            maturity_long = inventory[["Campaign", "Mature", "Unresolved"]].melt(
                "Campaign", var_name="Outcome maturity", value_name="Conversations"
            )
            maturity_chart = alt.Chart(maturity_long).mark_bar().encode(
                y=alt.Y("Campaign:N", sort="-x", title=None),
                x=alt.X("Conversations:Q", title="WhatsApp conversations"),
                color=alt.Color(
                    "Outcome maturity:N",
                    scale=alt.Scale(domain=["Mature", "Unresolved"], range=["#218380", "#d9a441"]),
                    legend=alt.Legend(orient="top"),
                ),
                tooltip=["Campaign", "Outcome maturity", "Conversations"],
            ).properties(width=760, height=max(120, len(campaigns) * 42))
            display(maturity_chart)
            """
        ),
        markdown(
            """
            ## 5. Leave-One-Out Peer Evidence And Prior

            The benchmark hierarchy is explicit:

            1. Use other campaigns with the same objective when at least two are valid.
            2. If those peers are insufficient, Awareness and Engagement may use their shared
               `upper_funnel_link_ctr` group because both have the same Link CTR numerator,
               denominator, and direction.
            3. Mark this fallback `provisional` and cap the final action at `KEEP_AS_TEST`.
            4. Show the all-portfolio same-metric rate only as context. It never enters the prior,
               corrected score, uncertainty range, or funding decision.

            The campaign being scored is always removed from its own benchmark.

            ```text
            adjusted peer center = (peer successes + 0.5) / (peer trials + 1)
            prior strength = conservative equivalent evidence allowed from peers
            prior alpha = peer center x prior strength
            prior beta = (1 - peer center) x prior strength
            ```

            The prior is learned from the selected peer evidence. It is not a business target.
            At least two valid compatible peers are required; otherwise the result is insufficient
            evidence.
            """
        ),
        code(
            """
            prior_rows = []
            for _, row in campaigns.iterrows():
                same_objective_peers = all_campaigns.loc[
                    all_campaigns["objective"].eq(FOCUS_OBJECTIVE)
                    & all_campaigns["entity_id"].ne(row["entity_id"])
                ].copy()
                compatible_objectives = [
                    name for name, candidate in registry.objectives.items()
                    if contract.fallback_benchmark_group
                    and candidate.fallback_benchmark_group == contract.fallback_benchmark_group
                    and candidate.primary_metric == contract.primary_metric
                    and candidate.primary_numerator == contract.primary_numerator
                    and candidate.primary_denominator == contract.primary_denominator
                    and candidate.primary_direction == contract.primary_direction
                ]
                if row["benchmark_scope"] == "same_objective":
                    selected_objectives = [FOCUS_OBJECTIVE]
                elif row["benchmark_scope"] == "shared_primary_kpi_group":
                    selected_objectives = compatible_objectives
                else:
                    selected_objectives = []
                peers = all_campaigns.loc[
                    all_campaigns["objective"].isin(selected_objectives)
                    & all_campaigns["entity_id"].ne(row["entity_id"])
                ].copy()
                for frame in [same_objective_peers, peers]:
                    frame["_successes"] = pd.to_numeric(
                        frame[contract.primary_numerator], errors="coerce"
                    )
                    frame["_trials"] = pd.to_numeric(
                        frame[contract.primary_denominator], errors="coerce"
                    )
                same_objective_peers = same_objective_peers.loc[
                    same_objective_peers["_trials"].gt(0)
                    & same_objective_peers["_successes"].ge(0)
                    & same_objective_peers["_successes"].le(same_objective_peers["_trials"])
                ]
                peers = peers.loc[
                    peers["_trials"].gt(0)
                    & peers["_successes"].ge(0)
                    & peers["_successes"].le(peers["_trials"])
                ]
                item = {
                    "Campaign": row["campaign_name"],
                    "Own evidence": f"{row['score_successes']:.0f} / {row['score_trials']:.0f}",
                    "Same-objective peers": len(same_objective_peers),
                    "Selected peers": len(peers),
                    "Benchmark source": row["benchmark_scope"],
                    "Benchmark quality": row["benchmark_quality"],
                    "Peer evidence": (
                        f"{peers['_successes'].sum():.0f} / {peers['_trials'].sum():.0f}"
                        if len(peers) else "None"
                    ),
                    "Prior center": np.nan,
                    "Prior strength": np.nan,
                    "Prior alpha": np.nan,
                    "Prior beta": np.nan,
                    "Posterior alpha": np.nan,
                    "Posterior beta": np.nan,
                    "Corrected rate": row["corrected_rate"],
                    "Portfolio context": row["portfolio_context_benchmark"],
                }
                if len(peers) >= contract.minimum_peer_entities and row["score_trials"] > 0:
                    prior = fit_beta_prior(peers["_successes"], peers["_trials"])
                    failures = row["score_trials"] - row["score_successes"]
                    item.update({
                        "Prior center": prior.mean,
                        "Prior strength": prior.strength,
                        "Prior alpha": prior.alpha,
                        "Prior beta": prior.beta,
                        "Posterior alpha": prior.alpha + row["score_successes"],
                        "Posterior beta": prior.beta + failures,
                    })
                prior_rows.append(item)

            prior_table = pd.DataFrame(prior_rows)
            display(prior_table.style.format({
                "Prior center": "{:.2%}", "Prior strength": "{:.2f}",
                "Prior alpha": "{:.2f}", "Prior beta": "{:.2f}",
                "Posterior alpha": "{:.2f}", "Posterior beta": "{:.2f}",
                "Corrected rate": "{:.2%}", "Portfolio context": "{:.2%}",
            }, na_rep="Insufficient peers"))
            """
        ),
        markdown(
            """
            ## 6. Raw Rate, Corrected Rate, Benchmark, And Range

            The corrected rate is a weighted compromise between peer evidence and the campaign's
            own evidence. Small samples move more toward the selected peer center; large samples
            retain more of their raw result. The horizontal line is the campaign's 95% plausible
            score range. The portfolio-context point is displayed for orientation only.
            """
        ),
        code(
            """
            score_chart_data = campaigns.dropna(subset=["corrected_rate"]).copy()
            if score_chart_data.empty:
                display(Markdown(
                    "**No corrected campaign scores:** neither the same objective nor a configured "
                    "compatible fallback group has two valid peers."
                ))
            else:
                y = alt.Y("campaign_name:N", sort="-x", title=None)
                ranges = alt.Chart(score_chart_data).mark_rule(strokeWidth=4, color="#8b95a5").encode(
                    y=y,
                    x=alt.X("range_low:Q", title="Primary rate", axis=alt.Axis(format=".0%")),
                    x2="range_high:Q",
                    tooltip=[
                        alt.Tooltip("campaign_name:N", title="Campaign"),
                        alt.Tooltip("range_low:Q", title="95% low", format=".2%"),
                        alt.Tooltip("range_high:Q", title="95% high", format=".2%"),
                    ],
                )
                points = score_chart_data[[
                    "campaign_name", "raw_rate", "corrected_rate", "benchmark",
                    "portfolio_context_benchmark"
                ]].melt("campaign_name", var_name="Estimate", value_name="Rate")
                point_layer = alt.Chart(points).mark_point(filled=True, size=100).encode(
                    y=y,
                    x=alt.X("Rate:Q", axis=alt.Axis(format=".0%")),
                    color=alt.Color(
                        "Estimate:N",
                        scale=alt.Scale(
                            domain=[
                                "raw_rate", "corrected_rate", "benchmark",
                                "portfolio_context_benchmark"
                            ],
                            range=["#2f6f8f", "#16815d", "#d68c16", "#7b61a8"],
                        ),
                        legend=alt.Legend(orient="top", title=None),
                    ),
                    shape=alt.Shape("Estimate:N", legend=None),
                    tooltip=[
                        alt.Tooltip("campaign_name:N", title="Campaign"),
                        alt.Tooltip("Estimate:N"),
                        alt.Tooltip("Rate:Q", format=".2%"),
                    ],
                )
                display((ranges + point_layer).properties(
                    width=760, height=max(140, len(score_chart_data) * 52)
                ))
            """
        ),
        markdown(
            """
            ## 7. Probability Better And The Funding Decision

            For each scored campaign, the engine creates 5,000 plausible campaign rates and 5,000
            plausible peer rates. `probability_better` is the fraction where favorable lift is
            above zero.

            ```text
            higher-is-better lift = campaign draw - benchmark draw
            lower-is-better lift  = benchmark draw - campaign draw

            SCALE: lift low > 0
            KILL:  lift high < 0
            HOLD:  lift range crosses 0
            ```

            Probability better supports interpretation and the two-factor budget priority. The complete lift
            range, not the probability alone, controls the statistical decision. A provisional
            fallback can still calculate a statistical direction, but its final funding action is
            always capped at `KEEP_AS_TEST`.
            """
        ),
        code(
            """
            decision_table = campaigns[[
                "campaign_name", "raw_rate", "corrected_rate", "benchmark",
                "benchmark_scope", "benchmark_quality", "portfolio_context_benchmark",
                "expected_lift", "lift_low", "lift_high", "probability_better",
                "statistical_decision", "recommended_action",
            ]].rename(columns={
                "campaign_name": "Campaign", "raw_rate": "Raw rate",
                "corrected_rate": "Corrected rate", "benchmark": "Benchmark",
                "benchmark_scope": "Benchmark source",
                "benchmark_quality": "Benchmark quality",
                "portfolio_context_benchmark": "Portfolio context",
                "expected_lift": "Expected lift", "lift_low": "Lift low",
                "lift_high": "Lift high", "probability_better": "Probability better",
                "statistical_decision": "Statistical decision",
                "recommended_action": "Final action",
            })
            display(decision_table.style.format({
                "Raw rate": "{:.2%}", "Corrected rate": "{:.2%}",
                "Benchmark": "{:.2%}", "Expected lift": "{:+.2%}",
                "Lift low": "{:+.2%}", "Lift high": "{:+.2%}",
                "Probability better": "{:.2%}", "Portfolio context": "{:.2%}",
            }, na_rep="Not available"))

            lift_data = campaigns.dropna(subset=["lift_low", "lift_high"]).copy()
            if not lift_data.empty:
                lift_ranges = alt.Chart(lift_data).mark_rule(strokeWidth=5).encode(
                    y=alt.Y("campaign_name:N", sort="-x", title=None),
                    x=alt.X("lift_low:Q", title="Favorable lift vs peer", axis=alt.Axis(format="+.0%")),
                    x2="lift_high:Q",
                    color=alt.Color(
                        "statistical_decision:N",
                        scale=alt.Scale(
                            domain=list(DECISION_COLORS), range=list(DECISION_COLORS.values())
                        ),
                        legend=alt.Legend(orient="top", title="Decision"),
                    ),
                    tooltip=[
                        alt.Tooltip("campaign_name:N", title="Campaign"),
                        alt.Tooltip("lift_low:Q", format="+.2%"),
                        alt.Tooltip("expected_lift:Q", format="+.2%"),
                        alt.Tooltip("lift_high:Q", format="+.2%"),
                        alt.Tooltip("probability_better:Q", format=".2%"),
                    ],
                )
                expected = alt.Chart(lift_data).mark_point(
                    filled=True, color="#20262e", size=90
                ).encode(y=alt.Y("campaign_name:N", sort="-x"), x="expected_lift:Q")
                zero = alt.Chart(pd.DataFrame({"zero": [0]})).mark_rule(
                    strokeDash=[5, 4], color="#20262e"
                ).encode(x="zero:Q")
                display((lift_ranges + expected + zero).properties(
                    width=760, height=max(140, len(lift_data) * 52)
                ))
            """
        ),
        markdown(
            """
            ## 8. Efficiency Is A Separate Gate

            The primary score answers whether the objective outcome was achieved. Efficiency asks
            what it cost, or what revenue return it produced. The peer benchmark is the median
            efficiency of other campaigns with this objective.

            The Awareness-plus-Engagement fallback does **not** combine efficiency metrics:
            Awareness keeps CPM, while Engagement keeps CPC. Their shared Link CTR is useful for
            stabilizing response evidence, but their costs answer different business questions.

            A statistical `SCALE` is promoted to final `SCALE` only when efficiency is at least as
            good as its peer benchmark. Efficiency is not mixed into the primary score.
            """
        ),
        code(
            """
            efficiency_table = campaigns[[
                "campaign_name", "efficiency_metric", "efficiency_direction",
                "efficiency_value", "efficiency_benchmark", "efficiency_peer_count",
                "efficiency_comparison",
            ]].rename(columns={
                "campaign_name": "Campaign", "efficiency_metric": "Metric",
                "efficiency_direction": "Better direction", "efficiency_value": "Value",
                "efficiency_benchmark": "Peer median", "efficiency_peer_count": "Peers",
                "efficiency_comparison": "Comparison",
            })
            display(efficiency_table.style.format({
                "Value": "{:,.3f}", "Peer median": "{:,.3f}"
            }, na_rep="Not available"))

            efficiency_long = efficiency_table.melt(
                id_vars=["Campaign", "Metric", "Better direction", "Comparison"],
                value_vars=["Value", "Peer median"],
                var_name="Measure", value_name="Efficiency",
            ).dropna(subset=["Efficiency"])
            if not efficiency_long.empty:
                efficiency_chart = alt.Chart(efficiency_long).mark_bar().encode(
                    y=alt.Y("Campaign:N", title=None),
                    x=alt.X("Efficiency:Q", title=contract.efficiency_metric.replace("_", " ").title()),
                    yOffset="Measure:N",
                    color=alt.Color(
                        "Measure:N",
                        scale=alt.Scale(domain=["Value", "Peer median"], range=["#2f6f8f", "#d68c16"]),
                        legend=alt.Legend(orient="top", title=None),
                    ),
                    tooltip=["Campaign", "Metric", "Better direction", "Measure", "Efficiency"],
                ).properties(width=760, height=max(140, len(campaigns) * 58))
                display(efficiency_chart)
            """
        ),
        markdown(
            """
            ## 9. Final Campaign Action And Budget

            The statistical decision and evidence status create reporting labels:

            | Statistical evidence | Efficiency | Final action |
            |---|---|---|
            | SCALE | Better or equal to peer | SCALE |
            | SCALE | Worse or unavailable | KEEP_AS_TEST |
            | HOLD | Any | KEEP_AS_TEST |
            | KILL | Any | DO_NOT_FUND |
            | Too little evidence | Any | INSUFFICIENT_EVIDENCE |

            For a `provisional` shared-Link-CTR benchmark, any assessable statistical result is
            capped at `KEEP_AS_TEST`. It cannot trigger `SCALE` or `DO_NOT_FUND`.

            For this POC, those labels do not gate budget. Previous-cycle spend shares preserve
            each objective envelope, then all campaigns with both components share the full
            envelope using `probability_better x semantic range_low`. Missing components receive
            zero; an objective with no valid priorities remains unallocated.
            """
        ),
        code(
            """
            recommendation_rows = []
            for _, row in campaigns.iterrows():
                allocation = allocations[str(row["campaign_id"])]
                recommendation_rows.append({
                    "Campaign": row["campaign_name"],
                    "Benchmark source": row["benchmark_scope"],
                    "Benchmark quality": row["benchmark_quality"],
                    "Statistical decision": row["statistical_decision"],
                    "Efficiency": row["efficiency_comparison"],
                    "Final action": row["recommended_action"],
                    "Budget pool": allocation.budget_pool,
                    "Primary probability": allocation.primary_probability_component,
                    "Quality lower bound": allocation.semantic_priority,
                    "Priority product": allocation.allocation_priority,
                    "Normalized weight": allocation.allocation_weight,
                    "Budget units": allocation.recommended_budget_units,
                    "Previous-spend scenario": allocation.previous_spend_budget_units,
                    "Allocation basis": allocation.allocation_basis,
                    "Portfolio share": allocation.recommended_budget_share,
                    "Reason codes": ", ".join(allocation.reason_codes),
                })
            recommendation_table = pd.DataFrame(recommendation_rows)
            display(recommendation_table.style.format({
                "Budget units": "{:.2f}", "Portfolio share": "{:.2%}",
                "Primary probability": "{:.2%}", "Quality lower bound": "{:.2%}",
                "Priority product": "{:.4f}", "Normalized weight": "{:.2%}"
            }))

            budget_data = recommendation_table[recommendation_table["Budget units"].gt(0)]
            if not budget_data.empty:
                budget_chart = alt.Chart(budget_data).mark_bar().encode(
                    y=alt.Y("Campaign:N", sort="-x", title=None),
                    x=alt.X("Budget units:Q", title="Recommended next-cycle budget units"),
                    color=alt.value("#16815d"),
                    tooltip=["Campaign", "Final action", "Primary probability",
                             "Quality lower bound", "Priority product",
                             alt.Tooltip("Budget units:Q", format=".2f")],
                ).properties(width=760, height=max(130, len(budget_data) * 48))
                display(budget_chart)
            else:
                display(Markdown("**No budget is assigned to this objective under the current evidence rules.**"))
            """
        ),
        markdown(
            """
            ## 10. Named Tests For KEEP_AS_TEST Campaigns

            The score-based budget is independent of action labels. When a funded campaign is
            labelled `KEEP_AS_TEST`, the report also creates a specific hypothesis with a success
            rule, failure rule, and stop rule for learning during the next cycle.
            """
        ),
        code(
            """
            if objective_tests:
                tests_table = pd.DataFrame([
                    {
                        "Campaign": item.campaign_name,
                        "Budget units": item.assigned_budget_units,
                        "Hypothesis": item.hypothesis,
                        "Primary metric": item.primary_metric,
                        "Success rule": item.success_rule,
                        "Failure rule": item.failure_rule,
                        "Stop rule": item.stop_rule,
                    }
                    for item in objective_tests
                ])
                display(tests_table.style.format({"Budget units": "{:.2f}"}))
            else:
                display(Markdown(
                    "No funded KEEP_AS_TEST campaign is present for this objective."
                ))
            """
        ),
        markdown(
            """
            ## 11. Adset, Ad, Creative, And Audience Evidence

            The same objective KPI and benchmark hierarchy are applied at every level.
            Campaign and adset are normal budget-control layers. Ads are run/test/stop candidates.
            Creative and audience views identify reusable patterns; their budgets are not added
            separately.

            A larger corrected score is a leader to investigate, not automatically a winner. The
            range-based decision and final action remain authoritative.
            """
        ),
        code(
            """
            child_rows = []
            for level in ["adset", "ad", "creative", "audience"]:
                frame = result.scorecards[level].loc[
                    result.scorecards[level]["objective"].eq(FOCUS_OBJECTIVE)
                ].copy()
                for _, row in frame.iterrows():
                    child_rows.append({
                        "Level": level,
                        "Campaign": row["campaign_name"],
                        "Entity": row["entity_name"],
                        "Successes": row["score_successes"],
                        "Trials": row["score_trials"],
                        "Raw rate": row["raw_rate"],
                        "Corrected rate": row["corrected_rate"],
                        "Lift low": row["lift_low"],
                        "Lift high": row["lift_high"],
                        "Probability better": row["probability_better"],
                        "Benchmark source": row["benchmark_scope"],
                        "Benchmark quality": row["benchmark_quality"],
                        "Statistical decision": row["statistical_decision"],
                        "Final action": row["recommended_action"],
                        "Spend": row["spend"],
                    })
            child_summary = pd.DataFrame(child_rows)
            display(pd.crosstab(
                [child_summary["Level"]], child_summary["Final action"], margins=True
            ))

            for level in ["adset", "ad", "creative", "audience"]:
                subset = child_summary[child_summary["Level"].eq(level)].copy()
                subset = subset.sort_values(
                    ["Probability better", "Trials"], ascending=[False, False], na_position="last"
                ).head(12)
                display(Markdown(f"### {level.title()} leaders and test candidates"))
                display(subset.style.format({
                    "Raw rate": "{:.2%}", "Corrected rate": "{:.2%}",
                    "Lift low": "{:+.2%}", "Lift high": "{:+.2%}",
                    "Probability better": "{:.2%}", "Spend": "{:,.2f}",
                }, na_rep="Not available"))
            """
        ),
        code(
            """
            child_chart_data = child_summary.dropna(subset=["Lift low", "Lift high"]).copy()
            child_chart_data = child_chart_data.sort_values(
                "Probability better", ascending=False
            ).groupby("Level", as_index=False).head(10)
            for level in ["adset", "ad", "creative", "audience"]:
                level_data = child_chart_data[child_chart_data["Level"].eq(level)]
                if level_data.empty:
                    continue
                base = alt.Chart(level_data)
                child_chart = base.mark_rule(strokeWidth=4).encode(
                    y=alt.Y("Entity:N", sort="-x", title=None),
                    x=alt.X("Lift low:Q", title="Favorable lift vs selected peer", axis=alt.Axis(format="+.0%")),
                    x2="Lift high:Q",
                    color=alt.Color(
                        "Statistical decision:N",
                        scale=alt.Scale(domain=list(DECISION_COLORS), range=list(DECISION_COLORS.values())),
                        legend=alt.Legend(orient="top"),
                    ),
                    tooltip=[
                        "Level", "Campaign", "Entity", "Successes", "Trials",
                        alt.Tooltip("Probability better:Q", format=".2%"),
                        "Final action",
                    ],
                )
                zero = base.mark_rule(color="#20262e", strokeDash=[5, 4]).encode(
                    x=alt.datum(0)
                )
                display(Markdown(f"### {level.title()} favorable-lift ranges"))
                display((child_chart + zero).properties(
                    width=760, height=max(180, len(level_data) * 38)
                ))
            """
        ),
        markdown(
            f"""
            ## 12. What Conversation Signals Contribute

            {content['semantic_note']}

            The semantic artifact is joined back to structured outcomes only after extraction.
            The extraction model did not receive revenue, outcome, customer identity, budget, or
            funding decisions. `unknown` is excluded from assessable denominators rather than
            converted to false.

            `next_step_order_progression_rate` means an agreed next step followed by an observed
            structured order. It is an order-progression proxy, not proof that every promised task
            was completed.

            The following sections calculate a separate objective-specific quality score. These
            full-conversation labels describe historical interest and agreement; they may record
            an agreement followed by cancellation. They are not predictions of later purchases.
            """
        ),
        code(
            """
            diagnostic_columns = [
                "semantic_coverage_rate", "high_purchase_intent_rate",
                "price_blocking_rate", "barrier_resolution_rate",
                "ad_alignment_rate", "agent_helpful_rate",
                "next_step_agreement_rate", "next_step_order_progression_rate",
            ]
            semantic_table = campaigns[[
                "campaign_name", "semantic_conversations", *diagnostic_columns,
                "top_customer_need", "top_barrier", "top_value_driver",
            ]].rename(columns={"campaign_name": "Campaign"})
            display(semantic_table.style.format(
                {column: "{:.2%}" for column in diagnostic_columns},
                na_rep="Unknown / not assessable",
            ))

            heatmap = semantic_table[["Campaign", *diagnostic_columns]].melt(
                "Campaign", var_name="Signal", value_name="Rate"
            ).dropna(subset=["Rate"])
            if not heatmap.empty:
                base = alt.Chart(heatmap).encode(
                    x=alt.X("Signal:N", title=None, axis=alt.Axis(labelAngle=-35)),
                    y=alt.Y("Campaign:N", title=None),
                )
                rectangles = base.mark_rect().encode(
                    color=alt.Color(
                        "Rate:Q", scale=alt.Scale(domain=[0, 0.5, 1], range=["#c44536", "#f2cf63", "#16815d"]),
                        legend=alt.Legend(format=".0%", orient="top"),
                    ),
                    tooltip=["Campaign", "Signal", alt.Tooltip("Rate:Q", format=".2%")],
                )
                labels = base.mark_text(size=11).encode(
                    text=alt.Text("Rate:Q", format=".0%"),
                    color=alt.condition("datum.Rate < 0.25 || datum.Rate > 0.78", alt.value("white"), alt.value("#20262e")),
                )
                display((rectangles + labels).properties(width=760, height=max(110, len(campaigns) * 48)))
            """
        ),
        markdown(
            """
            ## 13. Campaign-By-Campaign Recommendation

            The statements below translate the locked deterministic outputs. They do not create a
            new decision from the semantic signals.
            """
        ),
        code(
            """
            sections = []
            for _, row in campaigns.sort_values("spend", ascending=False).iterrows():
                allocation = allocations[str(row["campaign_id"])]
                probability = (
                    f"{row['probability_better']:.1%}"
                    if pd.notna(row["probability_better"])
                    else "not available"
                )
                lift = (
                    f"[{row['lift_low']:+.1%}, {row['lift_high']:+.1%}]"
                    if pd.notna(row["lift_low"]) else "not available"
                )
                portfolio_context = (
                    f"{row['portfolio_context_benchmark']:.1%}"
                    if pd.notna(row["portfolio_context_benchmark"])
                    else "not available"
                )
                semantic_sentence = (
                    f"Semantic coverage is {row['semantic_coverage_rate']:.1%}; the leading "
                    f"barrier is {row['top_barrier'] or 'not established'} and the leading "
                    f"value driver is {row['top_value_driver'] or 'not established'}."
                    if pd.notna(row["semantic_coverage_rate"])
                    else "Conversation semantics are not yet available for this campaign."
                )
                sections.append(
                    f"### {row['campaign_name']}\\n"
                    f"- **Action:** `{row['recommended_action'].upper()}`; "
                    f"statistical decision `{row['statistical_decision'].upper()}`.\\n"
                    f"- **Evidence:** {row['score_successes']:.0f} successes from "
                    f"{row['score_trials']:.0f} eligible trials; raw {row['raw_rate']:.1%}.\\n"
                    f"- **Uncertainty:** probability better {probability}; lift range {lift}.\\n"
                    f"- **Benchmark:** \`{row['benchmark_scope']}\` with "
                    f"\`{row['benchmark_quality']}\` quality; portfolio context "
                    f"{portfolio_context} is descriptive only.\\n"
                    f"- **Efficiency:** {row['efficiency_metric'].replace('_', ' ')} is "
                    f"`{row['efficiency_comparison']}`.\\n"
                    f"- **Budget:** {allocation.recommended_budget_units:.2f} "
                    f"{result.recommendation_input.cycle.currency} units; priority is "
                    f"{allocation.primary_probability_component:.1%} x "
                    f"{allocation.semantic_priority:.1%}.\\n"
                    f"- **Conversation context:** {semantic_sentence}\\n"
                    f"- **Reason codes:** {', '.join(allocation.reason_codes)}."
                )
            display(Markdown("\\n\\n".join(sections)))
            """
        ),
        markdown(
            """
            ## 14. Objective Summary For Stakeholders

            This final view keeps three audiences aligned:

            - **Business owner:** allocated and unallocated budget, outcome quality, and economics.
            - **Marketing director:** objective achievement, portfolio evidence, and strategic tests.
            - **Performance marketing manager:** campaign, adset, ad, creative, and audience actions.
            """
        ),
        code(
            """
            action_counts = campaigns["recommended_action"].value_counts().to_dict()
            objective_budget = sum(
                allocations[str(campaign_id)].recommended_budget_units
                for campaign_id in campaigns["campaign_id"]
            )
            objective_spend_share = campaigns["spend"].sum() / result.scorecards["campaign"]["spend"].sum()
            objective_envelope = policy.budget_units * objective_spend_share
            objective_unallocated = objective_envelope - objective_budget
            semantic_coverage = (
                campaigns["semantic_conversations"].sum()
                / campaigns["observed_conversations"].sum()
                if campaigns["observed_conversations"].sum() else np.nan
            )

            summary = pd.DataFrame([
                ["Campaigns", len(campaigns)],
                ["Final actions", action_counts],
                ["Previous-cycle objective spend share", objective_spend_share],
                ["Objective budget envelope", objective_envelope],
                ["Allocated to this objective", objective_budget],
                ["Unallocated in this objective", objective_unallocated],
                ["Conversation semantic coverage", semantic_coverage],
                ["Funded named tests", len(objective_tests)],
            ], columns=["Summary item", "Value"])
            display(summary.style.hide(axis="index"))

            display(Markdown(
                "**Decision discipline:** keep final actions as range-based reporting labels, "
                "allocate this POC's full objective envelopes with the explicit two-factor "
                "priority, and interpret overlapping ranges as uncertain rather than proven "
                "superiority."
            ))
            """
        ),
    ]
    semantic_position = next(i for i, cell in enumerate(cells)
                             if cell.cell_type == "markdown" and cell.source.startswith("## 13."))
    cells[semantic_position:semantic_position] = semantic_learning_cells()
    return new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.9"},
            "mvp_objective": objective,
        },
    )


def build_all() -> None:
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    for objective, content in OBJECTIVE_CONTENT.items():
        notebook = build_notebook(objective, content)
        path = NOTEBOOK_DIR / f"{content['number']}_{objective}_Analysis.ipynb"
        nbformat.write(notebook, path)
        print(f"Wrote {path}")


if __name__ == "__main__":
    build_all()
