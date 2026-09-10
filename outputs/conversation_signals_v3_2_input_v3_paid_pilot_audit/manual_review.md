# Schema-v3 Paid Pilot Manual Review

## Scope

- 10 outcome-stratified paid-attributed conversations.
- Prompt: `conversation-signals-v3.2`.
- Privacy projection: `semantic-input-v3`.
- Semantic extraction and ad-message alignment were reviewed against the
  redacted messages and cited message indexes.

## Result

The automated audit passed with zero schema, privacy, attribution, or evidence
validation issues. Eight records were accepted without a semantic calibration
warning. Two records need a business decision about the desired taxonomy before
the 617-record extraction:

| Conversation | Review | Reason |
| --- | --- | --- |
| `conv_068` | Pass | Product-information need, product-story preference, and accepted follow-up are supported. |
| `conv_016` | Pass | Repeated price questions support price interest; absent agent evidence remains not assessable. |
| `conv_010` | Pass | Checkout intent, agreement, later product-fit barrier, and cancellation-stage context remain separated. |
| `conv_003` | Pass with note | Checkout progression is supported; product availability is a cautious interpretation of "if you have." |
| `conv_006` | Pass | Price sensitivity and an unresolved price barrier are directly supported. |
| `conv_009` | Pass | Initial urgent bulk order and later return purpose are both retained without structured outcome input. |
| `conv_001` | Pass | Input-v3 preserves commercial context while masking the address; checkout, high intent, and accepted next step are now supported. |
| `conv_123` | Calibration warning | "Think and come back tomorrow" was labeled low urgency even though the prompt defines deferral as no positive urgency. |
| `conv_135` | Pass | Sparse price/offer questions produce low intent and not-assessable agent tone without invented agent evidence. |
| `conv_011` | Calibration warning | A provided-address step was labeled delivery readiness rather than the more specific checkout-details level. |

## Gate Decision

- Technical pilot gate: passed.
- Privacy and provenance gate: passed.
- Semantic calibration gate: conditional.
- Full 617-record run: not started.

The two warnings affect diagnostic subcategories only. They do not change the
Empirical-Bayes score, confidence range, or deterministic scale/hold/kill
decision. Before the full run, either accept these as tolerable MVP ambiguity or
add deterministic rules for deferral and redacted address progression.
