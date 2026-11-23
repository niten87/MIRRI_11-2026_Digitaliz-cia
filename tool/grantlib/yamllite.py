"""The single dependency-free nested-YAML subset loader for the framework.

Handles nested mappings, lists of scalars, lists of mappings, and inline flow
lists (`[a, b, c]`). Uses PyYAML when available, otherwise this hand-written
subset parser. This is the ONE parser; scripts must not re-implement it.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def strip_inline_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    output: list[str] = []
    for char in value:
        if escaped:
            output.append(char)
            escaped = False
            continue
        if char == "\\":
            output.append(char)
            escaped = True
            continue
        if char in {"'", '"'}:
            if quote == char:
                quote = None
            elif quote is None:
                quote = char
            output.append(char)
            continue
        if char == "#" and quote is None:
            break
        output.append(char)
    return "".join(output).strip()


def parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value in {"", "null", "Null", "NULL", "~"}:
        return None
    if value in {"[]", "[ ]"}:
        return []
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part) for part in split_flow_items(inner)]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def split_flow_items(inner: str) -> list[str]:
    items: list[str] = []
    quote: str | None = None
    buffer: list[str] = []
    for char in inner:
        if char in {"'", '"'}:
            if quote == char:
                quote = None
            elif quote is None:
                quote = char
            buffer.append(char)
            continue
        if char == "," and quote is None:
            items.append("".join(buffer).strip())
            buffer = []
            continue
        buffer.append(char)
    tail = "".join(buffer).strip()
    if tail:
        items.append(tail)
    return items


def _tokenize_yaml(text: str) -> list[tuple[int, str]]:
    tokens: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        content = strip_inline_comment(raw)
        if not content:
            continue
        tokens.append((indent, content))
    return tokens


def _split_key_value(content: str) -> tuple[str, str]:
    key, _, rest = content.partition(":")
    return key.strip(), rest.strip()


def _parse_yaml_block(tokens: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(tokens):
        return None, index
    if tokens[index][1].startswith("- ") or tokens[index][1] == "-":
        return _parse_yaml_list(tokens, index, indent)
    return _parse_yaml_map(tokens, index, indent)


def _parse_yaml_map(tokens: list[tuple[int, str]], index: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(tokens):
        cur_indent, content = tokens[index]
        if cur_indent != indent:
            break
        if content.startswith("- "):
            break
        key, rest = _split_key_value(content)
        index += 1
        if rest == "":
            if index < len(tokens) and tokens[index][0] > indent:
                value, index = _parse_yaml_block(tokens, index, tokens[index][0])
            else:
                value = None
            result[key] = value
        else:
            result[key] = parse_scalar(rest)
    return result, index


def _parse_yaml_list(tokens: list[tuple[int, str]], index: int, indent: int) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(tokens):
        cur_indent, content = tokens[index]
        if cur_indent != indent or not (content.startswith("- ") or content == "-"):
            break
        item_content = content[1:].strip()
        index += 1
        if item_content == "":
            if index < len(tokens) and tokens[index][0] > indent:
                value, index = _parse_yaml_block(tokens, index, tokens[index][0])
            else:
                value = None
            result.append(value)
            continue
        if ":" in item_content and not (item_content.startswith("[") or item_content.startswith(('"', "'"))):
            key, rest = _split_key_value(item_content)
            mapping: dict[str, Any] = {}
            if rest == "" and index < len(tokens) and tokens[index][0] > cur_indent:
                value, index = _parse_yaml_block(tokens, index, tokens[index][0])
                mapping[key] = value
            else:
                mapping[key] = parse_scalar(rest)
            while index < len(tokens) and tokens[index][0] > cur_indent:
                sub, index = _parse_yaml_map(tokens, index, tokens[index][0])
                if not sub:
                    break
                mapping.update(sub)
            result.append(mapping)
        else:
            result.append(parse_scalar(item_content))
    return result, index


def parse_subset(text: str) -> dict[str, Any]:
    """Parse the framework's YAML subset from text (no PyYAML). Root must be a mapping."""
    tokens = _tokenize_yaml(text)
    value, _ = _parse_yaml_block(tokens, 0, 0) if tokens else ({}, 0)
    if not isinstance(value, dict):
        raise ValueError("YAML root must be a mapping")
    return value


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML mapping. Uses PyYAML if present, else the subset parser."""
    text = Path(path).read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text) or {}
        if not isinstance(loaded, dict):
            raise ValueError("YAML root must be a mapping")
        return loaded
    except ModuleNotFoundError:
        return parse_subset(text)
