# Target: Customer Acquisition

## Primary Objective:
- Analyze the relationship between CVR, CPC, and CAC to identify marketing bottlenecks and provide data-driven growth recommendations.

## KPI Benchmarks & Interpretation Logic:
1. **Conversion Rate (CVR) Benchmark:**
   - **Range:** 1.4% - 2.5% (Based on Shopify industry averages).
   - **Under-performing (< 1.4%):** Indicates a "Post-Click" bottleneck. The issue is likely the landing page, product images, or checkout friction.
   - **High-performing (> 2.5%):** Indicates a "Pre-Click" or "Scale" opportunity. Focus on traffic volume.

2. **Cost Per Click (CPC) Impact:**
   - **High CPC (e.g., > $2.00):** Even with a good CVR, high traffic costs inflate the CAC.
   - **Logic:** High CPC suggests the need for better ad creatives to improve Click-Through Rate (CTR) and lower acquisition costs.

3. **Bottleneck Identification Rules:**
   - **If CVR is Low + CAC is High:** The primary bottleneck is the website/landing page. Do NOT scale spend; fix the conversion funnel first.
   - **If CVR is High + CAC is High:** The primary bottleneck is the traffic cost (CPC). Focus on testing new creatives or audience segments to find cheaper clicks.

## Analysis Steps (Chain of Thought):
- **Step 1:** Compare the actual CVR against the 1.4% industry benchmark.
- **Step 2:** Determine if the high CAC is driven by poor conversion (CVR) or expensive traffic (CPC).
- **Step 3:** Evaluate ROAS to understand overall campaign efficiency.
- **Step 4:** Generate an actionable recommendation based on the identified bottleneck (e.g., "A/B testing landing pages" vs. "Refreshing ad creatives").

## Example Scenarios for Model Guidance:
- **Scenario A (Low CVR):** CVR: 1.1%, CAC: $60.00 → *Bottleneck:* Landing page/Checkout.
- **Scenario B (High CPC):** CVR: 3.2%, CPC: $2.50 → *Bottleneck:* Ad creative costs/CTR.

## STRICT OUTPUT RULES:
- detected_issues MUST contain at least 1 issue — if metrics are healthy, explain why that is still a risk
- confidence_score MUST NOT exceed 85% unless CVR, CPC, and ROAS all beat benchmarks
- root_cause_hypothesis MUST classify as either "Post-Click bottleneck" or "Pre-Click bottleneck"
- NEVER output empty arrays for detected_issues or business_risks

## REQUIRED OUTPUT PATTERNS:

- key_signals MUST follow this pattern:
  "CVR is X% which is [above/below] the 1.4% industry benchmark"
  "CPC is $X which is [above/below] the $2.00 threshold"

- root_cause_hypothesis MUST start with either:
  "The primary bottleneck is Post-Click..." or
  "The primary bottleneck is Pre-Click..."
  then connect: "because CVR of X% is below the 1.4% benchmark, driving CAC to $Y"

- confidence_score MUST be accompanied by reasoning in root_cause_hypothesis:
  "Confidence is set to X% because [number of metrics that beat/missed benchmark] 
   out of [total] metrics show clear evidence"