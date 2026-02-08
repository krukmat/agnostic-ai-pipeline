# Distilabel Phase 2A Usage (Local / Dev-First)

Este documento describe el uso operativo de la infraestructura de Fase 2A sin GPU.

## Prerrequisitos

- Entorno virtual activo (`.venv`)
- Dependencias base instaladas
- (Opcional) perfil training: `pip install -r requirements-training.txt`

## Comandos principales

### 1) Ejecutar generación local por rol

```bash
make synthetic-data ROLE=ba MODE=local NUM_SAMPLES=10 BATCH_SIZE=5
```

### 2) Dry-run (sin persistir muestras)

```bash
make synthetic-data ROLE=architect MODE=local DRY_RUN=1
```

### 3) Validar dataset generado

```bash
make synthetic-validate ROLE=ba
```

### 4) Ver estadísticas

```bash
make synthetic-stats ROLE=ba
make synthetic-stats-all
```

### 5) Tests de la suite 2A

```bash
make test-distilabel-local
make test-distilabel-all
```

## Rutas relevantes

- Datasets: `training/datasets/<role>/results_latest.jsonl`
- Checkpoints: `artifacts/training/checkpoints/<role>.json`
- Config base: `training/configs/base.yaml`
- Schema mínimo JSONL: `training/configs/output_schema.json`

## Notas

- En Fase 2A el backend real GPU queda desacoplado; se usa `MockLLM` en local.
- El script `training/scripts/gpu_session.sh` queda preparado para Fase 2B.
