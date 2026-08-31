"""Build the campaign-level uncertainty and decision notebook."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "CAPI_Sample2_Campaign_Uncertainty_Analysis.ipynb"


def markdown(value: str):
    return nbf.v4.new_markdown_cell(dedent(value).strip())


def code(value: str):
    return nbf.v4.new_code_cell(dedent(value).strip())


cells = [
    markdown(
        """
        # Campaign-Level Performance With Small-Data Uncertainty

        ## Completed-cycle objective

        This notebook evaluates the **12 completed-cycle campaigns** before looking at
        individual adsets, audiences, ads, or creatives. It combines:

        1. Meta delivery and media-cost totals.
        2. Observed WhatsApp orders and revenue.
        3. Campaign-type objectives and peer benchmarks.
        4. Confidence intervals that show how stable the observed KPIs are.
        5. Evidence-aware recommendations for the next cycle.

        The notebook does not use an LLM and does not allow uncertainty calculations to
        hide the Meta-to-WhatsApp reconciliation limitation. Its purpose is to make every
        calculation inspectable by data scientists and business stakeholders.
        """
    ),
    markdown(
        """
        ## 1. Analysis environment

        This cell imports the existing `src_2` normalization and deterministic scorecard
        services. NumPy is used for reproducible bootstrap resampling, pandas for tables,
        and Altair for interval charts. No new statistical dependency is required.
        """
    ),
    code(
        """
        from pathlib import Path
        import math

        import altair as alt
        import numpy as np
        import pandas as pd
        from IPython.display import Markdown, display

        from src_2.analytics import build_assessment_bundle, build_scorecards
        from src_2.domain.models import CampaignType, EvidenceStatus
        from src_2.infrastructure.configuration import load_campaign_type_registry
        from src_2.ingestion import build_data_quality_report, load_sample2, normalize_cycle

        pd.set_option("display.max_columns", 100)
        pd.set_option("display.max_colwidth", 140)
        alt.data_transformers.disable_max_rows()

        CONFIDENCE_LEVEL = 0.95
        Z_95 = 1.959963984540054
        N_BOOTSTRAP = 5_000
        RANDOM_SEED = 42

        REPO_ROOT = Path.cwd()
        if not (REPO_ROOT / "src_2").exists():
            raise RuntimeError("Run this notebook from the Team2-MarketingExpert repository root.")

        INPUT_DIRECTORY = REPO_ROOT / "src_2" / "data" / "input" / "sampe_2"
        print(f"Repository: {REPO_ROOT}")
        print(f"Input data: {INPUT_DIRECTORY}")
        print(f"Bootstrap repetitions: {N_BOOTSTRAP:,}")
        """
    ),
    markdown(
        """
        ## 2. Normalize the completed cycle

        Normalization creates separate tables at their natural grain: campaign, adset,
        ad, creative, daily Meta insight, conversation, order line, and product. Raw
        messages and direct personal details are deliberately excluded from this analytic
        layer. Keeping the facts separate prevents spend or revenue from being duplicated.
        """
    ),
    code(
        """
        raw_payload = load_sample2(INPUT_DIRECTORY)
        canonical = normalize_cycle(raw_payload)

        inventory = pd.DataFrame(
            {
                "Canonical table": [
                    "campaigns", "adsets", "ads", "creatives",
                    "media_daily", "conversations", "order_lines", "products",
                ],
                "Rows": [
                    len(canonical.campaigns), len(canonical.adsets), len(canonical.ads),
                    len(canonical.creatives), len(canonical.media_daily),
                    len(canonical.conversations), len(canonical.order_lines),
                    len(canonical.products),
                ],
                "Natural grain": [
                    "campaign", "adset", "ad", "creative", "ad-day",
                    "conversation", "order-product line", "product",
                ],
            }
        )
        display(inventory)
        """
    ),
    markdown(
        """
        ## 3. Establish the data-quality boundary

        Meta conversation starts and supplied WhatsApp records are counted separately.
        Their ratio is a reconciliation diagnostic, not automatically literal coverage.
        Confidence intervals can quantify random variation inside the supplied WhatsApp
        sample; they cannot correct missing, selectively exported, or differently defined
        conversations.
        """
    ),
    code(
        """
        quality = build_data_quality_report(canonical)

        quality_table = pd.DataFrame(
            {
                "Check": [
                    "Evidence status",
                    "Meta-attributed conversation starts",
                    "Observed Meta-sourced WhatsApp conversations",
                    "Reconciliation ratio",
                    "Event definitions reconciled",
                    "Unmatched campaign references",
                    "Unmatched adset references",
                    "Unmatched ad references",
                ],
                "Value": [
                    quality.status.value,
                    f"{quality.meta_conversation_starts:,}",
                    f"{quality.observed_meta_whatsapp_conversations:,}",
                    f"{quality.reconciliation_ratio:.2%}" if quality.reconciliation_ratio is not None else "Unavailable",
                    quality.event_definitions_reconciled,
                    quality.unmatched_campaigns,
                    quality.unmatched_adsets,
                    quality.unmatched_ads,
                ],
            }
        )
        display(quality_table)
        for warning in quality.warnings:
            print(f"WARNING: {warning}")
        """
    ),
    markdown(
        """
        ## 4. Build the campaign scorecard

        Media, conversations, products, and setup counts are aggregated independently and
        joined only after aggregation. KPIs are calculated from total numerators and
        denominators rather than averaging daily ratios. The same service also builds
        adset, ad, creative, and audience scorecards, but this notebook intentionally uses
        only the campaign table.
        """
    ),
    code(
        """
        raw_scorecards = build_scorecards(canonical)
        registry = load_campaign_type_registry()
        cycle_id = f"cycle_{canonical.cycle_start.date()}_{canonical.cycle_end.date()}"
        assessment_bundle = build_assessment_bundle(
            cycle_id, raw_scorecards, registry, quality
        )
        campaigns = assessment_bundle.scorecards.campaign.copy()

        point_columns = [
            "campaign_name", "campaign_type", "active_days", "spend",
            "impressions", "link_ctr_pct", "meta_conversation_starts",
            "observed_conversations", "orders_created", "delivered_orders",
            "net_revenue", "net_roas", "aov", "delivered_rate",
            "negative_outcome_rate",
        ]
        display(campaigns[point_columns].sort_values(["campaign_type", "campaign_name"]))
        """
    ),
    markdown(
        """
        ## 5. Understand the uncertainty methods

        The point estimates above describe exactly what appears in the supplied cycle.
        Intervals answer how stable those patterns are under explicit assumptions:

        - **Wilson 95% interval:** binary conversation outcomes such as delivered/not
          delivered. It behaves better than the simple normal interval for small samples.
        - **Percentile bootstrap:** repeatedly resamples observed conversations and
          recalculates monetary KPIs. It measures sensitivity to the observed customer mix.
        - **No interval for exact counts or Meta reach:** totals such as spend and observed
          conversation count are reported exactly. A valid future-count interval requires a
          time-series/count model, while period reach requires a deduplicated Meta estimate.

        These are uncertainty summaries, not proof of causality or a correction for sample
        selection bias.
        """
    ),
    code(
        """
        def wilson_interval(successes, trials, z=Z_95):
            # Return a Wilson score interval for a binomial proportion.
            if trials is None or trials <= 0:
                return np.nan, np.nan
            successes = float(successes)
            trials = float(trials)
            proportion = successes / trials
            denominator = 1 + z**2 / trials
            center = (proportion + z**2 / (2 * trials)) / denominator
            half_width = (
                z
                * math.sqrt(
                    proportion * (1 - proportion) / trials
                    + z**2 / (4 * trials**2)
                )
                / denominator
            )
            return max(0.0, center - half_width), min(1.0, center + half_width)


        def percentile_interval(values, alpha=0.05):
            values = np.asarray(values, dtype=float)
            values = values[np.isfinite(values)]
            if values.size == 0:
                return np.nan, np.nan
            return tuple(np.quantile(values, [alpha / 2, 1 - alpha / 2]))


        def format_interval(lower, upper, *, percent=False, money=False, ratio=False):
            if pd.isna(lower) or pd.isna(upper):
                return "Not estimated"
            if percent:
                return f"{lower:.1%} to {upper:.1%}"
            if money:
                return f"EGP {lower:,.0f} to EGP {upper:,.0f}"
            if ratio:
                return f"{lower:.2f} to {upper:.2f}"
            return f"{lower:,.2f} to {upper:,.2f}"


        # Sanity checks that make the small-sample behavior visible.
        for successes, trials in [(52, 111), (2, 3), (0, 3)]:
            lower, upper = wilson_interval(successes, trials)
            print(
                f"{successes}/{trials} = {successes/trials:.1%}; "
                f"95% Wilson interval {lower:.1%} to {upper:.1%}"
            )
        """
    ),
    markdown(
        """
        ## 6. Calculate confidence intervals for conversation rates

        Each conversation is treated as one binary trial for the selected outcome. The
        denominator is always shown because an impressive percentage supported by three
        conversations should not be interpreted like the same percentage supported by one
        hundred conversations.
        """
    ),
    code(
        """
        rate_specs = {
            "order_creation_rate": ("orders_created", "observed_conversations"),
            "delivered_rate": ("delivered_orders", "observed_conversations"),
            "negative_outcome_rate": ("negative_outcomes", "observed_conversations"),
            "repeat_conversation_rate": ("repeat_conversations", "observed_conversations"),
            "repeat_order_rate": ("repeat_delivered_orders", "delivered_orders"),
            "refund_rate": (
                "refunded_orders",
                "delivered_plus_refunded",
            ),
        }

        rate_rows = []
        for _, campaign in campaigns.iterrows():
            row = {"campaign_id": campaign["campaign_id"]}
            for metric, (numerator_col, denominator_col) in rate_specs.items():
                numerator = int(campaign[numerator_col])
                denominator = (
                    int(campaign["delivered_orders"] + campaign["refunded_orders"])
                    if denominator_col == "delivered_plus_refunded"
                    else int(campaign[denominator_col])
                )
                lower, upper = wilson_interval(numerator, denominator)
                row[f"{metric}_numerator"] = numerator
                row[f"{metric}_denominator"] = denominator
                row[f"{metric}_lower"] = lower
                row[f"{metric}_upper"] = upper
            rate_rows.append(row)

        rate_uncertainty = pd.DataFrame(rate_rows)
        campaign_uncertainty = campaigns.merge(rate_uncertainty, on="campaign_id", how="left")

        rate_view = campaign_uncertainty[
            [
                "campaign_name", "campaign_type", "observed_conversations",
                "delivered_rate", "delivered_rate_lower", "delivered_rate_upper",
                "negative_outcome_rate", "negative_outcome_rate_lower",
                "negative_outcome_rate_upper",
            ]
        ].copy()
        display(rate_view.sort_values("delivered_rate", ascending=False))
        """
    ),
    markdown(
        """
        ## 7. Bootstrap monetary KPI stability

        For each campaign, the observed conversations are sampled with replacement 5,000
        times. Every resample recalculates net revenue, net ROAS, delivered-order cost,
        AOV, and net revenue per active day. Spend and the number of observed conversations
        are held fixed, so these intervals describe sensitivity to **customer outcome mix**;
        they do not include uncertainty about future media cost or future conversation
        volume.
        """
    ),
    code(
        """
        def bootstrap_campaign(conversations, spend, period_days, *, seed):
            if conversations.empty:
                return {}

            rng = np.random.default_rng(seed)
            n = len(conversations)
            indices = rng.integers(0, n, size=(N_BOOTSTRAP, n))

            net_revenue = conversations["net_revenue"].to_numpy(dtype=float)[indices].sum(axis=1)
            delivered_revenue = conversations["delivered_revenue"].to_numpy(dtype=float)[indices].sum(axis=1)
            delivered_orders = conversations["is_delivered"].to_numpy(dtype=float)[indices].sum(axis=1)

            with np.errstate(divide="ignore", invalid="ignore"):
                net_roas = net_revenue / spend if spend > 0 else np.full(N_BOOTSTRAP, np.nan)
                delivered_roas = delivered_revenue / spend if spend > 0 else np.full(N_BOOTSTRAP, np.nan)
                cost_per_delivered_order = np.where(delivered_orders > 0, spend / delivered_orders, np.nan)
                aov = np.where(delivered_orders > 0, delivered_revenue / delivered_orders, np.nan)
                net_revenue_per_day = net_revenue / max(float(period_days), 1.0)

            metrics = {
                "net_revenue": net_revenue,
                "net_roas": net_roas,
                "delivered_roas": delivered_roas,
                "cost_per_delivered_order": cost_per_delivered_order,
                "aov": aov,
                "net_revenue_per_day": net_revenue_per_day,
            }
            output = {}
            for metric, values in metrics.items():
                lower, upper = percentile_interval(values)
                output[f"{metric}_bootstrap_lower"] = lower
                output[f"{metric}_bootstrap_upper"] = upper
            return output


        bootstrap_rows = []
        for position, campaign in campaigns.reset_index(drop=True).iterrows():
            campaign_conversations = canonical.conversations[
                canonical.conversations["campaign_id"].eq(campaign["campaign_id"])
            ]
            result = bootstrap_campaign(
                campaign_conversations,
                float(campaign["spend"]),
                float(campaign["period_days"]),
                seed=RANDOM_SEED + position,
            )
            bootstrap_rows.append({"campaign_id": campaign["campaign_id"], **result})

        bootstrap_uncertainty = pd.DataFrame(bootstrap_rows)
        campaign_uncertainty = campaign_uncertainty.merge(
            bootstrap_uncertainty, on="campaign_id", how="left"
        )

        monetary_view = campaign_uncertainty[
            [
                "campaign_name", "campaign_type", "observed_conversations",
                "net_roas", "net_roas_bootstrap_lower", "net_roas_bootstrap_upper",
                "aov", "aov_bootstrap_lower", "aov_bootstrap_upper",
            ]
        ].copy()
        display(monetary_view.sort_values("net_roas", ascending=False))
        """
    ),
    markdown(
        """
        ## 8. Visualize delivered-rate uncertainty

        The point is the observed delivered rate. The horizontal line is its Wilson 95%
        interval. Long lines indicate that the available conversations do not locate the
        underlying rate precisely. Campaign color represents campaign type; color does not
        change the statistical calculation.
        """
    ),
    code(
        """
        delivered_chart_data = campaign_uncertainty[
            [
                "campaign_name", "campaign_type", "observed_conversations",
                "delivered_rate", "delivered_rate_lower", "delivered_rate_upper",
            ]
        ].copy()

        delivered_order = delivered_chart_data.sort_values("delivered_rate")["campaign_name"].tolist()
        delivered_base = alt.Chart(delivered_chart_data).encode(
            y=alt.Y("campaign_name:N", sort=delivered_order, title=None),
            color=alt.Color("campaign_type:N", title="Campaign type"),
            tooltip=[
                alt.Tooltip("campaign_name:N", title="Campaign"),
                alt.Tooltip("campaign_type:N", title="Type"),
                alt.Tooltip("observed_conversations:Q", title="Observed conversations", format=",.0f"),
                alt.Tooltip("delivered_rate:Q", title="Delivered rate", format=".1%"),
                alt.Tooltip("delivered_rate_lower:Q", title="95% lower", format=".1%"),
                alt.Tooltip("delivered_rate_upper:Q", title="95% upper", format=".1%"),
            ],
        )

        delivered_intervals = delivered_base.mark_rule(strokeWidth=3).encode(
            x=alt.X("delivered_rate_lower:Q", title="Delivered rate with Wilson 95% interval", axis=alt.Axis(format="%")),
            x2="delivered_rate_upper:Q",
        )
        delivered_points = delivered_base.mark_point(filled=True, size=95, stroke="white", strokeWidth=1).encode(
            x=alt.X("delivered_rate:Q", axis=alt.Axis(format="%"))
        )

        display((delivered_intervals + delivered_points).properties(width=760, height=360))
        """
    ),
    markdown(
        """
        ## 9. Visualize observed net ROAS stability

        This chart uses the conversation bootstrap interval. A vertical line at ROAS 1.0
        is a revenue-versus-media-spend reference, not a profit break-even line: product,
        delivery, tax, staffing, and overhead costs are unavailable. The result also covers
        only the supplied WhatsApp outcomes.
        """
    ),
    code(
        """
        roas_chart_data = campaign_uncertainty.dropna(
            subset=["net_roas_bootstrap_lower", "net_roas_bootstrap_upper"]
        )[
            [
                "campaign_name", "campaign_type", "observed_conversations",
                "net_roas", "net_roas_bootstrap_lower", "net_roas_bootstrap_upper",
            ]
        ].copy()
        roas_order = roas_chart_data.sort_values("net_roas")["campaign_name"].tolist()
        roas_base = alt.Chart(roas_chart_data).encode(
            y=alt.Y("campaign_name:N", sort=roas_order, title=None),
            color=alt.Color("campaign_type:N", title="Campaign type"),
            tooltip=[
                alt.Tooltip("campaign_name:N", title="Campaign"),
                alt.Tooltip("campaign_type:N", title="Type"),
                alt.Tooltip("observed_conversations:Q", title="Observed conversations", format=",.0f"),
                alt.Tooltip("net_roas:Q", title="Observed net ROAS", format=".2f"),
                alt.Tooltip("net_roas_bootstrap_lower:Q", title="95% lower", format=".2f"),
                alt.Tooltip("net_roas_bootstrap_upper:Q", title="95% upper", format=".2f"),
            ],
        )
        roas_intervals = roas_base.mark_rule(strokeWidth=3).encode(
            x=alt.X("net_roas_bootstrap_lower:Q", title="Observed net ROAS with bootstrap 95% interval"),
            x2="net_roas_bootstrap_upper:Q",
        )
        roas_points = roas_base.mark_point(filled=True, size=95, stroke="white", strokeWidth=1).encode(
            x="net_roas:Q"
        )
        reference = alt.Chart(pd.DataFrame({"x": [1.0]})).mark_rule(
            color="#555555", strokeDash=[5, 4]
        ).encode(x="x:Q")

        display((roas_intervals + roas_points + reference).properties(width=760, height=360))
        """
    ),
    markdown(
        """
        ## 10. Connect campaign type, primary KPI, and benchmark

        Each campaign is evaluated against the objective of its campaign type. The current
        POC benchmark excludes the campaign itself, then uses the current-cycle same-type
        median when another campaign of that type exists and the portfolio median otherwise.
        These are comparison references, not approved business targets.

        When a compatible interval exists, the notebook asks whether the whole interval is
        above or below the benchmark. When an interval cannot be justified from the supplied
        data, the result is explicitly marked `point estimate only`.
        """
    ),
    code(
        """
        assessments_by_id = {
            item.campaign_id: item for item in assessment_bundle.assessments
        }
        packs_by_id = {
            item.campaign_id: item for item in assessment_bundle.evidence_packs
        }

        primary_interval_columns = {
            "net_roas": ("net_roas_bootstrap_lower", "net_roas_bootstrap_upper"),
            "net_revenue": ("net_revenue_bootstrap_lower", "net_revenue_bootstrap_upper"),
            "net_revenue_per_day": (
                "net_revenue_per_day_bootstrap_lower",
                "net_revenue_per_day_bootstrap_upper",
            ),
        }


        def statistical_conclusion(actual, lower, upper, benchmark, direction):
            if benchmark is None or pd.isna(benchmark):
                return "No compatible peer benchmark"
            if pd.isna(lower) or pd.isna(upper):
                return "Point estimate only; uncertainty interval not estimated"
            if direction == "higher":
                if lower > benchmark:
                    return "Credible observed outperformer"
                if upper < benchmark:
                    return "Credible observed underperformer"
            else:
                if upper < benchmark:
                    return "Credible observed outperformer"
                if lower > benchmark:
                    return "Credible observed underperformer"
            return "Inconclusive relative to the POC benchmark"


        def uncertainty_recommendation(conclusion, evidence_status, current_action):
            if evidence_status == EvidenceStatus.DATA_NOT_READY.value:
                return "Data not ready"
            if evidence_status == EvidenceStatus.INSUFFICIENT.value:
                return "Insufficient evidence; collect more observations"
            if conclusion == "Credible observed outperformer":
                if evidence_status == EvidenceStatus.READY.value:
                    return "Scale candidate, subject to business approval"
                return "Keep as test; scale candidate after data reconciliation"
            if conclusion == "Credible observed underperformer":
                return "Do not increase funding unchanged; diagnose and retest"
            if conclusion.startswith("Inconclusive"):
                return "Keep as controlled test; evidence does not separate performance"
            return f"Manual review; current deterministic action is {current_action}"


        decision_rows = []
        for _, campaign in campaign_uncertainty.iterrows():
            campaign_id = str(campaign["campaign_id"])
            pack = packs_by_id[campaign_id]
            assessment = assessments_by_id[campaign_id]
            primary = pack.primary_kpis[0]
            interval_columns = primary_interval_columns.get(primary.metric)
            lower = campaign[interval_columns[0]] if interval_columns else np.nan
            upper = campaign[interval_columns[1]] if interval_columns else np.nan
            conclusion = statistical_conclusion(
                primary.actual, lower, upper, primary.benchmark, primary.direction
            )
            recommendation = uncertainty_recommendation(
                conclusion,
                assessment.evidence_status.value,
                assessment.next_cycle_action.value,
            )
            config = registry.campaign_types[CampaignType(campaign["campaign_type"])]

            decision_rows.append(
                {
                    "campaign_id": campaign_id,
                    "Campaign": campaign["campaign_name"],
                    "Type": campaign["campaign_type"],
                    "Business objective": config.business_job,
                    "Primary KPI": primary.label,
                    "Primary value": primary.actual,
                    "Primary CI lower": lower,
                    "Primary CI upper": upper,
                    "POC benchmark": primary.benchmark,
                    "Benchmark source": primary.benchmark_source,
                    "Statistical conclusion": conclusion,
                    "Observed conversations": int(campaign["observed_conversations"]),
                    "Delivered orders": int(campaign["delivered_orders"]),
                    "Spend": float(campaign["spend"]),
                    "Observed net revenue": float(campaign["net_revenue"]),
                    "Observed net ROAS": float(campaign["net_roas"]) if pd.notna(campaign["net_roas"]) else np.nan,
                    "Delivered rate": float(campaign["delivered_rate"]) if pd.notna(campaign["delivered_rate"]) else np.nan,
                    "Delivered CI lower": campaign["delivered_rate_lower"],
                    "Delivered CI upper": campaign["delivered_rate_upper"],
                    "Rule target result": assessment.target_status.value,
                    "Rule funding action": assessment.next_cycle_action.value,
                    "Uncertainty-aware recommendation": recommendation,
                    "Evidence status": assessment.evidence_status.value,
                }
            )

        campaign_decisions = pd.DataFrame(decision_rows)
        display(
            campaign_decisions[
                [
                    "Campaign", "Type", "Primary KPI", "Primary value",
                    "Primary CI lower", "Primary CI upper", "POC benchmark",
                    "Statistical conclusion", "Rule funding action",
                    "Uncertainty-aware recommendation", "Evidence status",
                ]
            ].sort_values(["Type", "Campaign"])
        )
        """
    ),
    markdown(
        """
        ## 11. Whole-cycle campaign decision table

        This is the compact management view: one row per campaign. It keeps the primary
        objective, point estimate, uncertainty, benchmark, observed business totals, current
        deterministic rule, and uncertainty-aware interpretation together. `Not estimated`
        is preferable to manufacturing a misleading interval for reach or exact cycle counts.
        """
    ),
    code(
        """
        summary = campaign_decisions.copy()
        summary["Primary 95% interval"] = summary.apply(
            lambda row: format_interval(
                row["Primary CI lower"], row["Primary CI upper"], ratio=row["Primary KPI"] == "Net return on ad spend"
            ),
            axis=1,
        )
        summary["Delivered rate (95% interval)"] = summary.apply(
            lambda row: (
                f"{row['Delivered rate']:.1%} "
                f"[{row['Delivered CI lower']:.1%}, {row['Delivered CI upper']:.1%}]"
            ),
            axis=1,
        )
        summary["Spend (EGP)"] = summary["Spend"].map(lambda value: f"{value:,.0f}")
        summary["Observed net revenue (EGP)"] = summary["Observed net revenue"].map(lambda value: f"{value:,.0f}")
        summary["Observed net ROAS"] = summary["Observed net ROAS"].map(
            lambda value: f"{value:.2f}" if pd.notna(value) else "Unavailable"
        )

        summary_columns = [
            "Campaign", "Type", "Primary KPI", "Primary value",
            "Primary 95% interval", "POC benchmark", "Statistical conclusion",
            "Observed conversations", "Delivered orders",
            "Delivered rate (95% interval)", "Spend (EGP)",
            "Observed net revenue (EGP)", "Observed net ROAS",
            "Rule target result", "Rule funding action",
            "Uncertainty-aware recommendation", "Evidence status",
        ]
        display(summary[summary_columns].sort_values(["Type", "Campaign"]).reset_index(drop=True))
        """
    ),
    markdown(
        """
        ## 12. Detailed table for every campaign

        The final output below prints one business-readable table per campaign. Each table
        separates the objective, evidence volume, point estimates, uncertainty, current
        rules, and the uncertainty-aware recommendation. This is the intended review format
        before drilling into adsets, audiences, ads, and creatives.
        """
    ),
    code(
        """
        uncertainty_by_id = campaign_uncertainty.set_index("campaign_id")

        for _, decision in campaign_decisions.sort_values(["Type", "Campaign"]).iterrows():
            campaign = uncertainty_by_id.loc[decision["campaign_id"]]
            primary_interval = format_interval(
                decision["Primary CI lower"],
                decision["Primary CI upper"],
                ratio=decision["Primary KPI"] == "Net return on ad spend",
            )
            delivered_interval = format_interval(
                campaign["delivered_rate_lower"],
                campaign["delivered_rate_upper"],
                percent=True,
            )
            order_interval = format_interval(
                campaign["order_creation_rate_lower"],
                campaign["order_creation_rate_upper"],
                percent=True,
            )
            negative_interval = format_interval(
                campaign["negative_outcome_rate_lower"],
                campaign["negative_outcome_rate_upper"],
                percent=True,
            )
            roas_interval = format_interval(
                campaign["net_roas_bootstrap_lower"],
                campaign["net_roas_bootstrap_upper"],
                ratio=True,
            )
            aov_interval = format_interval(
                campaign["aov_bootstrap_lower"],
                campaign["aov_bootstrap_upper"],
                money=True,
            )

            display(Markdown(f"### {decision['Campaign']}"))
            detail = pd.DataFrame(
                {
                    "Field": [
                        "Campaign type",
                        "Business objective",
                        "Primary KPI",
                        "Primary KPI value",
                        "Primary KPI 95% interval",
                        "POC benchmark",
                        "Benchmark source",
                        "Statistical conclusion",
                        "Observed conversations",
                        "Order-creation rate",
                        "Order-creation 95% interval",
                        "Delivered orders",
                        "Delivered rate",
                        "Delivered-rate 95% interval",
                        "Negative-outcome rate",
                        "Negative-outcome 95% interval",
                        "Spend",
                        "Observed net revenue",
                        "Observed net ROAS",
                        "Observed net ROAS 95% interval",
                        "AOV",
                        "AOV 95% interval",
                        "Current target result",
                        "Current funding action",
                        "Uncertainty-aware recommendation",
                        "Evidence status",
                    ],
                    "Value": [
                        decision["Type"],
                        decision["Business objective"],
                        decision["Primary KPI"],
                        f"{decision['Primary value']:,.3f}" if pd.notna(decision["Primary value"]) else "Unavailable",
                        primary_interval,
                        f"{decision['POC benchmark']:,.3f}" if pd.notna(decision["POC benchmark"]) else "Unavailable",
                        decision["Benchmark source"] or "Unavailable",
                        decision["Statistical conclusion"],
                        f"{int(decision['Observed conversations']):,}",
                        f"{campaign['order_creation_rate']:.1%}",
                        order_interval,
                        f"{int(decision['Delivered orders']):,}",
                        f"{campaign['delivered_rate']:.1%}",
                        delivered_interval,
                        f"{campaign['negative_outcome_rate']:.1%}",
                        negative_interval,
                        f"EGP {decision['Spend']:,.0f}",
                        f"EGP {decision['Observed net revenue']:,.0f}",
                        f"{decision['Observed net ROAS']:.2f}" if pd.notna(decision["Observed net ROAS"]) else "Unavailable",
                        roas_interval,
                        f"EGP {campaign['aov']:,.0f}" if pd.notna(campaign["aov"]) else "Unavailable",
                        aov_interval,
                        decision["Rule target result"],
                        decision["Rule funding action"],
                        decision["Uncertainty-aware recommendation"],
                        decision["Evidence status"],
                    ],
                }
            )
            display(detail)
        """
    ),
    markdown(
        """
        ## 13. Final interpretation

        The notebook can identify campaigns with attractive observed performance, but the
        correct POC conclusion is evidence-aware:

        - A high point estimate with a wide interval is a **test candidate**, not a winner.
        - A narrow interval above a meaningful target is a stronger scaling candidate.
        - A narrow interval below an acceptable target supports stopping or redesigning the
          campaign.
        - A peer median is not a substitute for an approved business target.
        - Because Meta and WhatsApp event populations are unreconciled, all WhatsApp-based
          findings describe the supplied sample and the budget remains illustrative.

        The next analytical layer can apply the same pattern within each approved campaign:
        adset, audience, creative, and ad point estimates, uncertainty, within-campaign peer
        comparison, and controlled-test recommendations.
        """
    ),
]


for index, cell in enumerate(cells):
    if cell.cell_type == "code":
        if index == 0 or cells[index - 1].cell_type != "markdown":
            raise AssertionError(f"Code cell {index} has no methodology markdown above it")


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
print(f"Created {OUTPUT}")
