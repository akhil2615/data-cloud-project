"""Create external activation targets in prod. Idempotent: look up by name first.

Usage:
  python scripts/recreate-external-targets.py --org dc1-prod --space france [--dry-run]

Templates live in api-payloads/10b-external-targets/. Secret fields use ${ENV_NAME}.
Values come from the environment, never from git. The id map is written to
data-kits/id-mappings/<space>-external-targets.json.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.lib.matrix import load_matrix  # noqa: E402

TEMPLATES = ROOT / "api-payloads" / "10b-external-targets"
API_VERSION = "68.0"
TOKEN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def sf_rest(org: str, url: str, method: str = "GET", body: dict | None = None) -> dict:
    cmd = [
        "sf",
        "api",
        "request",
        "rest",
        url,
        "--target-org",
        org,
        "--method",
        method,
    ]
    if body is not None:
        cmd.extend(["--body", json.dumps(body)])
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr or completed.stdout)
        raise SystemExit(completed.returncode or 1)
    text = completed.stdout.strip()
    return json.loads(text) if text else {}


def fill(value, missing: list[str]):
    if isinstance(value, dict):
        return {key: fill(item, missing) for key, item in value.items()}
    if isinstance(value, list):
        return [fill(item, missing) for item in value]
    if isinstance(value, str):
        def replace(match: re.Match) -> str:
            env = match.group(1)
            found = os.environ.get(env)
            if not found:
                missing.append(env)
                return match.group(0)
            return found
        return TOKEN.sub(replace, value)
    return value


def target_name(payload: dict) -> str:
    return str(payload.get("name") or payload.get("developerName") or "")


def existing_by_name(org: str) -> dict[str, dict]:
    url = f"/services/data/v{API_VERSION}/ssot/activation-targets"
    payload = sf_rest(org, url)
    rows = payload.get("activationTargets") or payload.get("targets") or payload.get("data") or []
    found = {}
    for row in rows:
        name = row.get("name") or row.get("developerName")
        if name:
            found[name] = row
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org", required=True)
    parser.add_argument("--space", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    templates = sorted(TEMPLATES.glob("*.json"))
    if not templates:
        print("No external-target templates found", file=sys.stderr)
        return 1

    current = {} if args.dry_run else existing_by_name(args.org)
    mapping = {"space": args.space, "org": args.org, "targets": []}
    for path in templates:
        missing: list[str] = []
        payload = fill(json.loads(path.read_text(encoding="utf-8")), missing)
        space = load_matrix()["spaces"][args.space]
        payload["dataSpaceName"] = space.get("api_name") or args.space
        name = target_name(payload)
        if not name:
            print(f"{path.name} has no name", file=sys.stderr)
            return 1
        if missing and not args.dry_run:
            print(f"{path.name} is missing environment values: {', '.join(sorted(set(missing)))}", file=sys.stderr)
            return 1
        if name in current:
            mapping["targets"].append({"name": name, "id": current[name].get("id"), "action": "exists"})
            print(f"exists {name}")
            continue
        if args.dry_run:
            mapping["targets"].append({"name": name, "id": None, "action": "would-create"})
            print(f"would create {name}")
            continue
        created = sf_rest(
            args.org,
            f"/services/data/v{API_VERSION}/ssot/activation-targets",
            "POST",
            payload,
        )
        mapping["targets"].append({"name": name, "id": created.get("id"), "action": "created"})
        print(f"created {name}")

    out = ROOT / "data-kits" / "id-mappings" / f"{args.space}-external-targets.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
