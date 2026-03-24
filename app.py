import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import src.metrics_engine as data_processor
import src.llm as llm_handler

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Marketing Expert Chatbot", page_icon="📈", layout="wide")

# Custom CSS for styling
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        height: 115px;
        font-size: 21px !important;
        font-weight: 800 !important;
        line-height: 1.35;
        border-radius: 10px;
        background-color: #f0f2f6;
        border: 1px solid #d1d5db;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #e5e7eb;
        border-color: #9ca3af;
        transform: translateY(-2px);
        box_shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .main-header {
        font-size: 3rem;
        color: #1f2937;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #4b5563;
        text-align: center;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">Marketing Expert Chatbot 🤖</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Select a category below to analyze your marketing performance</p>', unsafe_allow_html=True)

# Sidebar for debug/context
with st.sidebar:
    st.header("Debug Info")
    if st.checkbox("Show Raw Data"):
        df = data_processor.load_data()
        if df is not None:
            st.dataframe(df)
        else:
            st.error("Could not load data/campaign_data.csv")

# Initialize session state
if "selected_category" not in st.session_state:
    st.session_state.selected_category = ""
if "run_analysis" not in st.session_state:
    st.session_state.run_analysis = False

def handle_click_category(category_name):
    st.session_state.selected_category = category_name
    st.session_state.run_analysis = True

# Recommended Categories
st.subheader("💡 Choose a Category to Analyze")
col1, col2 = st.columns(2)
col3, col4 = st.columns(2)

# Make buttons larger and more prominent by default
def create_metric_card(col, label, key_suffix, category_name):
    with col:
        # Use custom styling for a card-like effect
        st.markdown("""
        <div style="
            background-color: #ffffff;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
            margin-bottom: 20px;
            height: 150px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            border: 1px solid #e5e7eb;
        ">
            <h3>""" + label.split(' ')[0] + " " + label.split(' ')[1] + """</h3>
            <h1>""" + label.split(' ')[2] + """</h1>
        </div>
        """, unsafe_allow_html=True)
        # Use a hidden button that covers the card or just the regular button below
        if st.button(label, key=f"btn_{key_suffix}", use_container_width=True):
            handle_click_category(category_name)

# Simplified grid layout with spacing
with col1:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    if st.button("💰 Customer Acquisition\nAnalyze your acquisition sources and costs", use_container_width=True):
        handle_click_category("Customer Acquisition")

with col2:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    if st.button("😊 Customer Satisfaction\nMonitor CSAT scores and feedback", use_container_width=True):
        handle_click_category("Customer Satisfaction")

with col3:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    if st.button("📈 Revenue Growth\nTrack revenue trends and performance", use_container_width=True):
        handle_click_category("Revenue Growth")

with col4:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    if st.button("🔄 Customer Retention\nEvaluate churn and retention rates", use_container_width=True):
        handle_click_category("Customer Retention")

st.markdown("---") # Section divider

# Main Logic
if st.session_state.run_analysis and st.session_state.selected_category:
    category = st.session_state.selected_category
    
    st.markdown(f"<h2 style='text-align: center; color: #4338ca;'>Analysis: {category}</h2>", unsafe_allow_html=True)

    with st.spinner(f"Generating detailed report for {category}..."):
        try:
            # 1. Data Retrieval
            df = data_processor.load_data()
            if df is not None:
                metrics = data_processor.calculate_metrics(df, category)
                
                # 2. LLM Generation
                if "error" in metrics:
                    st.error(metrics["error"])
                else:
                    # Display Metrics nicely in a grid
                    st.markdown("### Key Metrics")
                    
                    # Define strict UI cards with emojis
                    # Format numbers nicely
                    revenue = metrics.get('Total Revenue', 0)
                    spend = metrics.get('Total Spend', 0)
                    formatted_revenue = f"${revenue:,.0f}" if isinstance(revenue, (int, float)) else str(revenue)
                    formatted_spend = f"${spend:,.0f}" if isinstance(spend, (int, float)) else str(spend)
                    
                    # Note: Using 'Total Conversions' as proxy for New Customers if 'Total New Customers' is missing/0 based on data.py logic
                    new_customers = metrics.get('Total New Customers', metrics.get('Total Conversions', 0))
                    
                    ui_cards = [
                        ("📢 Campaign Name", metrics.get('Campaign Name', 'Unknown')),
                        ("👥 Total New Customers", str(new_customers)),
                        ("💰 Total Revenue", formatted_revenue),
                        ("💸 Total Spend", formatted_spend)
                    ]
                    
                    cols = st.columns(4)
                    for idx, (label, value) in enumerate(ui_cards):
                        with cols[idx]:
                            st.markdown(f"""
                            <div style="
                                background-color: white; 
                                padding: 18px; 
                                border-radius: 12px; 
                                box-shadow: 0 2px 8px rgba(0,0,0,0.10); 
                                border: 2px solid #6366f1;
                                text-align: center;
                                height: 100%;
                            ">
                                <span style="display:block; font-size:1.1em; font-weight:400; color:#4338ca; margin-bottom:6px; letter-spacing:0.03em;">{label}</span>
                                <span style="display:block; font-size:2.1em; font-weight:400; color:#111827;">{value}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)

                    # Generate AI Response (now returns JSON string)
                    response_json_str = llm_handler.generate_response(df, category, metrics)

                    try:
                        import json
                        report = json.loads(response_json_str)

                        analysis = report.get('analysis', {})
                        recommendations = report.get('recommendations', [])

                        # ── Analysis Summary ──────────────────────────────
                        st.markdown("### 🔬 Analysis Summary")
                        st.markdown(analysis.get('analysis', ''))

                        # Root-cause hypothesis
                        root_cause = analysis.get('root_cause_hypothesis', '')
                        if root_cause:
                            st.info(f"**Root-cause hypothesis:** {root_cause}")

                        # Key signals
                        signals = analysis.get('key_signals', [])
                        if signals:
                            with st.expander("📡 Key Signals"):
                                for sig in signals:
                                    st.write(f"- {sig}")

                        # Detected issues
                        issues = analysis.get('detected_issues', [])
                        if issues:
                            with st.expander("🚨 Detected Issues"):
                                for issue in issues:
                                    st.write(f"- {issue}")

                        # Business risks
                        risks = analysis.get('business_risks', [])
                        if risks:
                            with st.expander("⚠️ Business Risks"):
                                for risk in risks:
                                    st.write(f"- {risk}")

                        # Confidence score
                        confidence = analysis.get('confidence_score', 0)
                        if isinstance(confidence, str):
                            try:
                                confidence = float(confidence.strip('%'))
                            except ValueError:
                                confidence = 0
                        confidence = max(0, min(100, int(confidence)))
                        st.progress(confidence / 100, text=f"Confidence Score: {confidence}%")

                        # ── Recommendation Cards ─────────────────────────
                        st.markdown("---")
                        st.markdown("### 💡 Recommendations")

                        PRIORITY_COLORS = {
                            "high": "#dc2626",
                            "medium": "#d97706",
                            "low": "#16a34a",
                        }

                        for idx, rec in enumerate(recommendations, 1):
                            priority = rec.get('priority', 'medium').lower()
                            color = PRIORITY_COLORS.get(priority, "#6366f1")

                            st.markdown(f"""
                            <div style="
                                background: #fff;
                                border-left: 5px solid {color};
                                border-radius: 10px;
                                padding: 20px 24px;
                                margin-bottom: 18px;
                                box-shadow: 0 2px 8px rgba(0,0,0,0.07);
                            ">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                                    <span style="font-size:1.25em; font-weight:700; color:#1e293b;">{idx}. {rec.get('title','')}</span>
                                    <span style="
                                        background:{color}22;
                                        color:{color};
                                        font-weight:700;
                                        padding:3px 12px;
                                        border-radius:20px;
                                        font-size:0.85em;
                                    ">{priority.upper()} priority</span>
                                </div>
                                <div style="color:#475569; font-size:0.95em; margin-bottom:6px;">
                                    <b>Effort:</b> {rec.get('effort','')} · <b>Impact in:</b> {rec.get('time_to_see_impact','')} · <b>Confidence:</b> {rec.get('confidence','')}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                            # What's happening
                            st.markdown(f"**📋 What's happening:** {rec.get('whats_happening', '')}")

                            # Evidence
                            evidence = rec.get('evidence', [])
                            if evidence:
                                with st.expander("📊 Evidence"):
                                    for ev in evidence:
                                        st.write(f"- {ev}")

                            # Action steps
                            actions = rec.get('what_you_should_do', [])
                            if actions:
                                with st.expander("✅ Action Steps"):
                                    for step in actions:
                                        if isinstance(step, dict):
                                            st.markdown(f"**{step.get('step', '')}**")
                                            st.write(f"  *Where:* {step.get('where', '')}")
                                            st.write(f"  *How:* {step.get('how', '')}")
                                            guardrails = step.get('guardrails', [])
                                            if guardrails:
                                                st.write("  *Guardrails:* " + ", ".join(guardrails))
                                        else:
                                            st.write(f"- {step}")

                            # Why this matters
                            why = rec.get('why_this_matters', '')
                            if why:
                                st.markdown(f"**📉 Why this matters:** {why}")

                            # Expected impact
                            impact = rec.get('expected_impact', {})
                            if isinstance(impact, dict) and impact:
                                st.markdown(
                                    f"**🔮 Expected impact:** {impact.get('primary_kpi','')} "
                                    f"→ {impact.get('direction','')} — {impact.get('explanation','')}"
                                )

                            # Risks / Dependencies
                            dep_risks = rec.get('dependency_or_risk', [])
                            if dep_risks:
                                with st.expander("⚠️ Risks & Dependencies"):
                                    for dr in dep_risks:
                                        st.write(f"- {dr}")

                            # Measurement plan
                            mplan = rec.get('measurement_plan', {})
                            if isinstance(mplan, dict) and mplan:
                                with st.expander("📏 Measurement Plan"):
                                    st.write(f"**How to measure:** {mplan.get('how_to_measure', '')}")
                                    st.write(f"**Success criteria:** {mplan.get('success_criteria', '')}")
                                    st.write(f"**Check timing:** {mplan.get('check_timing', '')}")
                                    notes = mplan.get('notes', '')
                                    if notes:
                                        st.write(f"**Notes:** {notes}")

                            st.markdown(f"*Owner suggestion: {rec.get('owner_suggestion', '')}*")
                            st.markdown("---")

                    except json.JSONDecodeError:
                        st.markdown("### 📝 AI Evaluation Report")
                        st.markdown(f"""
                        <div style="
                            background-color: #f8fafc;
                            padding: 25px;
                            border-radius: 12px;
                            border-left: 5px solid #4338ca;
                            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                            font-family: 'Helvetica', sans-serif;
                            line-height: 1.6;
                            color: #374151;
                        ">
                            {response_json_str}
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.error("Data file not found. Please check data/campaign_data.csv")
        except Exception as e:
            st.error(f"An error occurred: {e}")
            
    # Reset analysis flag
    st.session_state.run_analysis = False
