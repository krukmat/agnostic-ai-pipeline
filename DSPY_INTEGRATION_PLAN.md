# DSPy Integration Plan

## Executive Summary

Este documento analiza la viabilidad y el plan de integración de DSPy (Declarative Self-improving Python) en el pipeline multi-role existente. DSPy es un framework de Stanford NLP (ahora parte de Databricks) que permite programar modelos de lenguaje mediante código compositivo en lugar de prompts frágiles. Versión actual: **3.0.3** (Agosto 2025).

**Decisión crítica requerida**: ¿Experimentación paralela o reemplazo gradual de roles BA/QA?

---

## Sobre DSPy Framework

### Descripción General
- **Origen**: Stanford NLP (Feb 2022), evolucionado desde DSP hasta DSPy (Oct 2023)
- **Adopción**: 28,000+ estrellas en GitHub, 160,000 descargas mensuales (mid-2025)
- **Licencia**: MIT
- **Repositorio**: https://github.com/stanfordnlp/dspy
- **Documentación**: https://dspy.ai

### Conceptos Core
1. **Signatures**: Declaraciones de transformaciones de texto con tipos de I/O natural
2. **Modules**: Componentes como `dspy.Predict`, `dspy.ChainOfThought`, `dspy.ReAct`
3. **Optimizers** (antes "teleprompters"): Algoritmos que ajustan prompts y/o pesos del modelo
   - `MIPROv2`: Recomendado para datasets grandes (200+ ejemplos, 40+ trials)
   - `BootstrapFewShot`: Para datasets pequeños
   - `COPRO`: Optimización cooperativa de prompts

### Versión 3.0 - Novedades (2025)
- **Multi-modal I/O**: `dspy.Image`, `dspy.Audio`, tipos compuestos (`list[dspy.Image]`), Pydantic models
- **Tool Integration**: Soporte nativo para MCP servers y LangChain tools
- **Observability**: Integración nativa con MLflow 3.0 (tracing, optimizer tracking, deployment)
- **Breaking Changes**:
  - Requiere Python 3.10–3.13 (dropped 3.9 support)
  - Removidos community retrievers no mantenidos (#8073)
  - Deprecaciones de `functional/`, `dsp/` legacy clients

---

## Observaciones de los prompts DSPy
- `01-context.md` exige un nuevo paquete `dspy_baseline/` para alojar módulos Python que expresen las etapas BA y QA como programas DSPy, sin modificar la estructura existente ni exponer secretos.
- `02-structure.md` detalla la jerarquía exacta de archivos que debemos crear (config, modules, optimizers, scripts, data). Cada módulo debe exportar funciones importables y usar imports relativos.
- `03-ba-module.md` y `04-qa-module.md` definen las firmas DSPy para BA (`BARequirements`) y QA (`QATestCases`), junto con funciones `generate_requirements` y `generate_testcases` que validan la salida y delegan validaciones a helpers en `common.py` y `metrics.py`.
- `05-optimizer.md` y `06-tune-script.md` solicitan un wrapper mínimo de `dspy.MIPROv2` y un script `tune.py` que combine trainset, métricas y MLflow para compilar los programas optimizados y guardar artefactos.
- `07-metrics-common.md` fija el contenido inicial de `dspy_baseline/config/metrics.py` y `dspy_baseline/modules/common.py` (trainsets diminutos, métrica heurística, TODO para validador YAML).
- `08-makefile.md` y `09-readme.md` piden exponer los scripts vía `make` y documentar la capa DSPy con dependencias y flujo de ejecución.

## Impacto en la arquitectura actual
- La automatización actual vive en `scripts/*.py` y se ejecuta vía `make`; no existe paquete `dspy_baseline/`, por lo que la nueva carpeta no colisiona pero sí implica actualizar rutas relativas y entorno (usa `PYTHONPATH` raíz).
- `scripts/run_ba.py` y `scripts/run_qa.py` ya generan artefactos YAML/Markdown con clientes LLM propios (`common.Client`, `logger`); la capa DSPy deberá convivir con ellos. Se planea introducir scripts `dspy_baseline/scripts/run_ba.py` y `run_qa.py` que puedan reutilizar artefactos existentes (p.ej. `planning/requirements.yaml`) sin romper los flujos actuales.
- El Makefile actual define muchas dianas; las nuevas (`dspy-ba`, `dspy-qa`, `dspy-tune-*`) deberán añadirse sin interferir con variables de entorno ni macros ya usados.
- `artifacts/` y `planning/` ya son directorios críticos; los scripts DSPy guardarán resultados bajo `artifacts/` (p.ej. `artifacts/dspy/` o archivos concretos) evitando sobreescribir la salida de los agentes tradicionales.
- El repositorio tiene dependencias gestionadas vía `requirements.txt`. DSPy, MLflow y dependencias extras deberán añadirse ahí o documentarse como requisito manual, verificando no romper `make setup`.

## Plan de trabajo propuesto
1. **Auditoría inicial**
   - Confirmar que no existe carpeta `dspy_baseline/` ni objetivos relacionados (ya verificado vía `rg`/`ls`).
   - Revisar `requirements.txt` y `README.md` para preparar la introducción de nuevas dependencias.
2. **Estructura del paquete**
   - Crear árbol `dspy_baseline/` con `__init__.py` en cada subcarpeta, `config/`, `modules/`, `optimizers/`, `scripts/`, `data/`, y archivos de datos de ejemplo (`demos/ba_demo.json`, `eval/ba_eval.json`).
   - Añadir placeholders y docstrings conforme a los prompts, usando `TODO` donde falte integración real (p.ej. carga de modelos desde config).
3. **Helpers y métricas**
   - Implementar `dspy_baseline/modules/common.py` con trainsets de juguete y validador YAML provisional (`TODO` para reglas estrictas).
   - Implementar `dspy_baseline/config/metrics.py` con heurísticas descritas, asegurando retornos en `[0,1]`.
4. **Programas DSPy**
   - Implementar `ba_requirements.py` (firma, predictor `dspy.Predict`, validaciones) y `qa_testcases.py` (`dspy.ChainOfThought`, métrica opcional).
   - Alinear comentarios con intención de optimización futura (MIPROv2).
5. **Optimización y scripts**
   - Implementar `dspy/optimizers/mipro.py` con wrapper indicado.
   - Crear scripts CLI (`dspy_baseline/scripts/run_ba.py`, `run_qa.py`, `tune.py`) que acepten argumentos (`typer` o `argparse`), carguen config, llamen a los programas y escriban resultados bajo `artifacts/`.
   - En `tune.py`, habilitar `mlflow.dspy.autolog()`, cargar trainset/metric y exportar programa compilado a `artifacts/` con carpeta creada si falta.
6. **Makefile y documentación**
   - Añadir targets `dspy-ba`, `dspy-qa`, `dspy-tune-ba`, `dspy-tune-qa` sin eliminar existentes. Si se requiere activar la venv (`$(PY)`), documentar un TODO según prompt.
   - Añadir README corto en `dspy_baseline/` siguiendo `09-readme.md` y apuntar a `provider.example.yaml`.
7. **Integración con pipeline**
   - Evaluar cómo los nuevos scripts se encadenan con `make loop` o si quedan como herramientas auxiliares; documentar TODOs para integración profunda (p.ej. intercambiar `scripts/run_ba.py` por la versión DSPy cuando esté estable).
   - Revisar `config.yaml`/`scripts/set_role.py` para decidir si necesitan conocer la capa DSPy (probablemente sólo documentar).
8. **Dependencias y QA**
   - Decidir si `requirements.txt` debe incluir `dspy-ai`, `mlflow`, `pyyaml` (ya presente). Añadir o dejar TODO según política del repo.
   - Diseñar verificación mínima (p.ej. ejecutar scripts con mocks o test unitarios stub) y documentar pasos manuales (`make dspy-ba`, etc.).
9. **Revisión final**
   - Confirmar imports relativos, ausencia de claves duras y coherencia de rutas.
   - Validar que la nueva carpeta no rompe `make setup` ni artefactos existentes (ejecución en seco o TODO).

## 🚨 RED FLAGS Y LIMITACIONES CRÍTICAS

### 1. **BLOCKER: Incompatibilidad de Python**
- **Problema**: DSPy 3.0 requiere Python 3.10–3.13
- **Situación actual**: El proyecto usa Python 3.9.10
- **Impacto**: NO se puede instalar DSPy 3.0 sin actualizar Python
- **Mitigación**:
  - Opción A: Actualizar todo el proyecto a Python 3.10+ (testing completo requerido)
  - Opción B: Usar DSPy 2.x (versión legacy, sin features 3.0)
  - Opción C: Entorno virtual separado para experimentos DSPy (complejidad operativa)

### 2. **Requisitos de Datos para Optimización**
- **MIPROv2** (optimizer planeado) requiere:
  - Mínimo 200 ejemplos de entrenamiento para evitar overfitting
  - 40+ trials de optimización (cada trial = llamadas LLM adicionales)
  - ~10 minutos de ejecución por optimization run
  - Costo: desde centavos hasta decenas de dólares por run
- **Problema actual**: No existe dataset de ejemplos BA/QA validados
- **Acción requerida**: Crear corpus de 200+ ejemplos (concept → requirements, requirements → test cases)

### 3. **Context Length Limitations**
- **Issue #381** (GitHub DSPy): Los modelos actuales tienen límites de contexto que causan fallos durante compilación con few-shot learning
  - GPT-3.5: 4,097 tokens
  - GPT-4: 8,192 tokens (modelos más recientes: 128k)
  - Mistral: 8,000+ tokens
- **Riesgo**: Los programas DSPy pueden exceder límites cuando se añaden ejemplos few-shot durante optimización
- **Mitigación**: Usar modelos con contextos grandes (Claude 3.5, GPT-4 Turbo) o limitar número de shots

### 4. **Silent Failures en Dependencias**
- **Bug conocido**: Si falta el paquete `datasets` (removido de deps por defecto en 3.0.0b1), MIPROv2 falla silenciosamente y produce peor optimización
- **Problema**: Errores no explícitos complican debugging
- **Mitigación**: Instalar todas las dependencias opcionales: `pip install dspy[all]` o verificar manualmente

### 5. **Read-Only Environments**
- **Issue conocido (March 2025)**: Múltiples módulos DSPy intentan crear archivos de log al importar, fallando en entornos read-only (AWS Lambda, containers inmutables)
- **Impacto en A2A**: Si los servicios corren en containers con filesystems read-only, DSPy puede fallar al importar
- **Mitigación**: Verificar permisos de escritura en `/tmp` o configurar cache directory custom

### 6. **Black Box Optimization**
- **Limitación inherente**: DSPy optimiza end-to-end sin visibilidad de métricas intermedias (no hay gradientes)
- **Implicación**: Dificulta debug de por qué un optimizer eligió ciertos prompts
- **Compromiso aceptado**: Trade-off conocido de prompt optimization

### 7. **Observability Gaps**
- `inspect_history` solo registra llamadas LLM, no otros componentes (retrievers, tools, módulos custom)
- Logs monolíticos dificultan organización cuando hay múltiples llamadas por predicción
- **Mitigado en parte**: MLflow 3.0 tracing ayuda pero no resuelve todo

### 8. **Synchronous Execution**
- DSPy tiene limitaciones en ejecución asíncrona; llamadas de red pueden bloquear
- **Impacto en A2A**: Puede afectar latencia en el modo distribuido (servicios HTTP)
- **Issue #8273**: Propuesta de capa de protocolo agent para MCP y A2A aún en discusión

### 9. **Dependency Weight**
- `mlflow`: ~200MB con dependencias transitivas
- `dspy-ai`: ~50MB + deps de LLM providers
- **Impacto**: Aumenta tamaño de entorno virtual y tiempo de instalación
- **Considerar**: Dependencias opcionales (`extras_require`) si no todo el equipo necesita DSPy

### 10. **Learning Curve**
- DSPy introduce paradigma diferente (programación vs prompting)
- Equipo necesitará familiarizarse con signatures, modules, optimizers
- **Tiempo estimado**: 1-2 semanas para proficiencia básica

---

## Riesgos Adicionales, Dependencias y Preguntas Abiertas
- **Configuración de proveedores**: falta definir cómo `dspy` leerá credenciales existentes (`config/provider.example.yaml` solo cubre ejemplo). Se requiere decidir si reutilizar `config.yaml` global o mantener archivos separados.
- **Compatibilidad con la orquestación**: las rutas de salida (`planning/requirements.yaml`, `artifacts/qa/`) ya están ocupadas por los agentes tradicionales. Habrá que decidir si los programas DSPy sobre-escriben, generan versiones alternativas o sólo sirven como experimentos (añadir `TODO` en scripts).
- **Gestión de dependencias**: `mlflow` y `dspy-ai` pueden ser pesados; verificar si deben añadirse al entorno principal o condicionar su instalación (p.ej. `extra[dspy]`).
- **Evaluaciones y datasets**: los prompts piden archivos `demos` y `eval` pero no definen contenido. Usar ejemplos mínimos y dejar `TODO` para reemplazarlos por datos reales.
- **Testing**: no hay instrucciones explícitas sobre tests para la capa DSPy. Considerar añadir `pytest` básicos o, al menos, descripciones en README sobre cómo validar manualmente.

---

## Análisis de Costos y Performance

### Costos de Optimización (MIPROv2)
| Escenario | Ejemplos | Trials | Tiempo estimado | Costo LLM estimado* |
|-----------|----------|--------|-----------------|---------------------|
| Mínimo viable | 50 | 20 | ~5 min | $0.50 - $2 |
| Recomendado | 200 | 40 | ~10 min | $2 - $10 |
| Enterprise | 500+ | 100+ | ~30 min | $10 - $50+ |

*Basado en GPT-4, varía significativamente por provider (Ollama local = $0)

### Performance Esperado
- **Sin optimización** (baseline `dspy.Predict`): Similar a prompts actuales
- **Con MIPROv2**: +20-30% mejora en métricas de calidad (según casos reportados)
  - Ejemplo DSPy docs: ReAct agent 24% → 51% accuracy
  - RAG system: 53% → 61% accuracy

### ROI Estimado
- **Inversión inicial**: 2-3 semanas (setup + creación de dataset + optimización)
- **Beneficio esperado**: Mejora consistente en calidad de outputs BA/QA sin ajuste manual continuo
- **Mantenimiento**: Reoptimización periódica cuando cambia distribución de inputs

---

## Estrategia de Migración Propuesta

### Fase 0: Decisiones Pre-requisito (BLOCKER)
- [ ] **Decidir versión de Python**: Actualizar a 3.10+ o usar DSPy 2.x
- [ ] **Decidir scope**: ¿Experimento paralelo o reemplazo progresivo?
- [ ] **Aprobar incremento de dependencias**: +250MB en .venv

### Fase 1: Proof of Concept (2 semanas)
**Objetivo**: Validar DSPy con BA role en modo experimental

1. **Setup aislado** (días 1-2)
   - Branch feature: `feature/dspy-poc`
   - Upgrade Python a 3.10+ en entorno de desarrollo (si aprobado)
   - Instalar `dspy-ai>=3.0.3` y `mlflow>=3.0` en .venv
   - Crear carpeta `dspy_baseline/` según estructura prompts

2. **BA Module baseline** (días 3-5)
   - Implementar `ba_requirements.py` con `dspy.Predict` (sin optimización)
   - Script `dspy_baseline/scripts/run_ba.py` que genere `artifacts/dspy/requirements_dspy.yaml`
   - Comparar outputs con `planning/requirements.yaml` (actual) manualmente

3. **Dataset creation** (días 6-8)
   - Recolectar 50 ejemplos históricos de concepts → requirements
   - Validar calidad manualmente (2 revisores por ejemplo)
   - Formato JSON: `{"concept": "...", "requirements": {...}}`
   - Almacenar en `dspy/data/demos/ba_demo.json`, `dspy/data/eval/ba_eval.json`

4. **Optimization trial** (días 9-10)
   - Implementar `tune.py` con `MIPROv2` (50 ejemplos, 20 trials)
   - Ejecutar optimización: `make dspy-tune-ba` (~5 min)
   - Comparar programa compilado vs baseline (métricas: completitud YAML, validez estructura)

5. **Evaluación PoC** (días 11-14)
   - Probar programa optimizado con 10 concepts nuevos
   - Comparar con outputs actuales (agente BA tradicional)
   - Documento de resultados: ¿mejora justifica complejidad?
   - **Go/No-Go decision**

### Fase 2: Producción BA (si Go, 2-3 semanas)
- Expandir dataset a 200+ ejemplos (crowdsource con equipo)
- Reoptimizar con 40 trials
- Integración con `make loop`: flag `USE_DSPY_BA=1`
- Métricas en MLflow dashboard
- Documentación en `dspy/README.md`

### Fase 3: QA Module (3-4 semanas)
- Repetir proceso para rol QA
- Dataset: requirements → test cases (200+ ejemplos)
- Integración con `make qa`

### Fase 3b: Decomiso BA Tradicional (2-3 días)
- Inventario de entry points (`Makefile`, scripts, docs) que apuntan a `scripts/run_ba.py`.
- Redefinir `make ba` como alias de `make dspy-ba` y ajustar orquestadores (`loop`, `iteration`, `run_orchestrator.py`).
- Deprecar/eliminar `scripts/run_ba.py` y referencias asociadas.
- Ejecutar QA puntual (`make ba → po → plan`) asegurando que Product Owner y Architect consumen DSPy.
- Actualizar documentación (`README`, `DSPY_INTEGRATION_PLAN`, changelog) anunciando el cambio.
- _(Siguiente)_ Añadir flag configurable `features.use_dspy_ba` en `config.yaml` para permitir fallback legacy. Documentar la fase en `docs/phase3b_configuration.md`.

### Fase 4: Integración DSPy → Product Owner (3 días)
- **Objetivo**: Ajustar el rol Product Owner para consumir `planning/requirements.yaml` generado por DSPy y seguir produciendo `product_vision.yaml` y `product_owner_review.yaml` útiles.
- **Tareas**:
  1. Revisar dependencias del prompt (`prompts/product_owner.md`) y decidir si se amplía el YAML DSPy (overview, stakeholders, personas) o si se infieren dentro del rol PO.
  2. Ejecutar `make dspy-ba` + `make po` con al menos dos conceptos (simple y medium) para validar la cadena `concept → visión → review`.
  3. Ajustar `dspy_baseline/modules/ba_requirements.py` o el prompt del PO según gaps detectados (por ejemplo, agregar secciones faltantes, enriquecer meta). *(Durante la validación inicial se detectó que el bloque REVIEW no se genera; queda pendiente reforzar el prompt o agregar validaciones adicionales).* 
  4. Documentar hallazgos y outputs en `docs/phase4_product_owner.md` (crear) e incluir checklist de QA puntual.
  5. _(Nice-to-have)_ Evaluar un módulo DSPy que genere borradores de visión y review cuando exista dataset suficiente (requirements ↔ feedback) para automatizar aún más este rol.

### Fase 5: Integración DSPy → Architect (4 días)
- **Objetivo**: Garantizar que el flujo de Architect (planificación de historias) funciona con la salida DSPy enriquecida.
- **Tareas**:
  1. Validar el clasificador de complejidad (`classify_complexity_with_llm`); si el YAML DSPy es corto, inyectar resúmenes o reutilizar el concepto original para evitar clasificaciones sesgadas a “simple”.
  2. Ejecutar `make dspy-ba`, `make po` y `make plan` con los mismos conceptos de Fase 4; evaluar `planning/stories.yaml` (historias, acceptance, riesgos).
  3. Ajustar prompts (`prompts/architect*.md`) o la generación DSPy para cubrir información que antes venía del BA tradicional.
  4. Registrar resultados en `docs/phase5_architect.md` y preparar recomendaciones para la decisión final (`merge / iterate`).
  5. _(Nice-to-have)_ Evaluar un módulo DSPy dedicado para Architect (firmas específicas de historias) si se dispone de dataset suficiente.
  6. _(Estado actual)_ QA puntual ejecutado con conceptos “Plataforma de eventos…” y “ERP manufactura”; se identificó necesidad de ampliar prompts para generar historias UI/UX.

> Tras las Fases 4 y 5, re-ejecutar QA puntual (PO + Architect) para confirmar que la cadena completa CONCEPT → Requirements → Vision/Stories sigue operativa.

---

## Plan de Testing DSPy Integration

### Tests Unitarios
```bash
tests/dspy/
├── test_ba_module.py          # Validar BARequirements signature
├── test_qa_module.py          # Validar QATestCases signature
├── test_common.py             # Validar helpers YAML
└── test_metrics.py            # Validar métricas heurísticas
```

### Tests de Integración
- `test_dspy_ba_end_to_end.py`: Concept → requirements YAML completo
- `test_dspy_tune_smoke.py`: Verificar MIPROv2 no crashea (con dataset pequeño)
- `test_mlflow_logging.py`: Verificar traces se registran correctamente

### Tests de Compatibilidad
- Verificar outputs DSPy son parseables por Product Owner y Architect
- Verificar `planning/requirements.yaml` schema si DSPy reemplaza agente actual

### CI/CD Considerations
- Tests DSPy requieren credenciales LLM (mock en CI, o usar Ollama local)
- Optimization tests son costosos/lentos → skip en CI, solo smoke tests

---

## Métricas de Éxito

### KPIs Técnicos
1. **Calidad Output BA**:
   - Completitud YAML (todos campos requeridos presentes): ≥95%
   - Validez sintáctica: 100%
   - Coherencia semántica (eval manual): ≥85%

2. **Calidad Output QA**:
   - Cobertura de requirements en test cases: ≥90%
   - Tests ejecutables (no pseudocódigo): ≥95%

3. **Performance**:
   - Latencia BA generation: ≤60s (p95)
   - Latencia QA generation: ≤90s (p95)

4. **Confiabilidad**:
   - Success rate (sin crashes): ≥99%
   - Consistency (mismos inputs → mismos outputs): ≥80%

### KPIs de Negocio
- Reducción en tiempo de revisión manual de requirements: -30%
- Reducción en iteraciones de QA feedback loop: -20%
- Developer satisfaction score: ≥8/10

---

## Checklist de Implementación

### Pre-implementación
- [ ] Aprobar upgrade Python 3.10+ o confirmar uso DSPy 2.x
- [ ] Confirmar budget para optimization runs (~$50 para PoC completo)
- [ ] Asignar resources: 1 dev full-time por 2 semanas (PoC)
- [ ] Revisar issues abiertos DSPy relevantes: https://github.com/stanfordnlp/dspy/issues
- [ ] Decidir estrategia de versionado (branch, feature flag, entorno separado)

### Durante implementación
- [ ] Documentar decisiones de arquitectura en ADRs
- [ ] Code reviews obligatorios en cambios core
- [ ] Validar manualmente primeros 20 outputs DSPy
- [ ] Setup MLflow tracking server (local o remoto)
- [ ] Configurar alertas en caso de degradación de métricas

### Post-implementación
- [ ] Training session equipo sobre DSPy (1-2 horas)
- [ ] Runbook para debugging issues DSPy
- [ ] Plan de rollback si resultados son peores que baseline
- [ ] Schedule reoptimización periódica (cada 3 meses o cuando dataset crece 30%)

---

## Decisiones Requeridas del Equipo

1. **Python Version Upgrade**: ¿Actualizar a 3.10+ ahora o usar DSPy 2.x legacy?
   - **Recomendación**: Upgrade a 3.10+ para aprovechar DSPy 3.0 features y futuras actualizaciones

2. **Modo de operación**: ¿Experimento paralelo o reemplazo gradual?
   - **Recomendación**: Experimento paralelo (outputs a `artifacts/dspy/`) durante PoC, reemplazo gradual solo si resultados son >20% mejor

3. **Dependency management**: ¿Agregar a requirements.txt o extras_require?
   - **Recomendación**: `extras_require` (`pip install -e .[dspy]`) para no impactar usuarios que no usan DSPy

4. **Dataset creation**: ¿Quién crea los 200+ ejemplos?
   - **Recomendación**: Combinar histórico (si existe logs), synthetic generation (LLM genera ejemplos), y validación manual (2 personas por ejemplo)

5. **MLflow hosting**: ¿Local o remoto?
   - **Recomendación**: Local (`mlruns/` en .gitignore) para PoC, remoto (MLflow tracking server) para producción

6. **Rollback plan**: Si DSPy empeora resultados, ¿cómo revertir?
   - **Recomendación**: Feature flag `USE_DSPY_BA=0` (default) permite toggle instantáneo

---

## Referencias y Recursos

### Documentación Oficial
- DSPy Docs: https://dspy.ai
- DSPy GitHub: https://github.com/stanfordnlp/dspy
- MLflow DSPy Flavor: https://mlflow.org/docs/latest/genai/flavors/dspy
- DSPy Optimizer Tracking: https://dspy.ai/tutorials/optimizer_tracking/

### Papers y Artículos
- DSPy Paper (arXiv): https://arxiv.org/pdf/2310.03714
- "Compiling Declarative Language Model Calls": https://hai.stanford.edu/research/dspy-compiling-declarative-language-model-calls-into-state-of-the-art-pipelines
- Comparative Study Teleprompters: https://arxiv.org/html/2412.15298v1

### Community
- DSPy Discord: Ver GitHub README
- Stack Overflow tag: `dspy`
- Issue tracking: https://github.com/stanfordnlp/dspy/issues

---

## Conclusión y Recomendaciones Finales

### Veredicto: 🟡 **PROCEDER CON CAUTELA**

DSPy es un framework maduro y bien soportado (Stanford/Databricks, 28k+ stars), pero la integración requiere inversión significativa:

**Pros**:
- ✅ Optimización automática de prompts (menos tuning manual)
- ✅ Integración nativa MLflow para observability
- ✅ Paradigma programático más mantenible que prompt strings
- ✅ Comunidad activa y desarrollo continuo

**Cons**:
- ❌ **BLOCKER**: Requiere Python 3.10+ (upgrade mandatorio)
- ❌ Necesita 200+ ejemplos validados (esfuerzo significativo)
- ❌ Curva de aprendizaje para equipo
- ❌ Dependencias pesadas (+250MB)
- ❌ Costos de optimización (aunque manejables con Ollama local)

**Recomendaciones**:

1. **Short term** (próximas 2 semanas):
   - Aprobar upgrade Python 3.10+ como pre-requisito
   - Ejecutar PoC Fase 1 con BA role (scope limitado, 50 ejemplos)
   - Decisión Go/No-Go basada en resultados cuantitativos

2. **Medium term** (si Go en PoC):
   - Expandir a producción BA con dataset completo (200+ ejemplos)
   - Comenzar PoC QA role en paralelo
   - Mantener agentes tradicionales como fallback (feature flag)

3. **Long term** (6+ meses):
   - Si DSPy demuestra valor en BA/QA, evaluar Architect/Dev roles
   - Considerar contribuciones upstream (Issue #8273: A2A protocol layer)
   - Posible talk/blog post compartiendo learnings

**Siguiente paso inmediato**: Reunión de decisión con stakeholders para aprobar/rechazar upgrade Python y presupuesto PoC.

---

> **Última actualización**: 2025-11-03
> **Autor**: Análisis técnico basado en documentación oficial DSPy 3.0.3, research papers, y GitHub issues
> **Estado**: Pendiente aprobación de decisiones críticas (Python upgrade, budget, scope)

> Acciones siguientes: revisar con el equipo si la integración debe reemplazar a los agentes actuales o convivir como experimento; confirmar la política de dependencias antes de agregar `dspy-ai`/`mlflow`; definir ubicación final de artefactos DSPy para no pisar la automatización vigente.
