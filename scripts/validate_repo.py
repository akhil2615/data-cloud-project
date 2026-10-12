"""Validate the repository structure. Safe to run with no Salesforce org.

Usage: python scripts/validate_repo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib.matrix import LAYERS, ROOT, kit_index, load_matrix  # noqa: E402

LIMIT = 52_428_800


def main() -> int:
    errors: list[str] = []
    matrix = load_matrix()
    spaces = matrix["spaces"]
    named = [key for key, space in spaces.items() if space.get("inventory") != "awaiting-name"]
    if len(named) != 30:
        errors.append(f"expected 30 named spaces from the sandbox inventory, found {len(named)}")
    if "unassigned" not in spaces:
        errors.append("missing unassigned placeholder row")
    if "default" not in spaces:
        errors.append("missing default space")

    index = kit_index(matrix)
    for name, info in index.items():
        manifest = ROOT / "manifest" / "kits" / f"{name}.xml"
        folder = ROOT / "data-cloud" / info["space"] / name
        if not manifest.is_file():
            errors.append(f"missing manifest for {name}")
        else:
            text = manifest.read_text(encoding="utf-8")
            if "<version>" not in text:
                errors.append(f"{manifest.name} has no version")
        if not folder.is_dir():
            errors.append(f"missing kit folder data-cloud/{info['space']}/{name}")
        else:
            size = sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())
            if size > LIMIT:
                errors.append(f"{name} is {size} bytes, over the 50 MB Metadata API limit")
        if not name.startswith(f"DK{info['layer']}_") or not name.endswith(f"_v{info['version']}"):
            errors.append(f"{name} does not match DK<layer>_<scope>_<space>_v<n>")

    for space_key, space in spaces.items():
        for layer in space.get("order") or []:
            if layer not in LAYERS:
                errors.append(f"{space_key} order contains unknown layer {layer}")
        for layer, entries in (space.get("kits") or {}).items():
            if layer == "10b" and entries:
                errors.append(f"{space_key} layer 10b is an API step and cannot list kits")

    secret_needles = ("BEGIN PRIVATE KEY", "SF_AUTH_URL=", "access_token")
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "node_modules" in path.parts:
            continue
        if path.suffix.lower() not in {".md", ".yml", ".yaml", ".json", ".xml", ".py", ".sh", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        for needle in secret_needles:
            if needle in text and "placeholder" not in text.lower() and "do not" not in text.lower():
                errors.append(f"possible secret marker {needle} in {path.relative_to(ROOT)}")

    if errors:
        print("\n".join(errors))
        return 1
    print(f"OK: {len(named)} spaces, {len(index)} seeded kits, layers {', '.join(LAYERS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
