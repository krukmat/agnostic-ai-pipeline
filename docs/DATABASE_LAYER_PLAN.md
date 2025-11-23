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
6. **Fase 2**: Dual-write en orchestrator y roles
7. **Fase 3**: Script de verificación y 5+ iteraciones de prueba
8. **Fase 4**: Cut-over a DB como source of truth
9. **Fase 5**: CLI de observabilidad y backups automáticos

---

## Referencias

- SQLite Best Practices: https://sqlite.org/whentouse.html
- Python sqlite3: https://docs.python.org/3/library/sqlite3.html
- WAL Mode: https://sqlite.org/wal.html
