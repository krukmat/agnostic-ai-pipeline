# Product Owner - Fix de Serialización DSPy MIPROv2
**Fecha**: 2025-11-10
**Task**: 9.0.8 - MIPROv2 Optimization
**Status**: 🟡 EN PROGRESO (test de validación corriendo)

---

## 📋 Resumen Ejecutivo

### Problema Descubierto
El primer run de optimización MIPROv2 para Product Owner (60 ejemplos, 4 trials, ~4h) completó exitosamente **PERO** falló al serializar el programa optimizado:

- ❌ `artifacts/dspy/product_owner_optimized/product_owner/program.pkl` solo tiene 2 bytes (vacío)
- ❌ Error: `Can't pickle StringSignature... has recursive self-references that trigger a RecursionError`
- ✅ Optimización funcionó (score MIPROv2: 1.56/100, valset: 0.53125)

### Causa Raíz
DSPy's MIPROv2 genera instrucciones muy largas para `StringSignature` que crean referencias circulares/recursivas. Python's `dill` (que DSPy usa internamente) no puede serializar objetos con self-references recursivas.

### Solución Implementada
Estrategia dual de serialización con fallback automático:
1. **Estrategia 1**: Intentar dill (método estándar DSPy)
2. **Estrategia 2 (Fallback)**: Extracción manual de componentes a JSON

---

## 🔧 Cambios Implementados

### Archivos Modificados

#### 1. `scripts/tune_dspy.py:87-146`
**Nueva función**: `_extract_program_components(compiled_program, role)`

```python
def _extract_program_components(compiled_program: Any, role: str) -> Dict[str, Any]:
    """Extract serializable components from an optimized DSPy program.

    This extracts:
    - Signature instructions (optimized by MIPROv2)
    - Demos/examples (few-shot learning)
    - Other metadata

    Returns a JSON-serializable dictionary.
    """
    components: Dict[str, Any] = {
        "role": role,
        "type": type(compiled_program).__name__,
        "modules": {},
    }

    # Extract components from each predictive module
    for attr_name in dir(compiled_program):
        attr = getattr(compiled_program, attr_name, None)
        if attr is None:
            continue

        # Check if this is a dspy.Predict or similar module
        if hasattr(attr, "signature") and hasattr(attr, "demos"):
            module_data: Dict[str, Any] = {
                "type": type(attr).__name__,
            }

            # Extract signature information
            sig = attr.signature
            if hasattr(sig, "instructions"):
                module_data["instructions"] = sig.instructions
            if hasattr(sig, "fields"):
                # Extract field names and descriptions
                fields_data = {}
                for field_name, field_info in sig.fields.items():
                    fields_data[field_name] = {
                        "type": "input" if field_info.json_schema_extra.get("__dspy_field_type") == "input" else "output",
                        "desc": field_info.json_schema_extra.get("desc", ""),
                    }
                module_data["fields"] = fields_data

            # Extract demos (few-shot examples)
            if attr.demos:
                demos_data = []
                for demo in attr.demos:
                    demo_dict = {}
                    if hasattr(demo, "inputs"):
                        demo_dict["inputs"] = demo.inputs()
                    if hasattr(demo, "outputs"):
                        demo_dict["outputs"] = demo.outputs()
                    elif hasattr(demo, "_store"):
                        # Fallback: extract from internal store
                        demo_dict = {k: v for k, v in demo._store.items()}
                    demos_data.append(demo_dict)
                module_data["demos"] = demos_data

            components["modules"][attr_name] = module_data

    return components
```

#### 2. `scripts/tune_dspy.py:230-260`
**Lógica de serialización dual**:

```python
# Try multiple serialization strategies
program_path = role_dir / "program.pkl"
success = False

# Strategy 1: Try dill (standard pickle alternative)
try:
    import dill
    with open(program_path, "wb") as f:
        dill.dump(compiled, f)
    typer.echo(f"✅ Optimized program saved to {program_path}")
    success = True
except Exception as e:
    typer.echo(f"⚠️  dill serialization failed: {e}")

# Strategy 2: Extract and save components manually (fallback)
if not success:
    try:
        typer.echo("🔄 Attempting manual component extraction...")
        components = _extract_program_components(compiled, role)
        components_path = role_dir / "program_components.json"
        with open(components_path, "w", encoding="utf-8") as f:
            json.dump(components, f, indent=2, ensure_ascii=False)
        typer.echo(f"✅ Program components saved to {components_path}")
        typer.echo("💡 Use load_program_from_components() to reconstruct the program")
        success = True
    except Exception as e2:
        typer.echo(f"⚠️  Component extraction also failed: {e2}")

if not success:
    typer.echo("❌ Could not serialize program with any method")
    typer.echo("💡 Program is still available in memory and was optimized successfully")
```

---

## 🧪 Test de Validación

### Configuración
**Objetivo**: Verificar que el fix de serialización funciona correctamente

**Dataset de prueba**:
```bash
# Crear subset de 20 ejemplos para test rápido
head -20 artifacts/synthetic/product_owner/product_owner_train_small.jsonl > /tmp/po_test_tiny.jsonl
```

**Comando ejecutado**:
```bash
PYTHONPATH=. .venv/bin/python scripts/tune_dspy.py \
  --role product_owner \
  --trainset /tmp/po_test_tiny.jsonl \
  --metric dspy_baseline.metrics.product_owner_metrics:product_owner_metric \
  --num-candidates 2 \
  --num-trials 2 \
  --max-bootstrapped-demos 2 \
  --seed 0 \
  --output /tmp/po_test_optimized \
  --provider ollama \
  --model mistral:7b-instruct \
  2>&1 | tee /tmp/po_serialization_test.log
```

**Parámetros**:
- Trainset: 20 ejemplos (mínimo viable)
- Candidates: 2 (reducido vs 4 en producción)
- Trials: 2 (reducido vs 4 en producción)
- Max demos: 2 (reducido vs 3 en producción)
- Modelo: mistral:7b-instruct (~30s/ejemplo vs granite4 ~90-110s)

**Duración esperada**: ~10-15 minutos

**Status**: 🟡 EN PROGRESO
- Shell ID: d219dd (background)
- Log: `/tmp/po_serialization_test.log`
- Inicio: 08:06 (approx)

### Criterios de Éxito
- ✅ Optimización completa sin errores
- ✅ Archivo generado en `/tmp/po_test_optimized/product_owner/`:
  - `program.pkl` (>100 bytes) **O**
  - `program_components.json` (fallback)
- ✅ Componentes extraídos incluyen:
  - `instructions` (optimizado por MIPROv2)
  - `demos` (few-shot examples)
  - `fields` (input/output field metadata)

---

## 📊 Siguiente Pasos (Post-Test)

### Si Test Exitoso ✅
1. **Ejecutar optimización completa**:
   ```bash
   PYTHONPATH=. .venv/bin/python scripts/tune_dspy.py \
     --role product_owner \
     --trainset artifacts/synthetic/product_owner/product_owner_train_small.jsonl \
     --valset artifacts/synthetic/product_owner/product_owner_val.jsonl \
     --metric dspy_baseline.metrics.product_owner_metrics:product_owner_metric \
     --num-candidates 4 \
     --num-trials 4 \
     --max-bootstrapped-demos 3 \
     --seed 0 \
     --output artifacts/dspy/product_owner_optimized \
     --provider ollama \
     --model mistral:7b-instruct \
     2>&1 | tee /tmp/mipro_product_owner_FIXED.log
   ```
   - Dataset: 60 ejemplos
   - Duración estimada: ~30-45 min (con mistral vs 4h con granite4)

2. **Evaluar modelo optimizado** (task 9.0.9):
   ```bash
   PYTHONPATH=. .venv/bin/python scripts/evaluate_po_optimized.py \
     --valset-path artifacts/synthetic/product_owner/product_owner_val.jsonl \
     --program-path artifacts/dspy/product_owner_optimized/product_owner/program.pkl \
     --baseline-report artifacts/benchmarks/product_owner_baseline.json \
     --output-report artifacts/benchmarks/product_owner_optimized.json \
     --provider ollama \
     --model mistral:7b-instruct
   ```

3. **Comparar con baseline**:
   - Baseline: 0.831 (83.1%)
   - Target: ≥0.88 (88%) para justificar optimización
   - Documentar resultados en plan

4. **Integrar en pipeline** (task 9.0.10):
   - Modificar `scripts/run_product_owner.py` para cargar programa optimizado
   - Añadir flag `features.use_dspy_product_owner` en `config.yaml` (con `USE_DSPY_PO` como override puntual) y actualizar `make po`.
   - Backwards compatibility si programa no existe

### Si Test Falla ❌
1. Revisar `/tmp/po_serialization_test.log` para errores
2. Verificar qué componentes se extrajeron (inspeccionar JSON)
3. Considerar alternativas:
   - Usar DSPy's `save` method nativo (si existe)
   - Serializar manualmente signature text + demos
   - Upgrade/downgrade DSPy version
   - Contact DSPy community sobre bug

---

## 📝 Notas Operativas

### Performance por Modelo
| Modelo | Tiempo/Ejemplo | 60 ejemplos | 142 ejemplos |
|--------|----------------|-------------|--------------|
| granite4 | ~90-110s | ~4h | ~9h |
| mistral:7b | ~30s | ~30-45min | ~1.5-2h |
| qwen2.5-coder:32b | ~20s | ~20-30min | ~45-60min |
| gemini-2.5-flash (Vertex) | ~10s | ~10-15min | ~20-30min |

**Recomendación**: Usar mistral:7b para balance entre velocidad y calidad local. Para producción considerar Vertex AI.

### Archivos Importantes
- **Log actual**: `/tmp/mipro_product_owner.log` (run original con fallo)
- **Log test**: `/tmp/po_serialization_test.log` (test de validación)
- **Baseline**: `artifacts/benchmarks/product_owner_baseline.json`
- **Programa vacío**: `artifacts/dspy/product_owner_optimized/product_owner/program.pkl` (2 bytes)
- **Metadata**: `artifacts/dspy/product_owner_optimized/product_owner/metadata.json`

### TODO List Actualizado
- [x] Fix serialization issue in tune_dspy.py
- [🟡] Test fix with 20 examples (~10-15 min) - EN PROGRESO
- [ ] If test passes, run optimization with 60 examples
- [ ] Evaluate optimized model on validation set
- [ ] Compare results with baseline and document in plan

---

## 🔗 Referencias
- **Plan maestro**: `docs/fase9_multi_role_dspy_plan.md:536-580`
- **Schema PO**: `docs/fase9_product_owner_schema.md`
- **Baseline evaluation**: Task 9.0.7 (completed)
- **DSPy MIPROv2 docs**: https://dspy-docs.vercel.app/docs/deep-dive/teleprompter/mipro
