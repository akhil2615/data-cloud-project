#!/usr/bin/env bash
# Retrieve a Data Kit manifest into data-cloud/<space>/<kit>/.
# A failed retrieve leaves the existing folder untouched.
#
# Usage: scripts/retrieve-kit.sh <kit> <org-alias>
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: scripts/retrieve-kit.sh <kit> <org-alias>" >&2
  exit 2
fi

KIT="$1"
ORG="$2"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi

MANIFEST="$ROOT/manifest/kits/${KIT}.xml"
if [[ ! -f "$MANIFEST" ]]; then
  echo "No manifest: $MANIFEST" >&2
  echo "Download it from the Data Kit UI before retrieving." >&2
  exit 1
fi
if grep -q "PLACEHOLDER" "$MANIFEST"; then
  echo "Refusing to retrieve $KIT. Replace manifest/kits/${KIT}.xml with the UI download." >&2
  exit 1
fi

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
TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

# --output-dir cannot be a package directory, so retrieve into a temp folder.
sf project retrieve start \
  --manifest "$MANIFEST" \
  --target-org "$ORG" \
  --output-dir "$TMP" \
  --wait 30

STAGE="${DEST}.partial"
rm -rf "$STAGE"
mkdir -p "$STAGE"
shopt -s dotglob
if [[ -d "$TMP/main/default" ]]; then
  mv "$TMP/main/default"/* "$STAGE"/
elif [[ -d "$TMP/unpackaged" ]]; then
  mv "$TMP/unpackaged"/* "$STAGE"/
else
  mv "$TMP"/* "$STAGE"/
fi
rm -rf "$DEST"
mv "$STAGE" "$DEST"
echo "Retrieved $KIT into data-cloud/${SPACE}/${KIT}"
