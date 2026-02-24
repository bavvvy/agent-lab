#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DATE_TAG="$(date +%Y%m%d)"
OUT_DIR="control/infra_exports"
OUT_FILE="${OUT_DIR}/repo_tree_${DATE_TAG}.txt"

mkdir -p "$OUT_DIR"

find . -mindepth 1 -maxdepth 4 \
  \( -path './.git' -o -path './.git/*' \
     -o -path '*/.venv' -o -path '*/.venv/*' \
     -o -path '*/__pycache__' -o -path '*/__pycache__/*' \
     -o -path './outputs/capital/runs' -o -path './outputs/capital/runs/*' \
     -o -path './outputs/research/runs' -o -path './outputs/research/runs/*' \
     -o -path './agents/scientist/output' -o -path './agents/scientist/output/*' \
  \) -prune -o -print \
  | sed 's#^\./##' \
  | grep -Ev '(^|/)\.(DS_Store)$' \
  | grep -Ev '^$' \
  | grep -Eiv '(^outputs/.*\.(parquet|csv)$|^agents/scientist/output/.*\.(parquet|csv)$)' \
  | LC_ALL=C sort > "$OUT_FILE"

echo "$OUT_FILE"
sed -n '1,40p' "$OUT_FILE"
