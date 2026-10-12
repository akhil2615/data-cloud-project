#!/usr/bin/env bash
# Poll until a deployed kit definition is visible, or time out.
# Inactive connections can leave components inactive after the definition exists.
#
# Usage: scripts/wait-for-active.sh <kit> <org-alias> [timeout-seconds]
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: scripts/wait-for-active.sh <kit> <org-alias> [timeout-seconds]" >&2
  exit 2
fi

KIT="$1"
ORG="$2"
TIMEOUT="${3:-1800}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi
START="$(date +%s)"

while true; do
  FOUND="$(sf data query --target-org "$ORG" --query "SELECT Id FROM DataPackageKitDefinition WHERE DeveloperName = '${KIT}'" --json || true)"
  COUNT="$(DEPLOY_JSON="$FOUND" "$PY" - <<'PY'
import json, os
try:
    payload = json.loads(os.environ["DEPLOY_JSON"])
except json.JSONDecodeError:
    print(0)
    raise SystemExit
result = payload.get("result") or {}
print(result.get("totalSize") or len(result.get("records") or []))
PY
)"
  if [[ "$COUNT" != "0" ]]; then
    echo "$KIT is present in $ORG. Confirm the connection is authenticated before calling it active."
    exit 0
  fi
  NOW="$(date +%s)"
  if (( NOW - START >= TIMEOUT )); then
    echo "Timed out waiting for $KIT in $ORG" >&2
    exit 2
  fi
  sleep 30
done
