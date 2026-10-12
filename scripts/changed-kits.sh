#!/usr/bin/env bash
# List kits changed since a git ref, ordered by layer.
#
# Usage: scripts/changed-kits.sh <base-ref>
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: scripts/changed-kits.sh <base-ref>" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi

git diff --name-only "${1}...HEAD" | "$PY" -c '
import sys
from pathlib import Path
sys.path.insert(0, ".")
from scripts.lib.matrix import kit_index, layer_sort_key, load_matrix

index = kit_index(load_matrix())
found = []
for line in sys.stdin:
    path = line.strip().replace("\\", "/")
    parts = path.split("/")
    name = ""
    if len(parts) >= 3 and parts[0] == "data-cloud":
        name = parts[2]
    elif len(parts) == 3 and parts[0] == "manifest" and parts[1] == "kits" and parts[2].endswith(".xml"):
        name = parts[2][:-4]
    if name in index and name not in found:
        found.append(name)

found.sort(key=lambda kit: layer_sort_key(index[kit]["layer"]))
print("\n".join(found))
'
