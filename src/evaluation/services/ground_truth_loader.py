import json
from typing import List


class GroundTruthLoader:
    """Loads recommendation ground-truth data for a campaign and target."""

    def load(self, path: str, campaign_id: str, target: str) -> List:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for campaign in data:
            if campaign["campaign_id"] == campaign_id:
                return campaign["ground_truth"].get(target, [])

        return []
