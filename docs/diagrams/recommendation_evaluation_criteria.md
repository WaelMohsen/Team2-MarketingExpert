# 🚀 Recommendation Evaluation Criteria

## 🎯 Purpose
Evaluate AI-generated marketing recommendations across business quality, expert alignment, and rule compliance.

---

## 🧩 Evaluation Dimensions

The system evaluates recommendations using **three independent components**:

1. Business Relevance
2. Ground Truth Alignment
3. Prompt Compliance

---

# 🟢 1. Business Relevance Evaluation

## 📊 Criteria

### 1. Insight Quality
- Explains *why* the issue/opportunity exists

### 2. Actionability
- Clear, specific, executable steps
- Includes what, where, and how

### 3. Data Grounding
- Based on provided analysis and metrics
- No unsupported assumptions

### 4. KPI Alignment
- Clearly linked to campaign KPIs

### 5. Priority Accuracy
- High-impact recommendations appear first

### 6. Decision Quality
- Represents strong business judgment

### 7. Feasibility
- Realistic and implementable

### 8. Readability
- Easy to understand for non-marketers

---

## 🧾 Output
- Overall score (weighted)
- Per-recommendation scores
- Flags for weak dimensions
- Weak recommendations detection

---

# 🟡 2. Ground Truth Alignment (Hybrid Evaluation)

## 📊 Criteria

### 1. Semantic Similarity
- How close recommendations are to expert GT

### 2. Coverage
- Whether all key expert insights are included

### 3. Matching Accuracy
- Correct pairing between generated and GT recommendations

### 4. Redundancy
- Penalizes duplicate or repeated ideas

---

## ⚙️ Method
- Embedding similarity (cosine)
- LLM fallback for ambiguous cases

---

## 🧾 Output
- Similarity score
- Coverage score
- Final hybrid score
- Matches (rec ↔ GT)
- Missed GT insights
- Flags (low similarity, missing insights)

---

# 🟡 3. Prompt Compliance Evaluation

## 📊 Structural Checks (Deterministic)

### 1. Recommendation Count
- Must be between 5 and 8

### 2. Required Fields
- title
- priority
- what_you_should_do
- evidence

### 3. Priority Order
- Sorted: High → Medium → Low

---

## 🤖 LLM-Based Checks

### 4. No Hallucination
- Uses only provided data

### 5. Clarity
- Easy to understand

### 6. Non-Repetition
- Avoids repeating analysis

---

## 🧾 Output
- Compliance score
- Dimension breakdown
- Flags (e.g., hallucination, missing fields)

---

# 🧮 Final Scoring

Final score is a weighted combination:
