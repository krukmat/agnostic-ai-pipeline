#!/bin/bash
# Comparison experiment: Master BA vs DSPy BA
# Usage: bash scripts/run_comparison.sh [--dry-run]
#
# Prerequisites:
#   - jq installed (brew install jq)
#   - git working tree clean
#   - make ba and make dspy-ba targets exist
#   - LLM credentials configured

set -e

# ===== Configuration =====
COMPARISON_DIR="artifacts/comparison"
CONCEPTS_FILE="$COMPARISON_DIR/concepts.txt"
LOG_FILE="$COMPARISON_DIR/execution_log.jsonl"
RATE_LIMIT_SECONDS=15  # Sleep between concepts to avoid rate limits
DRY_RUN=false

# Parse arguments
if [[ "$1" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "🧪 DRY RUN MODE - No actual execution, just showing what would happen"
fi

# ===== Prerequisite checks =====
echo "🔍 Running prerequisite checks..."

# Check jq
if ! command -v jq >/dev/null 2>&1; then
  echo "❌ ERROR: jq not found. Install with: brew install jq (macOS) or apt-get install jq (Linux)"
  exit 1
fi

# Check git working tree clean
if [[ -n $(git status --porcelain) ]]; then
  echo "⚠️  WARNING: Git working tree is NOT clean!"
  echo "Uncommitted changes:"
  git status --short
  read -p "Continue anyway? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborting. Run 'git stash' first."
    exit 1
  fi
fi

# Check branches exist
if ! git rev-parse --verify main >/dev/null 2>&1; then
  echo "❌ ERROR: Branch 'main' not found"
  exit 1
fi

if ! git rev-parse --verify dspy-integration >/dev/null 2>&1; then
  echo "❌ ERROR: Branch 'dspy-integration' not found"
  echo "Create it with: git checkout -b dspy-integration main"
  exit 1
fi

echo "✅ All prerequisite checks passed"
echo ""

# ===== Create directories =====
mkdir -p "$COMPARISON_DIR/master"
mkdir -p "$COMPARISON_DIR/dspy"
mkdir -p "$COMPARISON_DIR/logs"

# ===== Concept definitions =====
CONCEPTS=(
  # Simple (1-10)
  "Un blog personal con posts y comentarios"
  "Aplicación TODO list con prioridades"
  "Calculadora de propinas para restaurantes"
  "Generador de contraseñas seguras"
  "Conversor de unidades (temperatura, longitud, peso)"
  "Registro de gastos personales"
  "Timer Pomodoro con estadísticas"
  "Biblioteca de recetas de cocina"
  "Registro de hábitos diarios"
  "Generador de códigos QR"

  # Medium (11-25)
  "E-commerce para productos artesanales con carrito de compras"
  "API REST para reservas de restaurantes con gestión de mesas"
  "Sistema de gestión de inventario para retail con alertas de stock"
  "Plataforma de cursos online con videos y evaluaciones"
  "App de seguimiento de fitness con planes de entrenamiento"
  "Sistema de tickets de soporte técnico con asignación automática"
  "CRM básico para gestión de contactos y pipeline de ventas"
  "Plataforma de freelancing con perfiles y proyectos"
  "Sistema de votaciones online con resultados en tiempo real"
  "Marketplace de servicios profesionales con ratings"
  "Sistema de reservas de espacios coworking"
  "Dashboard de métricas de negocio con gráficos interactivos"
  "Plataforma de eventos con registro y check-in"
  "Sistema de gestión de contenidos (CMS) para sitios web"
  "App de delivery de comida con tracking de pedidos"

  # Complex (26-30)
  "Plataforma SaaS multi-tenant para gestión de proyectos con roles, permisos, facturación y analytics"
  "Sistema bancario online con cuentas, transferencias, préstamos y seguridad avanzada"
  "Plataforma de telemedicina con videoconsultas, historia clínica, prescripciones y integración con laboratorios"
  "Sistema ERP para manufactura con gestión de producción, supply chain, HR y finanzas"
  "Plataforma de trading algorítmico con data en tiempo real, backtesting y ejecución automática"
)

# Save concepts list
printf "%s\n" "${CONCEPTS[@]}" > "$CONCEPTS_FILE"
echo "📋 30 concepts saved to $CONCEPTS_FILE"

# Initialize log
echo "" > "$LOG_FILE"

CURRENT_BRANCH=$(git branch --show-current)
echo "🌿 Current branch: $CURRENT_BRANCH"
echo ""

# ===== Helper function to run BA =====
run_ba() {
  local branch=$1
  local concept=$2
  local index=$3
  local output_file=$4

  echo "⏳ [$branch] Running concept $index/30..."

  if [[ "$DRY_RUN" == "true" ]]; then
    echo "   [DRY RUN] Would execute: make ba CONCEPT=\"$concept\""
    echo "   [DRY RUN] Would copy output to: $output_file"
    return 0
  fi

  START_TIME=$(date +%s)
  ERROR=""

  if [[ "$branch" == "master" ]]; then
    # Run master version
    if make ba CONCEPT="$concept" 2>"$COMPARISON_DIR/logs/${index}_master_stderr.log" 1>"$COMPARISON_DIR/logs/${index}_master_stdout.log"; then
      if [[ -f "planning/requirements.yaml" ]]; then
        cp planning/requirements.yaml "$output_file" 2>/dev/null || ERROR="Copy failed"
      else
        ERROR="No output file (planning/requirements.yaml not found)"
      fi
    else
      ERROR="make ba failed (exit code: $?)"
    fi
  else
    # Run DSPy version
    if make dspy-ba CONCEPT="$concept" 2>"$COMPARISON_DIR/logs/${index}_dspy_stderr.log" 1>"$COMPARISON_DIR/logs/${index}_dspy_stdout.log"; then
      if [[ -f "artifacts/dspy/requirements_dspy.yaml" ]]; then
        cp artifacts/dspy/requirements_dspy.yaml "$output_file" 2>/dev/null || ERROR="Copy failed"
      else
        ERROR="No output file (artifacts/dspy/requirements_dspy.yaml not found)"
      fi
    else
      ERROR="make dspy-ba failed (exit code: $?)"
    fi
  fi

  END_TIME=$(date +%s)
  DURATION=$((END_TIME - START_TIME))

  # Log metrics as JSONL
  jq -n \
    --arg branch "$branch" \
    --arg concept "$concept" \
    --argjson index "$index" \
    --argjson duration "$DURATION" \
    --arg error "$ERROR" \
    --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{branch: $branch, concept: $concept, index: $index, duration: $duration, error: $error, timestamp: $timestamp}' \
    >> "$LOG_FILE"

  if [[ -n "$ERROR" ]]; then
    echo "❌ [$branch] Error: $ERROR"
    return 1
  else
    echo "✅ [$branch] Completed in ${DURATION}s"
    return 0
  fi
}

# ===== Main execution loop =====
echo "🚀 Starting comparison experiment..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

TOTAL_CONCEPTS=${#CONCEPTS[@]}
FAILED_MASTER=0
FAILED_DSPY=0

for i in "${!CONCEPTS[@]}"; do
  INDEX=$((i + 1))
  CONCEPT="${CONCEPTS[$i]}"
  PADDED_INDEX=$(printf "%02d" $INDEX)

  echo ""
  echo "📝 Concept $INDEX/$TOTAL_CONCEPTS: ${CONCEPT:0:70}..."
  echo ""

  # Master branch
  echo "  → Switching to main..."
  if [[ "$DRY_RUN" != "true" ]]; then
    git checkout main >/dev/null 2>&1
    source .venv/bin/activate 2>/dev/null || true
  fi

  if ! run_ba "master" "$CONCEPT" "$INDEX" "$COMPARISON_DIR/master/${PADDED_INDEX}_requirements.yaml"; then
    FAILED_MASTER=$((FAILED_MASTER + 1))
  fi

  # DSPy branch
  echo "  → Switching to dspy-integration..."
  if [[ "$DRY_RUN" != "true" ]]; then
    git checkout dspy-integration >/dev/null 2>&1
    source .venv/bin/activate 2>/dev/null || true
  fi

  if ! run_ba "dspy" "$CONCEPT" "$INDEX" "$COMPARISON_DIR/dspy/${PADDED_INDEX}_requirements.yaml"; then
    FAILED_DSPY=$((FAILED_DSPY + 1))
  fi

  echo "  ✓ Pair $INDEX/$TOTAL_CONCEPTS completed"

  # Rate limiting: sleep between concepts
  if [[ $INDEX -lt $TOTAL_CONCEPTS ]]; then
    echo "  💤 Sleeping ${RATE_LIMIT_SECONDS}s to avoid rate limits..."
    if [[ "$DRY_RUN" != "true" ]]; then
      sleep $RATE_LIMIT_SECONDS
    fi
  fi
done

# Return to original branch
if [[ "$DRY_RUN" != "true" ]]; then
  git checkout "$CURRENT_BRANCH" >/dev/null 2>&1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Comparison experiment completed!"
echo ""
echo "Results:"
echo "  - Master outputs:    $COMPARISON_DIR/master/"
echo "  - DSPy outputs:      $COMPARISON_DIR/dspy/"
echo "  - Execution log:     $LOG_FILE"
echo "  - Stderr/stdout logs: $COMPARISON_DIR/logs/"
echo ""
echo "Failures:"
echo "  - Master failed:     $FAILED_MASTER/$TOTAL_CONCEPTS"
echo "  - DSPy failed:       $FAILED_DSPY/$TOTAL_CONCEPTS"
echo ""

if [[ "$DRY_RUN" != "true" ]]; then
  echo "Summary statistics:"
  jq -s 'group_by(.branch) | map({
    branch: .[0].branch,
    total: length,
    errors: map(select(.error != "")) | length,
    avg_duration: (map(.duration) | add / length | floor),
    min_duration: (map(.duration) | min),
    max_duration: (map(.duration) | max)
  })' "$LOG_FILE"
fi

echo ""
echo "Next steps:"
echo "  1. Review outputs manually: ls -lh $COMPARISON_DIR/{master,dspy}/*.yaml"
echo "  2. Run Fase 4 analysis: python scripts/analyze_comparison.py"
echo "  3. Generate report: see docs/phase4_quantitative_analysis.md"
