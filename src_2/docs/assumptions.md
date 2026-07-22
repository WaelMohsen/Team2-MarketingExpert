# POC Assumptions

- The requested input directory name is `sampe_2`; the spelling is preserved intentionally.
- Campaign type is supplied by the Meta campaign record and resolved through `campaign_types.yaml`.
- Meta media facts and WhatsApp outcome facts are aggregated separately before entity-level joins.
- Net revenue and net ROAS are profitability proxies because product margin and fulfilment cost are unavailable.
- Current evidence thresholds are POC assumptions, not statistically validated sample sizes.
- The observed WhatsApp-to-Meta ratio is not considered literal coverage until both event definitions are reconciled.
- Limited-evidence outcome scenarios are explanatory and require human review.
- A child adset or ad cannot override a blocked parent campaign.
- The LLM explains supplied evidence and deterministic decisions; it does not calculate them.
