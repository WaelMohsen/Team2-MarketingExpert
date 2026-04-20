import json
import os
from datetime import datetime


class EvaluationLogger:

    def __init__(self, step_name: str):
        self.base_dir = os.path.join("evaluation_logs", step_name)

    def log(self, payload: dict):
        os.makedirs(self.base_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{self.base_dir}/eval_{timestamp}.json"

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)

        return path
