from readers.campaign_reader import Campaign_Reader
from calculators.metrics_calculator import MetricsCalculator
from services.llm_orchestrator import LLMOrchestrator

# read
reader = Campaign_Reader("../data/all_campaigns_data.csv")
campaigns = reader.read_campaign()
# calculate
calculator = MetricsCalculator()
metrics, selected_metrics = calculator.run(campaigns, "revenue")
# run
orchestrator = LLMOrchestrator("../prompts/","../output_log")
result = orchestrator.run("revenue", metrics, selected_metrics)

print(result)
