from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .cross_version_javac_checkpoint import (
    CrossVersionJavacCheckpointError,
    verify_cross_version_javac_checkpoint,
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
            "Independently verify one emitted public javac checkpoint "
            "against its redacted comparator + build-binding inputs."
        )
    )
    parser.add_argument("comparison_report", type=Path)
    parser.add_argument("old_binding_report", type=Path)
    parser.add_argument("new_binding_report", type=Path)
    parser.add_argument("checkpoint_report", type=Path)
    parser.add_argument(
        "--binary-backtest-id",
        help="Optional XVERBIN_* authority for the compared build pair.",
    )
    args = parser.parse_args()

    try:
        report = verify_cross_version_javac_checkpoint(
            _load(args.comparison_report),
            _load(args.old_binding_report),
            _load(args.new_binding_report),
            _load(args.checkpoint_report),
            binary_backtest_id=args.binary_backtest_id,
        )
    except CrossVersionJavacCheckpointError as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            {
                "checkpoint_id": report["checkpoint_id"],
                "tooling_commit": report["tooling_commit"],
                "report_id": report["comparison"]["report_id"],
                "identifiers_included": report["identifiers_included"],
                "verified": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
