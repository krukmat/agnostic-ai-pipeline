# Fase 3: Experimento Comparativo BA Master vs DSPy – Technical Guide

**Part of**: DSPy Comparison Plan (`DSPY_COMPARISON_PLAN.md`)  
**Duration**: 1 semana (2–3 horas ejecución + 1–2 días análisis)  
**Status**: ⬜ Ready to Start

---

## Resultados del Experimento (Ejecución Parcial)

> ⚠️ **Aún no se registran resultados en este entorno.**  
> Cuando ejecutes `bash scripts/run_comparison.sh`, documenta aquí los hallazgos (parciales o finales): métricas numéricas, observaciones cualitativas y conclusiones preliminares.

---

## (Contenido Original del Plan - Referencia)

El resto de este documento conserva el plan operativo para ejecutar la fase (prerrequisitos, dataset, script batch, verificaciones, troubleshooting, entregables y próximos pasos).

---

## Prerequisitos y Preparación

### 1. Verificar estado del repositorio

```bash
# 1.1 Git limpio
git status --porcelain

# Si hay cambios, stashear antes del experimento
git stash push -m "WIP before Phase 3 experiment"

# 1.2 Branches requeridos
git branch --list main dspy-integration

# Crear branch DSPy si falta
git checkout -b dspy-integration main
```

### 2. Herramientas necesarias

```bash
command -v jq >/dev/null && echo "✅ jq installed" || echo "❌ jq missing"
command -v pyenv >/dev/null && echo "✅ pyenv available" || echo "⚠️ pyenv not found (OK)"

make -n ba >/dev/null 2>&1 && echo "✅ make ba"
make -n dspy-ba >/dev/null 2>&1 && echo "✅ make dspy-ba"
```

### 3. Credenciales LLM

```bash
test -f config.yaml && echo "✅ config.yaml found" || echo "❌ config.yaml missing"
grep -A3 "^  ba:" config.yaml

# Validar claves según provider
if grep -q "provider: openai" config.yaml; then
  test -n "$OPENAI_API_KEY" && echo "✅ OPENAI_API_KEY set" || echo "⚠️ OPENAI_API_KEY missing"
fi
```

### 4. Directorios de salida

```bash
mkdir -p artifacts/comparison/{master,dspy,logs}
ls -ld artifacts/comparison/*
```

---

## Dataset de 30 Conceptos

Distribución: **10 simples**, **15 medias**, **5 complejas**.

```yaml
concepts:
  # Simple (1–10)
  - { id: C001, text: "Un blog personal con posts y comentarios", expected_complexity: simple }
  - { id: C002, text: "Aplicación TODO list con prioridades", expected_complexity: simple }
  - { id: C003, text: "Calculadora de propinas para restaurantes", expected_complexity: simple }
  - { id: C004, text: "Generador de contraseñas seguras", expected_complexity: simple }
  - { id: C005, text: "Conversor de unidades (temperatura, longitud, peso)", expected_complexity: simple }
  - { id: C006, text: "Registro de gastos personales", expected_complexity: simple }
  - { id: C007, text: "Timer Pomodoro con estadísticas", expected_complexity: simple }
  - { id: C008, text: "Biblioteca de recetas de cocina", expected_complexity: simple }
  - { id: C009, text: "Registro de hábitos diarios", expected_complexity: simple }
  - { id: C010, text: "Generador de códigos QR", expected_complexity: simple }

  # Media (11–25)
  - { id: C011, text: "E-commerce para productos artesanales con carrito de compras", expected_complexity: medium }
  - { id: C012, text: "API REST para reservas de restaurantes con gestión de mesas", expected_complexity: medium }
  - { id: C013, text: "Sistema de gestión de inventario para retail con alertas de stock", expected_complexity: medium }
  - { id: C014, text: "Plataforma de cursos online con videos y evaluaciones", expected_complexity: medium }
  - { id: C015, text: "App de seguimiento de fitness con planes de entrenamiento", expected_complexity: medium }
  - { id: C016, text: "Sistema de tickets de soporte técnico con asignación automática", expected_complexity: medium }
  - { id: C017, text: "CRM básico para gestión de contactos y pipeline de ventas", expected_complexity: medium }
  - { id: C018, text: "Plataforma de freelancing con perfiles y proyectos", expected_complexity: medium }
  - { id: C019, text: "Sistema de votaciones online con resultados en tiempo real", expected_complexity: medium }
  - { id: C020, text: "Marketplace de servicios profesionales con ratings", expected_complexity: medium }
  - { id: C021, text: "Sistema de reservas de espacios coworking", expected_complexity: medium }
  - { id: C022, text: "Dashboard de métricas de negocio con gráficos interactivos", expected_complexity: medium }
  - { id: C023, text: "Plataforma de eventos con registro y check-in", expected_complexity: medium }
  - { id: C024, text: "Sistema de gestión de contenidos (CMS) para sitios web", expected_complexity: medium }
  - { id: C025, text: "App de delivery de comida con tracking de pedidos", expected_complexity: medium }

  # Compleja (26–30)
  - { id: C026, text: "Plataforma SaaS multi-tenant para gestión de proyectos con roles, permisos, facturación y analytics", expected_complexity: complex }
  - { id: C027, text: "Sistema bancario online con cuentas, transferencias, préstamos y seguridad avanzada", expected_complexity: complex }
  - { id: C028, text: "Plataforma de telemedicina con videoconsultas, historia clínica, prescripciones e integración con laboratorios", expected_complexity: complex }
  - { id: C029, text: "Sistema ERP para manufactura con producción, supply chain, RRHH y finanzas", expected_complexity: complex }
  - { id: C030, text: "Plataforma de trading algorítmico con data en tiempo real, backtesting y ejecución automática", expected_complexity: complex }
```

---

## Script de Ejecución Batch

El repositorio incluye `scripts/run_comparison.sh`. Acciones principales:

1. Verifica prerequisitos (jq, git limpio, branches, claves).
2. Crea directorios `artifacts/comparison/{master,dspy,logs}`.
3. Define el arreglo `CONCEPTS` y lo guarda en `concepts.txt`.
4. Ejecuta, para cada concepto:
   - Cambia de branch (`main` → `dspy-integration`).
   - Llama `make ba` o `make dspy-ba`.
   - Copia la salida (`planning/requirements.yaml` o `artifacts/dspy/requirements_dspy.yaml`).
   - Registra métricas en `execution_log.jsonl`.
5. Respeta `RATE_LIMIT_SECONDS` entre conceptos.
6. Restaura el branch original y presenta un resumen.

Ejemplo de uso:

```bash
# Validar sin ejecutar
bash scripts/run_comparison.sh --dry-run

# Ejecutar experimento completo
bash scripts/run_comparison.sh
```

---

## Ejecución del Experimento

- **Opción A (recomendada)**: corrida completa con `--dry-run` previo y monitoreo de `execution_log.jsonl`.
- **Opción B**: segmentar por complejidad editando temporalmente el arreglo `CONCEPTS`.
- **Opción C**: fallback manual (`make ba`/`make dspy-ba` por concepto) si el script falla.

Tiempo estimado (OpenAI/Claude): ~35–40 minutos con sleeps de 15 s.  
Costo aproximado (GPT-4): USD $4–7 para 60 ejecuciones; costo cero si se usa Ollama.

---

## Artefactos esperados

```
artifacts/comparison/
├── concepts.txt
├── execution_log.jsonl
├── logs/
│   ├── 01_master_stdout.log / stderr.log
│   └── … (hasta 30 × 2)
├── master/
│   ├── 01_requirements.yaml
│   └── … 30_requirements.yaml
└── dspy/
    ├── 01_requirements.yaml
    └── … 30_requirements.yaml
```

---

## Validaciones tras la corrida

```bash
# Conteo mínimo de YAML por branch (≥20 para análisis significativo)
ls artifacts/comparison/master/*.yaml | wc -l
ls artifacts/comparison/dspy/*.yaml | wc -l

# Success rate y estadísticas de duración
jq -s 'group_by(.branch) | map({
  branch: .[0].branch,
  total: length,
  errors: (map(select(.error != "")) | length),
  success_rate: ((length - (map(select(.error != "")) | length)) / length * 100),
  avg_duration: (map(.duration) | add / length)
})' artifacts/comparison/execution_log.jsonl

# Porcentaje de YAML válidos por branch (snippet rápido)
python - <<'PY'
import yaml
from pathlib import Path

def count_valid(folder):
    total = valid = 0
    for file in Path(folder).glob("*.yaml"):
        total += 1
        try:
            yaml.safe_load(file.read_text())
            valid += 1
        except yaml.YAMLError:
            pass
    return valid, total

for name in ("master", "dspy"):
    valid, total = count_valid(f"artifacts/comparison/{name}")
    print(f"{name}: {valid}/{total} válidos ({(valid/total*100):.1f}% )" if total else f"{name}: 0/0")
PY
```

Interpretación: valores de `success_rate` ≥80 % por branch y `errors` bajos indican corrida útil. Usa latencias para comparar tendencias (no se fijan números exactos a priori).

---

## Troubleshooting rápido

- **429 / rate limits**: aumentar `RATE_LIMIT_SECONDS` o segmentar la ejecución.
- **Git dirty**: stashear antes de lanzar el script (`git stash push`).
- **YAMLs faltantes**: revisar logs en `artifacts/comparison/logs` para identificar fallas por branch.
- **Falta de espacio**: limpiar `artifacts/dspy/cache` y comprimir logs antiguos.

---

## Entregables de la fase

- [ ] `artifacts/comparison/concepts.txt` con los 30 conceptos.
- [ ] 30 pares de YAML (`master` vs `dspy`) o al menos 20 pares válidos.
- [ ] `artifacts/comparison/execution_log.jsonl` con métricas por ejecución.
- [ ] Logs stdout/stderr archivados en `artifacts/comparison/logs/`.
- [ ] Spot-check manual de 3–5 conceptos (simple/medium/complex).
- [ ] Sección de resultados completada en este documento.

---

## Próximos pasos

1. Ejecutar el experimento y documentar resultados.  
2. Pasar a **Fase 4** (análisis cuantitativo) con `scripts/analyze_comparison.py` o equivalente.  
3. Completar **Fase 5** con la decisión (merge / iterate / abandon) basada en datos.

---

**Last updated**: 2025-11-03 (sin corrida ejecutada en este entorno).  
**Owner**: Equipo DSPy Comparison.  
**Notas**: Actualiza la sección de resultados inmediatamente después de cualquier ejecución parcial o completa.
