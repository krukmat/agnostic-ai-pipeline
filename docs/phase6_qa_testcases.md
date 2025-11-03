# Fase 6 – Integración DSPy ↔ QA Testcases

**Objetivo**  
Construir un módulo DSPy que genere casos de prueba (Markdown numerado) para cada historia, cubriendo al menos un escenario “Happy Path” y uno “Unhappy Path”, utilizando la signature `QATestCases` descrita en `dspy_prompts/04-qa-module.md`.

- **Diagrama de estado**

```mermaid
graph TD
    A[Fase 6 - QA DSPy] --> B[Diseño de módulo QATestCases\n(Completado)]
    A --> C[Heurística de cobertura + Retry guidance\n(Completado)]
    A --> D[Dataset qa_eval.yaml + lint automático\n(Completado)]
    A --> E[Integración make qa con flag DSPY_QA_SKIP_IF_MISSING\n(Completado)]
    A --> F[Automatizar ejecución DSPy en sandbox o proveedor alterno\nPendiente]
    A --> G[Ampliar dataset según nuevos arquetipos\nEn curso continuo]
```

- **Duración estimada**: 4 días  
**Owner**: Equipo QA / DSPy  
**Prerequisitos**:
- Rama `dspy-integration` con BA/PO/Architect ya adaptados.
- YAML de historias (`planning/stories.yaml`) generado con el flujo DSPy.
- Servidor LLM activo (provider para QA configurado en `config.yaml`).

---

## 1. Diseño del módulo
- Archivo objetivo: `dspy_baseline/modules/qa_testcases.py`.
- Signature:
  ```python
  import dspy

  class QATestCases(dspy.Signature):
      story_title: str
      story_description: str
      acceptance_criteria: str
      test_cases_md: str
  ```
- Programa principal:
  ```python
  QA_PROGRAM = dspy.ChainOfThought(QATestCases)
  ```
  para permitir razonamiento paso a paso.
- Función pública `generate_testcases(story: dict) -> str`:
  1. Extraer `title`, `description` y `acceptance_criteria`.
  2. Ejecutar `QA_PROGRAM`.
  3. Retornar markdown numerado con al menos una prueba positiva y otra negativa.
  4. (Opcional) Evaluar cobertura con métrica en `dspy/config/metrics.py`; dejar TODO si es baja.
- Documentar en el módulo que está pensado para optimización futura con MIPROv2.

---

## 2. Plan paso a paso
1. Crear archivo y signature (`½ día`).
2. Implementar `generate_testcases(story)` siguiendo los requisitos (markdown con numeración y cobertura mínima).
3. Añadir métrica heurística en `dspy/config/metrics.py` para evaluar test cases (ej. validar que existan ambas rutas).
4. Ajustar `Makefile` y scripts para ejecutar QA DSPy (p.ej. `make dspy-qa` que recorra historias y genere archivos en `artifacts/dspy/testcases/`).
5. Validar:
   ```bash
   make dspy-ba CONCEPT="..."
   make po
   make plan
   make dspy-qa
   ```
   Revisar `planning/stories.yaml` y los casos generados.
6. Documentar en este archivo los hallazgos y próximos pasos.

---

## 3. Riesgos y mitigaciones
| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Markdown incompleto (faltan test negativos) | Casos insuficientes | Añadir validación y reintentar |
| LLM devuelve texto sin numeración | Dificulta QA manual | Postprocesar salida para numerar |
| Cobertura deficiente | Casos no detectan errores | Ajustar prompt o métrica |

---

## 4. Resultados esperados
- Módulo DSPy `qa_testcases.py` con ChainOfThought.
- Función opcional `make dspy-qa` que genere Markdown numerado en `artifacts/dspy/testcases/`.
- Documento actualizado con ejemplos de casos de prueba y observaciones.

---

## 5. Resultados
- **Fecha**: 2025-11-03  
- **Historias probadas**: stories.yaml (última salida de Architect)  
- **Hallazgos**:  
  - Markdown generado con listas numeradas; se incluye nota cuando falta cobertura negativa.  
  - El módulo reusa la configuración LLM de DSPy (BA) y corre vía `make dspy-qa`.  
  - Se reforzó la verificación heurística (`dspy_baseline/config/metrics.py`) para detectar encabezados “Happy Path/Unhappy Path”, expected result y numeración. `generate_testcases` ahora reintenta automáticamente con guías adicionales si la cobertura cae por debajo de 0.75 y anota un warning si sigue incompleta.  
  - Se añadieron guías base en el módulo (`BASE_GUIDANCE`, `EMAIL_GUIDANCE`) que obligan a generar secciones numeradas y a cubrir caídas del servicio de email, direcciones inválidas, rebotes y telemetría.  
  - `make dspy-qa` (ejecutado en host) generó 10 archivos (`artifacts/dspy/testcases/S001.md` … `S010.md`). Tras aplicar el nuevo guidance, `S010.md` ahora incluye secciones Happy/Unhappy con numeración y escenarios negativos para email inválido, servicio SMTP caído y retrasos por throttling, sin necesidad de advertencias adicionales.
  - Se agregó el validador automático `make dspy-qa-lint`, que revisa cada Markdown generado asegurando encabezados Happy/Unhappy, numeración y menciones a fallos. El smoke test `tests/smoke/test_dspy_qa_validation.py` ejecuta esta verificación cuando existen artefactos recientes. Las expectativas específicas se mantienen en `dspy_baseline/data/qa_eval.yaml` (ej. S001 debe incluir “invalid email” y “already registered”; S010 debe cubrir “unavailable” y “retry”).
  - El dataset `qa_eval.yaml` cubre todos los arquetipos actuales (registros, check-in, notificaciones push/email, catálogos, dashboards, accesibilidad, seguridad). Cada entrada fuerza vocabulario clave para validar escenarios negativos específicos (p.ej., S004 exige “no events” y “error message”; S009 requiere “throttling” y “unauthorized”).
  - Se añadió la bandera `DSPY_QA_SKIP_IF_MISSING=1` para entornos CI donde no se pueda generar DSPy on‑the‑fly: con esa variable, `make qa` omite la generación y el lint solo valida si ya existen artefactos (o pasa limpio si faltan). Recomendación: versionar un snapshot bajo `artifacts/dspy/testcases/` o ejecutarlo previamente en host antes de llamar a `make qa` en pipelines.
  - Nuevo modo stub (`DSPY_QA_STUB=1`) genera casos deterministas sin depender del modelo (usa `qa_eval.yaml` para poblar escenarios negativos). Útil en el sandbox donde no hay acceso a Ollama; las salidas cumplen el lint y sirven para smoke tests mínimos, aunque no sustituyen la revisión con DSPy real.
- **Siguientes pasos**: Ajustar prompts o heurística para aumentar cobertura en historias complejas (p.ej., front-end).  
  - Volver a ejecutar `make dspy-qa` (preferentemente en el host hasta que el sandbox pueda acceder al modelo) y confirmar que `S010.md` incorpora escenarios de fallo de notificación sin necesidad de la nota de advertencia.
