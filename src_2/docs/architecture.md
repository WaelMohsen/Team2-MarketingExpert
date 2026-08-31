# `src_2` — Architecture Diagrams

Reflects the current code (6 ports, deterministic decisions, optional conversation
semantics, LLM-only narrative, evaluation layer). Diagrams are **Mermaid** — they render directly in
GitHub and VS Code, and stay diffable in version control.

Contents:
1. [Pipeline (data-flow)](#1-pipeline--data-flow) — the workflow
2. [Hexagonal architecture (ports & adapters)](#2-hexagonal-architecture--ports--adapters) — the structure
3. [Decision rules](#3-decision-rules) — how a campaign's next action is chosen
4. [Trust boundary](#4-trust-boundary--deterministic-vs-ai) — deterministic vs AI

---

## 1. Pipeline / data-flow

What one call to `run_completed_cycle` does. Edge labels are the functions/ports;
node labels are the **contracts** passed between stages.

```mermaid
flowchart TD
    RAW["3 JSON files: meta, conversations, products"] -->|load_sample2| RP[RawCyclePayload]
    RP -->|normalize_cycle| CAN["CanonicalCycleData (privacy-safe fact tables)"]
    RP -->|redact message-only projection| SI["SemanticConversationInput[]"]
    SI -->|ConversationSignalExtractor.extract| CSR["ConversationSignalRecord JSONL"]
    CAN -->|build_data_quality_report| DQ[DataQualityReport]
    CAN -->|build_scorecards| RAWSC["Raw CycleScorecards (5 entity levels)"]
    RAWSC -->|add_empirical_bayes_scores| SC["Corrected scorecards: raw + posterior + benchmark + lift"]
    CSR -. optional diagnostic aggregation .-> SC
    SC -->|build_evidence_packs| EP["CampaignEvidencePack[]"]
    EP -->|"CampaignAssessor.assess (per campaign)"| AS["CampaignAssessment[]"]
    AS -->|enrich_scorecards| ES["enriched CycleScorecards"]
    ES -->|"BudgetAllocator.allocate"| BS[BudgetScenario]
    EP -->|"CampaignAnalyst.analyze (per campaign)"| CI["CampaignInsight[]"]
    CI -->|"PortfolioSynthesizer.synthesize"| PI[PortfolioInsight]
    PI --> NAR
    BS --> NAR["ReportNarrator.narrate"]
    NAR --> SR[StakeholderReport]
    AS --> RPT
    BS --> RPT
    CI --> RPT
    SR --> RPT[CompletedCycleReport]
    RPT -->|"NarrativeEvaluator.evaluate"| ER[EvaluationReport]

    DQ -. evidence status .-> EP
    DQ -. evidence status .-> BS
    CFG["config YAML: campaign_types, budget_policy"] -. policy .-> AS
    CFG -. policy .-> BS
```

**Read it as:** deterministic measurement (top) → decision ports → deterministic
enrichment → narrative ports → assembled report → evaluation.

---

## 2. Hexagonal architecture / ports & adapters

Dependencies point **inward** (edge → application → core → domain). The six ports
are the swappable sockets; adapters implement them.

```mermaid
flowchart TB
    subgraph EDGE["Presentation (edge)"]
        APP1["app_v2.py → streamlit_app (report)"]
        APP2["app_eval.py → eval_app (quality dashboard)"]
    end
    subgraph APP["Application (orchestration)"]
        RUN["run_completed_cycle"]
        PORTS["ports.py — 6 Protocols"]
    end
    subgraph CORE["Deterministic core"]
        ING[ingestion]
        ANA[analytics]
        DOM["domain (pure: enums, rules, config models)"]
    end
    subgraph ADAPT["Adapters — plug into the ports"]
        DET["Deterministic assessor + allocator (analytics)"]
        OAI["OpenAI analyst / synthesizer / narrator (intelligence)"]
    end
    EVAL["evaluation (checks the narrative)"]

    APP1 --> RUN
    APP2 --> RUN
    APP2 --> EVAL
    RUN --> PORTS
    RUN --> ING
    RUN --> ANA
    ING --> DOM
    ANA --> DOM
    EVAL --> DOM
    PORTS -. "decision ports (default: rules)" .-> DET
    PORTS -. "narrative ports (default: OpenAI)" .-> OAI
```

**The 6 ports:** `CampaignAssessor`, `BudgetAllocator` (decision — default
deterministic), `CampaignAnalyst`, `PortfolioSynthesizer`, `ReportNarrator`
(narrative — default OpenAI), and `ConversationSignalExtractor` (redacted,
schema-validated diagnostic classification).

---

## 3. Decision rules

The transparent logic combines objective-specific configuration with the
Empirical-Bayes lift distribution. No weighted composite score is created.

### 3a. Next-cycle action

```mermaid
flowchart TD
    START["entity successes/trials + compatible peers"] --> EB["fit empirical prior and corrected posterior"]
    EB --> LIFT["sample favorable entity-minus-benchmark lift"]
    LIFT --> LOW{"lift low > practical threshold?"}
    LOW -->|yes| SCALE["statistical decision: scale"]
    LOW -->|no| HIGH{"lift high < negative threshold?"}
    HIGH -->|yes| KILL["statistical decision: kill"]
    HIGH -->|no| HOLD["statistical decision: hold"]
    SCALE --> GUARD{"quality and guardrails permit operation?"}
    GUARD -->|yes| OPS["operational action: scale"]
    GUARD -->|no| TEST["operational action: keep as test"]
    KILL --> DNF["operational action: do not fund"]
```

### 3b. Target status (did it do its job?)

```mermaid
flowchart TD
    T["primary KPI result + guardrails + evidence"] --> TE{"evidence status?"}
    TE -->|data_not_ready| TDNR[data_not_ready]
    TE -->|insufficient| TINS[insufficient_evidence]
    TE -->|ready or limited| PP{"primary KPI passed?"}
    PP -->|no| NA[not_achieved]
    PP -->|yes| GG{"guardrails passed AND evidence ready?"}
    GG -->|no| AWC[achieved_with_concerns]
    GG -->|yes| ACH[achieved]
```

**Then, parent → child propagation** (`_add_child_decisions`): every child keeps its
own raw and corrected score for learning, but it cannot override a blocked parent.

---

## 4. Trust boundary — deterministic vs AI

The golden rule made visual: rules compute and decide (auditable, reproducible); the
AI only explains; the evaluator watches the AI.

```mermaid
flowchart LR
    subgraph DET["Deterministic — reproducible & auditable"]
        direction TB
        I[ingestion] --> S["raw scorecards"] --> EB["Empirical-Bayes corrected scores"] --> A["range-based funding decisions"] --> BU["70/30 budget"]
    end
    subgraph AI["AI — explanation only, cannot change any number or decision"]
        direction TB
        C["redacted conversation semantics"]
        N["analyze / synthesize / narrate"]
    end
    subgraph CHK["Evaluation — guardrail"]
        direction TB
        E["consistency checks + history"]
    end

    A --> N
    BU --> N
    C -. diagnostic context .-> S
    N --> R[CompletedCycleReport]
    R --> E

    classDef det fill:#e8f0ff,stroke:#3D8DFF,color:#15171a;
    classDef ai fill:#fff3e0,stroke:#D89A2B,color:#15171a;
    classDef chk fill:#e9f7ef,stroke:#2E8B57,color:#15171a;
    class I,S,A,BU det;
    class C,N ai;
    class E chk;
```

---

### Keeping these accurate
These are hand-maintained. If you change the pipeline order, a port, or a decision
rule, update the matching diagram. The decision rules (§3) mirror
`domain/assessment_rules.py` exactly; the pipeline (§1) mirrors
`application/reporting.py`.
