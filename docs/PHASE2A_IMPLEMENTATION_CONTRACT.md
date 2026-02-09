# PHASE2A Implementation Contract (Source of Truth)

**Estado**: Normativo para implementación
**Fecha**: 2026-02-08
**Ámbito**: Fase 2A (local/dev-first), previo a Fase 2B GPU y Fase 3 fine-tuning

---

## 1) Objetivo

Eliminar ambigüedades entre:

- `docs/PHASE2A_TECHNICAL_PLAN.md`
- `docs/PHASE2A_CODE_DESIGN.md`
- `PLAN_implementation_distilabel_finetuning_rag.md`

Este documento define el contrato operativo para implementar Fase 2A sin contradicciones.

---

## 2) Contrato de validación (real, no hipotético)

### 2.1 Fuente actual del repo

La validación disponible hoy está en:

- `post_training/src/posttrain/validators.py`

Tipo principal existente:

- `ValidationResult(ok: bool, score: float, reason: str, details: Dict[str, Any])`

### 2.2 Regla obligatoria

En Fase 2A **no se asume** la existencia de funciones como `validate_ba_output`/`validate_po_output` si no están implementadas.

Se define un `ValidatorAdapter` que traduce salida de pipeline a `ValidationResult`.

Contrato mínimo del adapter:

```python
class ValidatorAdapter:
    def validate(self, role: str, record: dict) -> ValidationResult: ...
```

`QualityFilterStep` debe depender de este adapter y no de imports no garantizados.

---

## 3) Contrato de ejecución (sync/async)

Para Fase 2A se congela:

- API pública del pipeline: **síncrona**
- Async interno: permitido, encapsulado

Contrato mínimo:

```python
class BaseSyntheticPipeline:
    def run(self, num_samples: int, batch_size: int, dry_run: bool = False, resume: bool = False) -> dict: ...
```

El CLI invoca `run()` de manera síncrona.

---

## 4) Contrato de output JSONL (mínimo)

Campos mínimos por registro:

- `instruction: str`
- `input: str`
- `output: str`
- `role: Literal[ba, product_owner, architect, dev, qa]`
- `metadata: object`
  - `timestamp: str`
  - `trace_id: str`
  - `batch_id: int`
  - `mode: Literal[local, gpu]`

Campos recomendados:

- `quality_score: float` (0..1)
- `reasoning: str` (especialmente architect)
- `quality_feedback: str`

---

## 5) Política de calidad por entorno

### Local/dev (mock)

- Objetivo: validar flujo, contrato, formato, checkpointing.
- No se usa como evidencia final de calidad de modelo.
- Gate recomendado: integridad estructural + score sintético estable.

### GPU/real (teacher)

- Objetivo: calidad real de dataset para Fase 3.
- Gate recomendado por rol: `quality_score >= threshold` + validación de formato.

---

## 6) Dependencias por perfil

### Perfil local

- Sin vLLM obligatorio.
- Distilabel opcional para pruebas de integración local.

### Perfil GPU

- `distilabel[vllm,hf]`
- `vllm`

Regla: el flujo local no debe romper por ausencia de stack GPU.

---

## 7) Contrato de tests

Matriz mínima:

1. `test-distilabel-local`
   - No requiere GPU
   - Verifica pipeline base + steps + checkpoint

2. `test-distilabel-gpu`
   - Requiere entorno GPU y dependencias
   - Debe skippear con razón explícita si faltan precondiciones

3. `test-distilabel-all`
   - Unión de ambos perfiles

Chequeos de precondición deben basarse en `import` real de módulos Python, no en binarios CLI ambiguos.

---

## 8) Checklist Ready-for-Implementation (Fase 2A)

- [ ] Adapter de validadores implementado sobre `ValidationResult`
- [ ] `BaseSyntheticPipeline.run()` síncrono, contrato estable
- [ ] `run_synthetic_pipeline.py` alineado con flags canónicas
- [ ] Output JSONL cumple esquema mínimo
- [ ] Checkpoint persistente y reanudación verificadas
- [ ] Test local estable sin GPU
- [ ] Tests GPU con skip explícito y correcto

---

## 9) Prioridades de implementación

1. Base pipeline + checkpoint + output schema
2. ValidatorAdapter + QualityFilterStep
3. CoT generator + FormatValidatorStep
4. Pipelines por rol
5. CLI + Makefile + tests

Este orden minimiza retrabajo y evita implementar features sobre contratos inconsistentes.
