import json

import pytest

from src.schemas.recommendation_output_schema import validate_recommendation_output


def _recommendation_payload(overrides=None):
    """Helper to create sample recommendation payload."""
    payload = {
        "recommendations": [
            {
                "id": "REC-01",
                "title": "Align landing page messaging",
                "category": "Landing_Page",
                "priority": "High",
                "effort": "Medium",
                "time_to_see_impact": "1-2 weeks",
                "confidence": "High",
                "whats_happening": "Ad messaging does not match landing page.",
                "evidence": ["Click-to-conversion drop is 98%"],
                "what_you_should_do": [
                    {
                        "step": "Update landing page headline",
                        "where": "website",
                        "how": "Use same keywords as ad copy.",
                        "guardrails": ["Maintain brand voice"],
                    }
                ],
                "why_this_matters": "Message alignment improves trust.",
                "expected_impact": {
                    "primary_kpi": "Conversion Rate",
                    "direction": "Increase",
                    "explanation": "Visitors will be less confused.",
                },
                "dependency_or_risk": ["Needs design review"],
                "measurement_plan": {
                    "how_to_measure": "Compare conversion rate before/after",
                    "success_criteria": "Conversion rate increases by 1%",
                    "check_timing": "2 weeks",
                    "notes": "Monitor bounce rate too",
                },
                "owner_suggestion": "Marketing team",
            }
        ]
    }
    if overrides:
        # Merge recommendations if provided
        if "recommendations" in overrides:
            payload["recommendations"] = overrides["recommendations"]
        else:
            payload.update(overrides)
    return payload


class TestRecommendationSchemaValidation:
    """Test suite for recommendation output schema validation."""

    def test_recommendation_single_card_below_min_count_fails(self):
        """High: Single recommendation card fails (min 5 required)."""
        payload = _recommendation_payload()

        with pytest.raises(ValueError, match="must contain 5"):
            validate_recommendation_output(json.dumps(payload))

    def test_recommendation_valid_five_cards_passes_validation(self):
        """High: Valid five recommendation cards pass validation."""
        cards = [_recommendation_payload()["recommendations"][0] for _ in range(5)]
        for i, card in enumerate(cards, 1):
            card["id"] = f"REC-0{i}"

        payload = {"recommendations": cards}
        model = validate_recommendation_output(json.dumps(payload))

        assert len(model.recommendations) == 5

    def test_recommendation_non_english_title_raises_value_error(self):
        """High: Non-English characters in title raise ValueError."""
        payload = _recommendation_payload()
        cards = [payload["recommendations"][0].copy() for _ in range(5)]
        for i, card in enumerate(cards):
            card["id"] = f"REC-{i:02d}"

        cards[0]["title"] = "Améliorer les performances"

        payload = {"recommendations": cards}
        with pytest.raises(ValueError, match="English"):
            validate_recommendation_output(json.dumps(payload, ensure_ascii=False))

    def test_recommendation_non_english_whats_happening_raises_value_error(self):
        """High: Non-English characters in whats_happening raise ValueError."""
        payload = _recommendation_payload()
        cards = [payload["recommendations"][0].copy() for _ in range(5)]
        for i, card in enumerate(cards):
            card["id"] = f"REC-{i:02d}"

        cards[0]["whats_happening"] = "客户流失 high"

        payload = {"recommendations": cards}
        with pytest.raises(ValueError, match="English"):
            validate_recommendation_output(json.dumps(payload, ensure_ascii=False))

    def test_recommendation_english_only_text_accepted(self):
        """High: English-only text in all fields passes validation."""
        cards = [
            _recommendation_payload()["recommendations"][0].copy() for _ in range(5)
        ]
        for i, card in enumerate(cards):
            card["id"] = f"REC-{i:02d}"

        payload = {"recommendations": cards}
        model = validate_recommendation_output(json.dumps(payload))

        assert model.recommendations[0].title == "Align landing page messaging"

    def test_recommendation_unicode_punctuation_is_normalized(self):
        """High: Smart punctuation is normalized instead of failing ASCII validation."""
        cards = [
            _recommendation_payload()["recommendations"][0].copy() for _ in range(5)
        ]
        for i, card in enumerate(cards):
            card["id"] = f"REC-{i:02d}"

        cards[0]["evidence"] = [
            "Frequency levels\u2014already high\u2026 avoid scaling"
        ]
        cards[0][
            "why_this_matters"
        ] = "Customers\u2019 trust improves with clearer messaging."

        payload = {"recommendations": cards}
        model = validate_recommendation_output(json.dumps(payload, ensure_ascii=False))

        assert model.recommendations[0].evidence == [
            "Frequency levels-already high... avoid scaling"
        ]
        assert (
            model.recommendations[0].why_this_matters
            == "Customers' trust improves with clearer messaging."
        )

    def test_recommendation_multiple_cards_different_ids_valid(self):
        """High: Multiple cards (5+) with different ids all validate successfully."""
        cards = []
        for i in range(5):
            card = _recommendation_payload()["recommendations"][0].copy()
            card["id"] = f"REC-{i:02d}"
            cards.append(card)

        payload = {"recommendations": cards}
        model = validate_recommendation_output(json.dumps(payload))

        assert len(model.recommendations) == 5
        assert model.recommendations[0].id == "REC-00"
        assert model.recommendations[1].id == "REC-01"
        assert model.recommendations[4].id == "REC-04"
