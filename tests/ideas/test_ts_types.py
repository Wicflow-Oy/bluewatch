"""frontend/src/screens/ideas/types.ts is written by hand; this keeps its fields in step with the models."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

from bluewatch.ideas import models

TYPES_TS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "screens" / "ideas" / "types.ts"
INTERNAL = {"Claim"}  # read inside the rubric, never sent over the API


def ts_interfaces() -> dict[str, set[str]]:
    text = TYPES_TS.read_text(encoding="utf-8")
    found = {}
    for name, body in re.findall(r"export interface (\w+) \{(.*?)\n\}", text, re.S):
        found[name] = set(re.findall(r"^\s+(\w+)\??:", body, re.M))
    return found


def test_every_api_model_has_a_matching_interface():
    interfaces = ts_interfaces()
    api_models = {
        name: cls
        for name, cls in vars(models).items()
        if isinstance(cls, type)
        and issubclass(cls, BaseModel)
        and cls.__module__ == models.__name__
        and name not in INTERNAL
    }
    assert set(api_models) <= set(interfaces), f"missing in types.ts: {set(api_models) - set(interfaces)}"
    for name, cls in api_models.items():
        assert interfaces[name] == set(cls.model_fields), f"{name} fields differ"
