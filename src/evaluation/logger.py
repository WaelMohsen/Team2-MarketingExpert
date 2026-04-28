import json
import os
from datetime import datetime


class EvaluationLogger:

    def __init__(self, timestamp: datetime):
        #self.base_dir = os.path.join("output_log", "REC_evaluation_logs", step_name)
        self.starttime=timestamp
        self.base_dir = os.path.join("logs", f"{timestamp}_log")


    def log(self, payload: dict,step_name : str):
        os.makedirs(self.base_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{self.base_dir}/{step_name}_{timestamp}.json"

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)

        return path
