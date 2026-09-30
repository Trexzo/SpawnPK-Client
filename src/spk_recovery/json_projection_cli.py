from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


class JsonProjectionError(ValueError):
    pass


def _exact_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise JsonProjectionError(
                f"duplicate JSON key: {key!r}"
            )
        out[key] = value
    return out


def _load(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_exact_object,
        )
    except OSError as exc:
        raise JsonProjectionError(str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise JsonProjectionError(str(exc)) from exc


def _pointer_token(value: str) -> str:
    return value.replace("~1", "/").replace("~0", "~")


def _resolve_pointer(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise JsonProjectionError(
            f"JSON Pointer must start with '/': {pointer!r}"
        )

    current = document
    for raw in pointer[1:].split("/"):
        token = _pointer_token(raw)
        if isinstance(current, dict):
            if token not in current:
                raise KeyError(token)
            current = current[token]
            continue
        if isinstance(current, list):
            if token == "-" or not token.isdigit():
                raise KeyError(token)
            index = int(token)
            if index < 0 or index >= len(current):
                raise KeyError(token)
            current = current[index]
            continue
        raise KeyError(token)
    return current


def _parse_field(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise JsonProjectionError(
            f"field must be ALIAS=/json/pointer: {value!r}"
        )
    alias, pointer = value.split("=", 1)
    alias = alias.strip()
    if not alias:
        raise JsonProjectionError("field alias is empty")
    if not pointer.startswith("/"):
        raise JsonProjectionError(
            f"field pointer must start with '/': {pointer!r}"
        )
    return alias, pointer


def project(
    document: Any,
    *,
    required: list[tuple[str, str]],
    optional: list[tuple[str, str]],
) -> dict[str, Any]:
    aliases: dict[str, str] = {}
    for alias, _pointer in [*required, *optional]:
        folded = alias.casefold()
        previous = aliases.get(folded)
        if previous is not None:
            raise JsonProjectionError(
                "field aliases collide case-insensitively: "
                f"{previous!r} and {alias!r}"
            )
        aliases[folded] = alias

    out: dict[str, Any] = {}
    for alias, pointer in required:
        try:
            out[alias] = _resolve_pointer(document, pointer)
        except KeyError as exc:
            raise JsonProjectionError(
                f"required JSON Pointer is missing: {pointer}"
            ) from exc

    for alias, pointer in optional:
        try:
            out[alias] = _resolve_pointer(document, pointer)
        except KeyError:
            out[alias] = None

    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spk-json-projection")
    parser.add_argument("json_path", type=Path)
    parser.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="ALIAS=/POINTER",
    )
    parser.add_argument(
        "--optional-field",
        action="append",
        default=[],
        metavar="ALIAS=/POINTER",
    )
    args = parser.parse_args(argv)

    try:
        required = [_parse_field(value) for value in args.field]
        optional = [
            _parse_field(value)
            for value in args.optional_field
        ]
        if not required and not optional:
            raise JsonProjectionError(
                "at least one field projection is required"
            )
        document = _load(args.json_path)
        result = project(
            document,
            required=required,
            optional=optional,
        )
    except JsonProjectionError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
