#!/bin/bash
# Comparison experiment: Master BA vs DSPy BA
# Usage: bash scripts/run_comparison.sh [--dry-run]
#
# Prerequisites:
#   - jq installed
#   - git working tree clean (or user confirms continuation)
#   - make ba / make dspy-ba targets available
#   - LLM credentials and providers configurados

set -e

COMPARISON_DIR="artifacts/comparison"
CONCEPTS_FILE="$COMPARISON_DIR/concepts.txt"
LOG_FILE="$COMPARISON_DIR/execution_log.jsonl"
RATE_LIMIT_SECONDS=15
DRY_RUN=false

if [[ "$1" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "🧪 DRY RUN MODE - No actual execution, just showing what would happen"
fi

echo "🔍 Running prerequisite checks..."

if ! command -v jq >/dev/null 2>&1; then
  echo "❌ ERROR: jq not found. Install with 'brew install jq' or 'apt-get install jq'."
  exit 1
fi

if [[ -n $(git status --porcelain) ]]; then
  echo "⚠️  WARNING: Git working tree is NOT clean!"
  git status --short
  read -p "Continue anyway? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborting. Stash or commit changes first."
    exit 1
  fi
fi

echo "✅ All prerequisite checks passed"
echo

mkdir -p "$COMPARISON_DIR/master" "$COMPARISON_DIR/dspy" "$COMPARISON_DIR/logs"

CONCEPTS=(
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
  "Plataforma SaaS multi-tenant para gestión de proyectos con roles, permisos, facturación y analytics"
  "Sistema bancario online con cuentas, transferencias, préstamos y seguridad avanzada"
  "Plataforma de telemedicina con videoconsultas, historia clínica, prescripciones e integración con laboratorios"
  "Sistema ERP para manufactura con producción, supply chain, RRHH y finanzas"
  "Plataforma de trading algorítmico con data en tiempo real, backtesting y ejecución automática"
)

printf "%s\n" "${CONCEPTS[@]}" > "$CONCEPTS_FILE"
echo "📋 30 concepts saved to $CONCEPTS_FILE"

echo "" > "$LOG_FILE"

CURRENT_BRANCH=$(git branch --show-current)
echo "🌿 Current branch: $CURRENT_BRANCH"
echo

run_ba() {
  local branch=$1
  local concept=$2
  local index=$3
  local output_file=$4

  echo "⏳ [$branch] Running concept $index/30..."

  if [[ "$DRY_RUN" == "true" ]]; then
    echo "   [DRY RUN] Would execute make target for branch $branch"
    echo "   [DRY RUN] Would copy output to $output_file"
    return 0
  fi

  local start_time=$(date +%s)
  local error=""

  if [[ "$branch" == "master" ]]; then
    if make ba CONCEPT="$concept" \
      1>"$COMPARISON_DIR/logs/${index}_master_stdout.log" \
      2>"$COMPARISON_DIR/logs/${index}_master_stderr.log"; then
      if [[ -f "planning/requirements.yaml" ]]; then
        cp planning/requirements.yaml "$output_file" || error="Copy failed"
      else
        error="planning/requirements.yaml not found"
      fi
    else
      error="make ba failed"
    fi
  else
    if make dspy-ba CONCEPT="$concept" \
      1>"$COMPARISON_DIR/logs/${index}_dspy_stdout.log" \
      2>"$COMPARISON_DIR/logs/${index}_dspy_stderr.log"; then
      if [[ -f "artifacts/dspy/requirements_dspy.yaml" ]]; then
        cp artifacts/dspy/requirements_dspy.yaml "$output_file" || error="Copy failed"
      else
        error="artifacts/dspy/requirements_dspy.yaml not found"
      fi
    else
      error="make dspy-ba failed"
    fi
  fi

  local end_time=$(date +%s)
  local duration=$((end_time - start_time))

  jq -n \
    --arg branch "$branch" \
    --arg concept "$concept" \
    --argjson index "$index" \
    --argjson duration "$duration" \
    --arg error "$error" \
    --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{branch: $branch, concept: $concept, index: $index, duration: $duration, error: $error, timestamp: $timestamp}' \
    >> "$LOG_FILE"

  if [[ -n "$error" ]]; then
    echo "❌ [$branch] Error: $error"
    return 1
  else
    echo "✅ [$branch] Completed in ${duration}s"
    return 0
  fi
}

echo "🚀 Starting comparison experiment..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

TOTAL_CONCEPTS=${#CONCEPTS[@]}
FAILED_MASTER=0
FAILED_DSPY=0

for i in "${!CONCEPTS[@]}"; do
  INDEX=$((i + 1))
  CONCEPT="${CONCEPTS[$i]}"
  PADDED_INDEX=$(printf "%02d" "$INDEX")

  echo ""
  echo "📝 Concept $INDEX/$TOTAL_CONCEPTS: ${CONCEPT:0:70}..."
  echo ""

  if ! run_ba "master" "$CONCEPT" "$INDEX" "$COMPARISON_DIR/master/${PADDED_INDEX}_requirements.yaml"; then
    FAILED_MASTER=$((FAILED_MASTER + 1))
  fi

  if ! run_ba "dspy" "$CONCEPT" "$INDEX" "$COMPARISON_DIR/dspy/${PADDED_INDEX}_requirements.yaml"; then
    FAILED_DSPY=$((FAILED_DSPY + 1))
  fi

  if [[ "$INDEX" -lt "$TOTAL_CONCEPTS" ]]; then
    echo "  💤 Sleeping ${RATE_LIMIT_SECONDS}s to avoid rate limits..."
    if [[ "$DRY_RUN" != "true" ]]; then
      sleep "$RATE_LIMIT_SECONDS"
    fi
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Comparison experiment completed!"
echo ""
echo "Results:"
echo "  - Master outputs:    $COMPARISON_DIR/master/"
echo "  - DSPy outputs:      $COMPARISON_DIR/dspy/"
echo "  - Execution log:     $LOG_FILE"
echo "  - Logs (stdout/err): $COMPARISON_DIR/logs/"
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
    errors: (map(select(.error != "")) | length),
    success_rate: ((length - (map(select(.error != "")) | length)) / length * 100),
    avg_duration: (map(.duration) | add / length),
    min_duration: (map(.duration) | min),
    max_duration: (map(.duration) | max)
  })' "$LOG_FILE"
fi

echo ""
echo "Next steps:"
echo "  1. Review outputs manually: ls -lh $COMPARISON_DIR/{master,dspy}/*.yaml"
echo "  2. Ejecutar análisis de Fase 4 (cuando esté disponible)."
echo "  3. Documentar resultados en docs/phase3_comparison_experiment.md."
