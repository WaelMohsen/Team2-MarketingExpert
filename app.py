import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import src.data as data_processor
import src.llm as llm_handler
import json

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
            

            # 1. Load data
            df = data_processor.load_data()
            if df is None:
                st.error("Data file not found. Please check data/campaign_data.csv")
            else:
                # 2. Calculate metrics using the correct target class
                target_class_map = {
                    "Revenue Growth": data_processor.RevenueGrowth,
                    "Customer Acquisition": data_processor.CustomerAcquisition,
                    "Customer Satisfaction": data_processor.CustomerSatisfaction,
                    "Customer Retention": data_processor.CustomerRetention,
                }
                metrics = target_class_map[category](df).calculate()

                # 3. Display key metrics as UI cards
                st.markdown("### Key Metrics")
                cols = st.columns(len(metrics))
                for idx, (label, value) in enumerate(metrics.items()):
                    formatted = f"{value}%" if "Rate" in label or label in ("CTR", "CVR") else f"${value}" if label in ("CPA", "CPC", "AOV", "ROAS", "Estimated Annual Value") else str(value)
                    with cols[idx]:
                        st.markdown(f"""
                        <div style="
                            background-color: white;
                            padding: 18px;
                            border-radius: 12px;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.10);
                            border: 2px solid #6366f1;
                            text-align: center;
                        ">
                            <span style="display:block; font-size:1em; font-weight:600; color:#4338ca; margin-bottom:6px;">{label}</span>
                            <span style="display:block; font-size:1.8em; font-weight:700; color:#111827;">{formatted}</span>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # 4. Run two-step LLM pipeline
                response_json_str = llm_handler.generate_response(df, f"Analyze metrics for {category}", category, metrics)

                try:
                    report = json.loads(response_json_str)

                    # 5. Display Analysis
                    analysis = report.get("analysis", {})
                    if isinstance(analysis, str):
                        analysis = json.loads(analysis)

                    st.markdown("## Analysis")
                    st.markdown(f"**{analysis.get('executive_summary', '')}**")

                    with st.expander("Budget & Efficiency"):
                        for item in analysis.get("budget_and_efficiency", []):
                            st.markdown(f"- **{item.get('insight')}** — {item.get('business_impact')}")

                    with st.expander("Results & Value"):
                        for item in analysis.get("results_and_value", []):
                            st.markdown(f"- **{item.get('insight')}** — {item.get('business_impact')}")

                    with st.expander("Risks & Patterns"):
                        for item in analysis.get("cross_channel_patterns_and_risks", []):
                            st.markdown(f"- **{item.get('pattern_or_risk')}** — {item.get('why_it_matters')}")

                    # 6. Display Recommendations
                    recommendations = report.get("recommendations", [])
                    if isinstance(recommendations, str):
                        recommendations = json.loads(recommendations).get("recommendations", [])

                    st.markdown("## Recommendations")
                    for rec in recommendations:
                        with st.expander(f"{rec.get('id')} — {rec.get('title')} [{rec.get('priority')}]"):
                            st.markdown(f"**What's happening:** {rec.get('whats_happening')}")
                            st.markdown(f"**Why it matters:** {rec.get('why_this_matters')}")
                            st.markdown(f"**Effort:** {rec.get('effort')} | **Time to impact:** {rec.get('time_to_see_impact')} | **Owner:** {rec.get('owner_suggestion')}")
                            st.markdown("**Steps:**")
                            for step in rec.get("what_you_should_do", []):
                                st.markdown(f"  - {step.get('step')} ({step.get('where')}): {step.get('how')}")

                except (json.JSONDecodeError, TypeError) as parse_err:
                    st.error(f"Could not parse LLM response: {parse_err}")
                    st.markdown("### Raw LLM Output")
                    st.write(response_json_str)

        except Exception as e:
            st.error(f"An error occurred: {e}")
            
    # Reset analysis flag
    st.session_state.run_analysis = False
