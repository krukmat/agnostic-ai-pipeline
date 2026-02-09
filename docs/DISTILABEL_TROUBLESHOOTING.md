# Distilabel 2A - Troubleshooting

## Error: `missing separator` en Makefile

Verificar que los comandos multilinea tengan tabs válidos.
Validar con:

```bash
make test-distilabel-all
```

## Error: no se generan muestras (`generated = 0`)

- Revisar `quality_thresholds` en `training/configs/base.yaml`
- Revisar heurística de `training/steps/validators_adapter.py`

## Error: `role_dir_not_found` al validar

Generar primero dataset del rol:

```bash
make synthetic-data ROLE=ba MODE=local
make synthetic-validate ROLE=ba
```

## Error por entorno GPU no disponible

En 2A usar siempre modo local:

```bash
make synthetic-data ROLE=ba MODE=local
```

Los tests GPU deben skippear con marker `integration_gpu`.

## Limpiar estado de ejecución

```bash
make synthetic-clean
```
