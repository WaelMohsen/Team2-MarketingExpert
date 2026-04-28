import pandas as pd
from dotenv import load_dotenv
import src.metrics_engine as data_processor
import src.llm as llm_handler
from src.evaluation.analysis_judge import AnalysisJudge 
from src.evaluation.logger import EvaluationLogger
from src.evaluation.recommendation_pipeline import RecommendationPipeline
from src.schemas.analysis_output_schema import AnalysisOutput
from src.evaluation.Decision_Interpreter import DecisionInterpreter
from datetime import datetime

CATEGORIES = [
    "Customer Acquisition",
    "Customer Satisfaction",
    "Revenue Growth",
    "Customer Retention",
]
category=CATEGORIES[0]

# Timestamp to create log dir for this run 
starttimestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#--------------------------------
# Init logger class 
logger = EvaluationLogger(starttimestamp)
#--------------------------------
# Init analyis eval
#--------------------------------
AnalysisJudger=AnalysisJudge()
#--------------------------------
#  Init  RECONMMENDATION pipeline
# ---------------------------

pipeline = RecommendationPipeline(
    llm_callable=llm_handler.llm_callable,
    embedding_callable=llm_handler.embedding_callable,
    timestamp = starttimestamp
)
#-----------------------
# Init recomendation evaluation interprter
#---------------------------------
interpreter = DecisionInterpreter()

#--------------------------------
# Marketing truth engin
#--------------------------------
# 1. Data Retrieval
df = data_processor.load_data()
# 2. Calculate metrics
metrics = data_processor.calculate_metrics_full(df, category)
# Generate AI Response (now returns JSON string)
response_dict_data = llm_handler.generate_response(df, category, metrics)
response_dict_data.keys()
# Log
logger.log(response_dict_data , "pipeline")


# ---------------------------
# Evaluation Inputs from engine output
# ---------------------------
campaign_id = "Spring Launch"
target = CATEGORIES[0]

analysis_output =response_dict_data.get("analysis" , {})

recommendation_output = response_dict_data.get("recommendations", [])

kpis = response_dict_data.get("kpis",[])

analysis_obj = AnalysisOutput(**analysis_output)

context = f"""
Campaign ID: {campaign_id}
Target: {target}
KPIs: {kpis}
"""
# ---------------------------
#  Run Analysis Evaluation
# ---------------------------
analysis_result = AnalysisJudger.evaluate(
    analysis=analysis_obj,
    context=context)
# Log
logger.log(analysis_result.model_dump(), "Analysis")

# ---------------------------
#  Run Recommendation Evaluation Pipline ()
# ---------------------------
recommendation_result = pipeline.run(
    campaign_id=campaign_id,
    target=target,
    analysis_output=analysis_output,
    recommendation_output=recommendation_output,
    kpis=kpis
)

# ---------------------------
#  Run interpreter Evaluation Pipline 
# ---------------------------
final_output = interpreter.interpret(recommendation_result)
# Log
logger.log(final_output , "EVA_interprter")
