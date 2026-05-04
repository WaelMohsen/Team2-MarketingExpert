import json
from typing import List


class FileGroundTruthLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load_ground_truth(self, campaign_id: str, target: str) -> List:
        with open(self.file_path, "r", encoding="utf-8") as ground_truth_file:
            data = json.load(ground_truth_file)

        for campaign in data:
            if campaign["campaign_id"] == campaign_id:
                return campaign["ground_truth"].get(target, [])

        return []
