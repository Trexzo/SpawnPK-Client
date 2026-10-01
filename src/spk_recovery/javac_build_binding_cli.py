from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .javac_build_binding import (
    JavacBuildBindingError,
    build_javac_build_binding,
    write_javac_build_binding,
)


def _exact_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise JavacBuildBindingError(
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
    except (OSError, json.JSONDecodeError) as exc:
        raise JavacBuildBindingError(
            f"failed to read JSON {path}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise JavacBuildBindingError(
            f"expected JSON object: {path}"
        )
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Bind a private javac diagnostic report to the exact "
            "clean-rebuild build/source authority that produced it."
        )
    )
    parser.add_argument("diagnostic_report", type=Path)
    parser.add_argument("clean_rebuild_report", type=Path)
    parser.add_argument("--expected-build-id", required=True)
    parser.add_argument(
        "--expected-authority-sha256",
        required=True,
    )
    parser.add_argument(
        "--tooling-commit",
        required=True,
        help="Exact SpawnPK-Client recovery-tooling commit.",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    try:
        report = build_javac_build_binding(
            _load(args.diagnostic_report),
            _load(args.clean_rebuild_report),
            expected_build_id=args.expected_build_id,
            expected_authority_sha256=(
                args.expected_authority_sha256
            ),
            tooling_commit=args.tooling_commit,
        )
        write_javac_build_binding(report, args.out)
    except JavacBuildBindingError as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            {
                "binding_id": report["binding_id"],
                "tooling_commit": report["tooling_commit"],
                "build_id": report["build_id"],
                "source_authority_sha256": (
                    report["source_authority_sha256"]
                ),
                "rebuild_id": report["rebuild_id"],
                "workspace_id": report["workspace_id"],
                "source_tree_sha256": report["source_tree_sha256"],
                "diagnostic_report_id": (
                    report["diagnostic_report_id"]
                ),
                "frontier_id": report["frontier_id"],
                "out": str(args.out),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
