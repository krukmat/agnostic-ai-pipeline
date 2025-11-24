# Plan: Capa de Base de Datos para Pipeline AI

## Estado Actual

### Almacenamiento Basado en Archivos

| Archivo | Formato | Rol que lo Genera | Propósito |
|---------|---------|-------------------|-----------|
| `planning/requirements.yaml` | YAML | BA | Requisitos funcionales/no-funcionales |
| `planning/product_vision.yaml` | YAML | PO | Visión del producto |
| `planning/product_owner_review.yaml` | YAML | PO | Validación de alineamiento |
| `planning/stories.yaml` | YAML | Architect | **ARCHIVO CRÍTICO** - estado de todas las historias |
| `planning/architecture.yaml` | YAML | Architect | Diseño técnico |
| `planning/epics.yaml` | YAML | Architect | Agrupación de épicas |
| `planning/prd.yaml` | YAML | Architect | PRD |
| `planning/notes.md` | Markdown | Orchestrator | Journal de ejecución |
| `artifacts/dev/<story>-<ts>/` | JSON | Developer | Código generado |
| `artifacts/qa/last_report.json` | JSON | QA | Resultados de tests |
| `artifacts/iterations/<ts>/` | Mixed | Orchestrator | Snapshots de iteración |

### Problemas Identificados

| Problema | Impacto | Severidad |
|----------|---------|-----------|
| **Fragilidad YAML** | `stories.yaml` malformado crashea el loop | **ALTA** |
| **Sin Transacciones** | Fallo parcial deja estado inconsistente | **ALTA** |
| **Archivo Único Mutable** | `stories.yaml` es cuello de botella | **ALTA** |
| **Pérdida en Crash** | Metadata en memoria se pierde | **MEDIA** |
| **Sin Locking** | Race conditions con múltiples orchestrators | **MEDIA** |
| **Audit Trail No Estructurado** | `notes.md` no es queryable | **MEDIA** |

---

## Propuesta: Capa de Base de Datos

### Tecnología Recomendada: **SQLite**

**Razones:**
- Zero-config, sin servidor externo
- Transacciones ACID nativas
- Compatible con el enfoque single-node actual
- Fácil migración a PostgreSQL si escala
- Python tiene soporte nativo (`sqlite3`)

### Modelo de Datos Propuesto

```
┌─────────────────────────────────────────────────────────────────┐
│                        SCHEMA v1.0                              │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐       ┌──────────────────┐
│    projects      │       │    iterations    │
├──────────────────┤       ├──────────────────┤
│ id (PK)          │───┐   │ id (PK)          │
│ name             │   │   │ project_id (FK)  │◄──┐
│ concept          │   │   │ started_at       │   │
│ created_at       │   │   │ finished_at      │   │
│ status           │   │   │ loops_requested  │   │
└──────────────────┘   │   │ status           │   │
                       │   │ config_snapshot  │   │
                       │   └──────────────────┘   │
                       │                          │
                       ▼                          │
┌──────────────────┐       ┌──────────────────┐   │
│  role_artifacts  │       │     stories      │   │
├──────────────────┤       ├──────────────────┤   │
│ id (PK)          │       │ id (PK)          │   │
│ project_id (FK)  │       │ iteration_id(FK) │───┘
│ role             │       │ story_id (S1,S2) │
│ artifact_type    │       │ title            │
│ content (JSON)   │       │ description      │
│ version          │       │ status           │
│ created_at       │       │ priority         │
└──────────────────┘       │ estimate         │
                           │ depends_on       │
                           │ metadata (JSON)  │
                           │ created_at       │
                           │ updated_at       │
                           └──────────────────┘

┌──────────────────┐       ┌──────────────────┐
│  story_attempts  │       │   event_log      │
├──────────────────┤       ├──────────────────┤
│ id (PK)          │       │ id (PK)          │
│ story_id (FK)    │       │ project_id (FK)  │
│ attempt_number   │       │ iteration_id(FK) │
│ role             │       │ story_id (FK)    │
│ provider         │       │ event_type       │
│ model            │       │ role             │
│ status           │       │ payload (JSON)   │
│ duration_ms      │       │ timestamp        │
│ tokens_in        │       └──────────────────┘
│ tokens_out       │
│ cost_usd         │
│ error_message    │
│ artifacts_path   │
│ created_at       │
└──────────────────┘

┌──────────────────┐
│   model_stats    │  (Vista Materializada o Tabla Agregada)
├──────────────────┤
│ provider         │
│ model            │
│ role             │
│ total_attempts   │
│ success_count    │
│ failure_count    │
│ avg_duration_ms  │
│ total_tokens     │
│ total_cost_usd   │
└──────────────────┘

```

---

## Fases de Migración (Estrategia Dual-Write)

### Fase 1: Preparación (Infraestructura)
- Crear módulo `src/db/storage.py` con un `Database` singleton (abre `sqlite3` con WAL mode).
- Exponer helpers transaccionales (`with db.transaction(): ...`) y repositorios por tabla.
- Crear schema inicial con todas las tablas.
- Tests unitarios para repositorios.

### Fase 2: Dual Write (YAML + SQLite)
- Inyectar el repositorio en los roles para que, además de los archivos actuales, registren su output en `role_artifacts` / `stories`.
- Mantener los archivos YAML como "source of truth" mientras se validan los registros en DB.
- Flag `USE_DB=1` para activar escritura dual.

### Fase 3: Verificación
- Comparar `planning/stories.yaml` vs tabla `stories` en cada loop (script `scripts/db_verify.py`).
- Ejecutar al menos **5 iteraciones completas** registradas en la DB antes del corte.
- Validar integridad referencial y consistencia de datos.

### Fase 4: Cut-over
- Cambiar los loaders del orchestrator para **leer desde SQLite**.
- Los archivos YAML pasan a ser snapshots generados desde la DB al final de cada iteration.
- Export automático: `sqlite3 pipeline.db .dump` → `artifacts/iterations/<ts>/`.

### Fase 5: Post-cut (Estabilización)
- Documentar plan de rollback (restaurar dumps + copiar back YAML).
- Programar backups automáticos (copiar `pipeline.db` a `artifacts/iterations/<ts>/`).
- Implementar CLI de observabilidad (`make db-stats`, `make db-costs`).

---

## Entidades Principales (DDL)

#### 1. `projects`
Representa un concepto/proyecto completo del pipeline.

```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    concept TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed', 'archived'))
);
```

#### 2. `iterations`
Cada ciclo BA→PO→Architect→Dev→QA.

```sql
CREATE TABLE iterations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    loops_requested INTEGER DEFAULT 1,
    loops_completed INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running' CHECK(status IN ('running', 'completed', 'failed', 'cancelled')),
    config_snapshot TEXT -- JSON del config.yaml usado
);
```

#### 3. `role_artifacts`
Outputs de cada rol (requirements, vision, architecture, etc.).

```sql
CREATE TABLE role_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    iteration_id INTEGER REFERENCES iterations(id),
    role TEXT NOT NULL CHECK(role IN ('ba', 'po', 'architect', 'dev', 'qa')),
    artifact_type TEXT NOT NULL, -- 'requirements', 'product_vision', 'architecture', etc.
    content TEXT NOT NULL, -- JSON o YAML serializado
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, role, artifact_type, version)
);
```

#### 4. `stories`
Historias de usuario con estado y metadata.

```sql
CREATE TABLE stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iteration_id INTEGER NOT NULL REFERENCES iterations(id),
    story_id TEXT NOT NULL, -- 'S1', 'S2', etc.
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'todo' CHECK(status IN (
        'todo', 'doing', 'in_progress', 'dev_ok',
        'done', 'in_review', 'blocked_dev', 'done_force_architect'
    )),
    priority TEXT CHECK(priority IN ('P0', 'P1', 'P2', 'P3')),
    estimate TEXT, -- 'XS', 'S', 'M', 'L', 'XL'
    acceptance_criteria TEXT, -- JSON array
    depends_on TEXT, -- JSON array de story_ids
    metadata TEXT, -- JSON con recovery_attempts, model_history, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(iteration_id, story_id)
);
```

#### 5. `story_attempts`
Historial de intentos por historia (tracking de modelos).

```sql
CREATE TABLE story_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER NOT NULL REFERENCES stories(id),
    attempt_number INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('dev', 'qa', 'architect_review')),
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('success', 'error', 'timeout')),
    duration_ms INTEGER,
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_usd REAL,
    error_message TEXT,
    error_category TEXT, -- 'parse_error', 'timeout', 'rate_limit', 'invalid_output'
    artifacts_path TEXT, -- Ruta al directorio de artifacts
    raw_response_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 6. `event_log`
Log estructurado de eventos (reemplaza notes.md).

```sql
CREATE TABLE event_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    iteration_id INTEGER REFERENCES iterations(id),
    story_id INTEGER REFERENCES stories(id),
    event_type TEXT NOT NULL, -- 'role_start', 'role_end', 'status_change', 'error', 'recovery', etc.
    role TEXT,
    severity TEXT DEFAULT 'info' CHECK(severity IN ('debug', 'info', 'warning', 'error')),
    message TEXT,
    payload TEXT, -- JSON con datos adicionales
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_event_log_timestamp ON event_log(timestamp);
CREATE INDEX idx_event_log_project ON event_log(project_id);
CREATE INDEX idx_event_log_type ON event_log(event_type);
```

#### 7. `model_stats`

```sql
CREATE TABLE model_stats (
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    role TEXT NOT NULL,
    total_attempts INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_duration_ms REAL,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd REAL DEFAULT 0,
    PRIMARY KEY (provider, model, role)
);
```

---

## Beneficios de la Migración

### 1. **Integridad de Datos**
- Transacciones ACID previenen estados inconsistentes
- Foreign keys garantizan referencias válidas
- CHECK constraints validan estados

### 2. **Queryabilidad**
```sql
-- Stories bloqueadas por modelo
SELECT s.story_id, sa.model, sa.error_category, COUNT(*) as failures
FROM stories s
JOIN story_attempts sa ON s.id = sa.story_id
WHERE sa.status = 'error'
GROUP BY s.story_id, sa.model, sa.error_category;

-- Costo total por iteración
SELECT i.id, SUM(sa.cost_usd) as total_cost
FROM iterations i
JOIN stories s ON i.id = s.iteration_id
JOIN story_attempts sa ON s.id = sa.story_id
GROUP BY i.id;

-- Tasa de éxito por modelo
SELECT provider, model,
       COUNT(*) as total,
       SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as successes,
       ROUND(100.0 * SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM story_attempts
GROUP BY provider, model;
```

### 3. **Observabilidad**
- Event log estructurado y queryable.
- Métricas de performance por modelo (tabla `model_stats`).
- Tracking de costos y tokens por rol.
- Historial completo de intentos (éxitos/errores, categorías, providers).

### 4. **Recuperación y Backups**
- Estado persistido después de cada operación.
- Export automático (`sqlite3 pipeline.db .dump`) al cerrar cada iteration.
- Backups sencillos: copiar `pipeline.db` + dump a `artifacts/iterations/<ts>/`.
- Rollback posible restaurando ese dump con un script `scripts/db_restore.py`.

### 5. **Concurrencia**
- Activar WAL mode para permitir lecturas concurrentes.
- Definir locking por `project_id` en el orchestrator (no correr 2 loops simultáneos sobre el mismo project).
- Si la contención crece, la capa de repositorios facilita migrar a PostgreSQL sin reescribir los roles.

### Integración con los Roles

| Componente | Cambios clave |
|------------|---------------|
| Orchestrator | Leer/escribir stories e iterations desde la DB, registrar eventos en `event_log`, y exportar dumps (`sqlite3 pipeline.db .dump`) dentro de `artifacts/iterations/<ts>/`. Aplicar locking por proyecto para evitar loops simultáneos. |
| BA / Product Owner | Continuar generando YAML para compatibilidad pero insertar cada artifact (requirements, product_vision, reviews) en `role_artifacts` mediante un repositorio compartido. |
| Architect | Al generar stories reales, insertar/actualizar `stories` y `role_artifacts` (epics, architecture, PRD). En modo `arch_only`, sólo se guarda la parte de arquitectura. |
| Developer | Por cada intento, registrar tokens, duración, estado, costos y rutas de artifacts en `story_attempts`. |
| QA | Persistir `last_report.json` y defect logs en `role_artifacts`, y registrar cada corrida en `story_attempts` (rol=qa). |

---

## Archivos a Crear/Modificar

### Nuevos Archivos
```
src/
└── db/
    ├── __init__.py
    ├── storage.py         # Database singleton con WAL mode
    ├── schema.py          # Definiciones de tablas (DDL)
    ├── repository.py      # Operaciones CRUD por entidad
    └── queries.py         # Queries analíticas comunes

scripts/
├── db_migrate.py          # CLI para crear/migrar schema
├── db_import_yaml.py      # Importar datos existentes de YAML
├── db_verify.py           # Comparar YAML vs DB (fase verificación)
├── db_export.py           # Exportar DB a YAML/JSON
└── db_restore.py          # Restaurar desde dump

data/
└── pipeline.db            # Base de datos SQLite (gitignored)
```

### Archivos a Modificar
```
scripts/
├── orchestrate.py         # Usar DB para estado
├── run_ba.py              # Guardar artifacts
├── run_product_owner.py   # Guardar artifacts
├── run_architect.py       # Crear stories
├── run_dev.py             # Registrar intentos
└── run_qa.py              # Registrar resultados

Makefile                   # Agregar comandos db-*
config.yaml                # Agregar sección database
```

---

## Decisiones Tomadas

| Decisión | Resolución |
|----------|------------|
| **¿Migración completa o híbrida?** | **Opción A**: DB como source of truth, YAML como export (post cut-over) |
| **¿Dónde almacenar contenido grande?** | **Filesystem**: Artifacts de código y respuestas raw en `artifacts/`, DB guarda solo rutas (`artifacts_path`, `raw_response_path`) |
| **¿Versionado de artifacts?** | **Todas las versiones**: Campo `version` en `role_artifacts`, incrementa con cada regeneración |
| **¿Esquema de costos?** | **Input desde LLM response**: Capturar `tokens_in`, `tokens_out` del response; calcular costo con tabla de precios configurable |

---

## Próximos Pasos

1. ✅ **Plan aprobado**
2. ✅ Crear branch `feature/database-layer`
3. ✅ **Fase 1**: Implementar `src/db/` (storage, schema, repository)
   - `src/db/storage.py` - Singleton con WAL mode
   - `src/db/schema.py` - DDL de 7 tablas + índices
   - `src/db/repository.py` - 6 repositorios CRUD
4. ✅ **Fase 1**: Tests unitarios para repositorios (17 tests passing)
5. ✅ **Fase 1**: `scripts/db_migrate.py` - CLI de migración
6. ✅ **Fase 2**: Dual-write en orchestrator y roles
   - `src/db/dual_write.py` - DualWriteContext centralizado
   - `scripts/orchestrate.py` - project/iteration, story attempts, status
   - `scripts/run_ba.py` - requirements artifact
   - `scripts/run_product_owner.py` - vision/review artifacts
   - `scripts/run_architect.py` - stories/epics/architecture artifacts
7. ✅ **Fase 3**: Script de verificación y tests
   - `scripts/db_verify.py` - CLI de verificación dual-write
   - `tests/test_db_verify.py` - 11 tests unitarios
8. ✅ **Fase 3**: Iteración de prueba validada (26 stories, integridad OK)
9. ✅ **Fase 4**: Cut-over a DB como source of truth
   - `load_stories()` ahora prioriza DB
   - `save_stories()` sincroniza a ambos
   - Export automático y backup al final de iteración
10. ✅ **Fase 5**: CLI de observabilidad
    - `scripts/db_stats.py` - CLI de estadísticas
    - Makefile targets: `db-stats`, `db-models`, `db-costs`, `db-verify`, `db-migrate`

---

## Implementación Fase 1 (Completada)

### Resumen
**Branch:** `feature/database-layer`
**Commit:** `077954b`
**Fecha:** 2025-11-23

### Archivos Creados

#### 1. `src/db/storage.py` - Database Singleton
Implementa el patrón singleton para la conexión SQLite con:
- **WAL mode**: Permite lecturas concurrentes mientras se escribe
- **Foreign keys**: Habilitadas para integridad referencial
- **Busy timeout**: 5000ms para evitar errores de bloqueo
- **Transaction helper**: Context manager `with db.transaction():`

```python
# Uso básico
from src.db import get_db
db = get_db()

# Transacción
with db.transaction():
    db.execute("INSERT INTO projects ...")
    db.execute("INSERT INTO iterations ...")
```

#### 2. `src/db/schema.py` - Definiciones DDL
Contiene:
- **7 tablas**: `projects`, `iterations`, `stories`, `story_attempts`, `role_artifacts`, `event_log`, `model_stats`, `schema_version`
- **7 índices**: Para optimizar queries frecuentes en `event_log`, `stories`, `story_attempts`, `role_artifacts`
- **Versionado**: `SCHEMA_VERSION = 1` para migraciones futuras

```python
# Crear schema
from src.db.schema import create_schema
create_schema(db)
```

#### 3. `src/db/repository.py` - Repositorios CRUD
6 clases de repositorio, cada una con operaciones específicas:

| Repositorio | Métodos Principales |
|-------------|---------------------|
| `ProjectRepository` | `create()`, `get()`, `get_by_name()`, `list_all()`, `update_status()` |
| `IterationRepository` | `create()`, `get()`, `get_latest()`, `update_status()`, `increment_loops()` |
| `StoryRepository` | `create()`, `get()`, `get_by_story_id()`, `list_by_iteration()`, `list_by_status()`, `update_status()`, `update_metadata()`, `count_by_status()` |
| `StoryAttemptRepository` | `create()`, `list_by_story()`, `get_last_attempt()`, `count_attempts()` |
| `RoleArtifactRepository` | `create()` (auto-versiona), `get_latest()`, `list_by_project()` |
| `EventLogRepository` | `log()`, `list_recent()`, `list_by_type()`, `list_errors()` |

```python
# Ejemplo de uso
from src.db import get_db, ProjectRepository, StoryRepository

db = get_db()
projects = ProjectRepository(db)
stories = StoryRepository(db)

pid = projects.create("mi-proyecto", "Concepto de negocio")
# ... crear iteration ...
stories.create(iteration_id, "S1", "Primera historia", priority="P1")
```

#### 4. `src/db/__init__.py` - Exports
Expone la API pública del módulo:
```python
from src.db import (
    Database, get_db,
    ProjectRepository, IterationRepository, StoryRepository,
    StoryAttemptRepository, RoleArtifactRepository, EventLogRepository
)
```

#### 5. `scripts/db_migrate.py` - CLI de Migración
Script ejecutable para gestionar el schema:

```bash
# Crear schema (primera vez)
python scripts/db_migrate.py

# Verificar versión actual
python scripts/db_migrate.py --check

# Forzar recreación (desarrollo)
python scripts/db_migrate.py --force

# Usar path alternativo
python scripts/db_migrate.py --db-path /tmp/test.db
```

#### 6. `tests/test_db_repository.py` - Tests Unitarios
17 tests cubriendo todos los repositorios:

| Clase Test | Tests | Cobertura |
|------------|-------|-----------|
| `TestProjectRepository` | 4 | create, get, get_by_name, list_all, update_status |
| `TestIterationRepository` | 3 | create, get_latest, increment_loops |
| `TestStoryRepository` | 4 | create, list_by_iteration, update_status, count_by_status |
| `TestStoryAttemptRepository` | 2 | create_and_list, count_attempts |
| `TestRoleArtifactRepository` | 2 | versioning, list_by_project |
| `TestEventLogRepository` | 2 | log_and_list, list_errors |

```bash
# Ejecutar tests
PYTHONPATH=. .venv/bin/pytest tests/test_db_repository.py -v
# Resultado: 17 passed in 0.10s
```

### Configuración en `config.yaml`

```yaml
database:
  enabled: false  # Cambiar a true para activar dual-write
  path: data/pipeline.db
  wal_mode: true
  busy_timeout_ms: 5000
  backup_on_iteration_end: true
```

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `enabled` | bool | `false` | Activa/desactiva la capa de DB |
| `path` | string | `data/pipeline.db` | Ruta al archivo SQLite |
| `wal_mode` | bool | `true` | Habilita WAL para lecturas concurrentes |
| `busy_timeout_ms` | int | `5000` | Timeout de espera si DB está bloqueada |
| `backup_on_iteration_end` | bool | `true` | Copia DB a artifacts al finalizar iteración |

#### `.gitignore` actualizado
```
data/pipeline.db
data/pipeline.db-wal
data/pipeline.db-shm
```

### Diagrama de Dependencias

```
src/db/
├── __init__.py          # Re-exports públicos
├── storage.py           # Database singleton (sin deps)
├── schema.py            # DDL (depende de storage)
└── repository.py        # CRUD (depende de storage)

scripts/
└── db_migrate.py        # CLI (depende de storage + schema)

tests/
└── test_db_repository.py  # Tests (depende de todo)
```

### Validación

```bash
# 1. Crear DB desde cero
$ python scripts/db_migrate.py --force
Database: data/pipeline.db
Current version: 0
Target version: 1
Creating schema...
Schema migrated to version 1
Tables created: ['event_log', 'iterations', 'model_stats', 'projects',
                 'role_artifacts', 'schema_version', 'sqlite_sequence',
                 'stories', 'story_attempts']

# 2. Verificar schema
$ python scripts/db_migrate.py --check
Current schema version: 1
Target schema version: 1
Schema is up to date

# 3. Correr tests
$ PYTHONPATH=. .venv/bin/pytest tests/test_db_repository.py -v
17 passed in 0.10s
```

---

## Implementación Fase 2 (Completada)

### Resumen
**Branch:** `feature/database-layer`
**Commit:** `ee3e198`
**Fecha:** 2025-11-23

### Componente Principal: `src/db/dual_write.py`

Clase `DualWriteContext` que centraliza todas las operaciones de dual-write:

```python
from src.db import DualWriteContext, db_enabled

if db_enabled():
    with DualWriteContext(project_name, concept) as ctx:
        # Iniciar iteración
        ctx.start_iteration(loops_requested=5, config_snapshot=config)

        # Guardar artifacts
        ctx.save_artifact("ba", "requirements", data)
        ctx.save_artifact("po", "product_vision", vision_yaml)

        # Crear stories desde lista
        ctx.create_stories_from_list(stories)

        # Registrar intentos
        ctx.log_attempt(
            story_id="S1", role="dev",
            provider="vertex_sdk", model="gemini-2.5-pro",
            status="success", tokens_in=100, tokens_out=500
        )

        # Actualizar status
        ctx.update_story_status("S1", "done")

        # Logging de eventos
        ctx.log_event("role_start", "BA started", role="ba")
```

### Integración por Componente

| Componente | Archivo | Operaciones DB |
|------------|---------|----------------|
| **Orchestrator** | `scripts/orchestrate.py` | Crea project/iteration, sincroniza stories, registra dev/qa attempts, actualiza status |
| **BA** | `scripts/run_ba.py` | Guarda `requirements` en `role_artifacts` |
| **PO** | `scripts/run_product_owner.py` | Guarda `product_vision`, `product_owner_review` |
| **Architect** | `scripts/run_architect.py` | Guarda `stories`, `epics`, `architecture`, crea stories en tabla |
| **Dev** | via orchestrator | Registra attempts con tokens/duración/error |
| **QA** | via orchestrator | Registra attempts con resultado/error |

### Activación

```yaml
# config.yaml
database:
  enabled: true  # Cambiar a true para activar
  path: data/pipeline.db
  wal_mode: true
```

### Flujo de Datos

```
┌─────────────────────────────────────────────────────────────┐
│                    CON database.enabled: true               │
└─────────────────────────────────────────────────────────────┘

  Orchestrator Start
      │
      ├─→ DualWriteContext.__enter__()
      │     ├─→ get_or_create project
      │     └─→ start_iteration
      │
      ├─→ BA ejecuta
      │     └─→ save_artifact("ba", "requirements", ...)
      │
      ├─→ PO ejecuta
      │     └─→ save_artifact("po", "product_vision", ...)
      │
      ├─→ Architect ejecuta
      │     ├─→ save_artifact("architect", "stories", ...)
      │     └─→ create_stories_from_list(...)
      │
      ├─→ Dev loop por story
      │     ├─→ log_attempt(story_id, role="dev", ...)
      │     └─→ update_story_status(sid, status)
      │
      ├─→ QA loop por story
      │     ├─→ log_attempt(story_id, role="qa", ...)
      │     └─→ update_story_status(sid, status)
      │
      └─→ DualWriteContext.__exit__()
            └─→ end_iteration("completed")
```

---

## Implementación Fase 3 (En Progreso)

### Resumen
**Branch:** `feature/database-layer`
**Fecha:** 2025-11-23

### Script de Verificación: `scripts/db_verify.py`

CLI para comparar datos entre YAML files y base de datos SQLite:

```bash
# Verificar última iteración
python scripts/db_verify.py

# Verificar iteración específica
python scripts/db_verify.py --iteration-id 5

# Verificar proyecto por nombre
python scripts/db_verify.py --project mi-proyecto

# Output JSON
python scripts/db_verify.py --json

# Verbose
python scripts/db_verify.py -v
```

### Funciones de Verificación

| Función | Propósito |
|---------|-----------|
| `verify_stories()` | Compara stories entre `planning/stories.yaml` y tabla `stories` |
| `verify_artifacts()` | Compara artifacts entre archivos y `role_artifacts` |
| `verify_integrity()` | Verifica integridad referencial (orphans) |
| `run_verification()` | Ejecuta verificación completa y genera reporte |

### Output del Reporte

```
============================================================
DUAL-WRITE VERIFICATION REPORT
============================================================
Project ID: 1
Iteration ID: 3
Overall Status: OK

STORIES:
  Status: ok
  YAML count: 5
  DB count: 5

INTEGRITY:
  Status: ok
  Orphan iterations: 0
  Orphan stories: 0
  Orphan attempts: 0

============================================================
```

### Tests: `tests/test_db_verify.py`

11 tests cubriendo todas las funciones de verificación:

| Clase Test | Tests | Cobertura |
|------------|-------|-----------|
| `TestVerifyStories` | 5 | matching, missing_in_db, missing_in_yaml, status_mismatch, yaml_not_found |
| `TestVerifyArtifacts` | 2 | matching, content_mismatch |
| `TestVerifyIntegrity` | 2 | fk_integrity, detect_orphans |
| `TestFullVerification` | 2 | full_report, empty_iteration |

```bash
# Ejecutar tests
PYTHONPATH=. .venv/bin/pytest tests/test_db_verify.py -v
# Resultado: 11 passed in 0.15s
```

### Total Tests DB Layer

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_db*.py tests/test_dual_write.py -v
# Resultado: 44 passed
```

| Suite | Tests |
|-------|-------|
| `test_db_repository.py` | 17 |
| `test_dual_write.py` | 16 |
| `test_db_verify.py` | 11 |
| **Total** | **44** |

### Próximo Paso: Iteraciones de Prueba

Para completar Fase 3, ejecutar al menos 5 iteraciones con `database.enabled: true`:

```bash
# 1. Habilitar dual-write
# En config.yaml: database.enabled: true

# 2. Ejecutar iteración
make iteration CONCEPT="Prueba dual-write 1"

# 3. Verificar consistencia
python scripts/db_verify.py -v

# 4. Repetir 5 veces con diferentes conceptos
```

---

## Implementación Fase 4 (Completada)

### Resumen
**Branch:** `feature/database-layer`
**Fecha:** 2025-11-24

### Cut-over: DB como Source of Truth

El orchestrator ahora usa la base de datos como fuente primaria de verdad para stories:

1. **`load_stories()`** - Prioridad: DB > YAML
   - Primero intenta cargar desde DB si está habilitado
   - Fallback a YAML si DB falla o no tiene datos
   - Mantiene recovery automático de YAML corrupto

2. **`save_stories()`** - Escribe a ambos
   - Siempre guarda YAML (backwards compatibility)
   - Sincroniza cambios de status a DB

3. **Export automático al final de iteración**
   - Exporta stories de DB a YAML
   - Crea backup de DB en `artifacts/db_backups/`

### Nuevas Funciones en `src/db/dual_write.py`

| Función | Propósito |
|---------|-----------|
| `load_stories_from_db(iteration_id)` | Carga stories de DB en formato YAML-compatible |
| `export_stories_to_yaml(iteration_id, path)` | Exporta stories de DB a archivo YAML |
| `backup_db_to_artifacts(artifacts_dir)` | Crea backup timestamped de la DB |

### Flujo de Datos Actualizado

```
┌─────────────────────────────────────────────────────────────┐
│            FASE 4: DB como Source of Truth                   │
└─────────────────────────────────────────────────────────────┘

  load_stories()
      │
      ├─→ ¿DB enabled + iteration_id?
      │     ├─→ SÍ: load_stories_from_db()
      │     │         └─→ return DB stories
      │     └─→ NO: continue to YAML
      │
      └─→ Load from planning/stories.yaml
            └─→ YAML recovery if needed

  save_stories()
      │
      ├─→ Write to planning/stories.yaml (always)
      │
      └─→ ¿DB enabled?
            └─→ SÍ: update_story_status() for each story

  End of iteration
      │
      ├─→ export_stories_to_yaml() → planning/stories.yaml
      │
      └─→ backup_db_to_artifacts() → artifacts/db_backups/
```

### Configuración

```yaml
# config.yaml
database:
  enabled: true  # Fase 4 activa
  path: data/pipeline.db
  wal_mode: true
  busy_timeout_ms: 5000
  backup_on_iteration_end: true
```

### Verificación

```bash
# Ejecutar orchestrator
PYTHONPATH=. CONCEPT="Test" .venv/bin/python scripts/orchestrate.py

# Verificar DB vs YAML
python scripts/db_verify.py -v

# Check backups
ls -la artifacts/db_backups/
```

### Total Tests: 44 passing

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_db*.py tests/test_dual_write.py -v
# 44 passed
```

---

## Implementación Fase 5 (Completada)

### Resumen
**Branch:** `feature/database-layer`
**Fecha:** 2025-11-24

### CLI de Observabilidad: `scripts/db_stats.py`

```bash
# Resumen general
python scripts/db_stats.py
make db-stats

# Estadísticas por proyecto
python scripts/db_stats.py --project simple_calculator_api

# Estadísticas por modelo
python scripts/db_stats.py --models
make db-models

# Resumen de costos
python scripts/db_stats.py --costs
make db-costs

# Eventos recientes
python scripts/db_stats.py --events 20

# Output JSON
python scripts/db_stats.py --json
```

### Makefile Targets

| Target | Descripción |
|--------|-------------|
| `make db-stats` | Muestra resumen general de la DB |
| `make db-models` | Estadísticas por provider/modelo |
| `make db-costs` | Resumen de tokens y costos |
| `make db-verify` | Verifica consistencia DB vs YAML |
| `make db-migrate` | Ejecuta migración de schema |

### Funciones de Estadísticas

| Función | Propósito |
|---------|-----------|
| `get_overview_stats()` | Conteos de projects, iterations, stories, attempts |
| `get_project_stats()` | Stats detalladas de un proyecto |
| `get_model_stats()` | Attempts, success rate, tokens por modelo |
| `get_cost_summary()` | Tokens y costos por provider/role |
| `get_recent_events()` | Últimos eventos del event_log |

### Ejemplo de Output

```
============================================================
DATABASE STATISTICS OVERVIEW
============================================================

Projects: 1
Iterations: 1

Stories: 26
  - todo: 26

Attempts: 0
  - Successful: 0
  - Success Rate: 0%

============================================================
```

---

## Referencias

- SQLite Best Practices: https://sqlite.org/whentouse.html
- Python sqlite3: https://docs.python.org/3/library/sqlite3.html
- WAL Mode: https://sqlite.org/wal.html
