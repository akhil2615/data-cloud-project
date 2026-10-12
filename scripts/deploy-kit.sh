#!/usr/bin/env bash
# Deploy one retrieved kit, then prove the components exist.
#
# Usage: scripts/deploy-kit.sh <kit> <org-alias> [--validate] [--method source-dir|connect-api]
#
# --validate uses sf project deploy start --dry-run.
# source-dir is the default. connect-api calls the Data Kit deploy endpoint and
# is for the pilot only; it installs a kit that is already in the target org.
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: scripts/deploy-kit.sh <kit> <org-alias> [--validate] [--method source-dir|connect-api]" >&2
  exit 2
fi

KIT="$1"
ORG="$2"
shift 2
VALIDATE=0
METHOD="source-dir"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --validate) VALIDATE=1 ;;
    --method) METHOD="$2"; shift ;;
    *) echo "Unknown argument $1" >&2; exit 2 ;;
  esac
  shift
done

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi

SPACE="$("$PY" - "$KIT" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from scripts.lib.matrix import kit_index, load_matrix
info = kit_index(load_matrix()).get(sys.argv[1])
if not info:
    raise SystemExit(1)
print(info["space"])
PY
)"

DEST="$ROOT/data-cloud/${SPACE}/${KIT}"
if [[ ! -d "$DEST" ]]; then
  echo "Missing retrieved kit: $DEST" >&2
  exit 1
fi
PAYLOAD_COUNT="$(find "$DEST" -type f ! -name .gitkeep | wc -l | tr -d ' ')"
if [[ "$PAYLOAD_COUNT" == "0" ]]; then
  echo "Refusing to deploy $KIT. Retrieve it from the sandbox first." >&2
  exit 1
fi

BYTES="$("$PY" - "$DEST" <<'PY'
import sys
from pathlib import Path
root = Path(sys.argv[1])
print(sum(p.stat().st_size for p in root.rglob("*") if p.is_file()))
PY
)"
if [[ "$BYTES" -gt 52428800 ]]; then
  echo "$KIT is ${BYTES} bytes, over the 50 MB Metadata API limit." >&2
  exit 1
fi

if [[ "$METHOD" == "connect-api" ]]; then
  echo "Pilot path: Connect API deploy of ${KIT} in ${ORG}."
  echo "This installs a kit that must already exist in the target."
  BODY="$(mktemp)"
  printf '{"developerName":"%s"}' "$KIT" > "$BODY"
  sf api request rest "/services/data/v68.0/ssot/data-kits/${KIT}?asyncMode=true" \
    --target-org "$ORG" --method POST --body "@${BODY}"
  rm -f "$BODY"
  exit 0
fi

if [[ "$METHOD" != "source-dir" ]]; then
  echo "Unknown method $METHOD" >&2
  exit 2
fi

ARGS=(project deploy start --source-dir "$DEST" --target-org "$ORG" --wait 120 --json)
if [[ "$VALIDATE" == "1" ]]; then
  ARGS+=(--dry-run)
fi

ATTEMPT=1
RESULT=""
while [[ "$ATTEMPT" -le 3 ]]; do
  set +e
  RESULT="$(sf "${ARGS[@]}")"
  CODE=$?
  set -e
  if [[ "$CODE" == "0" ]]; then
    break
  fi
  echo "Deploy attempt ${ATTEMPT} failed." >&2
  echo "$RESULT" >&2
  if [[ "$ATTEMPT" == "3" ]]; then
    exit "$CODE"
  fi
  ATTEMPT=$((ATTEMPT + 1))
  sleep 10
done

JOB_ID="$(DEPLOY_JSON="$RESULT" "$PY" - <<'PY'
import json, os
payload = json.loads(os.environ["DEPLOY_JSON"])
result = payload.get("result") or {}
print(result.get("id") or "")
PY
)"

if [[ -n "$JOB_ID" ]]; then
  sf project deploy report --job-id "$JOB_ID" --target-org "$ORG"
fi

if [[ "$VALIDATE" == "1" ]]; then
  echo "Check-only finished for $KIT"
  exit 0
fi

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
if [[ "$COUNT" == "0" ]]; then
  echo "Deploy report finished but ${KIT} is not queryable in ${ORG}." >&2
  echo "See Case 473942263. Do not treat CLI success as proof." >&2
  exit 3
fi
echo "Confirmed ${KIT} exists in ${ORG}"
