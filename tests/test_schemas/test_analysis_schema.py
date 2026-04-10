import json

import pytest

from src.schemas.analysis_output_schema import AnalysisOutput, validate_analysis_output


def _analysis_payload(overrides=None):
    """Helper to create sample analysis payload."""
    payload = {
        "analysis": "Campaign shows high impression volume but low conversion rate.",
        "key_signals": [
            "10K impressions",
            "500 clicks",
        ],
        "detected_issues": [
            "Low conversion rate at 2%",
            "High bounce rate on landing page",
        ],
        "root_cause_hypothesis": "Landing page does not match ad messaging.",
        "business_risks": [
            "Wasted ad spend on unqualified traffic",
        ],
        "confidence_score": 0.85,
    }
    if overrides:
        payload.update(overrides)
    return payload


class TestAnalysisSchemaValidation:
    """Test suite for analysis output schema validation."""

    def test_analysis_valid_complete_payload_passes_validation(self):
        """High: Complete valid analysis payload passes validation."""
        payload = _analysis_payload()
        model = validate_analysis_output(json.dumps(payload))

        assert (
            model.analysis
            == "Campaign shows high impression volume but low conversion rate."
        )
        assert len(model.key_signals) == 2
        assert model.confidence_score == 85.0

    def test_analysis_confidence_score_fraction_converted_to_percent(self):
        """High: Confidence score as fraction (0.72) converted to percent (72.0)."""
        payload = _analysis_payload({"confidence_score": 0.72})
        model = validate_analysis_output(json.dumps(payload))

        assert model.confidence_score == 72.0

    def test_analysis_confidence_score_already_percent_preserved(self):
        """Medium: Confidence score as percent (72) not double-converted."""
        payload = _analysis_payload({"confidence_score": 72})
        model = validate_analysis_output(json.dumps(payload))

        assert model.confidence_score == 72

    def test_analysis_empty_analysis_text_raises_value_error(self):
        """Low: Empty or whitespace-only analysis text raises ValueError."""
        payload = _analysis_payload({"analysis": "   "})

        with pytest.raises(ValueError):
            validate_analysis_output(json.dumps(payload))

    def test_analysis_empty_key_signals_accepted(self):
        """Medium: Empty key_signals list is accepted (no validation enforced)."""
        payload = _analysis_payload({"key_signals": []})
        model = validate_analysis_output(json.dumps(payload))

        assert model.key_signals == []

    def test_analysis_empty_detected_issues_accepted(self):
        """Medium: Empty detected_issues list is accepted (no validation enforced)."""
        payload = _analysis_payload({"detected_issues": []})
        model = validate_analysis_output(json.dumps(payload))

        assert model.detected_issues == []

    def test_analysis_empty_business_risks_accepted(self):
        """Medium: Empty business_risks list is accepted (no validation enforced)."""
        payload = _analysis_payload({"business_risks": []})
        model = validate_analysis_output(json.dumps(payload))

        assert model.business_risks == []

    def test_analysis_missing_root_cause_raises_value_error(self):
        """Low: Missing root_cause_hypothesis raises ValueError."""
        payload = _analysis_payload()
        del payload["root_cause_hypothesis"]

        with pytest.raises(ValueError):
            validate_analysis_output(json.dumps(payload))

    def test_analysis_broken_json_raises_json_decode_error(self):
        """Low: Broken JSON (single quotes, trailing commas) raises JSONDecodeError."""
        broken = "{ 'analysis': 'ok', 'key_signals': ['s',], 'detected_issues': ['i',], 'root_cause_hypothesis': 'r', 'business_risks': ['b',], 'confidence_score': 0.8 }"

        with pytest.raises(json.JSONDecodeError):
            validate_analysis_output(broken)

    def test_analysis_non_english_analysis_raises_value_error(self):
        """High: Non-English characters in analysis text raise ValueError."""
        payload = _analysis_payload({"analysis": "Café performance analysis"})

        with pytest.raises(ValueError, match="English"):
            validate_analysis_output(json.dumps(payload, ensure_ascii=False))

    def test_analysis_non_english_key_signal_raises_value_error(self):
        """High: Non-English characters in key_signals raise ValueError."""
        payload = _analysis_payload({"key_signals": ["Signal 中文"]})

        with pytest.raises(ValueError, match="English"):
            validate_analysis_output(json.dumps(payload, ensure_ascii=False))

    def test_analysis_english_only_text_accepted(self):
        """High: English-only text in all fields passes validation."""
        payload = _analysis_payload()
        model = validate_analysis_output(json.dumps(payload))

        assert "impression" in model.analysis

    def test_analysis_confidence_score_zero_valid(self):
        """Medium: Zero confidence score (0.0 or 0) is valid."""
        payload = _analysis_payload({"confidence_score": 0.0})
        model = validate_analysis_output(json.dumps(payload))

        assert model.confidence_score == 0.0

    def test_analysis_confidence_score_above_100_clamped_to_100(self):
        """Medium: Confidence score > 100 is clamped to 100."""
        payload = _analysis_payload({"confidence_score": 150.0})
        model = validate_analysis_output(json.dumps(payload))

        assert model.confidence_score == 100.0

    def test_analysis_to_dict_preserves_all_fields(self):
        """High: Converting model to dict preserves all fields."""
        payload = _analysis_payload()
        model = validate_analysis_output(json.dumps(payload))
        model_dict = model.dict()

        assert set(model_dict.keys()) == {
            "analysis",
            "key_signals",
            "detected_issues",
            "root_cause_hypothesis",
            "business_risks",
            "confidence_score",
        }
