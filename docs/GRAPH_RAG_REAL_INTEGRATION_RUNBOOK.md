# Graph RAG – Runbook de Integración Real (LightRAG + Ollama)

## Objetivo
Ejecutar tests `integration_real` para validar ciclo real:
`initialize -> ingest -> query/retrieve -> finalize`.

## Precondiciones
1. `lightrag` instalado.
2. `ollama` instalado y disponible en PATH.
3. `ollama serve` corriendo en `127.0.0.1:11434`.
4. Modelos descargados:
   - `qwen2.5:7b-instruct`
   - `bge-m3`

Comandos sugeridos:

```bash
ollama serve
ollama pull qwen2.5:7b-instruct
ollama pull bge-m3
```

## Ejecución

### Suite rápida (sin real integration)
```bash
make test-fast
```

### Suite real
```bash
make test-rag-real
```

o directamente:

```bash
pytest -m integration_real -q
```

## Interpretación de resultados
- **PASS**: entorno real listo y flujo validado.
- **SKIP (con razón explícita)**: faltan precondiciones (normal en CI sin Ollama).
- **FAIL**: regresión real en integración.

## Métricas mínimas recomendadas por corrida
1. `passed/skipped/failed` en marker `integration_real`.
2. Latencia p50/p95 para query base (si se mide en test o log).
3. Confirmación de deduplicación en ingestion (2ª corrida con más `skipped`).
4. Confirmación de cache hit (segunda query no más lenta que la primera).
