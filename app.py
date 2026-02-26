import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import src.data as data_processor
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
                metrics = data_processor.get_metrics_for_category(category, df)
                
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
                    response_json_str = llm_handler.generate_response(f"Analyze metrics for {category}", category, metrics)
                    
                    try:
                        import json
                        # Attempt to parse as JSON
                        report = json.loads(response_json_str)
                        
                        st.markdown("""
                        <div style="margin-top: 2.5em; margin-bottom: 1.5em;">
                            <div style="font-size:2.0em; font-weight:900; color:#4338ca; margin-bottom:0.5em;">📝 AI Evaluation Report</div>
                            <div style="font-size:1.3em; font-weight:800; color:#1e293b; margin-bottom:1.2em;">{headline}</div>
                            <div style="font-size:1.1em; font-weight:400; color:#0f172a; margin-bottom:1.1em;">
                                <span style="display:block; margin-bottom:0.7em;"><span style="font-weight:800;">🔬 Analysis:</span><br>{analysis}</span>
                                <span style="display:block; margin-bottom:0.7em;"><span style="font-weight:800;">🚨 Core Issue:</span><br>{core_issue}</span>
                                <span style="display:block; margin-bottom:0.7em;"><span style="font-weight:800;">📉 Why it matters:</span><br>{why_it_matters}</span>
                                <span style="display:block; margin-bottom:0.7em;"><span style="font-weight:800;">✅ Recommended Action:</span><br>{recommended_action}</span>
                                <span style="display:block; margin-bottom:0.7em;"><span style="font-weight:800;">🔮 Expected Outcome:</span><br>{expected_outcome}</span>
                            </div>
                        </div>
                        """.format(
                            headline=report.get('headline', 'Analysis Report'),
                            analysis=report.get('analysis', ''),
                            core_issue=report.get('core_issue', ''),
                            why_it_matters=report.get('why_it_matters', ''),
                            recommended_action=report.get('recommended_action', ''),
                            expected_outcome=report.get('expected_outcome', '')
                        ), unsafe_allow_html=True)
                        
                        # Check confidence score and normalize it
                        confidence = report.get('confidence_score', 0)
                        if isinstance(confidence, str):
                            try:
                                confidence = int(confidence.strip('%'))
                            except ValueError:
                                confidence = 0
                        
                        # Ensure confidence is within 0-100 range
                        confidence = max(0, min(100, confidence))
                        
                        st.progress(confidence / 100, text=f"Confidence Score: {confidence}%")
                        
                        # Detected Issues List
                        with st.expander("Detailed Issues Found"):
                            for issue in report.get('detected_issues', []):
                                st.write(f"- {issue}")
                                
                    except json.JSONDecodeError:
                        # Fallback if LLM didn't return valid JSON
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
