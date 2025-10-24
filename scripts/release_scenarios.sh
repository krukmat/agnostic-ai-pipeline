#!/usr/bin/env bash
set -euo pipefail

# release_scenarios.sh
# Preview or execute a battery of release iterations with varied configurations.
# Usage:
#   ./scripts/release_scenarios.sh            # Preview commands only
#   ./scripts/release_scenarios.sh --run      # Execute scenarios sequentially
#   ./scripts/release_scenarios.sh --run --flush-between

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
RUN=false
FLUSH=false

while (($#)); do
  case "$1" in
    --run)
      RUN=true
      ;;
    --flush-between)
      FLUSH=true
      ;;
    --help|-h)
      cat <<USAGE
release_scenarios.sh
  --run             Execute the commands instead of just printing them.
  --flush-between   After each scenario, run FLUSH=1 make clean to reset planning/ and project/.
  --help            Show this message.
USAGE
      exit 0
      ;;
    *)
      echo "Unknown flag: $1" >&2
      exit 1
      ;;
  esac
  shift
done

scenarios=(
  "name=baseline concept='Mid-market tagging assistant' loops=2 allow_no_tests=0 tier=''"
  "name=exploratory concept='Social proof dashboard' loops=1 allow_no_tests=1 tier=''"
  "name=architect_corporate concept='Enterprise content governance' loops=2 allow_no_tests=0 tier='FORCE_ARCHITECT_TIER=corporate'"
  "name=reuse_requirements concept='Retention uplift iteration' loops=1 allow_no_tests=0 tier='' skip_ba=1 skip_po=1"
  "name=long_loop concept='Marketplace analytics expansion' loops=3 allow_no_tests=0 tier=''"
)

run_command() {
  if [[ "$RUN" == true ]]; then
    echo "→ $*"
    (cd "$ROOT_DIR" && eval "$@")
  else
    echo "$*"
  fi
}

scenario_counter=0
for entry in "${scenarios[@]}"; do
  ((scenario_counter++))
  # shellcheck disable=SC2086
  eval $entry

  echo "\n=== Scenario $scenario_counter: $name ==="

  make_env="CONCEPT=\"$concept\""
  if [[ -n "${tier:-}" ]]; then
    make_env="$tier $make_env"
  fi

  skip_ba=${skip_ba:-0}
  skip_po=${skip_po:-0}

  if [[ "$RUN" == true ]]; then
    run_command "cd $ROOT_DIR && make clean"
  else
    echo "cd $ROOT_DIR && make clean"
  fi

  if [[ "$skip_ba" != 1 ]]; then
    run_command "cd $ROOT_DIR && $make_env make ba"
  else
    echo "(skipping BA; expects planning/requirements.yaml already present)"
  fi

  if [[ "$skip_po" != 1 ]]; then
    run_command "cd $ROOT_DIR && $make_env make po"
  else
    echo "(skipping Product Owner step)"
  fi

  run_command "cd $ROOT_DIR && $make_env make plan"

  run_command "cd $ROOT_DIR && MAX_LOOPS=$loops ALLOW_NO_TESTS=$allow_no_tests $make_env make loop"

  if [[ "$FLUSH" == true ]]; then
    run_command "cd $ROOT_DIR && FLUSH=1 make clean"
  fi

done
