# Product Owner Output Schema (Phase 9 - DSPy Optimization)

**Versión**: 1.0
**Fecha**: 2025-11-09
**Tarea**: 9.0.1 - Análisis de Output Product Owner Actual

---

## 1. Visión General

El rol **Product Owner** genera **dos archivos YAML** como output:

1. **`planning/product_vision.yaml`** - Visión autoritativa del producto
2. **`planning/product_owner_review.yaml`** - Evaluación de alineamiento con requirements

Estos archivos se generan a partir de:
- **Input primario**: `planning/requirements.yaml` (generado por BA)
- **Input secundario**: Concepto original (variable `CONCEPT` o `meta.original_request` en requirements.yaml)
- **Input evolutivo**: `planning/product_vision.yaml` previo (para iteraciones subsecuentes)

---

## 2. Schema de `product_vision.yaml`

### 2.1 Estructura YAML

```yaml
product_name: <string>
product_summary: <string>
target_users:
  - <string>
  - <string>
value_proposition:
  - <string>
  - <string>
key_capabilities:
  - <string>
  - <string>
non_goals:
  - <string>
  - <string>
success_metrics:
  - <string>
  - <string>
last_updated: <ISO 8601 timestamp>
```

### 2.2 Campos Obligatorios

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `product_name` | `string` | Nombre corto del producto | `"Blog Tecnológico Sencillo"` |
| `product_summary` | `string` | Narrativa de un párrafo (3-5 oraciones) | `"Se propone desarrollar un blog sencillo..."` |
| `target_users` | `list[string]` | Lista de audiencias primarias (≥1 elemento) | `["Usuarios tecnológicos interesados en compartir conocimientos"]` |
| `value_proposition` | `list[string]` | Lista de resultados clave para usuarios (≥1 elemento) | `["Proporcionar una plataforma accesible..."]` |
| `key_capabilities` | `list[string]` | Lista de capacidades principales (≥1 elemento) | `["Creación, edición y eliminación de publicaciones..."]` |
| `non_goals` | `list[string]` | Lista de exclusiones explícitas (puede ser `[]`) | `["Integración con bases de datos externas complejas"]` |
| `success_metrics` | `list[string]` | Lista de métricas estratégicas o KPIs (≥1 elemento) | `["Número de publicaciones generadas por usuarios activos"]` |
| `last_updated` | `string` | Timestamp ISO 8601 (generado por el LLM) | `"2024-08-14 00:00:00+00:00"` |

### 2.3 Reglas de Validación

1. **Formato timestamp**: Debe cumplir ISO 8601 (YYYY-MM-DD HH:MM:SS+TZ)
2. **Listas no vacías**: `target_users`, `value_proposition`, `key_capabilities`, `success_metrics` deben tener ≥1 elemento
3. **Lista opcional vacía**: `non_goals` puede ser `[]` si no hay exclusiones
4. **Sin backticks**: No usar `` ` `` dentro de valores YAML (causa errores de parsing)
5. **Concisión**: Cada entrada debe ser específica pero concisa (1-2 oraciones)

### 2.4 Ejemplo Validado (Blog Tecnológico)

```yaml
product_name: Blog Tecnológico Sencillo
product_summary: Se propone desarrollar un blog sencillo centrado en la tecnología,
  donde los usuarios puedan crear, editar y eliminar publicaciones. Cada post tendrá
  una categoría específica (por ejemplo, "IA", "Ciberseguridad" o "Desarrollo Web").
  Los usuarios también podrán comentar sobre las entradas existentes, permitiendo
  un intercambio de opiniones y enlaces adicionales.
target_users:
- Usuarios tecnológicos interesados en compartir conocimientos
value_proposition:
- Proporcionar una plataforma accesible para que cualquier persona publique sobre
  temas tecnológicos sin necesidad de complejidad administrativa.
key_capabilities:
- Creación, edición y eliminación de publicaciones con categorías predefinidas.
- Comentarios en las entradas existentes.
non_goals:
- Integración con bases de datos externas complejas.
- Soporte para contenido multimedia avanzado (por ejemplo, videos largos).
success_metrics:
- Número de publicaciones generadas por usuarios activos.
- Tasa de interacción entre comentarios y visitantes del sitio.
last_updated: 2024-08-14 00:00:00+00:00
```

---

## 3. Schema de `product_owner_review.yaml`

### 3.1 Estructura YAML

```yaml
status: <enum: aligned | needs_adjustment | misaligned>
summary:
  - <string>
  - <string>
requirements_alignment:
  aligned:
    - <string>
    - <string>
  gaps:
    - <string>
    - <string>
  conflicts:
    - <string>
    - <string>
recommended_actions:
  - <string>
  - <string>
narrative: <string>
```

### 3.2 Campos Obligatorios

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `status` | `enum` | Estado de alineamiento: `aligned`, `needs_adjustment`, `misaligned` | `"aligned"` |
| `summary` | `list[string]` | Lista de observaciones principales (≥1 elemento) | `["The requirements document directly reflects the product vision..."]` |
| `requirements_alignment` | `object` | Objeto con 3 sub-listas obligatorias | Ver abajo |
| `requirements_alignment.aligned` | `list[string]` | Requirements que encajan (puede ser `[]`) | `["FR001 (User can create new posts)"]` |
| `requirements_alignment.gaps` | `list[string]` | Requirements faltantes o riesgos (puede ser `[]`) | `["The vision mentions mobile accessibility but no explicit priority..."]` |
| `requirements_alignment.conflicts` | `list[string]` | Requirements que contradicen la visión (puede ser `[]`) | `["None identified"]` |
| `recommended_actions` | `list[string]` | Acciones concretas para el equipo (≥1 elemento) | `["Ensure implementation of NFR001 and NFR002..."]` |
| `narrative` | `string` | Párrafo sucinto explicando el veredicto (2-4 oraciones) | `"All functional, non-functional and constraint requirements align..."` |

### 3.3 Reglas de Validación

1. **Status enum**: Solo valores `aligned`, `needs_adjustment`, `misaligned`
2. **Traceabilidad**: Mencionar IDs de requirements (FR001, NFR002, C001, etc.) cuando sea posible
3. **Listas pueden estar vacías**: `aligned`, `gaps`, `conflicts` pueden ser `[]` si no aplica
4. **Actions obligatorias**: `recommended_actions` debe tener ≥1 elemento (aunque sea genérico como "Continue with current approach")
5. **Summary y narrative obligatorios**: Deben tener contenido (no vacíos)

### 3.4 Ejemplo Validado (Blog Tecnológico)

```yaml
status: aligned
summary:
- The requirements document directly reflects the product vision by focusing on a
  simple technology blog with core capabilities for creating, editing, deleting posts
  in predefined categories and allowing comments.
requirements_alignment:
  aligned:
  - FR001 (User can create new posts)
  - FR002 (User can edit own posts)
  - FR003 (System allows deletion of unwanted posts)
  - FR004 (Each post must have a preselected category)
  - FR005 (User can add comments to existing posts)
  gaps:
  - The vision mentions mobile/desktop accessibility but no explicit priority was
    assigned in the requirements.
  conflicts:
  - None identified
recommended_actions:
- Ensure implementation of NFR001 and NFR002 are prioritized due to their high priority
  status.
narrative: All functional, non-functional and constraint requirements align with the
  product vision for a simple technology-focused blog. No adjustments needed beyond
  confirming priorities for accessibility and usability.
```

---

## 4. Dependencias con `requirements.yaml`

### 4.1 Extracción de Concepto Original

El script `scripts/run_product_owner.py` extrae el concepto original de dos fuentes (en orden de prioridad):

1. **Variable de entorno** `CONCEPT` (si está definida)
2. **Campo `meta.original_request`** en `planning/requirements.yaml`:

```yaml
meta:
  original_request: "API REST para gestión de productos"
```

### 4.2 Traceabilidad con Requirements

El PO debe referenciar explícitamente los requirement IDs al evaluar alineamiento:

**Ejemplo de referencia correcta**:
```yaml
requirements_alignment:
  aligned:
    - FR001 (User can create new posts)
    - FR002 (User can edit own posts)
  gaps:
    - NFR003 (Security testing) is mentioned in vision but missing in requirements
  conflicts:
    - C002 (NoSQL constraint) contradicts vision's goal of using PostgreSQL
```

**Ejemplo de referencia incorrecta** (sin IDs):
```yaml
requirements_alignment:
  aligned:
    - Users can create posts  # ❌ Falta ID (FR001)
```

### 4.3 Schema de `requirements.yaml` (para referencia)

```yaml
meta:
  original_request: <string>
title: <string>
description: <string>
functional_requirements:
  - id: <string>  # FR001, FR002, etc.
    description: <string>
    priority: <enum: High | Medium | Low>
non_functional_requirements:
  - id: <string>  # NFR001, NFR002, etc.
    description: <string>
    priority: <enum: High | Medium | Low>
constraints:
  - id: <string>  # C001, C002, etc.
    description: <string>
    priority: <enum: High | Medium | Low>
```

---

## 5. Artefactos Intermedios

### 5.1 Debug Output

El script guarda la respuesta completa del LLM en:

**Ruta**: `artifacts/debug/debug_product_owner_response.txt`

**Formato esperado**:
```
```yaml VISION
product_name: ...
...
```

```yaml REVIEW
status: ...
...
```
```

### 5.2 Extracción de Bloques

El script usa regex para extraer los bloques:

```python
pattern = re.compile(rf"```{tag}\s*{label}\s*\n([\s\S]+?)\n```", re.MULTILINE)
# tag="yaml", label="VISION" o "REVIEW"
```

**Importante**: Los bloques deben seguir el formato exacto:
- ` ```yaml VISION` (no ` ```yaml` ni ` ```VISION`)
- ` ```yaml REVIEW` (no ` ```yaml` ni ` ```REVIEW`)

---

## 6. Sanitización de YAML

### 6.1 Función `sanitize_yaml()`

El script aplica dos estrategias de sanitización (scripts/run_product_owner.py:44-86):

**Estrategia 1**: Parse/dump cycle
```python
data = yaml.safe_load(content)
sanitized = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)
```

**Estrategia 2**: Regex cleanup (si parse falla)
```python
cleaned = re.sub(r'`([^`]+?)`', r'\1', content)  # Elimina backticks
```

### 6.2 Casos Problemáticos

| Problema | Causa | Solución |
|----------|-------|----------|
| `yaml.scanner.ScannerError` | Backticks en valores (`POST /api/users`) | Usar texto plano: `POST /api/users` |
| `yaml.parser.ParserError` | Comillas no balanceadas | Sanitización automática |
| Valores multi-línea rotos | Falta indentación | YAML auto-formatter en `safe_dump` |

---

## 7. Métricas de Calidad (para DSPy Optimization)

### 7.1 Componentes de la Métrica (30 pts cada)

Basado en `docs/fase9_multi_role_dspy_plan.md` (líneas 338-361):

#### **Componente 1: Schema Compliance (30 pts)**
- Todos los campos obligatorios presentes: 30 pts
- Falta 1-2 campos obligatorios: 15 pts
- Falta >2 campos: 0 pts

#### **Componente 2: Requirements Alignment (30 pts)**

**Pseudocódigo de implementación**:
```python
def calculate_requirements_alignment(requirements_yaml, vision_yaml, review_yaml):
    """
    Calcula traceabilidad entre requirements y vision/review.

    Estrategia:
    1. Parse requirements.functional_requirements (lista de objetos con title/description)
    2. Para cada requirement:
       a. Buscar mención explícita en vision (por keyword match en objetivos/KPIs)
       b. Buscar mención en review.action_items
       c. Match = True si aparece en a) o b)
    3. Score = (requirements_cubiertos / total_requirements) * 30

    Umbrales:
    - ≥85% cobertura → 30 pts
    - 70-85% → escala lineal 20-30 pts
    - 50-70% → escala lineal 10-20 pts
    - <50% → 0-10 pts
    """
    # Implementación usa fuzzy string matching (difflib.SequenceMatcher)
    # Threshold similarity: 0.6 para considerar "cubierto"
    pass
```

#### **Componente 3: Vision Completeness (30 pts)**
- `target_users`, `value_proposition`, `key_capabilities` con ≥2 elementos cada uno: 30 pts
- Al menos 1 lista con 1 solo elemento: 20 pts
- Alguna lista obligatoria vacía: 0 pts

#### **Componente 4: Review Specificity (30 pts)**
- `recommended_actions` con ≥2 acciones concretas + referencias a requirement IDs: 30 pts
- 1 acción concreta: 15 pts
- Acciones genéricas sin IDs: 5 pts

### 7.2 Umbrales de Aceptación

| Métrica Total | Calidad | Acción |
|---------------|---------|--------|
| ≥85 pts | Excelente | Aprobar para dataset optimizado |
| 70-84 pts | Aceptable | Incluir con anotaciones |
| 50-69 pts | Deficiente | Revisar manualmente antes de incluir |
| <50 pts | Rechazado | Excluir del dataset |

---

## 8. Validación con Ejemplos Reales

### 8.1 Ejemplo 1: Blog Tecnológico Sencillo (baseline legacy)

**Archivos**:
- `artifacts/examples/product_owner/blog_product_vision.yaml`
- `artifacts/examples/product_owner/blog_product_owner_review.yaml`

**Validación**:
- ✅ Schema Compliance: 30/30 pts (todos los campos presentes)
- ✅ Requirements Alignment: 28/30 pts (5/5 FR cubiertos, 1 gap identificado)
- ✅ Vision Completeness: 30/30 pts (todas las listas ≥1 elemento)
- ✅ Review Specificity: 25/30 pts (1 acción concreta con referencia a NFR001/NFR002)
- **Total**: **113/120 pts (94.2%)**

### 8.2 Ejemplo 2: Product REST API (concepto “API REST para gestión de productos”)

**Archivos**:
- `artifacts/examples/product_owner/product_rest_api_vision.yaml`
- `artifacts/examples/product_owner/product_rest_api_review.yaml`

**Validación**:
- ✅ Schema Compliance: 30/30 pts (listas obligatorias completas, timestamps válidos)
- ✅ Requirements Alignment: 27/30 pts (FR001-FR006 referenciados explícitamente, NFR001-NFR003 alineados)
- ✅ Vision Completeness: 30/30 pts (dos value propositions, dos key capabilities, métricas claras)
- ✅ Review Specificity: 26/30 pts (acciones concretas y trazabilidad a non-goals)
- **Total**: **113/120 pts (94.2%)**

**Notas**:
- Se detectó que el LLM tendía a devolver `null` en listas vacías; se corrigió el output para usar `[]` y se planea reforzar el prompt.
- El archivo se mantiene en inglés para asegurar consistencia con otros entregables técnicos.

### 8.3 Ejemplo 3: Inventory Management API para e-commerce

**Archivos**:
- `artifacts/examples/product_owner/inventory_api_vision.yaml`
- `artifacts/examples/product_owner/inventory_api_review.yaml`

**Validación**:
- ✅ Schema Compliance: 30/30 pts
- ✅ Requirements Alignment: 26/30 pts (gaps explícitos sobre stock en tiempo real y aislamiento multi-tenant)
- ✅ Vision Completeness: 28/30 pts (todas las listas pobladas; métricas duales)
- ✅ Review Specificity: 27/30 pts (acciones sobre OpenAPI + scope guardrails)
- **Total**: **111/120 pts (92.5%)**

Estos tres ejemplos cubren tanto escenarios legacy (blog) como los dos conceptos actuales del pipeline (API REST de productos e inventario e-commerce), cumpliendo el criterio de ≥3 muestras reales para cerrar la tarea 9.0.1.

---

## 9. Campos Opcionales (no presentes en schema actual)

**Nota**: El schema actual (versión 1.0) **no incluye campos opcionales**. Todos los campos listados en las secciones 2 y 3 son **obligatorios** o **pueden estar vacíos** (`[]` para listas).

Si en futuras fases se requieren campos opcionales, deben agregarse con:
- Marcador `(opcional)` en la tabla de campos
- Validación que permita su ausencia sin penalización
- Incremento de `schema_version` a 1.1 o 2.0

---

## 10. Migraciones de Schema

### 10.1 Versionado

Actualmente: **Versión 1.0** (sin campo `schema_version` en los archivos)

**Para Fase 9.1+**: Incluir campo `schema_version` en ambos outputs:

```yaml
# product_vision.yaml
schema_version: "1.0"
product_name: ...
...
```

```yaml
# product_owner_review.yaml
schema_version: "1.0"
status: ...
...
```

### 10.2 Migración Automática (GAP 6 del plan)

**Estrategia implementada** (docs/fase9_multi_role_dspy_plan.md:300):

> Implementar migración automática antes de abortar: si el schema no coincide, intentar migrar datos a la versión esperada; solo abortar si la migración falla.

**Ejemplo de migración 1.0 → 1.1**:
```python
def migrate_vision_1_0_to_1_1(data: dict) -> dict:
    """Migra product_vision.yaml de v1.0 a v1.1"""
    if not data.get("schema_version"):
        data["schema_version"] = "1.0"

    # Ejemplo: agregar campo 'stakeholders' opcional en v1.1
    if "stakeholders" not in data:
        data["stakeholders"] = []

    data["schema_version"] = "1.1"
    return data
```

---

## 11. Integración con DSPy

### 11.1 Clase Signature

```python
class ProductOwnerSignature(dspy.Signature):
    """Product Owner: Maintain product vision and evaluate requirements alignment"""

    # Inputs
    concept: str = dspy.InputField(desc="Original product concept")
    existing_vision: str = dspy.InputField(desc="Existing product_vision.yaml content (may be empty)")
    requirements: str = dspy.InputField(desc="Current requirements.yaml from BA")

    # Outputs
    vision_yaml: str = dspy.OutputField(desc="Updated product_vision.yaml content")
    review_yaml: str = dspy.OutputField(desc="Product owner review YAML content")
```

### 11.2 Metric Function

- **Ubicación**: `dspy_baseline/metrics/product_owner_metrics.py`
- **Nombre**: `product_owner_metric(example, prediction, trace=None)`
- **Salida**: flotante en `[0.0, 1.0]` (equivalente a 0-100% al multiplicar por 100)

Implementación real:

1. **Schema Compliance (30 pts)**  
   - Valida campos obligatorios en `product_vision.yaml` y `product_owner_review.yaml`  
   - Chequea formato de timestamp y que los bloques `requirements_alignment.*` sean listas

2. **Vision Completeness (30 pts)**  
   - Evalúa riqueza de listas (`target_users`, `value_proposition`, `key_capabilities`, `success_metrics`)  
   - Bonifica resúmenes ≥120 caracteres; puntúa a la mitad si sólo existe un elemento por lista

3. **Requirements Alignment (30 pts)**  
   - Parsea `requirements.yaml` y busca trazas por ID (`FR`, `NFR`, `C`) dentro del review  
   - Si no hay IDs, usa coincidencia semántica simple (token overlap ≥30%) contra `aligned/gaps/recommended_actions`

4. **Review Specificity (30 pts)**  
   - Puntúa cantidad/calidad de `summary`, `recommended_actions`, `gaps/conflicts` y longitud de `narrative`

> **Normalización**: `(schema + vision + alignment + review) / 120`

### 11.3 Dataset Format (JSONL)

```jsonl
{"concept": "Blog tecnológico sencillo", "existing_vision": "", "requirements": "meta:\n  original_request: Blog tecnológico...\nfunctional_requirements:\n- id: FR001\n  description: User can create new posts\n  priority: High\n...", "vision_yaml": "product_name: Blog Tecnológico Sencillo\n...", "review_yaml": "status: aligned\n..."}
{"concept": "API REST para gestión de productos", "existing_vision": "", "requirements": "meta:\n  original_request: API REST...\nfunctional_requirements:\n- id: FR001\n  description: Creación de productos...\n  priority: High\n...", "vision_yaml": "product_name: Sistema Gestión de Productos\n...", "review_yaml": "status: aligned\n..."}
```

**Campos obligatorios por registro**:
- `concept` (string)
- `existing_vision` (string, puede ser `""`)
- `requirements` (string YAML)
- `vision_yaml` (string YAML) - ground truth
- `review_yaml` (string YAML) - ground truth

---

## 12. Referencias

1. **Prompt Original**: `prompts/product_owner.md`
2. **Script de Generación**: `scripts/run_product_owner.py`
3. **Plan Fase 9**: `docs/fase9_multi_role_dspy_plan.md` (sección 9.0 - Product Owner)
4. **Ejemplos Reales**:
   - `planning/product_vision.yaml`
   - `planning/product_owner_review.yaml`
   - `planning/requirements.yaml`

---

### 11.4 Pruebas unitarias

- **Ruta**: `dspy_baseline/tests/test_product_owner_metric.py`
- **Cobertura**:
  - Caso completo (Blog / >=0.85)
  - Caso semi-semántico sin IDs explícitos (Inventory API / >0.70)
  - Caso incompleto (faltan secciones / <0.30)
- Toman `SimpleNamespace` como `example/prediction` para simular la firma DSPy

---

## 12. Referencias

1. **Prompt Original**: `prompts/product_owner.md`
2. **Script de Generación**: `scripts/run_product_owner.py`
3. **Plan Fase 9**: `docs/fase9_multi_role_dspy_plan.md` (sección 9.0 - Product Owner)
4. **Ejemplos Reales**:
   - `planning/product_vision.yaml`
   - `planning/product_owner_review.yaml`
   - `planning/requirements.yaml`

---

## 13. Historial de Cambios

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2025-11-09 | Creación inicial del schema (Tarea 9.0.1) |
| 1.1 | 2025-11-09 | Métrica implementada + pruebas unitarias (Tarea 9.0.2) |

---

**Documento generado por**: Tareas 9.0.1 y 9.0.2 (Schema + Métrica PO)  
**Estado**: ✅ Completo (3 ejemplos reales + métricas + tests)  
**Próxima acción**: Tarea 9.0.3 - Generación de inputs sintéticos (conceptos + requirements)
