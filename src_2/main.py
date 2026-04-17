from calculators.metrics_calculator import MetricsCalculator
from dotenv import load_dotenv
from readers.campaign_reader import Campaign_Reader
from services.llm_orchestrator import LLMOrchestrator

load_dotenv()

# read
reader = Campaign_Reader("../data/all_campaigns_data.csv")
campaigns = reader.read_campaign()

# calculate
calculator = MetricsCalculator()
metrics, selected_metrics = calculator.run(campaigns, "revenue")
# run
orchestrator = LLMOrchestrator("../prompts/", "../output_log")
result = orchestrator.run("revenue", metrics, selected_metrics)

print(result)
