"""Unit tests for schema validation in src_2."""

import sys
from pathlib import Path

# Add src_2 to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src_2"))

import pytest  # noqa: E402
from schemas.analysis_output_schema import (  # noqa: E402
    AnalysisOutput,
    validate_analysis_output,
)


class TestAnalysisOutputSchemaValidation:
    """Tests for AnalysisOutput schema validation."""

    def test_valid_analysis_output_complete(self):
        """High: Valid complete analysis output passes validation."""
        payload = """{
            "analysis": "Q1 performance strong across all channels",
            "key_signals": ["ROI improved 25%", "CTR increased"],
            "detected_issues": ["Bounce rate elevated"],
            "root_cause_hypothesis": "Weak landing page optimization",
            "business_risks": ["Q2 performance regression possible"],
            "confidence_score": 0.85
        }"""

        result = validate_analysis_output(payload)

        assert isinstance(result, AnalysisOutput)
        assert result.analysis == "Q1 performance strong across all channels"
        assert result.confidence_score == pytest.approx(85.0)  # Converted to percentage
        assert len(result.key_signals) == 2

    def test_analysis_confidence_score_fraction_converted_to_percent(self):
        """High: Confidence score 0-1 converted to 0-100."""
        payload = """{
            "analysis": "Test analysis",
            "key_signals": [],
            "detected_issues": [],
            "root_cause_hypothesis": "Test cause",
            "business_risks": [],
            "confidence_score": 0.75
        }"""

        result = validate_analysis_output(payload)

        assert result.confidence_score == pytest.approx(75.0)

    def test_analysis_confidence_score_already_percent_preserved(self):
        """High: Confidence score 50-100 preserved as-is."""
        payload = """{
            "analysis": "Test analysis",
            "key_signals": [],
            "detected_issues": [],
            "root_cause_hypothesis": "Test cause",
            "business_risks": [],
            "confidence_score": 92.5
        }"""

        result = validate_analysis_output(payload)

        assert result.confidence_score == pytest.approx(92.5)

    def test_analysis_empty_analysis_text_raises_error(self):
        """Low: Empty analysis text raises ValueError."""
        payload = """{
            "analysis": "",
            "key_signals": [],
            "detected_issues": [],
            "root_cause_hypothesis": "Test cause",
            "business_risks": [],
            "confidence_score": 0.8
        }"""

        with pytest.raises(ValueError, match="Missing or empty 'analysis'"):
            validate_analysis_output(payload)

    def test_analysis_empty_root_cause_raises_error(self):
        """Low: Empty root_cause_hypothesis raises ValueError."""
        payload = """{
            "analysis": "Test analysis",
            "key_signals": [],
            "detected_issues": [],
            "root_cause_hypothesis": "",
            "business_risks": [],
            "confidence_score": 0.8
        }"""

        with pytest.raises(
            ValueError, match="Missing or empty 'root_cause_hypothesis'"
        ):
            validate_analysis_output(payload)

    def test_analysis_empty_collections_accepted(self):
        """Medium: Empty key_signals, detected_issues, business_risks accepted."""
        payload = """{
            "analysis": "Minimal analysis",
            "key_signals": [],
            "detected_issues": [],
            "root_cause_hypothesis": "Root cause",
            "business_risks": [],
            "confidence_score": 0.5
        }"""

        result = validate_analysis_output(payload)

        assert result.key_signals == []
        assert result.detected_issues == []
        assert result.business_risks == []

    def test_analysis_confidence_score_zero_valid(self):
        """Medium: Confidence score 0 is valid."""
        payload = """{
            "analysis": "Low confidence analysis",
            "key_signals": [],
            "detected_issues": [],
            "root_cause_hypothesis": "Root cause",
            "business_risks": [],
            "confidence_score": 0.0
        }"""

        result = validate_analysis_output(payload)

        assert result.confidence_score == pytest.approx(0.0)

    def test_analysis_confidence_score_above_100_clamped(self):
        """Medium: Confidence score > 100 clamped to 100."""
        payload = """{
            "analysis": "Test analysis",
            "key_signals": [],
            "detected_issues": [],
            "root_cause_hypothesis": "Test cause",
            "business_risks": [],
            "confidence_score": 150.0
        }"""

        result = validate_analysis_output(payload)

        assert result.confidence_score == pytest.approx(100.0)

    def test_analysis_invalid_json_raises_error(self):
        """Low: Invalid JSON raises error."""
        payload = "{invalid json"

        with pytest.raises(Exception):  # JSONDecodeError
            validate_analysis_output(payload)

    def test_analysis_missing_required_field_raises_error(self):
        """Low: Missing required field raises error."""
        payload = """{
            "analysis": "Test",
            "key_signals": [],
            "detected_issues": [],
            "root_cause_hypothesis": "Cause"
        }"""  # Missing confidence_score

        with pytest.raises(Exception):  # ValidationError
            validate_analysis_output(payload)
