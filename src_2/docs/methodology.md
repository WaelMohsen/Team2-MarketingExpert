# POC Methodology

## Decision Layers

The report keeps three questions separate:

1. **Target achievement:** Did the campaign achieve the primary objective associated with its campaign type?
2. **Business outcome:** Did observed WhatsApp outcomes support funding the pattern again?
3. **Evidence readiness:** Is the available data complete and mature enough for action?

Supporting KPIs explain primary performance. They are not combined into an
arbitrary weighted score. Critical guardrails can downgrade or block a decision.

## Outcome Maturity and Customer Independence

`active` and `stuck_pending` conversations are unresolved. They are reported, but
excluded from mature conversion, delivery, and negative-outcome denominators.
Conversation-level rates are accompanied by customer-level rates so customers with
multiple chats do not silently receive extra statistical weight.

Objective-aligned binomial decision metrics use Empirical Bayes. A beta prior is
fitted from compatible peers, then combined with each entity's successes and trials.
Every campaign, adset, ad, creative, and audience receives its raw rate, corrected
rate, 95% posterior range, learned benchmark, favorable lift range, probability of
beating the benchmark, and `scale` / `hold` / `kill` statistical decision. Wilson
intervals remain descriptive companions for other raw binomial KPIs.

`scale` requires the full favorable-lift range to be above the practical threshold;
`kill` requires it to be fully below the negative threshold; a range crossing zero
is `hold`. The POC threshold is zero and is explicitly an assumption, not an approved
minimum worthwhile business effect.

## Benchmark Order

1. Historical peers from the same objective and type, when a separate history is supplied
2. Current-cycle same campaign for child entities
3. Current-cycle same type
4. Current-cycle same objective
5. Compatible portfolio fallback

The current Sample 2 run has no separate historical store, so the output correctly
labels its priors as current-cycle fallbacks. Every score retains prior alpha, beta,
strength, source, peer count, corrected range, and lift range.

Reach from daily Meta rows is not summed as unique cycle reach. Records where reach
exceeds impressions are counted as quality failures, and reach-dependent awareness
assessment is `data_not_ready` until a valid campaign-level reach extract is supplied.

## Conversation Intelligence

Conversation semantics are an optional diagnostic layer. The model receives only
redacted messages, relative timestamps, language, and product references. Customer
records, attribution, structured outcomes, revenue, and order status stay outside
the API request. Pydantic Structured Outputs produce joinable JSONL records with
prompt/model provenance; attribution is added deterministically afterward.

ConversationSignalsV3 retains the v2 fields and adds customer specificity,
financing intent, agent-elicitation flags for urgency and delivery, controlled
commercial traits, richer agent-tone labels, and product-quality, timing, and
financing barrier types. Every diagnostic rate exposes its raw numerator and
assessable denominator; `unknown` and `not_assessable` labels are excluded rather
than counted as failures. Structured outcomes determine whether an agreed step was
followed by an observed order. This is an order-progression proxy, not proof that
every promised follow-up was completed. These fields explain a deterministic
funding decision and generate tests; they do not override it without a
human-reviewed validation set.

Agent responsiveness is not an LLM opinion. Timestamped customer turns form a
separate response-event fact table. Scorecards report first-response medians,
overall response medians and p90s, answered customer turns, and conversations that
ended with an unanswered customer turn. No good/bad SLA label is assigned until the
business provides an approved service threshold.

Ad-message match is a separate semantic evaluation. It compares the ad headline,
message, theme, and angle with the validated customer need signals, never with the
order outcome. It returns `aligned`, `partial`, `mismatch`, or `unknown` and logs
separate prompt/model provenance. Unknown comparisons are excluded from match-rate
denominators.

## Budget Demonstration

The POC uses 100 normalized units: 70% exploit for statistically supported scale
decisions and 30% explore for named tests attached to hold decisions. Exploit is
weighted by probability of beating the learned benchmark. Explore preserves
historical spend among eligible hold campaigns. Budget is assigned only at campaign
level to avoid double-counting adsets, ads, creatives, and audiences. No maximum
campaign concentration cap is applied.

Every funded hold is emitted as a named exploration test with its hypothesis,
primary metric, assigned units, success and failure rules, and a stop rule fixed
before the next cycle begins.

When outcome definitions are unreconciled, the allocator may produce an
illustrative scenario, but it must mark the scenario as non-operational.
