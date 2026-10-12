"""Remove KQ_* fields and managed-package files. Fill empty CustomObject labels.

Usage: python scripts/cleanup_kit.py <kit-folder>
"""

from __future__ import annotations

import sys
from pathlib import Path

MANAGED = ("<manageableState>installed</manageableState>", "<manageableState>released</manageableState>")


def label_from_name(path: Path) -> str:
    name = path.name
    for suffix in (".object-meta.xml", ".object"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name.replace("__dll", "").replace("__dlm", "").replace("__c", "").replace("_", " ")


def ensure_label(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if "<CustomObject" not in text and not path.name.endswith(".object-meta.xml"):
        return False
    if "<label>" not in text:
        label = label_from_name(path)
        updated = text.replace("</CustomObject>", f"    <label>{label}</label>\n</CustomObject>", 1)
        if updated == text:
            return False
        path.write_text(updated, encoding="utf-8")
        print(f"label added: {path}")
        return True
    if "<label></label>" in text or "<label> </label>" in text:
        label = label_from_name(path)
        updated = text.replace("<label></label>", f"<label>{label}</label>").replace(
            "<label> </label>", f"<label>{label}</label>"
        )
        path.write_text(updated, encoding="utf-8")
        print(f"label filled: {path}")
        return True
    return False


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/cleanup_kit.py <kit-folder>", file=sys.stderr)
        return 2
    folder = Path(sys.argv[1])
    if not folder.is_dir():
        print(f"Not a directory: {folder}", file=sys.stderr)
        return 1
    changed = 0
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        if path.name.startswith("KQ_") or "/fields/KQ_" in path.as_posix():
            path.unlink()
            print(f"removed KQ field: {path}")
            changed += 1
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(token in text for token in MANAGED):
            path.unlink()
            print(f"removed managed package component: {path}")
            changed += 1
            continue
        if ensure_label(path):
            changed += 1
    print(f"cleanup complete: {changed} change(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
