# Fase 8: Estrategia de Evaluación 3-Way Comparison

**Fecha**: 2025-11-09
**Objetivo**: Comparación sistemática de 3 modelos para el rol BA

---

## 1. Modelos a Comparar

| ID | Modelo | Descripción | Score Actual | Características |
|----|--------|-------------|--------------|-----------------|
| **M1** | **Baseline** | Mistral-7B-Instruct (sin optimizar) | 72% | - Prompt original<br>- Sin fine-tuning<br>- Config default |
| **M2** | **Optimized (MIPROv2)** | Mistral-7B-Instruct + DSPy optimización | **85.35%** | - Prompt optimizado<br>- Sin fine-tuning<br>- 13 trials MIPROv2 |
| **M3** | **Fine-Tuned (LoRA)** | Mistral-7B-Instruct + LoRA adapters | **TBD** | - Mismo prompt que M2<br>- LoRA r=8<br>- 98 ejemplos train |

---

## 2. Datasets de Evaluación

### 2.1. Validation Set (Principal)
- **Path**: `artifacts/synthetic/ba_val_v2_fixed.jsonl`
- **Tamaño**: 22 ejemplos
- **Uso**: Evaluación primaria (hold-out set)
- **Características**:
  - ✅ No visto durante fine-tuning
  - ✅ Misma distribución que train set
  - ✅ IDs corregidos (FR001, NFR001, C001)

### 2.2. Training Set (Diagnóstico)
- **Path**: `artifacts/synthetic/ba_train_v2_fixed.jsonl`
- **Tamaño**: 98 ejemplos
- **Uso**: Detectar overfitting
- **Justificación**: Si M3 score(train) >> score(val) → overfitting

### 2.3. Production Samples (Opcional - Futuro)
- **Path**: `dspy_baseline/data/production/ba_val.jsonl`
- **Tamaño**: 35 ejemplos (reales, no sintéticos)
- **Uso**: Validación en datos reales
- **Nota**: Estos datos tienen formato YAML, requieren conversión

---

## 3. Métricas de Evaluación

### 3.1. Métrica Principal: `ba_requirements_metric`

**Definición** (7 componentes, peso igual):

```python
def ba_requirements_metric(example, prediction, trace=None):
    """Evaluate BA requirements quality (0-1 scale)."""
    score = 0.0
    components = []

    # 1. Field completeness (14.3%)
    required_fields = ["title", "description", "functional_requirements",
                      "non_functional_requirements", "constraints"]
    completeness = sum(1 for f in required_fields if f in prediction) / len(required_fields)
    components.append(("completeness", completeness))
    score += completeness

    # 2. Title quality (14.3%)
    title_score = 1.0 if (prediction.get("title") and 10 <= len(prediction["title"]) <= 100) else 0.0
    components.append(("title", title_score))
    score += title_score

    # 3. Description quality (14.3%)
    desc = prediction.get("description", "")
    desc_score = 1.0 if len(desc) >= 50 else 0.0
    components.append(("description", desc_score))
    score += desc_score

    # 4-6. Requirements validation (14.3% each)
    for category in ["functional_requirements", "non_functional_requirements", "constraints"]:
        items = prediction.get(category, [])
        if isinstance(items, str):  # YAML format
            items = yaml.safe_load(items) if items else []

        valid = True
        if len(items) < 2:  # Minimum 2 items
            valid = False
        for item in items:
            if not isinstance(item, dict) or "id" not in item or "description" not in item:
                valid = False
                break

        cat_score = 1.0 if valid else 0.0
        components.append((category, cat_score))
        score += cat_score

    # 7. ID format validation (14.3%)
    id_score = validate_id_formats(prediction)
    components.append(("id_format", id_score))
    score += id_score

    # Average (0-1 scale)
    final_score = score / 7.0

    return final_score, components
```

### 3.2. Métricas Secundarias

#### A. Sub-component Scores
- **Completeness**: ¿Todos los campos presentes?
- **Title Quality**: Longitud razonable (10-100 chars)
- **Description Quality**: ≥50 caracteres
- **FR Validation**: ≥2 items, formato correcto
- **NFR Validation**: ≥2 items, formato correcto
- **Constraints Validation**: ≥2 items, formato correcto
- **ID Format**: FR001, NFR001, C001 (3 dígitos)

#### B. Aggregates
- **Mean Score**: Promedio sobre todos los ejemplos
- **Median Score**: Robusto a outliers
- **Std Dev**: Consistencia del modelo
- **Min/Max**: Rango de performance

#### C. Pass Rates
- **Pass@0.8**: % de ejemplos con score ≥ 0.8
- **Pass@0.9**: % de ejemplos con score ≥ 0.9
- **Perfect@1.0**: % de ejemplos con score = 1.0

---

## 4. Protocolo de Evaluación

### 4.1. Ejecución de Evaluaciones

#### Comando Unificado (3 modelos en paralelo)

```bash
python scripts/compare_ba_models.py \
  --baseline "ollama:mistral:7b-instruct" \
  --optimized "artifacts/dspy/local_base_optimized" \
  --finetuned "artifacts/finetuning/mistral-7b-ba-lora" \
  --dataset artifacts/synthetic/ba_val_v2_fixed.jsonl \
  --metric dspy_baseline.metrics:ba_requirements_metric \
  --output artifacts/fase8/3way_comparison.json \
  --verbose
```

#### Evaluaciones Individuales (alternativa)

```bash
# M1: Baseline
python scripts/eval_ba.py \
  --model ollama:mistral:7b-instruct \
  --dataset artifacts/synthetic/ba_val_v2_fixed.jsonl \
  --output artifacts/fase8/eval_baseline.json

# M2: Optimized (MIPROv2)
python scripts/eval_ba.py \
  --model artifacts/dspy/local_base_optimized \
  --dataset artifacts/synthetic/ba_val_v2_fixed.jsonl \
  --output artifacts/fase8/eval_optimized.json

# M3: Fine-Tuned (LoRA)
python scripts/eval_ba.py \
  --model artifacts/finetuning/mistral-7b-ba-lora \
  --dataset artifacts/synthetic/ba_val_v2_fixed.jsonl \
  --output artifacts/fase8/eval_finetuned.json
```

### 4.2. Condiciones de Evaluación (Fairness)

Para garantizar comparación justa:

1. **Mismo dataset**: `ba_val_v2_fixed.jsonl` (22 ejemplos)
2. **Misma métrica**: `ba_requirements_metric` (7 componentes)
3. **Mismo sampling**:
   - `temperature=0.7` (consistente con config)
   - `max_tokens=2048`
   - `seed=42` (reproducibilidad)
4. **Mismo formato de prompt**: Instruction tuning format
5. **Misma infraestructura**: Ollama local (CPU)

---

## 5. Formato del Reporte de Comparación

### 5.1. Estructura JSON

```json
{
  "metadata": {
    "date": "2025-11-09",
    "dataset": "artifacts/synthetic/ba_val_v2_fixed.jsonl",
    "num_examples": 22,
    "metric": "ba_requirements_metric",
    "seed": 42
  },
  "models": {
    "baseline": {
      "id": "M1",
      "name": "Mistral-7B-Instruct (Baseline)",
      "config": {
        "provider": "ollama",
        "model": "mistral:7b-instruct",
        "temperature": 0.7,
        "max_tokens": 2048
      },
      "scores": {
        "mean": 0.72,
        "median": 0.71,
        "std": 0.15,
        "min": 0.43,
        "max": 1.00,
        "pass_rate_0.8": 0.36,
        "pass_rate_0.9": 0.18,
        "perfect_rate_1.0": 0.09
      },
      "component_scores": {
        "completeness": 0.95,
        "title": 0.82,
        "description": 0.68,
        "functional_requirements": 0.77,
        "non_functional_requirements": 0.64,
        "constraints": 0.55,
        "id_format": 0.59
      },
      "predictions": [...]
    },
    "optimized": {
      "id": "M2",
      "name": "Mistral-7B-Instruct (MIPROv2)",
      "scores": {
        "mean": 0.8535,
        "median": 0.86,
        "std": 0.12,
        "min": 0.57,
        "max": 1.00,
        "pass_rate_0.8": 0.68,
        "pass_rate_0.9": 0.45,
        "perfect_rate_1.0": 0.23
      },
      "component_scores": {...},
      "predictions": [...]
    },
    "finetuned": {
      "id": "M3",
      "name": "Mistral-7B-Instruct (LoRA r=8)",
      "scores": {
        "mean": 0.XX,  // TBD after fine-tuning
        "median": 0.XX,
        "std": 0.XX,
        "min": 0.XX,
        "max": 0.XX,
        "pass_rate_0.8": 0.XX,
        "pass_rate_0.9": 0.XX,
        "perfect_rate_1.0": 0.XX
      },
      "component_scores": {...},
      "predictions": [...]
    }
  },
  "comparison": {
    "winner": "M2|M3",  // Model with highest mean score
    "ranking": [
      {"model": "M2", "score": 0.8535, "delta_vs_baseline": +0.1335},
      {"model": "M3", "score": 0.XX, "delta_vs_baseline": +0.XX},
      {"model": "M1", "score": 0.72, "delta_vs_baseline": 0.00}
    ],
    "statistical_tests": {
      "wilcoxon_m2_vs_m1": {
        "statistic": 0.XX,
        "p_value": 0.XX,
        "significant": true
      },
      "wilcoxon_m3_vs_m2": {
        "statistic": 0.XX,
        "p_value": 0.XX,
        "significant": true|false
      }
    },
    "effect_sizes": {
      "m2_vs_m1": 0.XX,  // Cohen's d
      "m3_vs_m2": 0.XX
    }
  }
}
```

### 5.2. Visualización (Markdown Report)

```markdown
# 3-Way Model Comparison Report

## Summary

| Model | Mean Score | Δ vs Baseline | Pass@0.8 | Pass@0.9 | Perfect |
|-------|------------|---------------|----------|----------|---------|
| **M2 (Optimized)** | 85.35% | **+13.35%** | 68% | 45% | 23% |
| M3 (Fine-Tuned) | XX.XX% | +XX.XX% | XX% | XX% | XX% |
| M1 (Baseline) | 72.00% | - | 36% | 18% | 9% |

**Winner**: M2 (Optimized) / M3 (Fine-Tuned)

## Component Breakdown

| Component | M1 Baseline | M2 Optimized | M3 Fine-Tuned | Best |
|-----------|-------------|--------------|---------------|------|
| Completeness | 95% | 98% | XX% | M2/M3 |
| Title | 82% | 91% | XX% | M2/M3 |
| Description | 68% | 86% | XX% | M2/M3 |
| Functional Req | 77% | 89% | XX% | M2/M3 |
| Non-Functional Req | 64% | 82% | XX% | M2/M3 |
| Constraints | 55% | 79% | XX% | M2/M3 |
| ID Format | 59% | 95% | XX% | M2/M3 |

## Statistical Significance

- **M2 vs M1**: p < 0.05 (Wilcoxon signed-rank test) ✅ Significant improvement
- **M3 vs M2**: p = XX (TBD)

## Recommendations

...
```

---

## 6. Criterios de Decisión

### 6.1. Selección del Modelo Ganador

**Regla de decisión**:

```python
def select_winner(m1_score, m2_score, m3_score):
    """Select best model based on validation score."""

    # Rule 1: Fine-tuned mejora ≥5% sobre optimized → Fine-tuned wins
    if m3_score >= m2_score + 0.05:
        return "M3 (Fine-Tuned)", "Significant improvement over optimized baseline"

    # Rule 2: Fine-tuned mejora <5% pero ≥optimized → Optimized wins (simplicity)
    elif m3_score >= m2_score and (m3_score - m2_score) < 0.05:
        return "M2 (Optimized)", "Fine-tuned improvement not significant (prefer simpler model)"

    # Rule 3: Fine-tuned degrada → Optimized wins
    elif m3_score < m2_score:
        return "M2 (Optimized)", "Fine-tuning degraded performance (overfitting?)"

    # Rule 4: Optimized mejora ≥10% sobre baseline → Optimized wins
    elif m2_score >= m1_score + 0.10:
        return "M2 (Optimized)", "Strong improvement over baseline"

    # Default: Keep baseline
    else:
        return "M1 (Baseline)", "Insufficient improvement to justify change"
```

### 6.2. Umbrales de Decisión

| Escenario | Acción | Justificación |
|-----------|--------|---------------|
| M3 ≥ M2 + 5% | **Adoptar Fine-Tuned** | Mejora significativa justifica complejidad |
| M2 ≤ M3 < M2 + 5% | **Mantener Optimized** | Mejora marginal, preferir simplicidad |
| M3 < M2 | **Mantener Optimized** | Fine-tuning degradó (overfitting) |
| M2 < M1 + 10% | **Revisar Optimización** | Mejora insuficiente |

### 6.3. Análisis de Componentes

Si el modelo ganador es determinado, analizar:

1. **Fortalezas**: ¿Qué componentes mejoraron más?
2. **Debilidades**: ¿Qué componentes siguen bajos?
3. **Consistency**: ¿Std Dev aceptable (< 0.15)?
4. **Outliers**: ¿Ejemplos con score < 0.5? → Analizar causas

---

## 7. Checklist de Evaluación

### Pre-Evaluación
- [ ] Dataset `ba_val_v2_fixed.jsonl` disponible (22 ejemplos)
- [ ] Baseline model (Ollama) corriendo
- [ ] Optimized model artifacts en `artifacts/dspy/local_base_optimized`
- [ ] Fine-tuned model artifacts en `artifacts/finetuning/mistral-7b-ba-lora`
- [ ] Script `compare_ba_models.py` creado y testeado

### Ejecución
- [ ] Ejecutar evaluación M1 (Baseline)
- [ ] Ejecutar evaluación M2 (Optimized)
- [ ] Ejecutar evaluación M3 (Fine-Tuned)
- [ ] Verificar mismo seed/temperatura en todos
- [ ] Guardar predictions completas (debugging)

### Post-Evaluación
- [ ] Generar reporte JSON (`3way_comparison.json`)
- [ ] Generar reporte Markdown (`3way_comparison_report.md`)
- [ ] Aplicar regla de decisión → determinar ganador
- [ ] Análisis de componentes débiles
- [ ] Pruebas estadísticas (Wilcoxon)
- [ ] Actualizar `docs/fase8_progress.md` con resultados

---

## 8. Implementación: Script `compare_ba_models.py`

### Esqueleto del Script

```python
#!/usr/bin/env python3
"""Compare 3 BA models: Baseline vs Optimized vs Fine-Tuned."""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Any

from dspy_baseline.metrics import ba_requirements_metric
from datasets import load_dataset
import numpy as np
from scipy.stats import wilcoxon


def load_model(model_path: str):
    """Load model from path or provider string."""
    if model_path.startswith("ollama:"):
        # Load Ollama model
        pass
    elif Path(model_path).exists():
        # Load fine-tuned or optimized model
        pass
    else:
        raise ValueError(f"Unknown model path: {model_path}")


def evaluate_model(model, dataset: List[Dict], metric_fn) -> Dict[str, Any]:
    """Evaluate model on dataset with metric."""
    scores = []
    component_scores = {
        "completeness": [],
        "title": [],
        "description": [],
        "functional_requirements": [],
        "non_functional_requirements": [],
        "constraints": [],
        "id_format": []
    }
    predictions = []

    for example in dataset:
        # Generate prediction
        pred = model.generate(example["concept"])

        # Score prediction
        score, components = metric_fn(example, pred)
        scores.append(score)

        # Collect component scores
        for name, value in components:
            component_scores[name].append(value)

        predictions.append({
            "concept": example["concept"],
            "prediction": pred,
            "score": score,
            "components": dict(components)
        })

    # Aggregate
    results = {
        "scores": {
            "mean": np.mean(scores),
            "median": np.median(scores),
            "std": np.std(scores),
            "min": np.min(scores),
            "max": np.max(scores),
            "pass_rate_0.8": sum(1 for s in scores if s >= 0.8) / len(scores),
            "pass_rate_0.9": sum(1 for s in scores if s >= 0.9) / len(scores),
            "perfect_rate_1.0": sum(1 for s in scores if s == 1.0) / len(scores),
        },
        "component_scores": {k: np.mean(v) for k, v in component_scores.items()},
        "predictions": predictions
    }

    return results


def compare_models(baseline_results, optimized_results, finetuned_results):
    """Generate comparison report."""
    # Rank models
    models = [
        ("M1", "Baseline", baseline_results["scores"]["mean"]),
        ("M2", "Optimized", optimized_results["scores"]["mean"]),
        ("M3", "Fine-Tuned", finetuned_results["scores"]["mean"]),
    ]
    models_sorted = sorted(models, key=lambda x: x[2], reverse=True)

    # Statistical tests
    baseline_scores = [p["score"] for p in baseline_results["predictions"]]
    optimized_scores = [p["score"] for p in optimized_results["predictions"]]
    finetuned_scores = [p["score"] for p in finetuned_results["predictions"]]

    wilcoxon_m2_m1 = wilcoxon(optimized_scores, baseline_scores)
    wilcoxon_m3_m2 = wilcoxon(finetuned_scores, optimized_scores)

    comparison = {
        "winner": models_sorted[0][1],
        "ranking": [
            {
                "model": m[0],
                "name": m[1],
                "score": m[2],
                "delta_vs_baseline": m[2] - baseline_results["scores"]["mean"]
            }
            for m in models_sorted
        ],
        "statistical_tests": {
            "wilcoxon_m2_vs_m1": {
                "statistic": float(wilcoxon_m2_m1.statistic),
                "p_value": float(wilcoxon_m2_m1.pvalue),
                "significant": wilcoxon_m2_m1.pvalue < 0.05
            },
            "wilcoxon_m3_vs_m2": {
                "statistic": float(wilcoxon_m3_m2.statistic),
                "p_value": float(wilcoxon_m3_m2.pvalue),
                "significant": wilcoxon_m3_m2.pvalue < 0.05
            }
        }
    }

    return comparison


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--optimized", required=True)
    parser.add_argument("--finetuned", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    # Load dataset
    dataset = load_dataset("json", data_files=args.dataset, split="train")

    # Load models
    baseline_model = load_model(args.baseline)
    optimized_model = load_model(args.optimized)
    finetuned_model = load_model(args.finetuned)

    # Evaluate
    print("Evaluating baseline...")
    baseline_results = evaluate_model(baseline_model, dataset, ba_requirements_metric)

    print("Evaluating optimized...")
    optimized_results = evaluate_model(optimized_model, dataset, ba_requirements_metric)

    print("Evaluating fine-tuned...")
    finetuned_results = evaluate_model(finetuned_model, dataset, ba_requirements_metric)

    # Compare
    comparison = compare_models(baseline_results, optimized_results, finetuned_results)

    # Output
    report = {
        "metadata": {
            "dataset": args.dataset,
            "num_examples": len(dataset),
            "metric": "ba_requirements_metric"
        },
        "models": {
            "baseline": baseline_results,
            "optimized": optimized_results,
            "finetuned": finetuned_results
        },
        "comparison": comparison
    }

    Path(args.output).write_text(json.dumps(report, indent=2))
    print(f"Comparison saved to: {args.output}")


if __name__ == "__main__":
    main()
```

---

## 9. Timeline

| Tarea | Duración | Dependencias |
|-------|----------|--------------|
| Crear script `compare_ba_models.py` | 15 min | - |
| Ejecutar eval M1 (Baseline) | 5 min | Dataset listo |
| Ejecutar eval M2 (Optimized) | 5 min | Dataset listo |
| Ejecutar eval M3 (Fine-Tuned) | 5 min | **Fine-tuning completado** |
| Generar reporte comparativo | 2 min | Todas las evals completas |
| Análisis + decisión | 10 min | Reporte listo |
| **Total** | **~40 min** | - |

**Nota**: M3 evaluation solo se puede hacer después de completar Fase 8.4 (Fine-Tuning), estimado 1.5-2.5 horas.

---

## 10. Resultados Esperados

### Escenario Optimista (Fine-Tuning Exitoso)
- M1 (Baseline): 72%
- M2 (Optimized): 85.35%
- **M3 (Fine-Tuned): 90-95%** ← Target
- **Mejora**: +5-10% sobre M2
- **Decisión**: Adoptar M3

### Escenario Realista (Mejora Marginal)
- M1: 72%
- M2: 85.35%
- **M3: 86-88%** ← Mejora pequeña
- **Mejora**: +1-3% sobre M2
- **Decisión**: Mantener M2 (simplicidad)

### Escenario Pesimista (Overfitting)
- M1: 72%
- M2: 85.35%
- **M3: 80-84%** ← Degrada
- **Mejora**: Negativa
- **Decisión**: Mantener M2, revisar fine-tuning

---

## Referencias

- [Wilcoxon Signed-Rank Test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html)
- [Cohen's d Effect Size](https://en.wikipedia.org/wiki/Effect_size#Cohen's_d)
- [Model Evaluation Best Practices](https://huggingface.co/docs/evaluate/index)
