# Árbol de tareas — Refactorización CC/Deuda Técnica

Base de planificación: `CC_TD.md` + `DD_CC_REFACTOR.md`

---

## 🌳 Roadmap de refactor

```text
Refactor CC + Centralidad (runtime core)
├── Fase 1 (P0) — scripts/orchestrate.py::_process_story
│   ├── [x] Analizar hotspots y cortes seguros
│   ├── [x] Extraer helpers de metadata y recovery budget
│   ├── [x] Extraer manejo de failure Dev (status + metadata + override)
│   ├── [x] Extraer ramas de QA (pass / no_tests / failure)
│   ├── [x] Validar no regresión con tests de orquestación
│   └── [x] Medir CC post-refactor (E37 → B9)
│
├── Fase 2 (P1) — scripts/llm.py::_parse_cli_json_output
│   ├── [x] Separar extracción de candidato JSON
│   ├── [x] Separar parseo con fallback line-delimited
│   ├── [x] Separar extracción de texto desde payload dict/list
│   ├── [x] Validar no regresión con tests de llm/routing
│   └── [x] Medir CC post-refactor (D27 → A3)
│
├── Fase 3 (P1) — scripts/llm.py::_cli_chat_async + _cli_chat
│   ├── [x] Diseñar core común de ejecución CLI (sync/async wrappers)
│   ├── [x] Unificar manejo de errores, logging y timeout
│   ├── [x] Reducir duplicación de construcción/parseo de respuesta
│   ├── [x] Validar no regresión en tests CLI/providers
│   └── [x] Medir reducción CC objetivo (C20/C19 → B/C bajo)
│
└── Fase 4 (Governance CI)
    ├── [x] Agregar gate radon en CI para archivos tocados
    ├── [x] Bloquear nuevos bloques E/F
    ├── [x] Permitir D solo con justificación + issue de remediación
    └── [x] Publicar guideline de complejidad para PRs
```

---

## ✅ Estado ejecutivo actual

- **Completado**: Fase 1 + Fase 2 + Fase 3 + Fase 4
- **Pendiente**: siguiente ciclo de hardening/seguimiento

### Métricas ya logradas

- `scripts/orchestrate.py::_process_story`: **E(37) → B(9)**
- `scripts/llm.py::_parse_cli_json_output`: **D(27) → A(3)**
- `scripts/llm.py::_cli_chat_async`: **C(20) → B(7)**
- `scripts/llm.py::_cli_chat`: **C(19) → B(6)**

### Siguiente objetivo inmediato

Ejecutar un **ciclo de seguimiento** para institucionalizar la mejora:

- Revisar excepciones D abiertas y su remediación
- Añadir reporte de complejidad como artefacto del workflow
