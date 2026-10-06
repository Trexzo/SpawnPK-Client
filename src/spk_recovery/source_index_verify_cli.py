from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .indexer import index_jar


class IndexVerificationError(ValueError):
    pass


def _exact_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise IndexVerificationError(
                f"duplicate JSON key: {key!r}"
            )
        out[key] = value
    return out


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_exact_object,
        )
    except OSError as exc:
        raise IndexVerificationError(str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise IndexVerificationError(str(exc)) from exc
    if not isinstance(value, dict):
        raise IndexVerificationError("source index must be a JSON object")
    return value


def _authority_material(index: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in index.items()
        if key != "source_name"
    }


def verify_index(
    jar: Path,
    supplied_index: Path,
    *,
    expected_sha256: str,
) -> dict[str, Any]:
    canonical = index_jar(jar)
    actual_sha = str(canonical.get("sha256", "")).lower()
    expected = expected_sha256.lower()
    if actual_sha != expected:
        raise IndexVerificationError(
            f"source JAR SHA-256 {actual_sha} != expected {expected}"
        )

    supplied = _load(supplied_index)
    supplied_sha = str(supplied.get("sha256", "")).lower()
    if supplied_sha != expected:
        raise IndexVerificationError(
            f"supplied index SHA-256 {supplied_sha} != expected {expected}"
        )

    if _authority_material(supplied) != _authority_material(canonical):
        raise IndexVerificationError(
            "supplied source index does not exactly match a fresh index "
            "derived from the exact source JAR"
        )
    return canonical


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-source-index-verify",
    )
    parser.add_argument("jar", type=Path)
    parser.add_argument("source_index", type=Path)
    parser.add_argument("--expect-sha256", required=True)
    args = parser.parse_args(argv)

    try:
        canonical = verify_index(
            args.jar,
            args.source_index,
            expected_sha256=args.expect_sha256,
        )
    except IndexVerificationError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_SOURCE_INDEX_VERIFY_PASS")
    print(f"sha256={canonical['sha256']}")
    print(f"entries={canonical['summary']['entry_count']}")
    print(f"classes={canonical['summary']['class_count']}")
    print(f"rs_classes={canonical['summary']['rs_class_count']}")
    print(
        "parse_errors="
        + str(canonical["summary"]["class_parse_error_count"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
