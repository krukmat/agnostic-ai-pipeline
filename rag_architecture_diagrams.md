# RAG Local-First — Detailed Architecture Diagrams (Big Picture)

**Purpose**: provide detailed visualizations of the end-to-end pipeline, validation gates, and governance layers.

---

## 1. End-to-end pipeline (macro view)

```mermaid
flowchart TB
  subgraph Roles["Agentic Roles"]
    BA[BA]
    PO[PO]
    ARCH[Architect]
    DEV[Dev]
    QA[QA]
  end

  subgraph RAG["RAG Subsystem"]
    RG[Retrieval Gateway]
    CM[Context Manager]
    PP[Post-Processing]
  end

  subgraph KH["Knowledge Hub"]
    ING[Ingestion]
    META[Metadata]
    VDB[Vector Index]
    BM25[Lexical Index]
    RAW[Raw Store]
  end

  subgraph GOV["Validation & Governance"]
    BRV[Business Requirements Validator]
    QA_GATE[QA Gates]
    TRACE[Traceability]
  end

  BA --> RG
  PO --> RG
  ARCH --> RG
  DEV --> RG
  QA --> RG

  RG --> CM --> PP
  PP --> Roles

  ING --> RAW
  ING --> META
  ING --> VDB
  ING --> BM25

  RG --> BRV
  CM --> BRV
  PP --> BRV

  PP --> QA_GATE
  RG --> TRACE
  CM --> TRACE
  PP --> TRACE
```

---

## 2. Business requirements validation (stage gates)

```mermaid
flowchart LR
  A[Agent Request] --> RG[Retrieval]
  RG --> G1{Gate 1:
  Required evidence in top-k?}
  G1 -- No --> ABSTAIN[Abstain / Clarify]
  G1 -- Yes --> CM[Context Assembly]
  CM --> G2{Gate 2:
  Evidence aligned with requirements?}
  G2 -- No --> ABSTAIN
  G2 -- Yes --> GEN[Generation]
  GEN --> G3{Gate 3:
  Output meets acceptance criteria?}
  G3 -- No --> ABSTAIN
  G3 -- Yes --> PP[Post-Processing]
  PP --> G4{Gate 4:
  Final validation passes?}
  G4 -- No --> ABSTAIN
  G4 -- Yes --> OUT[Validated Output]
```

---

## 3. Evidence traceability (minimum schema)

```mermaid
sequenceDiagram
  participant A as Agent
  participant RG as Retrieval Gateway
  participant CM as Context Manager
  participant PP as Post-Processing

  A->>RG: query + role + filters + budgets
  RG->>RG: trace_id
  RG->>CM: retrieval_results (vector + bm25)
  CM->>CM: fuse/dedupe/trace decisions
  CM->>PP: final_context_chunks
  PP->>PP: citations_map + validation
  PP-->>A: response + trace_id
```

---

## 4. Phase 0 execution (gate-critical flow)

```mermaid
flowchart TB
  S[Start Phase 0] --> OBJ[Define objectives per role]
  OBJ --> HW[Confirm M1/16GB baseline + budgets]
  HW --> CORPUS[Define corpus <=5k docs or <=500MB]
  CORPUS --> METRICS[Define metrics + thresholds]
  METRICS --> TESTSET[Freeze test set + top-k]
  TESTSET --> EVIDENCE[Define evidence sufficiency rubric]
  EVIDENCE --> GATE{All checklist items complete?}
  GATE -- No --> STOP[Do not advance]
  GATE -- Yes --> NEXT[Proceed to Phase 1]
```

---

## 5. QA gates (backend Python development)

```mermaid
flowchart LR
  PR[PR/Change] --> COV{Coverage ≥80%?}
  COV -- No --> FAIL[Fix / Exception]
  COV -- Yes --> CC{Cyclomatic ≤10?}
  CC -- No --> FAIL
  CC -- Yes --> MI{Maintainability ≥65?}
  MI -- No --> FAIL
  MI -- Yes --> DUP{Duplication <5%?}
  DUP -- No --> FAIL
  DUP -- Yes --> LINT{Linting OK?}
  LINT -- No --> FAIL
  LINT -- Yes --> MERGE[Gate Pass]
```

---

## 6. RAG + Governance integration (big picture)

```mermaid
flowchart TB
  subgraph Governance
    BRV[Business Requirements Validator]
    Metrics[Metrics Suite]
    Gates[Decision Gates]
  end

  subgraph RAGPipeline
    Ingest[Ingestion]
    Retrieve[Retrieval]
    Assemble[Context Assembly]
    Generate[Generation]
    Post[Post-Processing]
  end

  Ingest --> Retrieve --> Assemble --> Generate --> Post
  Retrieve --> BRV
  Assemble --> BRV
  Generate --> BRV
  Post --> BRV
  BRV --> Gates
  Metrics --> Gates
```

---

## 7. Phase gates audit flow (end‑to‑end)

```mermaid
flowchart TB
  F0[Phase 0 Gate
  Objectives + Corpus + Metrics + Testset] --> F1[Phase 1 Gate
  Contracts + Policies]
  F1 --> F2[Phase 2 Gate
  Ingestion + Chunking + Metadata]
  F2 --> F3[Phase 3 Gate
  Context Assembly + Evidence Rules]
  F3 --> F4[Phase 4 Gate
  Metrics + Governance + Trace Review]
  F4 --> F5[Phase 5 Gate
  Offline Optimization]

  F0 -->|Fail| STOP0[Stop: missing Phase 0 checklist]
  F1 -->|Fail| STOP1[Stop: contract gaps]
  F2 -->|Fail| STOP2[Stop: ingestion/metadata gaps]
  F3 -->|Fail| STOP3[Stop: evidence policy gaps]
  F4 -->|Fail| STOP4[Stop: metrics not measured]
  F5 -->|Fail| STOP5[Stop: optimization criteria unmet]
```

---

## 8. Audit metrics coverage map

```mermaid
flowchart LR
  Metrics[Metrics Suite] --> Lat[Latency p50/p95]
  Metrics --> Mem[Memory peak/sustained]
  Metrics --> Idx[Index size]
  Metrics --> Gr[Groundedness rubric]
  Metrics --> Abs[Abstention rate]

  Lat --> Audit[Audit Report]
  Mem --> Audit
  Idx --> Audit
  Gr --> Audit
  Abs --> Audit
```

---

## 9. Data lineage and versioning (audit trail)

```mermaid
flowchart LR
  SRC[Sources] --> COR[Corpus vX]
  COR --> IDX[Index vY]
  COR --> TS[Testset vZ]
  IDX --> RUN[Evaluation Run]
  TS --> RUN
  RUN --> RPT[Audit Report]
```

---

## 10. Weaviate vs FAISS decision audit

```mermaid
flowchart TB
  START[Start Decision] --> RAM{RAM ≤12GB?}
  RAM -- No --> FAISS[Choose FAISS]
  RAM -- Yes --> P95{p95 ≤2s?}
  P95 -- No --> FAISS
  P95 -- Yes --> IDX{Index ≤2x limit?}
  IDX -- No --> FAISS
  IDX -- Yes --> WEAV[Choose Weaviate]
```

---

## 11. Compliance and security audit flow

```mermaid
flowchart TB
  COR[Corpus Sources] --> SENS[Classify Sensitivity]
  SENS --> EXC{PII/Secrets?}
  EXC -- Yes --> REDACT[Redact/Exclude]
  EXC -- No --> ACCESS[Access Rules]
  ACCESS --> LOGS[Logging Policy]
  LOGS --> AUDIT[Compliance Audit]
```

---

## 12. RACI audit mapping

```mermaid
flowchart LR
  OBJ[Objectives] --> R1[Product/BA R]
  OBJ --> A1[Sponsor A]
  OBJ --> C1[Architecture C]

  MET[Metrics] --> R2[Architecture R]
  MET --> A2[Sponsor A]
  MET --> C2[Dev/QA C]

  CORP[Corpus Scope] --> R3[Architecture/Security R]
  CORP --> A3[Sponsor A]
  CORP --> C3[BA/Legal/IT C]
```

---

**Status**: Ready for review.