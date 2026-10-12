"""Compare component counts between sandbox and prod for one data space.

Usage: python scripts/validate-prod.py --space germany --sandbox dc1-deploy --prod dc1-prod

Exits non-zero when a counted type differs. Queries that the org rejects are
reported and also fail the run, so a silent skip cannot look like a match.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib.matrix import load_matrix  # noqa: E402

QUERIES = {
    "DLOs": "SELECT COUNT() FROM MktDataLakeObject",
    "DMOs": "SELECT COUNT() FROM MktDataModelObject",
    "CIs": "SELECT COUNT() FROM MktCalculatedInsight",
    "segments": "SELECT COUNT() FROM MarketSegment",
    "activations": "SELECT COUNT() FROM MarketSegmentActivation",
}


def count(org: str, soql: str) -> int:
    completed = subprocess.run(
        ["sf", "data", "query", "--target-org", org, "--query", soql, "--json"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip())
    payload = json.loads(completed.stdout)
    result = payload.get("result") or {}
    if "totalSize" in result:
        return int(result["totalSize"])
    records = result.get("records") or []
    if records and "expr0" in records[0]:
        return int(records[0]["expr0"])
    return int(result.get("totalSize") or 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--space", required=True)
    parser.add_argument("--sandbox", required=True)
    parser.add_argument("--prod", required=True)
    args = parser.parse_args()
    matrix = load_matrix()
    if args.space not in matrix["spaces"]:
        print(f"Unknown space {args.space}", file=sys.stderr)
        return 1

    failed = False
    for label, soql in QUERIES.items():
        try:
            left = count(args.sandbox, soql)
            right = count(args.prod, soql)
        except RuntimeError as exc:
            print(f"FAIL {label}: {exc}")
            failed = True
            continue
        state = "OK" if left == right else "MISMATCH"
        print(f"{state} {label}: sandbox={left} prod={right}")
        if left != right:
            failed = True
    print("Mappings, transforms and data graphs have no verified org-wide count query yet.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
