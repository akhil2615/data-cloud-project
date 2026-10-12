"""Fail when a retrieved kit references a component that is not in the kit.

Usage: python scripts/check-dependencies.py <kit>
A placeholder kit that has not been retrieved yet exits 0 with a warning.
This does not replace View/Add Dependencies in the Data Kit UI.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib.matrix import ROOT, kit_index, load_matrix  # noqa: E402

REF_TAGS = ("sourceObject", "referenceObjectName", "targetObject", "dataSpaceDefinitionDevName")


def members(manifest: Path) -> set[str]:
    text = manifest.read_text(encoding="utf-8")
    return set(re.findall(r"<members>([^<]+)</members>", text))


def references(folder: Path) -> set[str]:
    found: set[str] = set()
    for path in folder.rglob("*"):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        if path.suffix.lower() not in {".xml", ".json"} and "Template" not in path.name:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for tag in REF_TAGS:
            found.update(re.findall(rf"<{tag}>([^<]+)</{tag}>", text))
            found.update(re.findall(rf'"{tag}"\s*:\s*"([^"]+)"', text))
    return {name for name in found if name and not name.startswith("PLACEHOLDER")}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/check-dependencies.py <kit>", file=sys.stderr)
        return 2
    kit = sys.argv[1]
    info = kit_index(load_matrix()).get(kit)
    if not info:
        print(f"{kit} is not in kit-matrix.yaml", file=sys.stderr)
        return 1
    folder = ROOT / "data-cloud" / info["space"] / kit
    manifest = ROOT / "manifest" / "kits" / f"{kit}.xml"
    payload_files = [p for p in folder.rglob("*") if p.is_file() and p.name != ".gitkeep"]
    if not payload_files:
        print(f"WARNING: {kit} has not been retrieved yet. Dependency check skipped.")
        return 0
    if "PLACEHOLDER" in manifest.read_text(encoding="utf-8"):
        print(f"WARNING: {kit} manifest is still a placeholder. Retrieve before relying on this check.")
        return 0
    known = members(manifest)
    known.add(kit)
    missing = sorted(ref for ref in references(folder) if ref not in known)
    if missing:
        print(f"{kit} references components that are not in the manifest:")
        print("\n".join(f"  {name}" for name in missing))
        return 1
    print(f"OK: {kit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
