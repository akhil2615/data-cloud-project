#!/usr/bin/env bash
# Remove KQ_* fields and managed-package components from a retrieved kit.
# Fill an empty CustomObject label. Safe to run again.
#
# Usage: scripts/cleanup-kit.sh <kit-folder>
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: scripts/cleanup-kit.sh <kit-folder>" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

"$PY" "$ROOT/scripts/cleanup_kit.py" "$1"
