"""Build the executed-ready Post-Eid campaign walkthrough notebook."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "CAPI_Sample2_Post_Eid_Campaign_Step_By_Step.ipynb"


def markdown(value: str):
    return nbf.v4.new_markdown_cell(dedent(value).strip())


def code(value: str):
    return nbf.v4.new_code_cell(dedent(value).strip())


cells = [
    markdown(
        """
        # Post-Eid Lookalike Test: Campaign Walkthrough

        ## Business question

        This notebook takes one completed campaign and walks through the revised
        reporting method from source records to the next-cycle decision.

        The selected campaign is **Post-Eid Lookalike Test**, classified as an
        **experimental** campaign. Its job is not simply to maximize revenue. Its job is
        to generate enough comparable evidence to identify audiences and creatives that
        deserve another controlled test.

        The analysis separates:

        1. Meta delivery and cost.
        2. Observed WhatsApp business outcomes.
        3. Mature versus unresolved conversations.
        4. Conversation-level versus customer-level evidence.
        5. Campaign, adset, audience, ad, and creative comparisons.
        6. Facts, statistical uncertainty, and business decisions.

        No LLM is required for the deterministic analysis. Optional validated
        conversation signals are loaded only when an existing artifact is supplied.
        """
    ),
    markdown(
        """
        ## 1. Prepare the analysis environment

        We use the production `src_2` services instead of reproducing KPI formulas in a
        separate notebook implementation. This keeps the notebook and Streamlit report
        consistent. Altair is used for professional, interactive charts.
        """
    ),
    code(
        """
        from pathlib import Path
        import os

        import altair as alt
        import pandas as pd
        from IPython.display import Markdown, display

        from src_2.analytics import (
            build_assessment_bundle,
            build_budget_scenario,
            build_scorecards,
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

        pd.set_option("display.max_columns", 100)
        pd.set_option("display.max_colwidth", 160)
        alt.data_transformers.disable_max_rows()

        REPO_ROOT = Path.cwd()
        if not (REPO_ROOT / "src_2").exists():
            raise RuntimeError(
                "Run the notebook from the Team2-MarketingExpert repository root."
            )

        INPUT_DIRECTORY = REPO_ROOT / "src_2" / "data" / "input" / "sampe_2"
        CAMPAIGN_NAME = "Post-Eid Lookalike Test"

        print(f"Repository: {REPO_ROOT}")
        print(f"Input directory: {INPUT_DIRECTORY}")
        print(f"Selected campaign: {CAMPAIGN_NAME}")
        """
    ),
    markdown(
        """
        ## 2. Load and normalize the completed cycle

        The three source files contain different grains:

        - `meta_data.json`: campaign setup and daily Meta delivery facts.
        - `conversations.json`: WhatsApp conversations and final business outcomes.
        - `products.json`: product reference data.

        Normalization keeps each fact table at its natural grain. Spend is never joined
        directly to individual conversations, which would duplicate media cost.
        """
    ),
    code(
        """
        raw_payload = load_sample2(INPUT_DIRECTORY)
        canonical = normalize_cycle(raw_payload)
        quality = build_data_quality_report(canonical)
        registry = load_campaign_type_registry()
        policy = load_budget_policy()

        raw_scorecards = build_scorecards(canonical)
        cycle_id = f"cycle_{canonical.cycle_start.date()}_{canonical.cycle_end.date()}"
        bundle = build_assessment_bundle(cycle_id, raw_scorecards, registry, quality)

        campaigns = bundle.scorecards.campaign.copy()
        selected_campaign = campaigns.loc[
            campaigns["campaign_name"].eq(CAMPAIGN_NAME)
        ].iloc[0]
        campaign_id = str(selected_campaign["campaign_id"])
        assessment = next(
            item for item in bundle.assessments if item.campaign_id == campaign_id
        )

        inventory = pd.DataFrame(
            {
                "Canonical table": [
                    "campaigns", "adsets", "ads", "creatives", "media_daily",
                    "conversations", "order_lines", "products",
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
        ## 3. Confirm the selected campaign and its structure

        A campaign owns the objective. An adset defines audience and delivery settings.
        An ad is the delivery unit, and a creative contains the message, theme, and angle.

        Counting these objects first is essential: if one audience is paired with only one
        creative, audience and creative effects are confounded and cannot be separated.
        """
    ),
    code(
        """
        identity = pd.DataFrame(
            {
                "Field": [
                    "Campaign ID", "Campaign name", "Campaign type", "Meta objective",
                    "Status", "Start", "End", "Active days", "Adsets", "Ads",
                    "Unique creatives",
                ],
                "Value": [
                    campaign_id,
                    selected_campaign["campaign_name"],
                    selected_campaign["campaign_type"],
                    selected_campaign["objective"],
                    selected_campaign["entity_effective_status"],
                    selected_campaign["media_start"].date(),
                    selected_campaign["media_end"].date(),
                    int(selected_campaign["active_days"]),
                    int(selected_campaign["adset_count"]),
                    int(selected_campaign["ad_count"]),
                    int(selected_campaign["unique_creatives"]),
                ],
            }
        )
        display(identity)

        structure = bundle.scorecards.ad.loc[
            bundle.scorecards.ad["campaign_id"].eq(campaign_id),
            [
                "adset_name", "audience_type", "entity_name", "creative_name",
                "theme", "angle", "entity_start_date", "entity_end_date",
            ],
        ].rename(
            columns={
                "adset_name": "Adset",
                "audience_type": "Audience type",
                "entity_name": "Ad",
                "creative_name": "Creative",
                "theme": "Theme",
                "angle": "Angle",
                "entity_start_date": "Start",
                "entity_end_date": "End",
            }
        )
        display(structure)
        """
    ),
    markdown(
        """
        ## 4. Visualize the ad timeline

        This chart checks whether ads ran during comparable windows. Different launch
        dates can create a time-period confound: an ad may look better because it ran on
        stronger demand days rather than because its audience or creative was better.
        """
    ),
    code(
        """
        timeline = bundle.scorecards.ad.loc[
            bundle.scorecards.ad["campaign_id"].eq(campaign_id)
        ].copy()
        timeline["Audience"] = timeline["adset_name"].str.extract(r"(^\\d+%)")[0]

        timeline_chart = (
            alt.Chart(timeline)
            .mark_bar(cornerRadius=3, height=18)
            .encode(
                x=alt.X("entity_start_date:T", title="Date"),
                x2="entity_end_date:T",
                y=alt.Y("entity_name:N", title=None, sort="x"),
                color=alt.Color(
                    "Audience:N",
                    scale=alt.Scale(range=["#2563EB", "#D97706"]),
                ),
                tooltip=[
                    alt.Tooltip("entity_name:N", title="Ad"),
                    alt.Tooltip("adset_name:N", title="Adset"),
                    alt.Tooltip("creative_name:N", title="Creative"),
                    alt.Tooltip("entity_start_date:T", title="Start", format="%d %b %Y"),
                    alt.Tooltip("entity_end_date:T", title="End", format="%d %b %Y"),
                ],
            )
            .properties(height=150, title="Ad flight dates")
        )
        timeline_chart
        """
    ),
    markdown(
        """
        ## 5. Establish the data-quality boundary

        Statistical intervals only describe variation inside the supplied records. They
        cannot repair missing conversations or reconcile different Meta and WhatsApp event
        definitions.

        Important checks for this cycle include unresolved outcomes, repeated customers,
        organic/direct conversations, and invalid Meta rows where reach exceeds
        impressions. Daily reach is also non-additive, so it is not interpreted as unique
        campaign reach.
        """
    ),
    code(
        """
        quality_table = pd.DataFrame(
            {
                "Check": [
                    "Evidence status",
                    "Meta-attributed starts",
                    "Observed Meta-sourced WhatsApp conversations",
                    "Reconciliation ratio",
                    "Open or pending conversations",
                    "Repeated customers",
                    "Organic/direct conversations",
                    "Reach greater than impressions rows",
                ],
                "Value": [
                    quality.status.value,
                    quality.meta_conversation_starts,
                    quality.observed_meta_whatsapp_conversations,
                    quality.reconciliation_ratio,
                    quality.open_or_pending_conversations,
                    quality.repeated_customers,
                    quality.organic_direct_conversations,
                    quality.reach_exceeds_impressions_rows,
                ],
            }
        )
        display(quality_table)
        display(pd.DataFrame({"Cycle limitation": quality.warnings}))
        """
    ),
    markdown(
        """
        ## 6. Compare Meta activity with observed WhatsApp outcomes

        Meta conversation starts and supplied WhatsApp conversations are not assumed to be
        the same event population. The ratio below is a reconciliation diagnostic, not a
        conversion rate.

        - Meta tells us about delivery, clicks, spend, and attributed starts.
        - WhatsApp tells us which supplied conversations created, delivered, cancelled, or
          refunded orders.
        - The business-outcome KPIs describe only the observed WhatsApp sample.
        """
    ),
    code(
        """
        campaign_boundary = pd.DataFrame(
            {
                "Measure": [
                    "Meta-attributed conversation starts",
                    "Observed WhatsApp conversations",
                    "Mature WhatsApp outcomes",
                    "Unresolved WhatsApp outcomes",
                ],
                "Count": [
                    int(selected_campaign["meta_conversation_starts"]),
                    int(selected_campaign["observed_conversations"]),
                    int(selected_campaign["mature_conversations"]),
                    int(selected_campaign["open_or_pending_conversations"]),
                ],
            }
        )
        display(campaign_boundary)

        observation_ratio = (
            selected_campaign["observed_conversations"]
            / selected_campaign["meta_conversation_starts"]
        )
        print(
            f"Observed WhatsApp / Meta-attributed starts diagnostic: "
            f"{observation_ratio:.2%}. Do not interpret this as a conversion rate."
        )
        """
    ),
    markdown(
        """
        ## 7. Separate mature and unresolved outcomes

        `active` and `stuck_pending` conversations have not reached a final outcome. They
        are reported as operational workload, but excluded from delivery and negative-rate
        denominators. Otherwise, an unresolved conversation would be treated as a failure
        simply because the observation window ended too early.
        """
    ),
    code(
        """
        campaign_conversations = canonical.conversations.loc[
            canonical.conversations["campaign_id"].eq(campaign_id)
        ].copy()
        outcome_counts = (
            campaign_conversations.groupby(
                ["outcome_type", "is_mature_outcome"], as_index=False
            )["conversation_id"]
            .nunique()
            .rename(columns={"conversation_id": "Conversations"})
        )
        outcome_counts["Maturity"] = outcome_counts["is_mature_outcome"].map(
            {True: "Mature", False: "Unresolved"}
        )
        outcome_counts["Outcome"] = outcome_counts["outcome_type"].str.replace(
            "_", " ", regex=False
        ).str.title()
        display(outcome_counts[["Outcome", "Maturity", "Conversations"]])

        outcome_chart = (
            alt.Chart(outcome_counts)
            .mark_bar(cornerRadiusEnd=3)
            .encode(
                x=alt.X("Conversations:Q", title="Conversation count"),
                y=alt.Y("Outcome:N", title=None, sort="-x"),
                color=alt.Color(
                    "Maturity:N",
                    scale=alt.Scale(
                        domain=["Mature", "Unresolved"],
                        range=["#2563EB", "#D97706"],
                    ),
                ),
                tooltip=["Outcome:N", "Maturity:N", "Conversations:Q"],
            )
            .properties(height=250, title="Observed WhatsApp outcome mix")
        )
        outcome_chart
        """
    ),
    markdown(
        """
        ## 8. Separate conversations from customers

        A conversation is an interaction; a customer is the statistical unit behind one or
        more interactions. Repeated chats from the same person are not independent.

        This campaign contains returning customers only according to the supplied cycle
        field. We therefore report both conversation-level and unique-customer-level
        evidence. For this campaign the two delivery rates are similar because each
        customer has one attributed conversation inside the campaign, but that equality
        should never be assumed in general.
        """
    ),
    code(
        """
        customer_summary = pd.DataFrame(
            {
                "Measure": [
                    "Observed conversations",
                    "Unique customers",
                    "Returning-customer conversations",
                    "Customers repeated anywhere in this cycle",
                    "Mature conversations",
                    "Customers with mature outcomes",
                    "Customers with at least one delivered outcome",
                ],
                "Value": [
                    int(selected_campaign["observed_conversations"]),
                    int(selected_campaign["unique_customers"]),
                    int(selected_campaign["returning_customer_conversations"]),
                    int(selected_campaign["repeated_customers"]),
                    int(selected_campaign["mature_conversations"]),
                    int(selected_campaign["mature_unique_customers"]),
                    int(selected_campaign["delivered_customers"]),
                ],
            }
        )
        display(customer_summary)
        """
    ),
    markdown(
        """
        ## 9. Calculate and explain the main KPIs

        The formulas use aggregated numerators and denominators:

        - **Link CTR** = link clicks / impressions. It describes ad response, not sales.
        - **CPM** = spend / impressions x 1,000. It describes media delivery cost.
        - **Cost per observed conversation** = spend / supplied attributed WhatsApp chats.
        - **Net ROAS** = observed net revenue / spend. It is a revenue-efficiency proxy,
          not profit, because margin and operating cost are missing.
        - **AOV** = delivered revenue / delivered orders.
        - **Mature delivery rate** = delivered orders / mature conversations.
        - **Customer delivery rate** = customers with delivery / mature customers.
        - **Unresolved rate** = open or pending / observed conversations.
        """
    ),
    code(
        """
        kpi_rows = [
            ("Spend", selected_campaign["spend"], "EGP", "Meta"),
            ("Impressions", selected_campaign["impressions"], "count", "Meta"),
            ("Link CTR", selected_campaign["link_ctr_pct"], "%", "Meta"),
            ("CPM", selected_campaign["cpm"], "EGP", "Meta"),
            (
                "Cost per observed conversation",
                selected_campaign["cost_per_observed_conversation"],
                "EGP",
                "Meta spend + observed WhatsApp",
            ),
            ("Observed net revenue", selected_campaign["net_revenue"], "EGP", "WhatsApp"),
            ("Net ROAS", selected_campaign["net_roas"], "x", "Meta + WhatsApp"),
            ("AOV", selected_campaign["aov"], "EGP", "WhatsApp"),
            ("Mature delivery rate", selected_campaign["delivered_rate"], "% fraction", "WhatsApp"),
            (
                "Customer delivery rate",
                selected_campaign["customer_delivered_rate"],
                "% fraction",
                "WhatsApp customers",
            ),
            (
                "Unresolved outcome rate",
                selected_campaign["unresolved_outcome_rate"],
                "% fraction",
                "WhatsApp",
            ),
        ]
        kpi_table = pd.DataFrame(kpi_rows, columns=["KPI", "Value", "Unit", "Evidence source"])
        kpi_table["Formatted value"] = kpi_table.apply(
            lambda row: (
                f"{row['Value']:.2%}"
                if row["Unit"] == "% fraction"
                else f"{row['Value']:.2f}"
            ),
            axis=1,
        )
        display(kpi_table[["KPI", "Formatted value", "Unit", "Evidence source"]])
        """
    ),
    markdown(
        """
        ## 10. Add uncertainty to rate KPIs

        A point estimate is not the whole result. The Wilson 95% interval shows a range of
        values compatible with the observed binary outcomes under the sampling model.

        A wide interval means the sample cannot distinguish nearby alternatives reliably.
        It does not mean the calculation is wrong; it means the evidence is limited.
        These intervals also do not correct the Meta-to-WhatsApp reconciliation problem.
        """
    ),
    code(
        """
        interval_rows = pd.DataFrame(
            [
                {
                    "Rate": "Order creation",
                    "Point": selected_campaign["order_creation_rate"],
                    "Low": selected_campaign["order_creation_rate_ci_low"],
                    "High": selected_campaign["order_creation_rate_ci_high"],
                },
                {
                    "Rate": "Mature delivery",
                    "Point": selected_campaign["delivered_rate"],
                    "Low": selected_campaign["delivered_rate_ci_low"],
                    "High": selected_campaign["delivered_rate_ci_high"],
                },
                {
                    "Rate": "Negative outcome",
                    "Point": selected_campaign["negative_outcome_rate"],
                    "Low": selected_campaign["negative_outcome_rate_ci_low"],
                    "High": selected_campaign["negative_outcome_rate_ci_high"],
                },
                {
                    "Rate": "Customer delivery",
                    "Point": selected_campaign["customer_delivered_rate"],
                    "Low": selected_campaign["customer_delivered_rate_ci_low"],
                    "High": selected_campaign["customer_delivered_rate_ci_high"],
                },
            ]
        )
        interval_rows["95% interval"] = interval_rows.apply(
            lambda row: f"{row['Low']:.1%} to {row['High']:.1%}", axis=1
        )
        display(interval_rows[["Rate", "Point", "95% interval"]])

        interval_rules = (
            alt.Chart(interval_rows)
            .mark_rule(strokeWidth=4, color="#94A3B8")
            .encode(
                x=alt.X("Low:Q", title="Rate", axis=alt.Axis(format="%")),
                x2="High:Q",
                y=alt.Y("Rate:N", title=None, sort=None),
                tooltip=[
                    "Rate:N",
                    alt.Tooltip("Low:Q", format=".1%"),
                    alt.Tooltip("High:Q", format=".1%"),
                ],
            )
        )
        interval_points = (
            alt.Chart(interval_rows)
            .mark_point(filled=True, size=110, color="#2563EB")
            .encode(
                x=alt.X("Point:Q", axis=alt.Axis(format="%")),
                y=alt.Y("Rate:N", sort=None),
                tooltip=["Rate:N", alt.Tooltip("Point:Q", format=".1%")],
            )
        )
        (interval_rules + interval_points).properties(
            height=230, title="Campaign rate estimates with 95% Wilson intervals"
        )
        """
    ),
    markdown(
        """
        ## 11. Evaluate the experimental campaign objective

        Campaigns are not compared with one universal KPI. The campaign-type registry
        defines the business job and target logic.

        For an experimental campaign:

        - Primary KPI: observed conversations, because the test must generate evidence.
        - Guardrails: at least two creatives, two ads, and ten observed conversations.
        - Allocation KPI: cost per observed conversation, where lower is better.

        The primary KPI is compared with another experimental campaign when available.
        Configured guardrails are assumptions for the POC, not approved business targets.
        """
    ),
    code(
        """
        campaign_type = registry.campaign_types[selected_campaign["campaign_type"]]
        type_definition = pd.DataFrame(
            {
                "Item": [
                    "Business job", "Success question", "Primary KPIs",
                    "Supporting KPIs", "Allocation KPI", "Budget pool",
                ],
                "Definition": [
                    campaign_type.business_job,
                    campaign_type.success_question,
                    ", ".join(campaign_type.primary_kpis),
                    ", ".join(campaign_type.supporting_kpis),
                    campaign_type.allocation_metric.metric,
                    campaign_type.budget_pool.value,
                ],
            }
        )
        display(type_definition)

        assessment_rows = []
        for result in [*assessment.primary_results, *assessment.guardrail_results]:
            assessment_rows.append(
                {
                    "Metric": result.metric,
                    "Actual": result.actual,
                    "Benchmark or threshold": result.benchmark,
                    "Passed": result.passed,
                    "Reason": result.reason,
                }
            )
        display(pd.DataFrame(assessment_rows))

        decision_summary = pd.DataFrame(
            {
                "Decision field": [
                    "Target status", "Next-cycle action", "Evidence status"
                ],
                "Result": [
                    assessment.target_status.value,
                    assessment.next_cycle_action.value,
                    assessment.evidence_status.value,
                ],
            }
        )
        display(decision_summary)
        """
    ),
    markdown(
        """
        ## 12. Compare with the appropriate campaign peers

        The campaign is compared first with other experimental campaigns, not with
        awareness, retention, or seasonal campaigns that perform different jobs.

        More observed conversations are better for the experimental primary objective.
        Lower cost per observed conversation is better for efficient evidence generation.
        The peer comparison is descriptive because there are only two experimental
        campaigns in this cycle.
        """
    ),
    code(
        """
        experimental_peers = campaigns.loc[
            campaigns["campaign_type"].eq("experimental"),
            [
                "campaign_name", "observed_conversations",
                "cost_per_observed_conversation", "mature_conversations",
                "delivered_rate", "net_roas", "next_cycle_action",
            ],
        ].copy()
        display(experimental_peers)

        volume_chart = (
            alt.Chart(experimental_peers)
            .mark_bar(cornerRadiusEnd=3, color="#2563EB")
            .encode(
                x=alt.X("observed_conversations:Q", title="Observed conversations"),
                y=alt.Y("campaign_name:N", title=None, sort="-x"),
                tooltip=["campaign_name:N", "observed_conversations:Q"],
            )
            .properties(height=120, title="Primary objective: evidence volume")
        )
        cost_chart = (
            alt.Chart(experimental_peers)
            .mark_bar(cornerRadiusEnd=3, color="#D97706")
            .encode(
                x=alt.X(
                    "cost_per_observed_conversation:Q",
                    title="Cost per observed conversation (EGP; lower is better)",
                ),
                y=alt.Y("campaign_name:N", title=None, sort="x"),
                tooltip=[
                    "campaign_name:N",
                    alt.Tooltip("cost_per_observed_conversation:Q", format=".2f"),
                ],
            )
            .properties(height=120, title="Allocation efficiency")
        )
        alt.vconcat(volume_chart, cost_chart).resolve_scale(y="shared")
        """
    ),
    markdown(
        """
        ## 13. Inspect daily performance without scoring per day

        The score belongs to the campaign, but daily rows can reveal timing and fatigue.
        The chart keeps Meta spend and starts separate from observed WhatsApp outcomes.
        Daily variation is descriptive and should not be used to infer causality.
        """
    ),
    code(
        """
        media_daily = canonical.media_daily.loc[
            canonical.media_daily["campaign_id"].eq(campaign_id)
        ].groupby("date_start", as_index=False).agg(
            spend=("spend", "sum"),
            impressions=("impressions", "sum"),
            link_clicks=("link_clicks", "sum"),
            meta_conversation_starts=("meta_conversation_starts", "sum"),
        )
        media_daily["date"] = pd.to_datetime(media_daily["date_start"])

        whatsapp_daily = campaign_conversations.copy()
        whatsapp_daily["date"] = (
            whatsapp_daily["started_at"].dt.tz_convert(None).dt.normalize()
        )
        whatsapp_daily = whatsapp_daily.groupby("date", as_index=False).agg(
            observed_whatsapp=("conversation_id", "nunique"),
            delivered_orders=("is_delivered", "sum"),
        )
        daily = media_daily.merge(whatsapp_daily, on="date", how="left").fillna(
            {"observed_whatsapp": 0, "delivered_orders": 0}
        )

        spend_chart = (
            alt.Chart(daily)
            .mark_bar(color="#94A3B8")
            .encode(
                x=alt.X("date:T", title=None),
                y=alt.Y("spend:Q", title="Daily spend (EGP)"),
                tooltip=[
                    alt.Tooltip("date:T", format="%d %b"),
                    alt.Tooltip("spend:Q", format=".2f"),
                ],
            )
            .properties(height=150)
        )
        trend_long = daily.melt(
            id_vars="date",
            value_vars=[
                "meta_conversation_starts", "observed_whatsapp", "delivered_orders"
            ],
            var_name="Measure",
            value_name="Count",
        )
        trend_chart = (
            alt.Chart(trend_long)
            .mark_line(point=True, strokeWidth=2)
            .encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y("Count:Q", title="Daily count"),
                color=alt.Color(
                    "Measure:N",
                    scale=alt.Scale(
                        range=["#2563EB", "#D97706", "#059669"]
                    ),
                ),
                tooltip=[
                    alt.Tooltip("date:T", format="%d %b"),
                    "Measure:N",
                    alt.Tooltip("Count:Q", format=".0f"),
                ],
            )
            .properties(height=210)
        )
        alt.vconcat(spend_chart, trend_chart).resolve_scale(x="shared")
        """
    ),
    markdown(
        """
        ## 14. Compare the two adsets and audiences

        A lookalike audience contains people Meta considers similar to a source customer
        group. A smaller percentage is generally narrower and closer to the seed; a larger
        percentage is broader.

        The bubble chart uses:

        - X-axis: cost per observed conversation, lower is better.
        - Y-axis: customer delivery rate, higher is better.
        - Bubble size: mature outcome evidence.

        The deterministic child action is intentionally cautious. A favorable point
        estimate without a validated sampling interval is a test hypothesis, not a scale
        decision.
        """
    ),
    code(
        """
        adsets = bundle.scorecards.adset.loc[
            bundle.scorecards.adset["campaign_id"].eq(campaign_id)
        ].copy()
        adsets["Audience cell"] = adsets["entity_name"].str.extract(r"(^\\d+%)")[0]

        adset_columns = [
            "entity_name", "Audience cell", "spend", "observed_conversations",
            "mature_conversations", "open_or_pending_conversations",
            "delivered_orders", "customer_delivered_rate",
            "customer_delivered_rate_ci_low", "customer_delivered_rate_ci_high",
            "cost_per_observed_conversation", "net_roas", "next_cycle_action",
            "decision_reason",
        ]
        display(adsets[adset_columns].sort_values("cost_per_observed_conversation"))

        bubble = (
            alt.Chart(adsets)
            .mark_circle(opacity=0.88, stroke="white", strokeWidth=1.5)
            .encode(
                x=alt.X(
                    "cost_per_observed_conversation:Q",
                    title="Cost per observed conversation (EGP; lower is better)",
                    scale=alt.Scale(zero=False),
                ),
                y=alt.Y(
                    "customer_delivered_rate:Q",
                    title="Customer delivery rate",
                    axis=alt.Axis(format="%"),
                    scale=alt.Scale(zero=False),
                ),
                size=alt.Size(
                    "mature_conversations:Q",
                    title="Mature outcomes",
                    scale=alt.Scale(range=[300, 1100]),
                ),
                color=alt.Color(
                    "Audience cell:N",
                    scale=alt.Scale(range=["#2563EB", "#D97706"]),
                ),
                tooltip=[
                    alt.Tooltip("entity_name:N", title="Adset"),
                    alt.Tooltip("spend:Q", title="Spend", format=".2f"),
                    alt.Tooltip(
                        "cost_per_observed_conversation:Q",
                        title="Cost / observed conversation",
                        format=".2f",
                    ),
                    alt.Tooltip(
                        "customer_delivered_rate:Q",
                        title="Customer delivery rate",
                        format=".1%",
                    ),
                    alt.Tooltip("net_roas:Q", title="Net ROAS", format=".2f"),
                    alt.Tooltip("next_cycle_action:N", title="Decision"),
                ],
            )
            .properties(height=360, title="Audience-cell performance")
        )
        labels = (
            alt.Chart(adsets)
            .mark_text(dx=14, dy=-12, fontSize=12)
            .encode(
                x="cost_per_observed_conversation:Q",
                y="customer_delivered_rate:Q",
                text="Audience cell:N",
            )
        )
        bubble + labels
        """
    ),
    markdown(
        """
        ## 15. Show uncertainty for the audience comparison

        The 5% and 10% customer delivery intervals overlap substantially. That means the
        observed delivery-rate difference is not strong evidence of a real audience
        difference. The 10% cell still has a better cost and ROAS point estimate, so it is
        the leading hypothesis for another controlled test.
        """
    ),
    code(
        """
        audience_intervals = adsets[
            [
                "Audience cell", "customer_delivered_rate",
                "customer_delivered_rate_ci_low", "customer_delivered_rate_ci_high",
                "mature_unique_customers",
            ]
        ].rename(
            columns={
                "customer_delivered_rate": "Point",
                "customer_delivered_rate_ci_low": "Low",
                "customer_delivered_rate_ci_high": "High",
                "mature_unique_customers": "Customers",
            }
        )
        display(audience_intervals)

        audience_rules = (
            alt.Chart(audience_intervals)
            .mark_rule(strokeWidth=5, color="#94A3B8")
            .encode(
                x=alt.X("Low:Q", title="Customer delivery rate", axis=alt.Axis(format="%")),
                x2="High:Q",
                y=alt.Y("Audience cell:N", title=None),
            )
        )
        audience_points = (
            alt.Chart(audience_intervals)
            .mark_point(filled=True, size=140, color="#2563EB")
            .encode(
                x="Point:Q",
                y="Audience cell:N",
                tooltip=[
                    "Audience cell:N", "Customers:Q",
                    alt.Tooltip("Point:Q", format=".1%"),
                    alt.Tooltip("Low:Q", format=".1%"),
                    alt.Tooltip("High:Q", format=".1%"),
                ],
            )
        )
        (audience_rules + audience_points).properties(
            height=150, title="Audience customer-delivery uncertainty"
        )
        """
    ),
    markdown(
        """
        ## 16. Inspect ads, creatives, and angles

        Each audience cell has one ad and one creative. Therefore these dimensions move
        together:

        - 5% lookalike + creative A + experimental intro angle.
        - 10% lookalike + creative B + experimental premium angle.

        We can identify the stronger **combination**, but we cannot conclude whether the
        audience, creative, copy angle, or their interaction caused the difference. Calling
        creative B the winner would overstate the evidence.
        """
    ),
    code(
        """
        ads = bundle.scorecards.ad.loc[
            bundle.scorecards.ad["campaign_id"].eq(campaign_id)
        ].copy()
        ad_creative_view = ads[
            [
                "adset_name", "audience_type", "entity_name", "creative_name",
                "theme", "angle", "spend", "observed_conversations",
                "mature_conversations", "delivered_orders",
                "cost_per_observed_conversation", "net_roas",
                "next_cycle_action", "decision_reason",
            ]
        ].rename(
            columns={
                "adset_name": "Adset",
                "audience_type": "Audience type",
                "entity_name": "Ad",
                "creative_name": "Creative",
                "theme": "Theme",
                "angle": "Angle",
                "spend": "Spend",
                "observed_conversations": "Observed conversations",
                "mature_conversations": "Mature outcomes",
                "delivered_orders": "Delivered orders",
                "cost_per_observed_conversation": "Cost / observed conversation",
                "net_roas": "Net ROAS",
                "next_cycle_action": "Decision",
                "decision_reason": "Reason",
            }
        )
        display(ad_creative_view)

        mapping_check = pd.DataFrame(
            {
                "Question": [
                    "More than one audience?",
                    "More than one creative?",
                    "Same creative used across audiences?",
                    "Can audience and creative effects be separated?",
                ],
                "Answer": ["Yes", "Yes", "No", "No - the design is confounded"],
            }
        )
        display(mapping_check)
        """
    ),
    markdown(
        """
        ## 17. Optional conversation-intelligence diagnostics

        Meta cannot explain customer needs, product interest, objections, promotion
        confusion, or agent quality. A validated semantic artifact can add those insights.

        This cell never calls an LLM. It loads only an existing JSONL artifact created by
        the governed extraction command. If no artifact exists, the notebook states that
        semantic evidence is unavailable rather than inventing it.

        Start with five campaign conversations:

        ```bash
        python scripts/extract_conversation_signals.py \\
          --campaign-name "Post-Eid Lookalike Test" \\
          --limit 5
        ```

        Inspect the validated JSONL and error log, then run the same command without
        `--limit` to resume and process all 63 campaign conversations.
        """
    ),
    code(
        """
        configured_signal_path = os.getenv("CONVERSATION_SIGNALS_PATH", "").strip()
        signal_path = (
            Path(configured_signal_path).expanduser()
            if configured_signal_path
            else REPO_ROOT / "src_2" / "artifacts" / "conversation_signals.jsonl"
        )

        if signal_path.exists():
            signal_records = load_conversation_signal_records(signal_path)
            semantic_scorecards = build_scorecards(canonical, signal_records)
            semantic_campaign = semantic_scorecards.campaign.loc[
                semantic_scorecards.campaign["campaign_id"].eq(campaign_id)
            ].iloc[0]
            semantic_view = pd.DataFrame(
                {
                    "Diagnostic": [
                        "Validated transcripts", "High purchase-intent rate",
                        "Barrier conversation rate", "Helpful agent rate",
                        "Top conversation purpose", "Top barrier", "Top mentioned product",
                    ],
                    "Value": [
                        semantic_campaign.get("semantic_conversations"),
                        semantic_campaign.get("high_purchase_intent_rate"),
                        semantic_campaign.get("barrier_conversation_rate"),
                        semantic_campaign.get("agent_helpful_rate"),
                        semantic_campaign.get("top_conversation_purpose"),
                        semantic_campaign.get("top_barrier"),
                        semantic_campaign.get("top_mentioned_product"),
                    ],
                }
            )
            display(semantic_view)
            print(
                "Semantic fields are diagnostic only and do not alter the funding decision."
            )
        else:
            display(
                pd.DataFrame(
                    {
                        "Semantic status": ["Not available"],
                        "Reason": [
                            "No validated conversation_signals.jsonl artifact was supplied."
                        ],
                        "Expected path": [str(signal_path)],
                    }
                )
            )
        """
    ),
    markdown(
        """
        ## 18. Place the campaign inside the illustrative budget scenario

        The POC budget is expressed as 100 normalized units, not currency. Campaign-type
        envelopes follow the previous cycle's spend mix. Experimental campaigns compete
        only inside the historical experimental envelope using cost per observed
        conversation.

        Because Meta and WhatsApp populations are not reconciled, this scenario is
        explicitly non-operational and requires human approval.
        """
    ),
    code(
        """
        scenario = build_budget_scenario(
            cycle_id,
            bundle.scorecards.campaign,
            bundle.assessments,
            registry,
            policy,
            quality,
        )
        selected_allocation = next(
            item for item in scenario.allocations if item.entity_id == campaign_id
        )
        allocation_view = pd.DataFrame(
            {
                "Field": [
                    "Campaign action", "Budget units", "Budget share %",
                    "Operational", "Reason",
                ],
                "Value": [
                    selected_allocation.action.value,
                    selected_allocation.budget_units,
                    selected_allocation.budget_share_pct,
                    scenario.operational,
                    selected_allocation.reason,
                ],
            }
        )
        display(allocation_view)
        display(pd.DataFrame({"Scenario assumption": scenario.assumptions}))
        """
    ),
    markdown(
        """
        ## 19. Final campaign conclusion

        The final result must distinguish what the data supports from what remains a
        hypothesis. This prevents a visually stronger cell from being turned into an
        unjustified scale or kill decision.
        """
    ),
    code(
        """
        leading_adset = adsets.sort_values(
            "cost_per_observed_conversation"
        ).iloc[0]
        other_adset = adsets.sort_values(
            "cost_per_observed_conversation"
        ).iloc[-1]

        conclusion = pd.DataFrame(
            [
                {
                    "Decision area": "Campaign objective",
                    "Conclusion": (
                        f"{assessment.target_status.value}: the experiment generated "
                        f"{int(selected_campaign['observed_conversations'])} observed "
                        "conversations and met its configured evidence guardrails."
                    ),
                    "Action": assessment.next_cycle_action.value,
                },
                {
                    "Decision area": "Leading execution cell",
                    "Conclusion": (
                        f"{leading_adset['entity_name']} has the better observed cost per "
                        f"conversation (EGP {leading_adset['cost_per_observed_conversation']:.2f}) "
                        f"and net ROAS ({leading_adset['net_roas']:.2f}x)."
                    ),
                    "Action": "Carry forward as the leading test hypothesis, not a proven winner.",
                },
                {
                    "Decision area": "Other execution cell",
                    "Conclusion": (
                        f"{other_adset['entity_name']} has weaker point estimates, but the "
                        "current design and sample do not justify declaring it a universal loser."
                    ),
                    "Action": "Insufficient evidence for a scale/kill claim.",
                },
                {
                    "Decision area": "Creative conclusion",
                    "Conclusion": (
                        "Audience, ad, creative, and angle changed together, so their effects "
                        "cannot be separated."
                    ),
                    "Action": "Do not name a best creative from this campaign alone.",
                },
                {
                    "Decision area": "Next controlled test",
                    "Conclusion": (
                        "Hold creative, offer, dates, and budget treatment constant while "
                        "comparing 5% versus 10% lookalike audiences; then test creatives "
                        "inside the winning audience in a separate experiment."
                    ),
                    "Action": "Change one major variable at a time and predefine success criteria.",
                },
                {
                    "Decision area": "Data limitation",
                    "Conclusion": (
                        "Observed WhatsApp outcomes are not reconciled to Meta-attributed "
                        "conversation starts."
                    ),
                    "Action": "Treat all budget output as illustrative until reconciliation is complete.",
                },
            ]
        )
        display(conclusion)

        display(
            Markdown(
                f'''
                ### Plain-language takeaway

                **Post-Eid Lookalike Test achieved its evidence-generation objective with
                concerns and should remain a controlled test.** The 10% lookalike cell is
                the stronger observed combination, but the campaign did not independently
                test audience and creative. The correct next step is a cleaner experiment,
                not immediate broad scaling or an automatic kill decision.
                '''
            )
        )
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
