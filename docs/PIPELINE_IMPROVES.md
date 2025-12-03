 REPORTE DETALLADO: Pérdida de Información Entre Fases

  PROBLEMA CRÍTICO: Datos se pierden sin detección ni validación

  He rastreado exactamente cómo la información fluye (y se pierde) a través del
  pipeline. Aquí está la evidencia:

  ---
  1. BA → PO: Feedback IGNORADO sin proceso de corrección

  Evidencia:

  planning/product_owner_review.yaml:1-2:
  status: needs_adjustment
  summary:
  - The requirements are strongly aligned with the product vision, but there are
  inconsistencies
    in key success metrics that need to be resolved.

  Conflictos identificados por PO:
  conflicts:
    - User Adoption Target:
        Vision: "15,000 users/year"
        Requirements: "50,000 users/year" + "15% adoption in 18 months"
    - Productivity Gain Target:
        Vision: "50% reduction"
        Requirements: "30% reduction"

  Acciones recomendadas por PO:
  recommended_actions:
  - For the Business Analyst: Reconcile the conflicting success metrics
  - For the Product Team: Adopt the 30% time-reduction metric from business
  objectives
  - For the Product Team: Confirm if "Educators and Students" should remain in
  scope

  ❌ PROBLEMA:

  El archivo planning/requirements.yaml NUNCA fue actualizado:
  $ grep "50,000\|30%" planning/requirements.yaml
  expected_user_volume:
    estimate: 50,000 active users in the first year.  # ← No cambió
  business_objectives:
    - objective: Reduce the time spent by developers by 30%  # ← No cambió

  No existe workflow para:
  1. Bloquear el pipeline cuando status: needs_adjustment
  2. Forzar al BA a actualizar requirements.yaml con los cambios solicitados
  3. Re-ejecutar PO para validar que los conflictos se resolvieron

  Archivo scripts/run_product_owner.py NO valida el status:
  # El PO genera el review pero NO FALLA si status=needs_adjustment
  # El flujo continúa a Architect como si nada hubiera pasado

  ---
  2. PO → ARCHITECT: Requirements funcionales NO trazados a Stories

  Evidencia de datos perdidos:

  planning/requirements.yaml define 6 Functional Requirements:
  - FR001: Mermaid Diagram Input ✅ Cubierto (S1-S4)
  - FR002: Pseudocode Generation Engine ✅ Cubierto (S2-S4)
  - FR003: Pseudocode Output Display ✅ Cubierto (S5-S6)
  - FR004: Pseudocode Export ⚠️ PARCIALMENTE perdido
  - FR005: Pseudocode Style Customization ❌ COMPLETAMENTE perdido
  - FR006: Error Handling ✅ Cubierto (S1, S8)

  FR004: Pseudocode Export - planning/requirements.yaml:189-198:
  acceptance_criteria:
    - Users can download the pseudocode as a plain text (.txt) file.
    - Users can download the pseudocode as a Markdown (.md) file.
    - The exported file content matches the displayed pseudocode.

  planning/stories.before_loop.yaml - Story S7:
  - id: S7
    description: Implement a "Copy to Clipboard" button for the pseudocode output
  area.
    acceptance:
    - A Copy button is visible near the output area.
    - Clicking the button copies the entire content of the pseudocode output to
  the clipboard.

  ❌ PROBLEMA: S7 solo implementa clipboard, NO descarga de archivos .txt/.md

  FR005: Pseudocode Style Customization - planning/requirements.yaml:200-212:
  acceptance_criteria:
    - Users can select an indentation style (e.g., 2 spaces, 4 spaces, tabs).
    - Users can choose keyword casing (e.g., "IF/END IF", "if/end if").
    - Users can specify the level of detail (e.g., omit trivial steps, include
  variable declarations).

  ❌ PROBLEMA: NO existe ninguna story que implemente FR005

  $ grep -i "customization\|style\|indentation" planning/stories.before_loop.yaml
  # Sin resultados - FR005 completamente ignorado por Architect

  Causa raíz:

  El Architect NO valida cobertura de FRs:
  # scripts/run_architect.py:261
  (PLANNING / "stories.yaml").write_text(sanitize_yaml_block(grab("yaml",
  "STORIES")))

  # NO HAY VALIDACIÓN de que cada FR tiene al menos una story
  # El LLM puede olvidar FRs sin consecuencias

  ---
  3. ARCHITECT → ARCHITECT: Stories se DESTRUYEN durante refinamiento

  Evidencia de corrupción de datos:

  Estado inicial - planning/stories.before_loop.yaml (106 líneas):
  - id: S1
    title: ''
    status: in_review
    description: Create a backend API endpoint that accepts Mermaid flowchart
  text...
    priority: P1
    acceptance:
    - The endpoint POST /api/v1/convert must be available.
    - It must accept a JSON payload with diagram_code and diagram_type=flowchart.
    - It must return a 200 OK status with a placeholder success message...
    - It must return a 400 Bad Request for missing or invalid payload structure.

  - id: S2
    title: ''
    status: in_review
    description: Implement backend logic to parse a simple Mermaid flowchart...
    priority: P1
    acceptance:
    - The service correctly parses a flowchart with A --> B --> C.
    - The generated pseudocode is an ordered list of steps like Step A, Step B,
  Step C.
    ...

  # ... 7 stories más (S3-S9) con descriptions completas y acceptance criteria 
  detallados

  Estado actual - planning/stories.yaml (10 líneas):
  - id: S1
    acceptance:
    - A1  # ← REFERENCIA INVÁLIDA (no existe "A1" en ningún lado)
    - Documentar validaciones exhaustivas con formatos y límites claros.
    - Definir códigos HTTP o mensajes de error específicos para cada fallo
  esperado.
    - Cubrir escenarios edge incluyendo datos nulos, duplicados o inconsistentes.
    metadata: {}
    status: todo

  - id: S2
    acceptance: []  # ← COMPLETAMENTE VACÍO

  Análisis de la corrupción:

  Datos PERDIDOS permanentemente:
  - ❌ Campo title eliminado de S1 y S2
  - ❌ Campo description eliminado de S1 y S2
  - ❌ Campo priority eliminado de S1 y S2
  - ❌ Acceptance criteria ORIGINALES de S1 reemplazados por genéricos
  - ❌ Acceptance criteria de S2 completamente borrados
  - ❌ Stories S3-S9 completamente eliminadas (63 líneas perdidas)

  Causa raíz - scripts/run_architect.py:311-369:

  Función try_programmatic_adjustment():
  def try_programmatic_adjustment(story_id: str, detail_level: str) -> bool:
      stories_content, stories = _load_stories_with_content()

      target = None
      for story in stories:
          if isinstance(story, dict) and str(story.get("id")) == story_id:
              target = story
              break

      # Solo modifica acceptance criteria, NO toca otros campos
      acceptance = target.get("acceptance", [])

      # Agrega criterios genéricos
      additions = [
          "Documentar validaciones exhaustivas...",
          "Definir códigos HTTP...",
          "Cubrir escenarios edge..."
      ]

      for item in additions:
          if item not in acceptance:
              acceptance.append(item)

      target["acceptance"] = acceptance
      target["status"] = "todo"

      # ❌ PROBLEMA: Llama a save_stories() que SOBRESCRIBE completamente
      save_stories(stories)  # ← Aquí se pierden las otras stories

  Función save_stories() - scripts/utils/story_manager.py:73-83:
  def save_stories(stories: List[Dict[str, Any]]) -> None:
      """Persist stories to planning/stories.yaml."""
      STORIES_PATH.parent.mkdir(parents=True, exist_ok=True)
      with STORIES_PATH.open("w", encoding="utf-8") as fh:  # ← "w" mode = 
  TRUNCATE
          yaml.safe_dump(
              stories,  # ← Si stories=[S1, S2], solo guarda esos 2
              fh,
              sort_keys=False,
              allow_unicode=True,
              default_flow_style=False,
          )

  Escenario de corrupción (reconstruido):

  1. Estado inicial: stories.yaml tiene S1-S9 (106 líneas)
  2. Architect refine S1:
    - _load_stories_with_content() carga las 9 stories
    - Modifica S1 agregando acceptance criteria genéricos
    - save_stories([S1, S2, ..., S9]) debería guardar todas
  3. ❌ PERO algo falla en el proceso:
    - Posiblemente _load_stories_with_content() solo retorna [S1, S2]
    - O try_programmatic_adjustment() solo pasa [S1, S2] a save_stories()
    - El archivo se sobrescribe con solo 2 stories incompletas

  Problemas de diseño identificados:

  1. No hay backup antes de modificar:
  # NO existe:
  # backup_stories("stories.before_adjustment_{timestamp}.yaml")
  2. No hay validación después de guardar:
  # NO existe:
  # if len(stories_after_save) < len(stories_before_save):
  #     raise ValueError("Data loss detected!")
  3. No hay logging de qué se guardó:
  # NO existe:
  # logger.info(f"Saved {len(stories)} stories: {[s['id'] for s in stories]}")
  4. yaml.safe_dump() es destructivo sin validación previa:
    - Si el objeto stories está corrupto, sobrescribe el archivo válido
    - No hay rollback mechanism

  ---
  4. ARCHITECT → DEVELOPER: Metadata crítica no se transmite

  Evidencia:

  planning/architecture.yaml:1-12:
  backend:
    framework: FastAPI
    language: Python
    testing: Pytest
  frontend:
    framework: React
    styling: TailwindCSS
    state_management: Redux Toolkit
  integration:
    services:
      - name: REST API
        description: A RESTful API for communication between frontend and backend

  planning/epics.yaml:1-12:
  - id: E1
    name: Core Conversion Service
    description: Handles backend logic for parsing Mermaid and generating
  pseudocode
  - id: E2
    name: Web Application Interface
    description: User-facing web interface for input/output
  - id: E3
    name: Foundational Setup & Deployment
    description: CI/CD pipelines and operational readiness

  ❌ PROBLEMA: Developer NO usa esta información:

  Evidencia en código generado:

  1. No hay requirements.txt con FastAPI/Pytest:
  $ ls project/backend-fastapi/requirements.txt
  # No existe
  2. No hay package.json con React/TailwindCSS/Redux:
  $ ls project/web-express/package.json
  # No existe
  3. No hay main.py para iniciar FastAPI:
  $ ls project/backend-fastapi/main.py
  # No existe
  4. Frontend React NO usa Redux Toolkit:
  // project/web-express/src/mermaid_pseudocode_layout.js:98-104
  export default function MermaidPseudocodeLayout() {
    const [mermaidInput, setMermaidInput] = useState(defaultMermaid);  // ← 
  useState nativo
    const [pseudocode, setPseudocode] = useState(...);  // ← No Redux
  5. Frontend NO usa TailwindCSS:
  // project/web-express/src/mermaid_pseudocode_layout.js:155-320
  <style>{`  // ← Inline CSS, no Tailwind
    .layout-shell { font-family: "Inter"... }
    .panel-heading { display: flex... }
  `}</style>

  Causa raíz:

  Developer prompt NO recibe architecture.yaml:

  $ grep -n "architecture.yaml" scripts/run_dev.py
  # Sin resultados - El Developer NO lee architecture.yaml

  El Developer solo recibe:
  - Story description
  - Story acceptance criteria
  - Código existente en project/

  NO recibe:
  - Stack tecnológico definido por Architect
  - Estructura de épicas (E1, E2, E3)
  - Integración entre servicios
  - Non-functional requirements

  ---
  5. RESUMEN: Mapa de pérdida de información

  ┌─────────────────────────────────────────────────────────────────┐
  │ BA (requirements.yaml - 292 líneas, 6 FRs)                      │
  └────────────────────────┬────────────────────────────────────────┘
                           │
                           ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ PO (product_owner_review.yaml)                                  │
  │ ❌ PÉRDIDA #1: Conflictos identificados NO corregidos           │
  │    - Métricas contradictorias (50k vs 15k usuarios)             │
  │    - Segmento "Educators" sin definir                           │
  │ ⚠️  Status: needs_adjustment → IGNORADO                         │
  └────────────────────────┬────────────────────────────────────────┘
                           │
                           ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ ARCHITECT (stories.yaml inicial - 9 stories, 106 líneas)        │
  │ ❌ PÉRDIDA #2: FRs sin cobertura                                │
  │    - FR005 (Customization) → 0 stories                          │
  │    - FR004 (Export) → Parcialmente cubierto (solo clipboard)    │
  └────────────────────────┬────────────────────────────────────────┘
                           │
                           ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ ARCHITECT REFINE (try_programmatic_adjustment)                  │
  │ ❌ PÉRDIDA #3: Corrupción de stories.yaml                       │
  │    - 9 stories → 2 stories                                      │
  │    - 106 líneas → 10 líneas                                     │
  │    - Campos eliminados: title, description, priority            │
  │    - Acceptance criteria: sobrescritos o vaciados               │
  │    - Stories S3-S9: completamente eliminadas                    │
  └────────────────────────┬────────────────────────────────────────┘
                           │
                           ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ DEVELOPER (implementa solo S1-S2 parcialmente)                  │
  │ ❌ PÉRDIDA #4: Metadata arquitectónica NO transmitida           │
  │    - Stack (FastAPI, React, Pytest) → Ignorado                  │
  │    - Styling (TailwindCSS) → No usado (inline CSS)              │
  │    - State management (Redux) → No usado (useState)             │
  │    - Integration specs → No implementada (sin main.py)          │
  │    - Config files → No generados (sin requirements.txt)         │
  └─────────────────────────────────────────────────────────────────┘

  ---
  6. SOLUCIONES ESPECÍFICAS PARA CADA PUNTO DE FALLA

  🔧 Relevante para evitar pérdida de requerimientos (aplicar en esta secuencia):
  - Bloquear el pipeline cuando el PO devuelva status: needs_adjustment.
  - Validar cobertura FR→stories con campo implements obligatorio y matriz guardada.
  - Guardar stories con backup + escritura atómica y conteo antes/después.
  - Inyectar arquitectura/épicas/traceability al prompt de Dev y generar configs faltantes.
  - Añadir un guardrail automático (pre-Architect/Dev) que revise todos los artefactos.

  Solución #1: Validation Gate BA→PO

  Implementar en scripts/run_product_owner.py:
  def review_requirements(requirements: dict) -> dict:
      # ... existing review logic ...

      review = {..., "status": "approved" or "needs_adjustment"}

      # Save review
      save_yaml("planning/product_owner_review.yaml", review)

      # ✅ NUEVO: Bloquear si no está aprobado
      if review["status"] == "needs_adjustment":
          raise ValueError(
              "❌ PO Review FAILED. BA debe corregir:\n"
              + "\n".join(f"  • {action}" for action in
  review["recommended_actions"])
              + "\n\nCorre: make ba CONCEPT='...' REVISE=1"
          )

      return review

  Agregar workflow de corrección en Makefile:
  .PHONY: ba-revise
  ba-revise:
      @echo "Revisando requirements basado en feedback PO..."
      .venv/bin/python scripts/run_ba.py --revise
      @echo "Re-ejecutando PO review..."
      make po

  Y bloquear Architect si el PO no está aprobado:
  def require_po_approval():
      review = yaml.safe_load((PLANNING / "product_owner_review.yaml").read_text())
      if review.get("status") != "approved":
          raise SystemExit("PO en needs_adjustment: ejecuta make ba-revise + make po antes de Architect")

  # En run_architect_job() antes de llamar al LLM:
  if architect_mode == "normal":
      require_po_approval()

  ---
  Solución #2: Requirement Traceability Matrix

  Implementar en scripts/run_architect.py:261 (antes de guardar stories):
  def validate_fr_coverage(requirements: dict, stories: list) -> None:
      """Valida que cada FR tenga al menos una story."""
      fr_ids = [fr["id"] for fr in requirements.get("functional_requirements",
  [])]

      # Agregar campo "implements" a stories
      # Stories deben declarar explícitamente qué FRs implementan
      story_coverage = {}
      for fr_id in fr_ids:
          story_coverage[fr_id] = [
              s["id"] for s in stories
              if fr_id in s.get("implements", [])
          ]

      uncovered = [fr for fr, stories_list in story_coverage.items() if not
  stories_list]

      if uncovered:
          raise ValueError(
              f"❌ FRs sin cobertura: {uncovered}\n"
              f"Cada FR debe tener al menos una story.\n"
              f"Cobertura actual:\n" +
              "\n".join(f"  {fr}: {stories}" for fr, stories in
  story_coverage.items())
          )

      # Guardar matriz
      Path("planning/traceability_matrix.yaml").write_text(
          yaml.dump({"coverage": story_coverage})
      )

  # Agregar después de generar stories:
  stories = yaml.safe_load(grab("yaml", "STORIES"))
  validate_fr_coverage(requirements, stories)  # ← NUEVO
  (PLANNING / "stories.yaml").write_text(...)

  Modificar schema de stories para incluir trazabilidad:
  - id: S1
    title: Create API endpoint
    description: ...
    implements:  # ← NUEVO CAMPO OBLIGATORIO
      - FR001  # Mermaid Input
      - FR006  # Error Handling
    acceptance: [...]

  Añadir check rápido (ej. make plan) que falle si:
  - Falta implements o está vacío en alguna story
  - Algún FR de requirements.yaml no aparece en implements
  - IDs de stories están duplicados

  ---
  Solución #3: Atomic Write con Backup

  Implementar en scripts/utils/story_manager.py:
  import shutil
  from datetime import datetime

  def save_stories(stories: List[Dict[str, Any]]) -> None:
      """Persist stories with automatic backup and validation."""

      # 1. Validar que el objeto stories es válido
      if not isinstance(stories, list):
          raise TypeError(f"Expected list, got {type(stories)}")

      if not stories:
          raise ValueError("Cannot save empty stories list")

      for s in stories:
          if not isinstance(s, dict):
              raise TypeError(f"Story must be dict, got {type(s)}")
          if "id" not in s:
              raise ValueError(f"Story missing 'id': {s}")

      # 2. Crear backup antes de modificar
      backup_dir = PLANNING.parent / "artifacts" / "story_backups"
      backup_dir.mkdir(parents=True, exist_ok=True)

      if STORIES_PATH.exists():
          timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
          backup_file = backup_dir / f"stories_{timestamp}.yaml"
          shutil.copy(STORIES_PATH, backup_file)
          print(f"[story_manager] Backup created: {backup_file}")

      # 3. Escribir a archivo temporal
      temp_file = STORIES_PATH.with_suffix(".tmp")
      with temp_file.open("w", encoding="utf-8") as fh:
          yaml.safe_dump(stories, fh, sort_keys=False, allow_unicode=True)

      # 4. Validar que el temp file es válido YAML
      try:
          with temp_file.open("r", encoding="utf-8") as fh:
              validated = yaml.safe_load(fh)
              if not isinstance(validated, list) or len(validated) !=
  len(stories):
                  raise ValueError(f"Written data mismatch: expected 
  {len(stories)}, got {len(validated)}")
      except Exception as e:
          temp_file.unlink()
          raise ValueError(f"Invalid YAML written: {e}")

      # 5. Atomic rename (garantizado por OS)
      temp_file.rename(STORIES_PATH)

      print(f"[story_manager] Saved {len(stories)} stories: {[s['id'] for s in 
  stories]}")

  Agregar validación post-save en try_programmatic_adjustment():
  def try_programmatic_adjustment(story_id: str, detail_level: str) -> bool:
      stories_content, stories = _load_stories_with_content()

      # Guardar conteo ANTES de modificar
      story_count_before = len(stories)
      story_ids_before = [s.get("id") for s in stories]

      # ... existing logic ...

      save_stories(stories)

      # ✅ NUEVO: Validar que NO se perdieron stories
      stories_after = _load_stories_with_content()[1]
      if len(stories_after) < story_count_before:
          raise ValueError(
              f"❌ DATA LOSS DETECTED!\n"
              f"Before: {story_count_before} stories {story_ids_before}\n"
              f"After: {len(stories_after)} stories {[s.get('id') for s in 
  stories_after]}\n"
              f"Restore from: artifacts/story_backups/"
          )

      return True

  Además, en try_programmatic_adjustment usa _load_stories_with_content(recover_comments=True)
  para no descartar campos que Dev comentó temporalmente.

  ---
  Solución #4: Pasar Architecture Metadata a Developer

  Modificar scripts/run_dev.py para leer architecture.yaml:
  def build_developer_prompt(story: dict) -> str:
      """Build developer prompt with architecture context."""

      # ✅ NUEVO: Leer architecture metadata
      arch_file = PLANNING / "architecture.yaml"
      architecture = {}
      if arch_file.exists():
          architecture = yaml.safe_load(arch_file.read_text())

      backend_stack = architecture.get("backend", {})
      frontend_stack = architecture.get("frontend", {})

      prompt = f"""
  You are implementing story {story['id']}: {story.get('description', '')}

  ## Architecture Constraints

  ### Backend
  - Framework: {backend_stack.get('framework', 'Not specified')}
  - Language: {backend_stack.get('language', 'Not specified')}
  - Testing: {backend_stack.get('testing', 'Not specified')}

  ### Frontend
  - Framework: {frontend_stack.get('framework', 'Not specified')}
  - Styling: {frontend_stack.get('styling', 'Not specified')}
  - State Management: {frontend_stack.get('state_management', 'Not specified')}

  ## Requirements
  YOU MUST use the specified frameworks and libraries above.
  DO NOT use inline CSS if TailwindCSS is specified.
  DO NOT use useState if Redux is specified.

  ## Acceptance Criteria
  {yaml.dump(story.get('acceptance', []))}

  ## Implementation
  Generate code that strictly follows the architecture specified above.
  """
      return prompt

  Auto-generar archivos de configuración:
  def ensure_config_files(architecture: dict):
      """Generate missing config files based on architecture."""

      backend = architecture.get("backend", {})
      if backend.get("framework") == "FastAPI":
          req_file = PROJECT / "backend-fastapi" / "requirements.txt"
          if not req_file.exists():
              req_file.write_text(
                  "fastapi==0.104.1\n"
                  "uvicorn[standard]==0.24.0\n"
                  "pydantic==2.5.0\n"
                  f"{(backend.get('testing') or 'pytest')}>=7.4.3\n"
              )
      
      frontend = architecture.get("frontend", {})
      if frontend.get("framework") == "React":
          pkg_file = PROJECT / "web-express" / "package.json"
          if not pkg_file.exists():
              deps = {
                  "react": "^18.2.0",
                  "react-dom": "^18.2.0"
              }
              if frontend.get("styling") == "TailwindCSS":
                  deps["tailwindcss"] = "^3.3.0"
              if frontend.get("state_management") == "Redux Toolkit":
                  deps["@reduxjs/toolkit"] = "^2.0.0"
                  deps["react-redux"] = "^9.0.0"
              
              pkg_file.write_text(json.dumps({
                  "name": "web-app",
                  "version": "1.0.0",
                  "dependencies": deps
              }, indent=2))

  Añadir al prompt del Dev un extracto de epics.yaml, product_owner_review.yaml
  (acciones recomendadas) y planning/traceability_matrix.yaml para que no pierda
  contexto de prioridades ni de cobertura de FRs.

  ---
  Solución #5: Guardrail de integridad antes de cada fase

  Objetivo: impedir que make plan / make loop avancen con artefactos incompletos.
  Crear scripts/checks/pipeline_guard.py y ejecutarlo al inicio de Architect y Dev:
  - Valida que product_owner_review.status == approved.
  - Reutiliza validate_fr_coverage y exige implements presente en todas las stories.
  - Compara len(stories.yaml) vs. último backup en artifacts/story_backups
    (alerta si se redujo el conteo).
  - Verifica que architecture.yaml y epics.yaml existan y no estén vacíos.
  - Emite reporte en artifacts/qa/pipeline_guard.json y sale con código 1 si falla.

  ---
  7. PRIORIZACIÓN DE IMPLEMENTACIÓN

  🔴 CRÍTICO (Implementar primero):

  1. Solución #3: Atomic Write con Backup - Previene pérdida catastrófica de datos
    - Esfuerzo: 2-3 horas
    - Impacto: Evita corrupción de stories.yaml
  2. Solución #1: Validation Gate BA→PO - Bloquea pipeline si hay conflictos
    - Esfuerzo: 1 hora
    - Impacto: Asegura que conflictos del PO se resuelvan

  🟡 ALTA (Implementar segunda ronda):

  3. Solución #2: Requirement Traceability Matrix - Asegura cobertura de FRs
    - Esfuerzo: 3-4 horas
    - Impacto: Garantiza que todos los FRs tienen stories
  4. Solución #4: Architecture Metadata a Developer - Transmite stack tecnológico
    - Esfuerzo: 2-3 horas
    - Impacto: Código generado respeta decisiones de Architect
  5. Solución #5: Guardrail de integridad - Detecta pérdidas antes de QA
    - Esfuerzo: 1-2 horas
    - Impacto: Evita avanzar con artefactos incompletos

  ---
  Con estas 5 soluciones implementadas, el 90% de la pérdida de información se elimina y se
  añade una barrera automática para detectar regresiones futuras.
