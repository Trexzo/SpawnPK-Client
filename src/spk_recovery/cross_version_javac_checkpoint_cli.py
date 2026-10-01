from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .cross_version_javac_checkpoint import (
    CrossVersionJavacCheckpointError,
    build_cross_version_javac_checkpoint,
    verify_cross_version_javac_checkpoint,
    write_cross_version_javac_checkpoint,
)


def _exact_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise CrossVersionJavacCheckpointError(
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
        raise CrossVersionJavacCheckpointError(
            f"failed to read JSON {path}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise CrossVersionJavacCheckpointError(
            f"expected JSON object: {path}"
        )
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a public-safe deterministic checkpoint from one "
            "redacted cross-version javac report and two redacted verified "
            "javac build bindings."
        )
    )
    parser.add_argument("comparison_report", type=Path)
    parser.add_argument("old_binding_report", type=Path)
    parser.add_argument("new_binding_report", type=Path)
    parser.add_argument(
        "--binary-backtest-id",
        help="Optional XVERBIN_* authority for the compared build pair.",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    try:
        report = build_cross_version_javac_checkpoint(
            _load(args.comparison_report),
            _load(args.old_binding_report),
            _load(args.new_binding_report),
            binary_backtest_id=args.binary_backtest_id,
        )
        write_cross_version_javac_checkpoint(report, args.out)
        report = verify_cross_version_javac_checkpoint(
            _load(args.comparison_report),
            _load(args.old_binding_report),
            _load(args.new_binding_report),
            _load(args.out),
            binary_backtest_id=args.binary_backtest_id,
        )
    except CrossVersionJavacCheckpointError as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            {
                "checkpoint_id": report["checkpoint_id"],
                "tooling_commit": report["tooling_commit"],
                "old_build_id": report["old"]["build_id"],
                "new_build_id": report["new"]["build_id"],
                "report_id": report["comparison"]["report_id"],
                "exact_frontier_equal": report["comparison"][
                    "summary"
                ].get("exact_frontier_equal"),
                "identifiers_included": report[
                    "identifiers_included"
                ],
                "verified": True,
                "out": str(args.out),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
