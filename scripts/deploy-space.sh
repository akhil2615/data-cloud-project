#!/usr/bin/env bash
# Deploy every applicable kit for one data space, in that space's order.
# Stops on the first failure. Completed kits are recorded in deployment-state/.
#
# Usage: scripts/deploy-space.sh <space> <org-alias> [--resume]
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: scripts/deploy-space.sh <space> <org-alias> [--resume]" >&2
  exit 2
fi

SPACE="$1"
ORG="$2"
RESUME=0
if [[ "${3:-}" == "--resume" ]]; then
  RESUME=1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi
LEDGER="$ROOT/deployment-state/${ORG}-${SPACE}.json"
mkdir -p "$ROOT/deployment-state"

"$PY" - "$SPACE" "$ORG" "$LEDGER" "$RESUME" <<'PY' > "$ROOT/deployment-state/${ORG}-${SPACE}.plan"
import json, sys
from pathlib import Path
sys.path.insert(0, ".")
from scripts.lib.matrix import kits_for, load_matrix

space_key, org, ledger_path, resume = sys.argv[1:]
matrix = load_matrix()
space = matrix["spaces"].get(space_key)
if not space:
    raise SystemExit(f"Unknown space {space_key}")
done = set()
path = Path(ledger_path)
if resume == "1" and path.is_file():
    done = set(json.loads(path.read_text(encoding="utf-8")).get("completed") or [])
for item in kits_for(space, matrix.get("gates")):
    if item.get("gate"):
        print(f"gate\t{item['layer']}\t{item.get('name') or item['layer']}")
        continue
    if item["kit"] in done:
        print(f"skip\t{item['layer']}\t{item['kit']}")
        continue
    print(f"kit\t{item['layer']}\t{item['kit']}")
PY

while IFS=$'\t' read -r KIND LAYER NAME; do
  if [[ "$KIND" == "skip" ]]; then
    echo "skip $NAME"
    continue
  fi
  if [[ "$KIND" == "gate" ]]; then
    echo "GATE ${LAYER} (${NAME}): complete this post-deployment step, then rerun with --resume"
    "$PY" "$ROOT/scripts/update-space-status.py" --mark "$SPACE" "$LAYER" "gate"
    exit 20
  fi
  echo "deploy $NAME ($LAYER) to $ORG"
  "$ROOT/scripts/deploy-kit.sh" "$NAME" "$ORG"
  "$ROOT/scripts/wait-for-active.sh" "$NAME" "$ORG"
  "$PY" - "$LEDGER" "$NAME" "$LAYER" <<'PY'
import json, sys
from pathlib import Path
path, name, layer = sys.argv[1:]
file = Path(path)
data = json.loads(file.read_text(encoding="utf-8")) if file.is_file() else {"completed": []}
data.setdefault("completed", [])
if name not in data["completed"]:
    data["completed"].append(name)
data["lastLayer"] = layer
data["lastKit"] = name
file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
  "$PY" "$ROOT/scripts/update-space-status.py" --mark "$SPACE" "$LAYER" "deployed"
done < "$ROOT/deployment-state/${ORG}-${SPACE}.plan"

echo "Space $SPACE finished in $ORG"
