import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import src.data as data_processor
import src.llm as llm_handler

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Marketing Expert Chatbot", page_icon="📈")

st.title("Marketing Expert Chatbot 🤖")
st.markdown("Ask me anything about your marketing performance!")

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
if "user_query" not in st.session_state:
    st.session_state.user_query = ""
if "run_analysis" not in st.session_state:
    st.session_state.run_analysis = False

def handle_click(question):
    st.session_state.user_query = question
    st.session_state.run_analysis = True

# Recommended Questions
st.subheader("Recommended Questions")
col1, col2 = st.columns(2)
col3, col4 = st.columns(2)

questions = [
    "How can we improve our customer acquisition cost?",
    "What is the trend in customer satisfaction scores?",
    "How is our revenue growth performing this month?",
    "What strategies can boost our retention rates?"
]

with col1:
    if st.button("Acquisition Cost 💰", use_container_width=True):
        handle_click(questions[0])
with col2:
    if st.button("Satisfaction Trends 😊", use_container_width=True):
        handle_click(questions[1])
with col3:
    if st.button("Revenue Growth 📈", use_container_width=True):
        handle_click(questions[2])
with col4:
    if st.button("Retention Strategy 🔄", use_container_width=True):
        handle_click(questions[3]) # Force rerun happens on button click automatically in script execution flow for next frame? No.

# Text Input
# value=... sets the initial value. If the user types, it updates.
user_input = st.text_input("Or type your own question here:", value=st.session_state.user_query)

# Analyze Button
if st.button("Analyze", type="primary"):
    st.session_state.user_query = user_input
    st.session_state.run_analysis = True

# Main Logic
if st.session_state.run_analysis and st.session_state.user_query:
    query = st.session_state.user_query
    
    with st.spinner(f"Analyzing: {query}"):
        try:
            # 1. Classification
            category = llm_handler.classify_query(query)
            st.info(f"Categorized as: **{category}**")
            
            # 2. Data Retrieval
            df = data_processor.load_data()
            if df is not None:
                metrics = data_processor.get_metrics_for_category(category, df)
                
                # 3. LLM Generation
                if "error" in metrics:
                    st.error(metrics["error"])
                else:
                    with st.expander("See Calculated Metrics"):
                        st.json(metrics)
                    
                    response = llm_handler.generate_response(query, category, metrics)
                    st.markdown("### Analysis")
                    st.markdown(response)
            else:
                st.error("Data file not found. Please check data/campaign_data.csv")
        except Exception as e:
            st.error(f"An error occurred: {e}")
            
    # Reset analysis flag so it doesn't re-run purely on refresh
    st.session_state.run_analysis = False
