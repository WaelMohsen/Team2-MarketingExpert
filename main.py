import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src_2"))

from calculators.metrics_calculator import MetricsCalculator  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from readers.campaign_reader import Campaign_Reader  # noqa: E402
from services.llm_orchestrator import LLMOrchestrator  # noqa: E402
from targets.acquisition_target import AcquisitionTarget  # noqa: E402
from targets.retention_target import RetentionTarget  # noqa: E402
from targets.revenue_target import RevenueTarget  # noqa: E402
from targets.satisfaction_target import SatisfactionTarget  # noqa: E402

load_dotenv()

# read
reader = Campaign_Reader("data/all_campaigns_data.csv")
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
orchestrator = LLMOrchestrator("prompts/", "output_log")
result = orchestrator.run(target, metrics, selected_metrics)

print(result)
