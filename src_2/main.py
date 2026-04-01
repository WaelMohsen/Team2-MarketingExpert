from dotenv import load_dotenv
from readers.campaign_reader import Campaign_Reader
from calculators.metrics_calculator import MetricsCalculator
from targets.acquisition_target import AcquisitionTarget
from targets.revenue_target import RevenueTarget
from targets.retention_target import RetentionTarget
from targets.satisfaction_target import SatisfactionTarget
from services.llm_orchestrator import LLMOrchestrator

load_dotenv()

# read
reader = Campaign_Reader("../data/all_campaigns_data.csv")
campaigns = reader.read_campaign()

# calculate
calculator = MetricsCalculator()
metrics = calculator.calculate(campaigns)

# select target
target_map = {
    "revenue": RevenueTarget(),
    "acquisition": AcquisitionTarget(),
    "retention": RetentionTarget(),
    "satisfaction": SatisfactionTarget(),
}

target = "revenue"
selected_metrics = target_map[target].select(metrics)

# run
orchestrator = LLMOrchestrator("../prompts/","../output_log")
result = orchestrator.run(target, metrics, selected_metrics)

print(result)
