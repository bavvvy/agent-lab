#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DATE_TAG="$(date +%Y%m%d)"
OUT_DIR="control/infra_exports"
BASE_FILE="${OUT_DIR}/repo_tree_${DATE_TAG}.txt"
OUT_FILE="$BASE_FILE"

mkdir -p "$OUT_DIR"

if [[ -e "$OUT_FILE" ]]; then
  n=1
  while :; do
    CANDIDATE="${OUT_DIR}/repo_tree_${DATE_TAG}_$(printf '%02d' "$n").txt"
    if [[ ! -e "$CANDIDATE" ]]; then
      OUT_FILE="$CANDIDATE"
      break
    fi
    n=$((n + 1))
  done
fi

find . -mindepth 1 -maxdepth 4 \
  \( -path './.git' -o -path './.git/*' \
     -o -path '*/.venv' -o -path '*/.venv/*' \
     -o -path '*/__pycache__' -o -path '*/__pycache__/*' \
     -o -path './outputs/capital/runs' -o -path './outputs/capital/runs/*' \
     -o -path './outputs/research/runs' -o -path './outputs/research/runs/*' \
     -o -path './outputs/capital/legacy/archive' -o -path './outputs/capital/legacy/archive/*' \
     -o -path './agents/scientist/output' -o -path './agents/scientist/output/*' \
  \) -prune -o -print \
  | sed 's#^\./##' \
  | grep -Ev '(^|/)\.(DS_Store)$' \
  | grep -Ev '^$' \
  | grep -Eiv '(^outputs/.*\.(parquet|csv)$|^agents/scientist/output/.*\.(parquet|csv)$)' \
  | LC_ALL=C sort > "$OUT_FILE"

FULL_PATH="$(realpath "$OUT_FILE")"
echo "$FULL_PATH"
sed -n '1,40p' "$OUT_FILE"
