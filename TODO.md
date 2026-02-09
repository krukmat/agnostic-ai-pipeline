# TODO — Fase 3 (próximo mes)

Estado acordado: el refactor actual se considera cerrado por ahora y la **Fase 3** queda planificada para retomarse el próximo mes cuando haya recursos (incluyendo GPU si aplica para validaciones ampliadas).

## Objetivo de Fase 3 (pendiente)

Consolidar y endurecer la capa de ejecución CLI de `scripts/llm.py` para dejar la complejidad estabilizada y con cobertura operacional ampliada.

## Backlog detallado (mes siguiente)

1. **Hardening de wrappers sync/async**
   - Revisar caminos de error poco frecuentes (`timeout`, `stderr` ruidoso, comandos parciales).
   - Validar comportamiento homogéneo entre `_cli_chat_async` y `_cli_chat` en todos los providers CLI.

2. **Cobertura de pruebas ampliada**
   - Agregar tests específicos de regresión para casos de salida vacía y parseo degradado.
   - Añadir escenarios con respuestas mixtas (`stdout` válido + `stderr` no crítico).

3. **Observabilidad y trazas**
   - Estandarizar campos de logs para diagnóstico de fallos en producción.
   - Evaluar export de métricas de latencia/fallo por provider.

4. **Validación con recursos GPU (cuando estén disponibles)**
   - Ejecutar smoke/integración extendida en entorno con GPU.
   - Confirmar que no hay desvíos de comportamiento respecto a entorno local/dev.

5. **Criterios de cierre de Fase 3**
   - Mantener `_cli_chat_async` y `_cli_chat` en rango B/C bajo sin regresiones.
   - Suite de tests de LLM/orchestrator en verde.
   - Checklist de incidentes conocidos en 0 para esta capa.

## Nota operativa

Hasta retomar esta fase, se mantiene el gate de complejidad en CI para prevenir regresión estructural en nuevos PRs.
