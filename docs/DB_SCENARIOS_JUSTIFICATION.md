# JUSTIFICACIÓN DB: CASOS DE USO CON REGISTROS REALES

## CASO 1: ORDEN NORMAL (Architect → Dev → QA)

### Comando ejecutado:
```bash
make ba CONCEPT="Simple calculator"
make plan
make dev STORY=S1
make qa STORY=S1
```

---

### 🔹 PASO 1: `make ba CONCEPT="Simple calculator"`

**Acción**: BA genera requirements

**Tablas afectadas**:

#### `projects` (si no existe)
```
id | name            | concept              | status  | created_at
---+----------------+---------------------+---------+-------------------
1  | adhoc-ba       | Simple calculator   | active  | 2025-12-02 10:00:00
```

#### `iterations` (si no existe)
```
id | project_id | loops_requested | loops_completed | status    | created_at
---+-----------+----------------+----------------+----------+-------------------
1  | 1         | 1              | 0              | running  | 2025-12-02 10:00:00
```

#### `role_artifacts`
```
id | iteration_id | role | artifact_type | content                           | created_at
---+-------------+-----+--------------+----------------------------------+-------------------
1  | 1           | ba  | requirements | features:                         | 2025-12-02 10:00:01
   |             |     |              |   - Calculator operations         |
   |             |     |              |   - Basic UI                      |
```

#### `event_log`
```
id | iteration_id | event_type | role | story_id | message                              | severity | created_at
---+-------------+-----------+-----+---------+------------------------------------+---------+-------------------
1  | 1           | ba_start  | ba  | NULL    | Generating requirements for: Simple... | info    | 2025-12-02 10:00:00
2  | 1           | ba_end    | ba  | NULL    | BA requirements generated successfully | info    | 2025-12-02 10:00:01
```

**Estado `stories`**: VACÍA (BA no crea historias)

---

### 🔹 PASO 2: `make plan`

**Acción**: Architect genera y sincroniza stories

**Tablas afectadas**:

#### `role_artifacts` (nuevos registros)
```
id | iteration_id | role      | artifact_type | content                    | created_at
---+-------------+----------+--------------+---------------------------+-------------------
2  | 1           | architect| stories      | - id: S1                   | 2025-12-02 10:01:00
   |             |          |              |   title: Add operation     |
   |             |          |              |   status: todo             |
   |             |          |              |   complexity: medium       |
3  | 1           | architect| epics        | E1: Calculator core        | 2025-12-02 10:01:00
4  | 1           | architect| architecture | tech_stack: Python FastAPI | 2025-12-02 10:01:00
```

#### `stories` (POBLACIÓN INICIAL)
```
id | iteration_id | story_id | title              | description               | status | priority | complexity | created_at
---+-------------+---------+-------------------+--------------------------+-------+---------+-----------+-------------------
1  | 1           | S1      | Add operation      | Implement addition logic  | todo  | P1      | medium    | 2025-12-02 10:01:00
2  | 1           | S2      | Subtract operation | Implement subtract logic  | todo  | P2      | medium    | 2025-12-02 10:01:00
```

**Nota**: Las historias se crearon con `normalize_status()` → todas tienen `status` y `complexity`.

#### `event_log` (nuevos registros)
```
id | iteration_id | event_type      | role      | story_id | message                           | severity | created_at
---+-------------+----------------+----------+---------+----------------------------------+---------+-------------------
3  | 1           | architect_start | architect| NULL    | Generating stories (DSPy, tier=...) | info    | 2025-12-02 10:01:00
4  | 1           | architect_end   | architect| NULL    | Architect artifacts generated     | info    | 2025-12-02 10:01:00
```

---

### 🔹 PASO 3: `make dev STORY=S1`

**Acción**: Developer implementa S1

**Tablas afectadas**:

#### `role_artifacts` (nuevos registros)
```
id | iteration_id | role | artifact_type | content                              | created_at
---+-------------+-----+--------------+-------------------------------------+-------------------
5  | 1           | dev | files_json   | [{"path":"main.py","content":"..."}] | 2025-12-02 10:02:00
6  | 1           | dev | model_info   | {"provider":"openai","model":"gpt-4"}| 2025-12-02 10:02:00
```

#### `story_attempts` (PRIMER ATTEMPT)
```
id | story_id | attempt_number | role | provider | model  | status  | duration_ms | tokens_in | tokens_out | created_at
---+---------+---------------+-----+---------+-------+--------+------------+----------+-----------+-------------------
1  | 1       | 1             | dev | openai  | gpt-4 | success| 2500       | 1200     | 800       | 2025-12-02 10:02:00
```

**IMPORTANTE**: `story_id=1` es el DB ID de la tabla `stories`, NO el string "S1".

**Proceso interno**:
```python
# Dev llama:
log_attempt(story_id="S1", ...)

# Internamente:
db_story_id = get_story_db_id("S1")  # Busca en tabla stories
# → Encuentra: id=1, story_id="S1"
# → db_story_id = 1

# Inserta en story_attempts con story_id=1 (FK)
```

#### `event_log` (nuevos registros)
```
id | iteration_id | event_type | role | story_id | message                            | severity | created_at
---+-------------+-----------+-----+---------+-----------------------------------+---------+-------------------
5  | 1           | dev_start | dev | S1      | Starting development for story: S1 | info    | 2025-12-02 10:02:00
6  | 1           | dev_end   | dev | S1      | Development completed for story: S1| info    | 2025-12-02 10:02:01
```

---

### 🔹 PASO 4: `make qa STORY=S1`

**Acción**: QA valida S1

**Tablas afectadas**:

#### `role_artifacts` (nuevos registros)
```
id | iteration_id | role | artifact_type | content                              | created_at
---+-------------+-----+--------------+-------------------------------------+-------------------
7  | 1           | qa  | report_json  | {"status":"pass","tests_run":5,...}  | 2025-12-02 10:03:00
8  | 1           | qa  | qa_summary   | {"areas":{"backend":{"status":"pass"}}}| 2025-12-02 10:03:00
```

#### `story_attempts` (NUEVO ATTEMPT QA)
```
id | story_id | attempt_number | role | provider | model  | status  | duration_ms | created_at
---+---------+---------------+-----+---------+-------+--------+------------+-------------------
1  | 1       | 1             | dev | openai  | gpt-4 | success| 2500       | 2025-12-02 10:02:00
2  | 1       | 1             | qa  | local   | pytest| success| 3000       | 2025-12-02 10:03:00
```

**Nota**: QA tiene `attempt_number=1` porque es el primer intento de QA para esta historia.

#### `event_log` (nuevos registros)
```
id | iteration_id | event_type | role | story_id | message                        | severity | created_at
---+-------------+-----------+-----+---------+-------------------------------+---------+-------------------
7  | 1           | qa_start  | qa  | S1      | QA starting for story: S1      | info    | 2025-12-02 10:03:00
8  | 1           | qa_end    | qa  | S1      | QA completed with status: pass | info    | 2025-12-02 10:03:01
```

---

### 📊 RESUMEN CASO 1 (Orden Normal)

**Estado final de `stories`**:
```
id | story_id | title              | status | created_at
---+---------+-------------------+-------+-------------------
1  | S1      | Add operation      | todo  | 2025-12-02 10:01:00  ← CREADA POR ARCHITECT
2  | S2      | Subtract operation | todo  | 2025-12-02 10:01:00
```

**Total registros**:
- `role_artifacts`: 8 registros (BA: 1, Architect: 3, Dev: 2, QA: 2)
- `story_attempts`: 2 registros (Dev: 1, QA: 1)
- `event_log`: 8 eventos (BA: 2, Architect: 2, Dev: 2, QA: 2)
- `stories`: 2 historias (S1, S2)

**Foreign Keys**:
- ✅ `story_attempts.story_id` → `stories.id` (1 → S1)

---

## CASO 2: OUT-OF-ORDER (Dev ANTES de Architect)

### Comando ejecutado:
```bash
make dev STORY=S1  # SIN haber corrido make plan
make plan          # DESPUÉS
```

---

### 🔹 PASO 1: `make dev STORY=S1` (SIN ARCHITECT)

**Acción**: Dev intenta implementar S1, pero S1 no existe en DB

**Estado inicial de `stories`**: **VACÍA**

**Proceso interno**:
```python
# Dev llama:
log_attempt(story_id="S1", ...)

# Internamente:
db_story_id = get_story_db_id("S1")
# → Busca en tabla stories WHERE story_id="S1"
# → NO ENCUENTRA (tabla vacía)
# → db_story_id = None

# PHASE 3: Crear placeholder
if not db_story_id:
    db_story_id = self._stories.create(
        story_id="S1",
        title="[Placeholder] S1",  ← MARCADO COMO PLACEHOLDER
        description="Created automatically during dev/qa run",
        status="doing",
    )
    # → db_story_id = 1 (nuevo registro)
```

**Tablas afectadas**:

#### `stories` (PLACEHOLDER CREADO)
```
id | iteration_id | story_id | title              | description                           | status | priority | created_at
---+-------------+---------+-------------------+--------------------------------------+-------+---------+-------------------
1  | 1           | S1      | [Placeholder] S1   | Created automatically during dev/qa   | doing | NULL    | 2025-12-02 10:02:00
```

**IMPORTANTE**: 
- `title` empieza con `[Placeholder]` (marcador para identificar)
- `status="doing"` (Dev está trabajando en esto)
- `priority=NULL`, `estimate=NULL` (no hay metadata)

#### `story_attempts` (ATTEMPT LOGUADO CON PLACEHOLDER)
```
id | story_id | attempt_number | role | provider | model  | status  | created_at
---+---------+---------------+-----+---------+-------+--------+-------------------
1  | 1       | 1             | dev | openai  | gpt-4 | success| 2025-12-02 10:02:00
```

**Nota**: `story_id=1` apunta al placeholder. FK intacta.

#### `event_log` (CON WARNING)
```
id | iteration_id | event_type               | role | story_id | message                            | severity | created_at
---+-------------+-------------------------+-----+---------+-----------------------------------+---------+-------------------
1  | 1           | dev_start               | dev | S1      | Starting development for story: S1 | info    | 2025-12-02 10:02:00
2  | 1           | story_placeholder_created| dev | S1      | Auto-created placeholder for S1    | warning | 2025-12-02 10:02:00
3  | 1           | dev_end                 | dev | S1      | Development completed for story: S1| info    | 2025-12-02 10:02:01
```

**Nota**: Evento `story_placeholder_created` con severity `warning` para auditoría.

---

### 🔹 PASO 2: `make plan` (DESPUÉS DE DEV)

**Acción**: Architect genera stories, encuentra placeholder de S1

**Proceso interno en `StoryRepository.create()`**:
```python
# Architect llama:
create_stories_from_list([
    {"id": "S1", "title": "Add operation", "description": "Real desc", ...}
])

# Para cada historia:
existing = self.get_by_story_id(iteration_id, "S1")
# → Encuentra: id=1, title="[Placeholder] S1"

is_placeholder = existing["title"].startswith("[Placeholder]")
# → True

if is_placeholder:
    # UPDATE en lugar de INSERT
    UPDATE stories
    SET title="Add operation",
        description="Real desc",
        priority="P1",
        status="todo",  ← RESET de "doing" a "todo"
        ...
    WHERE id=1
```

**Tablas afectadas**:

#### `stories` (PLACEHOLDER ACTUALIZADO)

**ANTES**:
```
id | story_id | title              | description                    | status | priority | created_at
---+---------+-------------------+-------------------------------+-------+---------+-------------------
1  | S1      | [Placeholder] S1   | Created automatically during...| doing | NULL    | 2025-12-02 10:02:00
```

**DESPUÉS**:
```
id | story_id | title              | description               | status | priority | complexity | created_at
---+---------+-------------------+--------------------------+-------+---------+-----------+-------------------
1  | S1      | Add operation      | Implement addition logic  | todo  | P1      | medium    | 2025-12-02 10:02:00
```

**CAMBIOS**:
- ✅ `title`: `[Placeholder] S1` → `Add operation`
- ✅ `description`: placeholder text → descripción real
- ✅ `status`: `doing` → `todo` (reseteo)
- ✅ `priority`: `NULL` → `P1`
- ✅ `complexity`: `NULL` → `medium`
- ✅ **`id` NO CAMBIA**: sigue siendo `1`

#### `story_attempts` (SIN CAMBIOS)
```
id | story_id | attempt_number | role | provider | model  | status  | created_at
---+---------+---------------+-----+---------+-------+--------+-------------------
1  | 1       | 1             | dev | openai  | gpt-4 | success| 2025-12-02 10:02:00
```

**IMPORTANTE**: El attempt de Dev sigue apuntando a `story_id=1`, que ahora es la historia completa. **FK preservada**.

---

### 📊 RESUMEN CASO 2 (Out-of-Order)

**Timeline**:
1. Dev crea placeholder → `stories.id=1` con `title="[Placeholder] S1"`
2. Dev loguea attempt → `story_attempts.story_id=1`
3. Architect actualiza placeholder → `stories.id=1` con `title="Add operation"`
4. Attempt de Dev sigue vinculado → `story_id=1` apunta a historia real

**Estado final idéntico a Caso 1**:
- `stories`: Historia S1 completa (sin "[Placeholder]")
- `story_attempts`: Attempt de Dev preservado
- `event_log`: Evento extra `story_placeholder_created` como auditoría

**Ventaja**: Zero data loss, foreign keys intactas.

---

## CASO 3: IDEMPOTENTE (Architect múltiples veces)

### Comando ejecutado:
```bash
make plan
make plan  # Segunda vez
```

---

### 🔹 PASO 1: `make plan` (Primera vez)

**Resultado**: Como Caso 1, Paso 2.

```
stories:
id | story_id | title              | status | created_at
---+---------+-------------------+-------+-------------------
1  | S1      | Add operation      | todo  | 2025-12-02 10:01:00
2  | S2      | Subtract operation | todo  | 2025-12-02 10:01:00
```

---

### 🔹 PASO 2: `make plan` (Segunda vez)

**Acción**: Architect vuelve a generar stories

**Proceso interno**:
```python
# Architect llama:
create_stories_from_list([
    {"id": "S1", "title": "Add operation", ...}
])

# Para S1:
existing = self.get_by_story_id(iteration_id, "S1")
# → Encuentra: id=1, title="Add operation"

is_placeholder = existing["title"].startswith("[Placeholder]")
# → False (no es placeholder)

if not is_placeholder:
    # NO ACTUALIZAR - solo retornar ID existente
    return existing["id"]  # → 1
```

**Tablas afectadas**: **NINGUNA** (no se escribe nada)

#### `stories` (SIN CAMBIOS)
```
id | story_id | title              | status | created_at
---+---------+-------------------+-------+-------------------
1  | S1      | Add operation      | todo  | 2025-12-02 10:01:00  ← MISMO REGISTRO
2  | S2      | Subtract operation | todo  | 2025-12-02 10:01:00
```

**Query ejecutado**:
```sql
-- Primera vez:
INSERT INTO stories (...) VALUES (...)  ← id=1

-- Segunda vez:
SELECT * FROM stories WHERE story_id='S1'  ← Encuentra id=1
-- NO INSERT, NO UPDATE
-- Return 1
```

---

### 📊 RESUMEN CASO 3 (Idempotente)

**Llamadas a `create_stories_from_list()`**:
1. Primera: INSERT nuevos registros
2. Segunda: SELECT + return ID (sin escrituras)

**Ventaja**: Arquitecto puede re-correr sin duplicar historias.

---

## CASO 4: STANDALONE (Cada rol independiente)

### Comando ejecutado (sin orchestrator):
```bash
make ba CONCEPT="Calculator"
make plan
make dev STORY=S1
make qa STORY=S1
```

---

### 🔹 CONTEXTO AD-HOC

Cada rol crea su propio contexto ad-hoc:

#### BA crea:
```
projects:
id | name      | concept     | created_at
---+----------+------------+-------------------
1  | adhoc-ba | Calculator  | 2025-12-02 10:00:00

iterations:
id | project_id | loops_requested | created_at
---+-----------+----------------+-------------------
1  | 1         | 1              | 2025-12-02 10:00:00
```

#### Architect reusa o crea:
```python
# Busca proyecto adhoc-architect
# Si no existe, crea nuevo
# Si existe, reusa iteration actual
```

**Resultado**: Todos los roles pueden escribir a DB aunque se ejecuten standalone.

---

## VERIFICACIÓN EN DB REAL

Para verificar estos escenarios en tu DB real:

```bash
# Limpiar estado
rm -f data/pipeline.db

# CASO 2: Out-of-order
make dev STORY=S1

# Ver placeholder
sqlite3 data/pipeline.db << 'SQL'
SELECT id, story_id, title, status, priority 
FROM stories 
WHERE story_id='S1';
SQL
# Esperado: 1 | S1 | [Placeholder] S1 | doing | NULL

# Ver attempt vinculado al placeholder
sqlite3 data/pipeline.db << 'SQL'
SELECT id, story_id, role, status 
FROM story_attempts 
WHERE role='dev';
SQL
# Esperado: 1 | 1 | dev | success

# Ahora architect
make plan

# Ver historia actualizada
sqlite3 data/pipeline.db << 'SQL'
SELECT id, story_id, title, status, priority 
FROM stories 
WHERE story_id='S1';
SQL
# Esperado: 1 | S1 | Add operation | todo | P1
# ← MISMO ID, TITLE ACTUALIZADO

# Ver que attempt sigue vinculado
sqlite3 data/pipeline.db << 'SQL'
SELECT sa.id, sa.story_id, sa.role, s.title
FROM story_attempts sa
JOIN stories s ON sa.story_id = s.id
WHERE sa.role='dev';
SQL
# Esperado: 1 | 1 | dev | Add operation
# ← FK preservada
```

