#!/bin/sh
set -eu

MODE="full"
FIX_MODE="false"
RUN_TESTS="true"

usage() {
  cat <<'EOF'
Usage: ./scripts/check.sh [options]

Options:
  --staged      Run checks only on staged Python files (fast path)
  --fix         Auto-fix formatting/import order (black + isort)
  --no-tests    Skip pytest (applies to full mode)
  -h, --help    Show help
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --staged)
      MODE="staged"
      ;;
    --fix)
      FIX_MODE="true"
      ;;
    --no-tests)
      RUN_TESTS="false"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 2
      ;;
  esac
  shift
done

ROOT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$ROOT_DIR"

if [ -d ".venv/bin" ]; then
  PATH=".venv/bin:$PATH"
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[check] Missing required command: $1"
    exit 1
  fi
}

require_cmd black
require_cmd isort
require_cmd flake8
require_cmd git

STAGED_LIST=""
if [ "$MODE" = "staged" ]; then
  STAGED_LIST=$(mktemp)
  trap 'rm -f "$STAGED_LIST"' EXIT INT TERM
  git diff --cached --name-only --diff-filter=ACMR -- '*.py' > "$STAGED_LIST"
  if [ ! -s "$STAGED_LIST" ]; then
    echo "[check] No staged Python files."
    exit 0
  fi
fi

run_black() {
  if [ "$FIX_MODE" = "true" ]; then
    echo "[check] black (fix)"
    if [ "$MODE" = "staged" ]; then
      tr '\n' '\0' < "$STAGED_LIST" | xargs -0 black
    else
      black app tests scripts
    fi
  else
    echo "[check] black --check"
    if [ "$MODE" = "staged" ]; then
      tr '\n' '\0' < "$STAGED_LIST" | xargs -0 black --check --quiet
    else
      black --check app tests scripts
    fi
  fi
}

run_isort() {
  if [ "$FIX_MODE" = "true" ]; then
    echo "[check] isort (fix)"
    if [ "$MODE" = "staged" ]; then
      tr '\n' '\0' < "$STAGED_LIST" | xargs -0 isort
    else
      isort app tests scripts
    fi
  else
    echo "[check] isort --check-only"
    if [ "$MODE" = "staged" ]; then
      tr '\n' '\0' < "$STAGED_LIST" | xargs -0 isort --check-only --quiet
    else
      isort --check-only app tests scripts
    fi
  fi
}

run_flake8() {
  echo "[check] flake8 (F-errors)"
  if [ "$MODE" = "staged" ]; then
    tr '\n' '\0' < "$STAGED_LIST" | xargs -0 flake8 --jobs=1 --select=F --ignore=F541
  else
    flake8 app tests scripts --jobs=1 --select=F --ignore=F541
  fi
}

run_secrets_scan() {
  echo "[check] secret scan"
  SECRET_PATTERN='(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|password\s*[:=]\s*["'"'"'"][^"'"'"']{8,}["'"'"'"])'
  OUT_FILE=$(mktemp)
  trap 'rm -f "$OUT_FILE" ${STAGED_LIST:-}' EXIT INT TERM

  if command -v rg >/dev/null 2>&1; then
    if [ "$MODE" = "staged" ]; then
      tr '\n' '\0' < "$STAGED_LIST" | xargs -0 rg -n -H -I -e "$SECRET_PATTERN" -- >"$OUT_FILE" 2>/dev/null || true
    else
      rg -n -H -I -e "$SECRET_PATTERN" app tests scripts >"$OUT_FILE" 2>/dev/null || true
    fi
  else
    if [ "$MODE" = "staged" ]; then
      tr '\n' '\0' < "$STAGED_LIST" | xargs -0 grep -nHE "$SECRET_PATTERN" -- >"$OUT_FILE" 2>/dev/null || true
    else
      grep -R -nHE "$SECRET_PATTERN" app tests scripts >"$OUT_FILE" 2>/dev/null || true
    fi
  fi

  if [ -s "$OUT_FILE" ]; then
    echo "[check] Possible secrets found:"
    cat "$OUT_FILE"
    exit 1
  fi
}

run_pytest() {
  if [ "$RUN_TESTS" != "true" ] || [ "$MODE" = "staged" ]; then
    return
  fi
  require_cmd pytest
  echo "[check] pytest -q"
  pytest -q
}

run_black
run_isort
run_flake8
run_secrets_scan
run_pytest

echo "[check] OK"
