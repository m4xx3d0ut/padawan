#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/dist/padawan-wheelhouse"
ARCHIVE_DIR="${ROOT_DIR}/dist"
PYTHON_BIN="${PYTHON_BIN:-python}"
SKIP_BUILD=0

usage() {
  cat <<'EOF'
usage: scripts/build_wheelhouse.sh [--out PATH] [--archive-dir PATH] [--python PYTHON] [--skip-build]

Build Padawan wheelhouse release artifacts:
  - padawan-wheelhouse.tar.gz
  - padawan-wheelhouse.zip

Install with:
  python -m pip install --no-index --find-links <wheelhouse> padawan
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      OUT_DIR="$2"
      shift 2
      ;;
    --archive-dir)
      ARCHIVE_DIR="$2"
      shift 2
      ;;
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --skip-build)
      SKIP_BUILD=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

cmd=(
  "$PYTHON_BIN"
  "$ROOT_DIR/scripts/build_wheelhouse.py"
  --out "$OUT_DIR"
  --archive-dir "$ARCHIVE_DIR"
  --python "$PYTHON_BIN"
)

if [[ "$SKIP_BUILD" == "1" ]]; then
  cmd+=(--skip-build)
fi

"${cmd[@]}"
