# Mapa conceptual general (Fase 1 + Fase 2A + Fase 3)

> **Objetivo**: visualizar cómo encaja lo ya existente (Graph RAG + Orchestrator + CoT runtime) con el diseño de **Phase 2A Distilabel** y la **Fase 3 de fine-tuning**.
> Este documento queda como mapa conceptual de referencia.

---

## 1) Vista ejecutiva (qué existe y cómo se conecta)

Este repo hoy combina **cuatro planos**:

1. **Plano de ejecución/orquestación** (pipeline agentic + CoT de runtime).
2. **Plano de conocimiento** (Graph RAG de Fase 1, integrado al cliente LLM y al orchestrator).
3. **Plano de entrenamiento** (Fase 2A: diseño de generación sintética local/dev-first con Distilabel).
4. **Plano de adaptación de modelos** (Fase 3: fine-tuning por rol, priorizado y medido).

La idea central: Fase 2A y Fase 3 **no reemplazan** Fase 1; extienden el sistema con un ciclo de mejora donde mejores datasets generan mejores modelos, que a su vez generan mejores artefactos para Graph RAG.

---

## 2) Mapa conceptual global

```mermaid
flowchart TB
    subgraph RUNTIME[Plano Runtime Orquestacion]
        O1[Orchestrator V2]
        O2[CoT Runtime]
        O3[Artifacts operativos]
        O1 --> O2
        O1 --> O3
    end

    subgraph RAG[Plano Conocimiento Fase 1]
        G1[GraphRAG Engine]
        G2[Ingestion incremental]
        G3[Retriever por rol]
        G4[Augmentacion de prompt]
        G2 --> G1 --> G3 --> G4
    end

    subgraph TRAIN[Plano Entrenamiento Fase 2A]
        T1[training pipelines]
        T2[training steps]
        T3[datasets sinteticos]
        T4[checkpoints y stats]
        T1 --> T2 --> T3
        T1 --> T4
    end

    subgraph FT[Plano Fine Tuning Fase 3]
        F1[seleccion de dataset por rol]
        F2[entrenamiento student model]
        F3[evaluacion y criterios de aceptacion]
        F4[modelo ajustado por rol]
        F1 --> F2 --> F3 --> F4
    end

    O3 --> G2
    O3 --> T1
    T3 --> F1
    F4 -. mejora calidad de artifacts .-> O1
    G4 -. contexto para prompts .-> O1
    G4 -. reuso opcional .-> T1
```

---

## 3) Línea temporal por fase (visión de producto técnico)

```mermaid
flowchart LR
    P0[Base Orchestrator BA PO Architect Dev QA] -->
    P1[Fase 1 Graph RAG integrado] -->
    P2A[Fase 2A Distilabel local] -->
    P2B[Fase 2B corridas GPU y batch] -->
    P3[Fase 3 fine tuning por rol]
```

---

## 4) Contrato de CoT: evitar colisión conceptual

```mermaid
flowchart LR
    subgraph COT_A[CoT Orquestacion ya existe]
        A1[Entrada decisiones runtime]
        A2[Salida trazas y auditoria]
        A1 --> A2
    end

    subgraph COT_B[CoT Generacion sintetica Fase 2A]
        B1[Entrada seed y template de rol]
        B2[Salida sample con reasoning]
        B1 --> B2
    end

    COT_A -. no reemplaza .-> COT_B
    COT_B -. no reemplaza .-> COT_A
```

Regla de arquitectura:

- **CoT Runtime** = observabilidad del sistema en ejecución.
- **CoT Sintético** = contenido entrenable dentro de ejemplos.

---

## 5) Fase 1 Graph RAG dentro de la película completa

```mermaid
sequenceDiagram
    participant Art as Artifacts del pipeline
    participant Ing as Graph Ingestion
    participant Eng as GraphRAG Engine
    participant Ret as Retriever por rol
    participant LLM as Cliente LLM y Orchestrator
    participant Tr as Phase2A Training Pipeline

    Art->>Ing: nuevos docs/código/outputs
    Ing->>Eng: indexación incremental + dedup
    LLM->>Ret: consulta por rol/objetivo
    Ret->>Eng: retrieve context
    Eng-->>LLM: contexto enriquecido

    Note over LLM,Tr: Reuso opcional de contexto RAG para prompts sinteticos
    LLM-->>Tr: seeds y contexto de mayor calidad
```

---

## 6) Roles implementados hoy (runtime) y su encaje

Roles implementados en la cadena principal:

- **BA** (Business Analyst)
- **PO** (Product Owner)
- **Architect**
- **Dev**
- **QA**

```mermaid
flowchart LR
    BA[BA] --> PO[PO]
    PO --> AR[Architect]
    AR --> DV[Dev]
    DV --> QA[QA]

    RAG[Graph RAG Fase 1] -. contexto por rol .-> BA
    RAG -. contexto por rol .-> PO
    RAG -. contexto por rol .-> AR
    RAG -. contexto por rol .-> DV
    RAG -. contexto por rol .-> QA

    COT[CoT Runtime] -. trazabilidad .-> BA
    COT -. trazabilidad .-> PO
    COT -. trazabilidad .-> AR
    COT -. trazabilidad .-> DV
    COT -. trazabilidad .-> QA
```

---

## 7) Fase 2A (dev-first) encajada con componentes existentes

```mermaid
flowchart TD
    S1[Seeds y fixtures] --> P[BaseSyntheticPipeline]
    P --> G[ChainOfThoughtGenerator]
    G --> Q[QualityFilterStep]
    Q --> F[FormatValidatorStep]
    F --> D[Dataset JSONL y metadata]
    P --> C[Checkpoint store]

    V[post training validators existentes] --> Q
    M[MockLLM local] --> G
    VLLM[vLLM teacher GPU fase posterior] -. modo gpu .-> G
```

---

## 8) Fase 3 (fine-tuning) y cómo encaja con Fase 1 + Fase 2A

Referencia conceptual tomada de: `PLAN_implementation_distilabel_finetuning_rag.md`.

Puntos clave de encaje:

- Fase 3 consume datasets filtrados/producidos en Fase 2.
- Se propone entrenamiento **por rol** (no todo en paralelo) para controlar costo/riesgo.
- Define criterios de aceptación por calidad del student.
- Cierra un ciclo con Fase 1: mejores modelos generan mejores artefactos, que enriquecen el KG.

```mermaid
flowchart LR
    D2[Fase 2 datasets sinteticos validados] -->
    T3[Fase 3 fine tuning por rol] -->
    M3[student models mejorados] -->
    R1[mejores artifacts del pipeline runtime] -->
    G1[Graph RAG Fase 1 mas rico]

    G1 -. mejor contexto por rol .-> R1
```

```mermaid
flowchart TD
    A[Backlog de roles BA PO Architect Dev QA] --> B[Priorizar rol a entrenar]
    B --> C[Entrenar student de ese rol]
    C --> D[Evaluar contra baseline y criterio de aceptacion]
    D -->|cumple| E[Promover modelo]
    D -->|no cumple| F[Remediar dataset o estrategia]
    F --> C
```

---

## 9) Qué ya está “productivo” vs qué es diseño/plan

| Bloque | Estado actual |
|---|---|
| Graph RAG Fase 1 (`graph_rag/*`, integración en llm/orchestrate) | **Implementado** |
| CoT de orquestación (`scripts/orchestrator/cot_*`) | **Implementado** |
| Cadena de roles BA PO Architect Dev QA (runtime) | **Implementado** |
| Diseño Distilabel Fase 2A (`docs/PHASE2A_*`) | **Implementado y cerrado en local** |
| `training/steps/cot_generator.py` | **Implementado** |
| Fase 3 fine-tuning por rol (`PLAN_implementation_distilabel_finetuning_rag.md`) | **Planificado** |

---

## 10) DSPy: concepto y encaje con RAG + Distilabel

DSPy en este proyecto cumple el rol de **optimización programática de prompts/programas de ejecución** (BA/PO/Architect y QA), mientras que Distilabel Fase 2A se enfoca en **infra de generación sintética** para entrenamiento.

No compiten; se complementan:

- **DSPy**: mejora cómo razonan/estructuran respuestas los agentes en runtime y evaluación.
- **Graph RAG**: mejora el contexto (knowledge grounding) que reciben esos agentes.
- **Distilabel (2A/2B)**: genera datasets para entrenar modelos por rol (Fase 3).

```mermaid
flowchart LR
    RAG[Graph RAG contexto estructurado] --> RT[Runtime de agentes]
    DSPY[DSPy programas y tuning] --> RT
    RT --> ART[Artifacts de pipeline]
    ART --> DATA[Distilabel datasets sinteticos]
    DATA --> FT[Fine tuning por rol]
    FT --> RT
```

Regla práctica:

- DSPy = capa de **calidad de inferencia/orquestación**.
- Distilabel = capa de **producción de datos**.
- Fine-tuning = capa de **adaptación de modelo**.

---

## 11) Lectura recomendada para aterrizar rápido

1. `docs/ONBOARDING_BRANCH_PHASE1_GRAPH_RAG.md`
2. `docs/PHASE2A_TECHNICAL_PLAN.md`
3. `docs/PHASE2A_CODE_DESIGN.md`
4. `docs/PHASE2A_IMPLEMENTATION_CONTRACT.md` (contrato normativo Fase 2A)
5. `PLAN_implementation_distilabel_finetuning_rag.md`

---

## 12) Conclusión conceptual

- Fase 1, Fase 2A y Fase 3 forman una cadena: **contexto (RAG) → datos sintéticos → modelos ajustados → mejores artifacts → mejor contexto**.
- La posible “duplicación CoT” es **de término**, no de responsabilidad, si se mantiene el contrato de separación por dominio.
- Este marco permite evolucionar por iteraciones sin romper lo existente, priorizando roles de mayor impacto.
