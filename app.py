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
        height: 100px;
        font_size: 20px !important;
        font-weight: bold;
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
                    
                    metric_items = list(metrics.items())
                    num_metrics = len(metric_items)
                    # Simple automated grid layout
                    cols_per_row = 4
                    
                    for i in range(0, num_metrics, cols_per_row):
                        cols = st.columns(cols_per_row)
                        for j in range(cols_per_row):
                            if i + j < num_metrics:
                                key, value = metric_items[i+j]
                                with cols[j]:
                                    st.markdown(f"""
                                    <div style="
                                        background-color: white; 
                                        padding: 15px; 
                                        border-radius: 10px; 
                                        box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
                                        border: 1px solid #e5e7eb;
                                        text-align: center;
                                        height: 100%;
                                    ">
                                        <p style="margin: 0; font-size: 0.85em; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em;">{key}</p>
                                        <p style="margin: 5px 0 0 0; font-size: 1.5em; font-weight: 700; color: #111827;">{value}</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)

                    # Generate AI Response
                    response = llm_handler.generate_response(f"Analyze metrics for {category}", category, metrics)
                    
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
                        {response}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.error("Data file not found. Please check data/campaign_data.csv")
        except Exception as e:
            st.error(f"An error occurred: {e}")
            
    # Reset analysis flag
    st.session_state.run_analysis = False
