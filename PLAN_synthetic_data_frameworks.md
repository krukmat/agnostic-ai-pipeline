# Evaluación de Frameworks para Generación de Datos Sintéticos

**Objetivo**: Minimizar customizaciones y acelerar fine-tuning usando frameworks especializados
**Fecha**: 2026-02-03

---

## Comparativa de Frameworks (2024-2026)

### 1. NVIDIA NeMo / Nemotron-4 340B

| Aspecto | Detalle |
|---------|---------|
| **Descripción** | Framework completo con NeMo Data Designer para generación sintética a escala |
| **Modelo Maestro** | Nemotron-4 340B (98% de sus datos son sintéticos) |
| **Componentes** | Instruct (generación) + Reward (evaluación) |
| **Caso de Uso** | Generó datos sintéticos para entrenar Nemotron-4 340B Instruct |
| **Licencia** | Open source (Apache 2.0) |
| **Infraestructura** | NVIDIA GPUs (optimizado para A100/H100) |
| **Facilidad** | ⭐⭐⭐⭐ Alta - Pipeline prebuilt |
| **Costo GPU** | Alto (340B requiere multi-GPU) |

**Ventajas**:
- ✅ Pipeline completo end-to-end
- ✅ Evaluación automática con Reward model
- ✅ Escalable a millones de ejemplos
- ✅ Integración con NeMo fine-tuning

**Desventajas**:
- ❌ Nemotron-4 340B es muy grande (más caro que Qwen2.5-72B)
- ❌ Requiere infraestructura NVIDIA (vendor lock-in)
- ❌ Curva de aprendizaje de NeMo framework

**Fuentes**: [NeMo Synthetic Data](https://docs.nvidia.com/nemo-framework/user-guide/24.12/datacuration/syntheticdata.html), [NeMo Data Designer](https://github.com/NVIDIA-NeMo/DataDesigner), [Nemotron Blog](https://blogs.nvidia.com/blog/nemotron-4-synthetic-data-generation-llm-training/)

---

### 2. Llama 3.1 405B + RAFT

| Aspecto | Detalle |
|---------|---------|
| **Descripción** | Llama 3.1 405B con framework RAFT para generación sintética |
| **Modelo Maestro** | Llama 3.1 405B (contexto 128K tokens) |
| **Framework** | RAFT (Retrieval Augmented Fine Tuning) |
| **Caso de Uso** | Q&A y Chain-of-Thought desde documentos |
| **Licencia** | Llama 3.1 License (uso comercial permitido) |
| **Infraestructura** | Multi-cloud (AWS, Azure, NVIDIA) |
| **Facilidad** | ⭐⭐⭐ Media - Requiere setup de RAFT |
| **Costo GPU** | Alto (405B requiere ~800GB VRAM) |

**Ventajas**:
- ✅ Modelo muy capaz (mejor que Qwen2.5-72B en benchmarks)
- ✅ 128K contexto (útil para documentos largos)
- ✅ RAFT especializado en RAG + fine-tuning
- ✅ Amplio soporte en clouds

**Desventajas**:
- ❌ 405B es CARO (~$10-15/hora en cloud)
- ❌ RAFT requiere setup adicional
- ❌ No tiene modelo de reward integrado

**Fuentes**: [AWS Llama 3.1 Synthetic Data](https://aws.amazon.com/blogs/machine-learning/use-llama-3-1-405b-to-generate-synthetic-data-for-fine-tuning-tasks/), [NVIDIA Llama 3.1 Tutorial](https://developer.nvidia.com/blog/creating-synthetic-data-using-llama-3-1-405b/), [Microsoft RAFT](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/the-future-of-ai-synthetic-data-gen-with-llama-3-1-405b--raft/4236077)

---

### 3. Distilabel (Hugging Face)

| Aspecto | Detalle |
|---------|---------|
| **Descripción** | Framework Python para pipelines de síntesis de datos |
| **Modelo Maestro** | Agnóstico (soporta Llama, Qwen, Mistral, etc.) |
| **Framework** | Pipeline builder con steps modulares |
| **Caso de Uso** | Crear datasets para instruction fine-tuning |
| **Licencia** | Apache 2.0 |
| **Infraestructura** | Flexible (local, cloud, APIs) |
| **Facilidad** | ⭐⭐⭐⭐⭐ Muy alta - Python simple |
| **Costo GPU** | Variable según modelo |

**Ventajas**:
- ✅ **AGNÓSTICO** - funciona con cualquier modelo
- ✅ Python simple y flexible
- ✅ Pipelines modulares y reutilizables
- ✅ Integración con Hugging Face
- ✅ Soporta APIs (menos costo GPU)

**Desventajas**:
- ❌ No incluye modelos (debes elegir)
- ❌ No tiene evaluación automática de calidad

**Código Ejemplo**:
```python
from distilabel.llms import vLLM
from distilabel.pipeline import Pipeline
from distilabel.steps import LoadDataFromDicts, GenerateSentencePair

with Pipeline(name="synthetic-sft-pipeline") as pipeline:
    load_dataset = LoadDataFromDicts(
        data=[
            {"instruction": "Analiza este concepto..."},
            # ...
        ]
    )

    generate = GenerateSentencePair(
        llm=vLLM(model="Qwen/Qwen2.5-72B-Instruct"),
        input_batch_size=8
    )

    load_dataset >> generate
```

**Fuentes**: [Distilabel with Llama3](https://huggingface.co/blog/dvilasuero/synthetic-data-with-llama3-distilabel)

---

### 4. Gretel Navigator (Compound AI)

| Aspecto | Detalle |
|---------|---------|
| **Descripción** | Sistema compound AI con agentes y herramientas |
| **Modelo Maestro** | Múltiples modelos orquestados |
| **Framework** | Agentic workflows + task planning |
| **Caso de Uso** | Datos sintéticos de alta calidad |
| **Licencia** | Comercial (con tier gratuito) |
| **Infraestructura** | Managed service |
| **Facilidad** | ⭐⭐⭐⭐⭐ Muy alta - API |
| **Costo GPU** | Managed (pricing por uso) |

**Ventajas**:
- ✅ **Superó GPT-4 en 25.6%** en calidad
- ✅ Compound AI (orquesta múltiples modelos)
- ✅ Managed service (sin infra)
- ✅ Evaluación automática de calidad

**Desventajas**:
- ❌ Servicio comercial (no 100% open source)
- ❌ Vendor lock-in
- ❌ Pricing puede ser alto a escala

**Fuentes**: [Gretel Navigator](https://www.gretel.ai/blog/how-to-create-high-quality-synthetic-data-for-fine-tuning-llms)

---

### 5. FineInstructions (2026 - Nuevo)

| Aspecto | Detalle |
|---------|---------|
| **Descripción** | Método para generar billions de pares con templates |
| **Modelo Maestro** | Agnóstico |
| **Framework** | 18M instruction templates |
| **Caso de Uso** | Generación masiva de instruction-answer pairs |
| **Licencia** | Research (pendiente release público) |
| **Infraestructura** | Flexible |
| **Facilidad** | ⭐⭐⭐ Media - Pendiente tooling |
| **Costo GPU** | Bajo (usa templates eficientemente) |

**Ventajas**:
- ✅ **Billions de ejemplos** con templates
- ✅ Resultados superiores en human eval
- ✅ Eficiente en costo (templates reutilizables)

**Desventajas**:
- ❌ Muy reciente (Feb 2026)
- ❌ Pendiente release de código
- ❌ Falta documentación

**Fuentes**: [FineInstructions Research](https://quantumzeitgeist.com/enhanced-fineinstructions-achieves-billions-synthetic-data/)

---

## Matriz de Decisión

| Framework | Facilidad | Costo | Calidad | Agnóstico | Open Source | **RECOMENDADO** |
|-----------|-----------|-------|---------|-----------|-------------|-----------------|
| **NeMo/Nemotron** | ⭐⭐⭐⭐ | 🔴 Alto | ⭐⭐⭐⭐⭐ | ❌ NVIDIA | ✅ | Para scale |
| **Llama 3.1 + RAFT** | ⭐⭐⭐ | 🔴 Muy Alto | ⭐⭐⭐⭐⭐ | ❌ Meta | ✅ | Para RAG |
| **Distilabel** | ⭐⭐⭐⭐⭐ | 🟢 Variable | ⭐⭐⭐⭐ | ✅ | ✅ | **✅ SÍ** |
| **Gretel Navigator** | ⭐⭐⭐⭐⭐ | 🟡 Medio | ⭐⭐⭐⭐⭐ | ✅ | ❌ | Para empresas |
| **FineInstructions** | ⭐⭐⭐ | 🟢 Bajo | ⭐⭐⭐⭐ | ✅ | ⚠️ Pendiente | Futuro |

---

## Framework Propuesto: Distilabel + Qwen2.5-72B

### Por Qué Distilabel

1. **Agnóstico de modelos**: Podemos cambiar de Qwen2.5 a Llama 3.1 sin reescribir código
2. **Python simple**: Reduce código custom, más fácil para la comunidad
3. **Open source**: Apache 2.0, sin vendor lock-in
4. **Integración Hugging Face**: Facilita publicación de datasets
5. **Pipelines modulares**: Reutilizables entre roles

### Arquitectura Propuesta

```
┌─────────────────────────────────────────────────────────────────┐
│                   DISTILABEL PIPELINE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. LoadDataFromDicts (datos semilla)                          │
│  2. GenerateInstructions (aumentar prompts)                    │
│  3. GenerateResponses (Qwen2.5-72B)                            │
│  4. GenerateReasoningCoT (opcional para Architect)             │
│  5. QualityFilter (auto-evaluación)                            │
│  6. SaveToHub (publicar en HuggingFace)                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Implementación Concreta

```python
# training/pipelines/synthetic_data_pipeline.py

from distilabel.llms import vLLM
from distilabel.pipeline import Pipeline
from distilabel.steps import (
    LoadDataFromDicts,
    ExpandColumns,
    GenerateEmbeddings,
    FormatPrompt,
    SelfInstructGenerator,
    QualityScorer,
)
from distilabel.steps.tasks import TextGeneration

class SyntheticDataPipeline:
    """
    Pipeline agnóstico para generación de datos sintéticos.
    Usa Distilabel para minimizar código custom.
    """

    def __init__(self, role: str, teacher_model: str = "Qwen/Qwen2.5-72B-Instruct"):
        self.role = role
        self.teacher_model = teacher_model
        self.config = self._load_role_config(role)

    def build_pipeline(self) -> Pipeline:
        """Construye pipeline modular basado en rol."""

        with Pipeline(name=f"synthetic-{self.role}") as pipeline:
            # 1. Cargar datos semilla
            load_seeds = LoadDataFromDicts(
                data=self._get_seed_data(),
                output_mappings={"concept": "input"}
            )

            # 2. Generar variaciones (aumentación)
            if self.config.get("augment_inputs"):
                augment = SelfInstructGenerator(
                    llm=vLLM(model=self.teacher_model),
                    num_variations=3,
                    system_prompt=self._get_augmentation_prompt()
                )

            # 3. Generar respuestas con maestro
            generate_response = TextGeneration(
                llm=vLLM(model=self.teacher_model),
                system_prompt=self._get_generation_prompt(),
                temperature=0.7,
                max_new_tokens=2048
            )

            # 4. Chain-of-Thought (solo para roles complejos)
            if self.config.get("reasoning_transfer"):
                generate_cot = TextGeneration(
                    llm=vLLM(model=self.teacher_model),
                    system_prompt="Explica paso a paso tu razonamiento...",
                    input_mappings={"response": "input"}
                )

            # 5. Auto-evaluación de calidad
            quality_scorer = QualityScorer(
                llm=vLLM(model=self.teacher_model),
                criteria=self.config["quality_criteria"],
                min_score=7.0  # Filtrar ejemplos <7/10
            )

            # Conectar steps
            if self.config.get("augment_inputs"):
                load_seeds >> augment >> generate_response
            else:
                load_seeds >> generate_response

            if self.config.get("reasoning_transfer"):
                generate_response >> generate_cot >> quality_scorer
            else:
                generate_response >> quality_scorer

        return pipeline

    def _load_role_config(self, role: str) -> dict:
        """Configuración específica por rol."""
        configs = {
            "ba": {
                "augment_inputs": True,
                "reasoning_transfer": False,
                "quality_criteria": ["completeness", "clarity", "format"],
                "min_examples": 500
            },
            "architect": {
                "augment_inputs": True,
                "reasoning_transfer": True,  # CRÍTICO para Architect
                "quality_criteria": ["design_coherence", "tradeoffs", "adr_quality"],
                "min_examples": 600
            },
            "dev": {
                "augment_inputs": False,
                "reasoning_transfer": False,
                "quality_criteria": ["correctness", "tests", "style"],
                "min_examples": 1000
            },
            "qa": {
                "augment_inputs": True,
                "reasoning_transfer": True,
                "quality_criteria": ["edge_cases", "test_quality", "coverage"],
                "min_examples": 500
            }
        }
        return configs.get(role, {})

    def _get_generation_prompt(self) -> str:
        """Prompts específicos por rol."""
        prompts = {
            "ba": """
                Eres un Business Analyst senior. Analiza el siguiente concepto
                y genera un requirements.yaml completo con:
                - Requisitos funcionales (mínimo 5)
                - Requisitos no funcionales
                - Stakeholders
                - Constraints
                """,
            "architect": """
                Eres un Arquitecto de Software senior. Diseña la arquitectura
                para el siguiente concepto. IMPORTANTE: Explica paso a paso
                tu razonamiento antes de presentar la arquitectura final.

                Incluye:
                1. Análisis del dominio
                2. Componentes clave con justificación
                3. Patrones aplicables con trade-offs
                4. ADR formal
                """,
            # ... otros roles
        }
        return prompts.get(self.role, "")

    def run(self, output_path: str = None):
        """Ejecuta pipeline y guarda resultados."""
        pipeline = self.build_pipeline()

        # Ejecutar con progress tracking
        distiset = pipeline.run(
            use_cache=True,
            storage_parameters={"strategy": "disk"}
        )

        # Guardar localmente
        if output_path:
            distiset.save_to_disk(output_path)

        # Publicar a HuggingFace (opcional)
        if self.config.get("publish_to_hub"):
            distiset.push_to_hub(
                f"agnostic-pipeline/{self.role}-synthetic-v1",
                private=False
            )

        return distiset
```

### Uso Simplificado

```bash
# Generar datos sintéticos para Architect (ejemplo crítico)
python -m training.pipelines.synthetic_data_pipeline \
    --role architect \
    --teacher-model "Qwen/Qwen2.5-72B-Instruct" \
    --seed-data dspy_baseline/data/production/architect_train.jsonl \
    --output training/datasets/architect_synthetic_v1 \
    --target-examples 600
```

---

## Comparativa: Custom vs Distilabel

### Código Custom (Propuesta Original)

```python
# ~300 líneas de código custom
class SyntheticDataGenerator:
    def generate_for_role(...):
        # Manejo manual de prompts
        # Manejo manual de variaciones
        # Manejo manual de evaluación
        # Manejo manual de formato
        pass
```

**Problemas**:
- ❌ Código custom difícil de mantener
- ❌ No reutilizable entre roles
- ❌ Sin caching automático
- ❌ Sin retry logic
- ❌ Sin progress tracking

### Con Distilabel

```python
# ~50 líneas de configuración
pipeline = (
    LoadDataFromDicts(data) >>
    GenerateResponses(llm) >>
    QualityFilter(criteria) >>
    SaveToHub(repo)
)
distiset = pipeline.run()
```

**Ventajas**:
- ✅ Código declarativo simple
- ✅ Caching automático
- ✅ Retry logic incluido
- ✅ Progress bars
- ✅ Integración HuggingFace
- ✅ Testing built-in

---

## Roadmap de Implementación

### Fase 1: Setup Distilabel (1 semana)

```bash
# Instalación
pip install distilabel[vllm,hf]

# Crear pipeline base para BA (quick win)
python training/pipelines/synthetic_data_pipeline.py \
    --role ba \
    --seed-data dspy_baseline/data/production/ba_train_unique.jsonl \
    --target-examples 500 \
    --dry-run  # Validar primero
```

### Fase 2: Architect con CoT (2 semanas)

```python
# Pipeline específico para Architect con reasoning transfer
architect_pipeline = SyntheticDataPipeline(
    role="architect",
    teacher_model="Qwen/Qwen2.5-72B-Instruct"
)

# Generar 600 ejemplos con CoT
distiset = architect_pipeline.run(
    output_path="training/datasets/architect_v1"
)
```

### Fase 3: Todos los Roles (4 semanas)

```bash
# Script batch para todos los roles
for role in ba po architect dev qa; do
    python training/pipelines/synthetic_data_pipeline.py \
        --role $role \
        --target-examples ${MIN_EXAMPLES[$role]}
done
```

---

## Costos Estimados (con Distilabel)

### Opción A: vLLM Local (GPU Rentada)

| Actividad | GPU | Tiempo | Costo |
|-----------|-----|--------|-------|
| Setup Distilabel + vLLM | A100 80GB | 1h | $2 |
| Generar 600 ejemplos Architect | A100 80GB | 10-15h | $15-22 |
| Generar 500 ejemplos BA/PO/QA (cada uno) | A100 80GB | 8-12h | $12-18 |
| Generar 1000 ejemplos Dev | A100 80GB | 15-20h | $22-30 |
| **Total primer ciclo** | - | **~50-70h** | **$75-110** |

### Opción B: APIs (Menos GPU, Más Flexible)

| Actividad | API | Costo |
|-----------|-----|-------|
| 600 ejemplos Architect (Qwen2.5-72B) | OpenRouter/Together | ~$30-40 |
| 1500 ejemplos otros roles | OpenRouter/Together | ~$50-70 |
| **Total** | - | **$80-110** |

**Ventaja API**: Sin setup de GPU, más flexible, mismo costo

---

## Decisión Final

### Framework Recomendado: Distilabel + Qwen2.5-72B

**Razones**:

1. **Minimiza customizaciones** (objetivo principal)
   - 50 líneas vs 300 líneas de código custom
   - Pipelines reutilizables entre roles

2. **Agnóstico de modelos**
   - Podemos cambiar de Qwen2.5 a Llama 3.1 sin refactorizar
   - Podemos usar APIs en lugar de GPU local

3. **Open source completo**
   - Apache 2.0, sin vendor lock-in
   - Comunidad activa Hugging Face

4. **Productivo**
   - Caching, retry, progress tracking built-in
   - Integración HuggingFace para publicación

5. **Comprobado**
   - Usado por múltiples proyectos open source
   - Documentación extensa

### Alternativa Secundaria: NeMo (Si Budget Permite)

Si presupuesto permite y queremos máxima calidad:
- Usar Nemotron-4 340B con NeMo Data Designer
- Costo ~2-3x más que Qwen2.5-72B
- Mejor para producción enterprise

---

## Próximos Pasos Inmediatos

### Esta Semana

1. **Instalar Distilabel**
   ```bash
   pip install "distilabel[vllm,hf]>=1.4.0"
   ```

2. **Crear pipeline base para BA**
   ```bash
   python training/pipelines/create_ba_pipeline.py
   ```

3. **Generar 100 ejemplos test**
   ```bash
   # Validar que funciona antes de escalar
   python training/pipelines/synthetic_data_pipeline.py \
       --role ba \
       --target-examples 100 \
       --teacher-model "Qwen/Qwen2.5-72B-Instruct"
   ```

### Próxima Semana

4. **Escalar a 500 ejemplos BA** (quick win)
5. **Crear pipeline para Architect con CoT**
6. **Documentar proceso para comunidad**

---

**Estado**: Propuesta de Framework
**Decisión**: Distilabel + Qwen2.5-72B (agnóstico, open source, minimal custom code)
**Próximos Pasos**: Implementar pipeline base para BA esta semana

---

## Referencias

- [NVIDIA NeMo Synthetic Data](https://docs.nvidia.com/nemo-framework/user-guide/24.12/datacuration/syntheticdata.html)
- [NeMo Data Designer GitHub](https://github.com/NVIDIA-NeMo/DataDesigner)
- [Nemotron Blog](https://blogs.nvidia.com/blog/nemotron-4-synthetic-data-generation-llm-training/)
- [AWS Llama 3.1 Synthetic Data](https://aws.amazon.com/blogs/machine-learning/use-llama-3-1-405b-to-generate-synthetic-data-for-fine-tuning-tasks/)
- [NVIDIA Llama 3.1 Tutorial](https://developer.nvidia.com/blog/creating-synthetic-data-using-llama-3-1-405b/)
- [Microsoft RAFT](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/the-future-of-ai-synthetic-data-gen-with-llama-3-1-405b--raft/4236077)
- [Distilabel with Llama3](https://huggingface.co/blog/dvilasuero/synthetic-data-with-llama3-distilabel)
- [Gretel Navigator](https://www.gretel.ai/blog/how-to-create-high-quality-synthetic-data-for-fine-tuning-llms)
- [FineInstructions Research](https://quantumzeitgeist.com/enhanced-fineinstructions-achieves-billions-synthetic-data/)
- [Scale AI Synthetic Data Strategies](https://scale.com/blog/synthetic-data-fine-tuning-llms)
- [Hugging Face Synthetic Data Cost Savings](https://huggingface.co/blog/synthetic-data-save-costs)
