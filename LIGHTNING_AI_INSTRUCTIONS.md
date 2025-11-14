# Instrucciones: Evaluación LoRA en Lightning AI Studio

## Setup Inicial

1. **Crear cuenta**: [lightning.ai](https://lightning.ai) → Sign Up (gratis)
2. **Nuevo Studio**: Click "New Studio" → Selecciona "Python"
3. **Activar GPU**: Settings (⚙️) → Machine → **GPU T4** → Apply
4. **Esperar**: Unos segundos mientras carga el entorno

---

## Celdas del Notebook (Copiar y Pegar)

### CELDA 1: Verificar GPU
**Tipo**: Code

```bash
!nvidia-smi
```

---

### CELDA 2: Instalar Dependencias
**Tipo**: Code

```bash
%%bash
pip install -q transformers>=4.36.0 peft>=0.7.0 bitsandbytes>=0.41.0 accelerate>=0.25.0 torch typer pyyaml
```

---

### CELDA 3: Clonar Repositorio
**Tipo**: Code

```python
import os
from pathlib import Path

# Clonar repositorio
repo_url = "https://github.com/krukmat/agnostic-ai-pipeline.git"
repo_branch = "dspy-multi-role"
repo_path = "/teamspace/studios/this_studio/agnostic-ai-pipeline"

if not os.path.exists(repo_path):
    !git clone --depth 1 --branch {repo_branch} {repo_url} {repo_path}
    print(f"✅ Repositorio clonado (branch: {repo_branch})")
else:
    print(f"✅ Repositorio ya existe")

# Verificar modelo
model_path = f"{repo_path}/artifacts/models/po_student_v1"
valset_path = f"{repo_path}/artifacts/synthetic/product_owner/product_owner_val.jsonl"

if not os.path.exists(model_path):
    raise FileNotFoundError(f"Modelo no encontrado en: {model_path}")
if not os.path.exists(valset_path):
    raise FileNotFoundError(f"Dataset no encontrado en: {valset_path}")

print(f"✅ Modelo: {model_path}")
print(f"✅ Dataset: {valset_path}")

# Verificar archivos
!ls -lh {model_path}

required_files = ["adapter_config.json", "adapter_model.safetensors", "tokenizer_config.json"]
for file in required_files:
    file_path = os.path.join(model_path, file)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Falta: {file}")
    size_mb = os.path.getsize(file_path) / 1024**2
    print(f"  ✓ {file} ({size_mb:.1f} MB)")

os.chdir(repo_path)
print(f"\n✅ Working dir: {os.getcwd()}")
```

---

### CELDA 4: Evaluación Baseline
**Tipo**: Code

```bash
%%bash
cd /teamspace/studios/this_studio/agnostic-ai-pipeline

PYTHONPATH=. python scripts/eval_po_student.py \
  --tag baseline \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --max-samples 20 \
  --retries 2 \
  --max-new-tokens 1200 \
  --load-4bit \
  --bnb-compute-dtype float16
```

⏱️ **Tiempo estimado**: 15-20 minutos

---

### CELDA 5: Evaluación Student
**Tipo**: Code

```bash
%%bash
cd /teamspace/studios/this_studio/agnostic-ai-pipeline

PYTHONPATH=. python scripts/eval_po_student.py \
  --tag student \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --adapter-path artifacts/models/po_student_v1 \
  --max-samples 20 \
  --retries 2 \
  --max-new-tokens 1200 \
  --load-4bit \
  --bnb-compute-dtype float16
```

⏱️ **Tiempo estimado**: 15-20 minutos

---

### CELDA 6: Comparar Resultados
**Tipo**: Code

```python
import json
from pathlib import Path

# Buscar resultados
results_dir = Path("/teamspace/studios/this_studio/agnostic-ai-pipeline/inference_results")
baseline_files = sorted(results_dir.glob("baseline_*.json"))
student_files = sorted(results_dir.glob("student_*.json"))

if not baseline_files or not student_files:
    print("⚠️  No se encontraron resultados")
else:
    # Cargar JSONs
    with open(baseline_files[-1], 'r') as f:
        baseline_data = json.load(f)
    with open(student_files[-1], 'r') as f:
        student_data = json.load(f)

    print(f"\n{'='*60}")
    print("COMPARACIÓN DE RESULTADOS")
    print(f"{'='*60}\n")

    # Métricas
    baseline_metrics = baseline_data.get('metrics', {})
    student_metrics = student_data.get('metrics', {})

    print("📈 MÉTRICAS GENERALES\n")
    print(f"{'Métrica':<20} {'Baseline':<15} {'Student':<15} {'Diff'}")
    print("-" * 60)

    for metric in ['mean', 'std', 'min', 'max']:
        b_val = baseline_metrics.get(metric, 0)
        s_val = student_metrics.get(metric, 0)
        diff = s_val - b_val
        diff_pct = (diff / b_val * 100) if b_val != 0 else 0
        print(f"{metric.upper():<20} {b_val:<15.4f} {s_val:<15.4f} {diff:+.4f} ({diff_pct:+.1f}%)")

    # YAML válido
    print(f"\n📋 TASA DE ÉXITO YAML\n")
    b_total = baseline_data.get('total_samples', 0)
    b_valid = baseline_data.get('valid_samples', 0)
    b_rate = (b_valid / b_total * 100) if b_total > 0 else 0

    s_total = student_data.get('total_samples', 0)
    s_valid = student_data.get('valid_samples', 0)
    s_rate = (s_valid / s_total * 100) if s_total > 0 else 0

    print(f"Baseline: {b_valid}/{b_total} ({b_rate:.1f}%)")
    print(f"Student:  {s_valid}/{s_total} ({s_rate:.1f}%)")

    # Criterios
    print(f"\n✅ CRITERIOS (9.D.4)\n")
    yaml_pass = (b_rate >= 90) and (s_rate >= 90)
    quality_pass = (s_val >= 0.9 * b_val) if baseline_metrics and student_metrics else False

    print(f"1. YAML ≥90%: {'✅ PASS' if yaml_pass else '❌ FAIL'}")
    if baseline_metrics and student_metrics:
        target = 0.9 * baseline_metrics.get('mean', 0)
        actual = student_metrics.get('mean', 0)
        print(f"2. Student ≥ 0.9×Baseline: {'✅ PASS' if quality_pass else '❌ FAIL'}")
        print(f"   Target: {target:.4f} | Actual: {actual:.4f}")

    overall = yaml_pass and quality_pass
    print(f"\n{'='*60}")
    print(f"RESULTADO: {'✅ PASS - Listo para 9.D.5' if overall else '❌ FAIL - Ajustar'}")
    print(f"{'='*60}")
```

---

### CELDA 7: Guardar Resultados
**Tipo**: Code

```python
import os
import shutil
from pathlib import Path

# Comprimir
results_dir = "/teamspace/studios/this_studio/agnostic-ai-pipeline/inference_results"
output_dir = "/teamspace/studios/this_studio"
archive_path = f"{output_dir}/eval_results_20251115"

if os.path.exists(results_dir):
    shutil.make_archive(archive_path, 'zip', results_dir)
    print(f"✅ ZIP: {archive_path}.zip")

    # Copiar JSONs
    json_files = list(Path(results_dir).glob("*.json"))
    for json_file in json_files:
        dest = Path(output_dir) / json_file.name
        shutil.copy2(json_file, dest)
        print(f"  ✓ {json_file.name}")

    print(f"\n✅ {len(json_files)} archivos en /teamspace/studios/this_studio/")
    print("💡 Usa el navegador de archivos (sidebar) para descargar")
else:
    print("❌ No se encontró directorio de resultados")
```

---

## Descargar Resultados

1. **Sidebar izquierdo** → File Browser
2. Navega a `/teamspace/studios/this_studio/`
3. Encontrarás:
   - `eval_results_20251115.zip` (todos los resultados)
   - `baseline_<timestamp>.json`
   - `student_<timestamp>.json`
4. **Click derecho** en cada archivo → **Download**

---

## Próximos Pasos

Después de descargar los resultados:

1. Subir JSON a `inference_results/` en el repo
2. Actualizar `docs/po_distillation_report.md`
3. Si **PASS** → Task 9.D.5 (integración)
4. Si **FAIL** → Analizar casos `format_error`

---

## Notas

- **Cuota GPU**: 10 horas/mes gratis
- **Duración**: ~30-40 minutos total (baseline + student)
- **Detener Studio**: Click "Stop" cuando termines para conservar cuota
- **Reanudar**: Puedes pausar y reanudar sin perder datos

---

**Fecha**: 2025-11-15
**Archivo**: `LIGHTNING_AI_INSTRUCTIONS.md`
