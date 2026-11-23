"""Minimal dependency-free schema validation for framework config files.

Catches the failure mode where the YAML subset parser silently returns a wrong
structure: unknown keys (typos), missing required keys, and wrong scalar types.

A schema is a plain dict:

    {"type": "map",
     "required": ["a"],
     "allow_unknown": False,
     "fields": {
         "a": {"type": "str"},
         "n": {"type": "int"},
         "items": {"type": "list", "item": {"type": "map", "fields": {...}}},
         "mode": {"type": "str", "enum": ["x", "y"]},
     }}

`validate(value, schema)` returns a list of human-readable error strings (empty
== valid). Types: map, list, str, int, float, number, bool, any.
"""
from __future__ import annotations

from typing import Any


def _type_ok(value: Any, type_name: str) -> bool:
    if type_name == "any":
        return True
    if type_name == "bool":
        return isinstance(value, bool)
    if type_name == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name in {"float", "number"}:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "str":
        return isinstance(value, str)
    if type_name == "list":
        return isinstance(value, list)
    if type_name == "map":
        return isinstance(value, dict)
    return False


def validate(value: Any, schema: dict[str, Any], path: str = "") -> list[str]:
    errors: list[str] = []
    type_name = schema.get("type", "any")
    where = path or "<root>"

    if value is None and not schema.get("required_value", False):
        # A present-but-null key is tolerated unless explicitly required to have a value.
        return errors

    if not _type_ok(value, type_name):
        errors.append(f"{where}: expected {type_name}, got {type(value).__name__}")
        return errors

    enum = schema.get("enum")
    if enum is not None and value not in enum:
        errors.append(f"{where}: value {value!r} not in {enum}")

    if type_name == "map":
        fields = schema.get("fields", {})
        required = schema.get("required", [])
        allow_unknown = schema.get("allow_unknown", True)
        for key in required:
            if key not in value or value[key] is None:
                errors.append(f"{where}: missing required key `{key}`")
        for key, item_value in value.items():
            child_path = f"{where}.{key}" if path else key
            if key in fields:
                errors.extend(validate(item_value, fields[key], child_path))
            elif not allow_unknown:
                known = ", ".join(sorted(fields)) or "(none)"
                errors.append(f"{child_path}: unknown key `{key}` (known: {known})")
    elif type_name == "list":
        item_schema = schema.get("item")
        if item_schema is not None:
            for index, item in enumerate(value):
                errors.extend(validate(item, item_schema, f"{where}[{index}]"))

    return errors


def require_valid(value: Any, schema: dict[str, Any], *, source: str) -> None:
    """Raise ValueError with all schema errors, prefixed by `source`."""
    errors = validate(value, schema)
    if errors:
        joined = "; ".join(errors)
        raise ValueError(f"Invalid {source}: {joined}")
