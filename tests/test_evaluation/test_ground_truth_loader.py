import json

from src.evaluation.services import GroundTruthLoader


def test_ground_truth_loader_returns_target_data(tmp_path):
    payload = [
        {
            "campaign_id": "Spring Launch",
            "ground_truth": {
                "Customer Acquisition": [{"title": "Refresh creative"}],
                "Revenue Growth": [{"title": "Adjust bid strategy"}],
            },
        }
    ]
    path = tmp_path / "recommendation_GT.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    loader = GroundTruthLoader()

    result = loader.load(
        str(path),
        campaign_id="Spring Launch",
        target="Customer Acquisition",
    )

    assert result == [{"title": "Refresh creative"}]


def test_ground_truth_loader_returns_empty_list_for_missing_campaign(tmp_path):
    payload = [{"campaign_id": "Other Campaign", "ground_truth": {}}]
    path = tmp_path / "recommendation_GT.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    loader = GroundTruthLoader()

    result = loader.load(
        str(path),
        campaign_id="Spring Launch",
        target="Customer Acquisition",
    )

    assert result == []
