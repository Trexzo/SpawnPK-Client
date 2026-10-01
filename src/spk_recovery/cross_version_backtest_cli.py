from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .cross_version_backtest import (
    CrossVersionBacktestError,
    build_cross_version_backtest,
    write_cross_version_backtest,
)


def _exact_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise CrossVersionBacktestError(
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
        raise CrossVersionBacktestError(
            f"failed to read JSON {path}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise CrossVersionBacktestError(
            f"expected JSON object: {path}"
        )
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify recovered/readable source authority across two exact "
            "client builds."
        )
    )
    parser.add_argument("old_release", type=Path)
    parser.add_argument("new_release", type=Path)
    parser.add_argument("update_intake", type=Path)
    parser.add_argument("semantic_carryforward", type=Path)
    parser.add_argument(
        "--source-name-carryforward",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--binary-delta",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--expectations",
        type=Path,
        default=None,
        help=(
            "Optional JSON object of exact migration-summary expectations."
        ),
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    try:
        report = build_cross_version_backtest(
            _load(args.old_release),
            _load(args.new_release),
            _load(args.update_intake),
            _load(args.semantic_carryforward),
            source_name_carryforward=(
                _load(args.source_name_carryforward)
                if args.source_name_carryforward is not None
                else None
            ),
            binary_delta=(
                _load(args.binary_delta)
                if args.binary_delta is not None
                else None
            ),
            expectations=(
                _load(args.expectations)
                if args.expectations is not None
                else None
            ),
        )
        write_cross_version_backtest(report, args.out)
    except CrossVersionBacktestError as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            {
                "backtest_id": report["backtest_id"],
                "old_build_id": report["old_build_id"],
                "new_build_id": report["new_build_id"],
                "passed": report["passed"],
                "failed_required_check_count": report[
                    "failed_required_check_count"
                ],
                "out": str(args.out),
            },
            sort_keys=True,
        )
    )
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
