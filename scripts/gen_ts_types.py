"""Generate frontend/src/contracts.ts from the pydantic contracts in bluewatch/models.py.

Run from the repo root: .venv/bin/python scripts/gen_ts_types.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pydantic import BaseModel  # noqa: E402

from bluewatch import models  # noqa: E402

OUT = ROOT / "frontend" / "src" / "contracts.ts"


def ts_type(schema: dict) -> str:
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]
    if "anyOf" in schema:
        return " | ".join(dict.fromkeys(ts_type(s) for s in schema["anyOf"]))
    if "enum" in schema:
        return " | ".join(f'"{v}"' for v in schema["enum"])
    if "const" in schema:
        return f'"{schema["const"]}"'
    kind = schema.get("type")
    if kind == "string":
        return "string"
    if kind in ("integer", "number"):
        return "number"
    if kind == "boolean":
        return "boolean"
    if kind == "null":
        return "null"
    if kind == "array":
        items = schema.get("items", {})
        inner = ts_type(items) if items else "unknown"
        return f"({inner})[]" if "|" in inner else f"{inner}[]"
    if kind == "object":
        extra = schema.get("additionalProperties")
        if isinstance(extra, dict):
            return f"Record<string, {ts_type(extra)}>"
        return "Record<string, unknown>"
    return "unknown"


def main() -> None:
    defs: dict[str, dict] = {}
    roots = [
        obj
        for obj in vars(models).values()
        if isinstance(obj, type) and issubclass(obj, BaseModel) and obj not in (models.Model, BaseModel)
    ]
    for cls in roots:
        schema = cls.model_json_schema(ref_template="#/$defs/{model}")
        for name, sub in schema.pop("$defs", {}).items():
            defs.setdefault(name, sub)
        defs.setdefault(cls.__name__, schema)
    lines = [
        "// Generated from bluewatch/models.py by scripts/gen_ts_types.py. Do not edit by hand.",
        f'export const CONTRACTS_VERSION = "{models.CONTRACTS_VERSION}";',
        "",
    ]
    for name in sorted(defs):
        schema = defs[name]
        if "enum" in schema and schema.get("type") == "string":
            lines.append(f"export type {name} = {ts_type(schema)};")
            lines.append("")
            continue
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        lines.append(f"export interface {name} {{")
        for prop, sub in props.items():
            optional = "" if prop in required else "?"
            lines.append(f"  {prop}{optional}: {ts_type(sub)};")
        lines.append("}")
        lines.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} ({len(defs)} types)")


if __name__ == "__main__":
    main()
