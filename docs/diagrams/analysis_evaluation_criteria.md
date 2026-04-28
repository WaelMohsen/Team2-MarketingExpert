# 🧠 Analysis Evaluation Criteria

## 🎯 Purpose
Evaluate the quality of marketing campaign analysis based on clarity, logic, and business relevance.

---

## 📊 Scoring System
- Scale: **1 to 5**
  - 1 = Very Poor
  - 2 = Poor
  - 3 = Acceptable
  - 4 = Good
  - 5 = Excellent

- Each criterion includes:
  - Weight
  - Pass Threshold
  - Borderline Threshold
  - Hard Fail Threshold

---

## 🧩 Criteria

### 1. Analysis Quality (Weight: 0.30)
- Written in clear business language
- No marketing jargon or abbreviations
- Directly addresses campaign performance

---

### 2. Key Signals (Weight: 0.10)
- Specific observations from data
- Not generic or vague statements
- Clearly tied to campaign metrics

---

### 3. Detected Issues (Weight: 0.10)
- Concrete problems identified
- Clear business impact
- Avoids repetition or vagueness

---

### 4. Root Cause Hypothesis (Weight: 0.20)
- Logical explanation of *why* issues occurred
- Strong connection to signals and issues
- Demonstrates reasoning

---

### 5. Business Risks (Weight: 0.15)
- Clearly explains impact on:
  - Revenue
  - Growth
  - Efficiency
- Written for non-marketing stakeholders

---

### 6. Confidence Score (Weight: 0.15)
- Reflects strength of evidence
- Not overconfident or unrealistic
- Consistent with analysis depth

---

## 🧾 Output

The evaluator returns:

- Overall Score (1–5)
- Overall Status:
  - PASS
  - BORDERLINE
  - FAIL
- Per-criterion scores + rationale
- Summary (one-line verdict)
- Improvement suggestions

---

## 🧠 Evaluation Type

- ✅ AI-as-Judge (LLM-based)
- ✅ Rubric-driven
- ❌ No deterministic scoring aggregation