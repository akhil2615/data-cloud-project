"""Read data-kits/kit-matrix.yaml. The file is a small YAML subset: maps, lists, scalars."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "data-kits" / "kit-matrix.yaml"

LAYERS = [
    "01",
    "02",
    "02b",
    "03",
    "04",
    "05",
    "06",
    "07",
    "08",
    "09",
    "10",
    "10c",
    "10b",
    "11",
    "12",
]

SCRIPT_ONLY = {"10b"}


def layer_sort_key(layer: str) -> tuple:
    if layer not in LAYERS:
        raise ValueError(f"Unknown layer {layer}")
    return (LAYERS.index(layer),)


def _key(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _parse_scalar(raw: str):
    value = raw.strip()
    if value == "" or value in ("null", "~"):
        return None
    if value in ("[]", "{}"):
        return [] if value == "[]" else {}
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value in ("true", "false"):
        return value == "true"
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)
    return value


def _lines(text: str) -> list[tuple[int, str]]:
    parsed = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        raw = line.split(" #", 1)[0].rstrip()
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            raise ValueError(f"Line {line_no}: indent must be multiples of 2")
        parsed.append((indent, raw.strip()))
    return parsed


def _parse_block(rows: list[tuple[int, str]], index: int, indent: int):
    if index >= len(rows) or rows[index][0] < indent:
        return {}, index
    if rows[index][1].startswith("- "):
        items = []
        while index < len(rows) and rows[index][0] == indent and rows[index][1].startswith("- "):
            content = rows[index][1][2:].strip()
            index += 1
            if ":" in content and not content.startswith(("'", '"')):
                key, _, rest = content.partition(":")
                mapping = {}
                if rest.strip():
                    mapping[_key(key)] = _parse_scalar(rest)
                else:
                    child, index = _parse_block(rows, index, indent + 2)
                    mapping[_key(key)] = child
                while (
                    index < len(rows)
                    and rows[index][0] == indent + 2
                    and not rows[index][1].startswith("- ")
                ):
                    key, _, rest = rows[index][1].partition(":")
                    index += 1
                    if rest.strip() == "":
                        child, index = _parse_block(rows, index, indent + 4)
                        mapping[_key(key)] = child
                    else:
                        mapping[_key(key)] = _parse_scalar(rest)
                items.append(mapping)
            else:
                items.append(_parse_scalar(content))
        return items, index
    mapping = {}
    while index < len(rows) and rows[index][0] == indent and not rows[index][1].startswith("- "):
        key, _, rest = rows[index][1].partition(":")
        index += 1
        if rest.strip() == "":
            child, index = _parse_block(rows, index, indent + 2)
            mapping[_key(key)] = child
        else:
            mapping[_key(key)] = _parse_scalar(rest)
    return mapping, index


def load_yaml(text: str):
    rows = _lines(text)
    value, index = _parse_block(rows, 0, 0)
    if index != len(rows):
        raise ValueError(f"Unparsed matrix content near: {rows[index][1]}")
    if not isinstance(value, dict):
        raise ValueError("Matrix root must be a mapping")
    return value


def load_matrix(path: Path | None = None) -> dict:
    path = path or MATRIX_PATH
    data = load_yaml(path.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError("kit-matrix.yaml version must be 1")
    missing = [layer for layer in LAYERS if layer not in data.get("layers_order", [])]
    if missing:
        raise ValueError(f"layers_order is missing {missing}")
    return data


def kits_for(space: dict, gates: dict | None = None) -> list[dict]:
    """Kits in the space's order. 10b is a gate and never a kit."""
    gates = gates or {}
    order = space.get("order") or []
    found = []
    kits = space.get("kits") or {}
    for layer in order:
        if layer in SCRIPT_ONLY:
            found.append({"layer": layer, "gate": True, "name": gates.get(layer, layer)})
            continue
        entries = kits.get(layer, [])
        if entries is None:
            continue
        emitted = False
        for entry in entries:
            found.append({"layer": layer, "gate": False, **entry})
            emitted = True
        if emitted and layer in gates:
            found.append({"layer": layer, "gate": True, "name": gates[layer]})
    return found


def kit_index(matrix: dict) -> dict[str, dict]:
    index = {}
    for space_key, space in matrix["spaces"].items():
        for item in kits_for(space, matrix.get("gates")):
            if item.get("gate"):
                continue
            name = item["kit"]
            index[name] = {**item, "space": space_key}
    return index


def dumps(data: dict) -> str:
    return json.dumps(data, indent=2) + "\n"
