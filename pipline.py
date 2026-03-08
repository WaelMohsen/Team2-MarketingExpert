import os
import json
import pandas as pd 
from datetime import datetime
from metrics_engine import calculate_metrics
from schemas.input_schema import validate_campaign_data
from src.llm import ContentGenerator

OUTPUT_LOG_DIR = "output_log"



def save_output(output: dict):
    os.makedirs(OUTPUT_LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(OUTPUT_LOG_DIR, f"pipeline_output_{timestamp}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
    print(f"Output saved to {filename}")

def run_pipeline(df, target, business_domain, 
                 insight_model="gpt-4o", recommendations_model="gpt-4o"):
    canonical_data = validate_campaign_data(df)
    canonical_df = pd.DataFrame([record.model_dump() for record in canonical_data])

    metrics = calculate_metrics(canonical_df, target)

    generator = ContentGenerator(insight_model=insight_model, recommendations_model=recommendations_model)
    insights = generator.generate_insights( business_domain=business_domain, canonical_data=canonical_df,metrics=None, )
    print(insights)
    recommendations = generator.generate_recommendations(business_domain, metrics, target, insights)
    print(recommendations)
    output = {
        "metrics": metrics,
        "insights": insights,
        "recommendations": recommendations
    }

    save_output(output)
    return output

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

df=pd.read_csv(r"C:\noor\6 LLM club\project\Team2-MarketingExpert\data\all_campaigns_data.csv")
target= "Revenue Growth"
business_domain="Fashion dress's store"

output = run_pipeline( df, target, business_domain,
    insight_model="gpt-4o",
    recommendations_model="gpt-3.5-turbo"
)
