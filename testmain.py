import pandas as pd
from dotenv import load_dotenv
import src.metrics_engine as data_processor
import src.llm as llm_handler

from src.evaluation.recommendation_pipeline import RecommendationPipeline

CATEGORIES = [
    "Customer Acquisition",
    "Customer Satisfaction",
    "Revenue Growth",
    "Customer Retention",
]
category=CATEGORIES[0]

# 1. Data Retrieval
df = data_processor.load_data()
# 2. Calculate metrics
metrics = data_processor.calculate_metrics_full(df, category)
# Generate AI Response (now returns JSON string)
response_dict_data = llm_handler.generate_response(df, category, metrics)



#--------------------------------
# 🔹 Init  RECONMMENDATION pipeline
# ---------------------------
client=llm_handler.get_client()
pipeline = RecommendationPipeline(
    llm_callable=llm_handler.llm_callable,
    embedding_callable=llm_handler.embedding_callable
)

# 🔹 Inputs from engine output
# ---------------------------
campaign_id = "Spring Launch"
target = CATEGORIES[0]

analysis_output = {
    "summary": "Low conversion in Google Ads"
}

recommendation_output = {
    "recommendations": [
        {
            "id": "REC-01",
            "title": "Improve targeting",
            "category": "Targeting",
            "priority": "High",
            "whats_happening": "...",
            "what_you_should_do": [{"step": "Adjust audience"}],
            "expected_impact": {"primary_kpi": "Conversion Rate"}
        }
    ]
}

kpis = ["Conversion Rate", "Revenue"]


# ---------------------------
# 🔹 Run
# ---------------------------
result = pipeline.run(
    campaign_id=campaign_id,
    target=target,
    analysis_output=analysis_output,
    recommendation_output=recommendation_output,
    kpis=kpis
)

print(result)

