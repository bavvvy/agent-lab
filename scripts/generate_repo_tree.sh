#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DATE_TAG="$(date +%Y%m%d)"
OUT_DIR="control/infra_exports"
ARCHIVE_DIR="${OUT_DIR}/Archive"
OUT_FILE="${OUT_DIR}/repo_tree_${DATE_TAG}.txt"

mkdir -p "$OUT_DIR" "$ARCHIVE_DIR"

# Enforce single active repo tree export.
shopt -s nullglob
for existing in "${OUT_DIR}"/repo_tree_*.txt; do
  [[ -f "$existing" ]] || continue
  base_name="$(basename "$existing")"
  archive_stamp="$(date +%Y-%m-%d_%H-%M)"
  archive_target="${ARCHIVE_DIR}/${archive_stamp}_${base_name}"
  if [[ -e "$archive_target" ]]; then
    n=1
    while :; do
      candidate="${ARCHIVE_DIR}/${archive_stamp}_$(printf '%02d' "$n")_${base_name}"
      if [[ ! -e "$candidate" ]]; then
        archive_target="$candidate"
        break
      fi
      n=$((n + 1))
    done
  fi
  mv "$existing" "$archive_target"
done
shopt -u nullglob

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
