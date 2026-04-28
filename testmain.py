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

#----------------------------------
# Config_inputs
#------------------------------------
config_inputs = {
    "category": CATEGORIES[0] , # to change choose one from the above list 
    "analysis_model": "gpt-4o-mini",
    "analysis_temp" :0.0 ,
    "recommendation_model" : "gpt-4o-2024-11-20", # "gpt-4o"
    "recommendation_temp"  : 0.2 , 
    "llm_judge_model" : "gpt-4o-mini" , #  "gpt-4o-mini"
    "llm_judge_temp" : 0.0

}
#---------------------------------------
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
#  Inputs
#-----------------------------

category = config_inputs["category"]
Analysis_model= config_inputs["analysis_model"]
Analysis_temp = config_inputs["analysis_temp"]
Rec_model = config_inputs["recommendation_model"]
Rec_temp = config_inputs["recommendation_temp"]

llm_judge_model= config_inputs["llm_judge_model"]
llm_judge_temp = config_inputs["llm_judge_temp"]

#log 
logger.log (config_inputs , "config")

#-----------------------------------------------
# Marketing truth engin
#--------------------------------
# 1. Data Retrieval
df = data_processor.load_data()
# 2. Calculate metrics
metrics = data_processor.calculate_metrics_full(df, category)
# Generate AI Response (now returns JSON string)
response_dict_data = llm_handler.generate_response(df, category, metrics,  Analysis_model , Analysis_temp, Rec_model, Rec_temp )
response_dict_data.keys()
# Log
logger.log(response_dict_data , "pipeline")


# ---------------------------
# Evaluation Inputs from engine output
# ---------------------------
campaign_id = "Spring Launch"
target = CATEGORIES[0]

analysis_output = response_dict_data.get("analysis", {})

recommendation_output = response_dict_data.get("recommendations", [])

kpis = response_dict_data.get("kpis", [])

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
    context=context,
    model= llm_judge_model, 
    temp= llm_judge_temp)
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
    kpis=kpis,
    model= llm_judge_model,
    temp= llm_judge_temp
)

# ---------------------------
#  Run interpreter Evaluation Pipline 
# ---------------------------
final_output = interpreter.interpret(recommendation_result)
# Log
logger.log(final_output , "EVA_interprter")
