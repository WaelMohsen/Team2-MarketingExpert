from dataclasses import dataclass
import re


@dataclass
class CriterionResult:
    name: str
    passed: bool
    partial: bool
    weight: int
    detail: str


class InsightQualityChecker:
    """Learn by implementing each check."""

    @staticmethod
    def _coerce_float(value, default: float = 0.0) -> float:
        if value is None:
            return default
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        if number != number:
            return default
        return number
    @classmethod
    def _normalize_bounce_rate(cls, value) -> float:
        rate = cls._coerce_float(value, 0.0)
        if 0.0 <= rate <= 1.0:
            return rate * 100.0
        return rate
    def __init__(self, analysis: dict, campaign_row: dict):
        self.analysis = analysis
        self.row = campaign_row
        
        # Pre-compute some values you'll need
        self._frequency = self._coerce_float(self.row.get("frequency", 0), 0.0)
        self._bounce_rate = self._normalize_bounce_rate(self.row.get("bounce_rate", 0))
        self._confidence = self._coerce_float(self.analysis.get("confidence_score", 0), 0.0)
        self._detected_issues = self.analysis.get("detected_issues") or []

    # ========================================================================
    # CHECK 1: FACTUAL GROUNDING
    # ========================================================================
    def check_factual_grounding(self) -> CriterionResult:
        key_signals = self.analysis.get("key_signals", [])
        analysis_text = self.analysis.get("analysis", "")
        grounded = [s for s in key_signals if re.search(r"\d+\.?\d*", s)]
        has_numbers = bool(re.search(r"\d+\.?\d*", analysis_text))
        if len(key_signals) == 0:
            return CriterionResult(
                name="Factual grounding",
                passed=False,
                partial=False,
                weight=2,
                detail="No key signals provided. The analysis must include key signals with specific metrics.",
            )
        all_ok = has_numbers and len(grounded) == len(key_signals) and len(grounded) > 0
        partial_ok = has_numbers and len(grounded) < len(key_signals) and len(grounded) > 0
        if all_ok:
            detail = f"All {len(key_signals)} key signals cite specific numbers, and the analysis includes data values."
        elif partial_ok:
            ungrounded = [s for s in key_signals if not re.search(r"\d+\.?\d*", s)]
            detail = (
                f"Analysis has numbers, but only {len(grounded)}/{len(key_signals)} key signals cite specific metrics. "
                f"Missing data in: {ungrounded[0][:50]}..." if ungrounded else ""
            )
        else:
            # No signals grounded OR no numbers in analysis
            if not has_numbers:
                detail = (
                    f"Analysis text contains no numeric references. "
                    f"Only {len(grounded)}/{len(key_signals)} key signals have numbers. "
                    f"Add specific metric values to the analysis explanation."
                )
            else:
                detail = (
                    f"Analysis has numbers, but only {len(grounded)}/{len(key_signals)} key signals cite specific metrics. "
                    f"Every signal must reference a concrete number."
                )
        return CriterionResult(
            name="Factual Grounding",
            passed=all_ok,
            partial=partial_ok,
            weight=2,
            detail=detail
        )


    # ========================================================================
    # CHECK 2: BENCHMARK SPECIFICITY
    # ========================================================================
    
    def check_benchmark_specificity(self) -> CriterionResult:
        signals_text = " ".join(self.analysis.get("key_signals", []))
        text = signals_text + " " + self.analysis.get("analysis", "")
        text = text.lower()        
        has_benchmark = bool(re.search(r"(benchmark|threshold|above|exceeds)\D{0,20}\d", text))
        vague_words = ["good performance", "strong performance", "healthy", "effective"]
        has_vague = any(word in text.lower() for word in vague_words)
        if has_benchmark and not has_vague:
            return CriterionResult(
                name="Benchmark Specificity",
                passed=True,
                partial=False,
                weight=2,
                detail="Benchmarks are stated with explicit numbers/thresholds."
            )
        elif has_benchmark and has_vague:
            return CriterionResult(
                name="Benchmark Specificity",
                passed=False,
                partial=True,
                weight=2,
                detail="Benchmarks are stated with numbers, but vague adjectives are also used."
            )
        else:
            return CriterionResult(
                name="Benchmark Specificity",
                passed=False,
                partial=False,
                weight=2,
                detail="No benchmarks with explicit numbers were found."
            )


    # ========================================================================
    # CHECK 3: ISSUE DETECTION COMPLETENESS
    # ========================================================================
   
    def check_issue_detection(self) -> CriterionResult:
        flag_freq   = self._frequency   > 2.5
        flag_bounce = self._bounce_rate > 0.35
 
        if not (flag_freq or flag_bounce):
            return CriterionResult(
                name="Issue detection completeness",
                passed=True, partial=False, weight=3,
                detail="No mandatory flags triggered by campaign data.",
            )
 
        triggers = []
        if flag_freq:
            triggers.append(
                f"frequency={self._frequency} > 2.5 "
                f"(Instagram fatigue threshold)"
            )
        if flag_bounce:
            triggers.append(
                f"bounce_rate={self._bounce_rate} > 0.35"
            )
 
        if not self.analysis.get("detected_issues"):
            return CriterionResult(
                name="Issue detection completeness",
                passed=False, partial=False, weight=3,
                detail=(
                    "detected_issues is empty but these flags were triggered: "
                    + "; ".join(triggers)
                    + ". The analysis MUST surface these as detected issues."
                ),
            )
 
        issues_text = " ".join(self._detected_issues).lower()
        missing = []
        if flag_freq   and not any(w in issues_text for w in ("frequency", "fatigue")):
            missing.append("frequency fatigue")
        if flag_bounce and "bounce" not in issues_text:
            missing.append("bounce rate")
 
        if missing:
            return CriterionResult(
                name="Issue detection completeness",
                passed=False, partial=True, weight=3,
                detail=(
                    f"detected_issues present but missing: {', '.join(missing)}. "
                    "Triggered: " + "; ".join(triggers)
                ),
            )
        return CriterionResult(
            name="Issue detection completeness",
            passed=True, partial=False, weight=3,
            detail="All threshold-triggered issues are present in detected_issues.",
        )


    # ========================================================================
    # CHECK 4: CONFIDENCE CALIBRATION
    # ========================================================================
    
    def check_confidence_calibration(self) -> CriterionResult:
       
        if self.analysis.get("detected_issues") == [] and self.analysis.get("confidence_score") > 80:
            return CriterionResult(
                name="Confidence Calibration",
                passed=False,
                partial=False,
                weight=2,
                detail=f"confidence_score={self.analysis.get('confidence_score')} but detected_issues empty. Cap must be ≤80 with no detected issues."
            )
        return CriterionResult(
            name="Confidence Calibration",
            passed=True,
            partial=False,
            weight=2,
            detail=f"confidence_score={self.analysis.get('confidence_score')} is appropriately calibrated."
        )

