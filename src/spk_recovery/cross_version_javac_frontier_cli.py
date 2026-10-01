from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .cross_version_javac_frontier import (
    CrossVersionJavacFrontierError,
    compare_javac_frontiers,
    write_cross_version_javac_frontier,
)


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CrossVersionJavacFrontierError(
            f"failed to read JSON {path}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise CrossVersionJavacFrontierError(
            f"expected JSON object: {path}"
        )
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare two private javac diagnostic frontiers and report "
            "shared versus build-specific compiler failures."
        )
    )
    parser.add_argument("old_report", type=Path)
    parser.add_argument("new_report", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--include-identifiers",
        action="store_true",
        help=(
            "Include normalized source paths and raw diagnostic identifiers "
            "in the output. Keep such reports private."
        ),
    )
    args = parser.parse_args()

    try:
        report = compare_javac_frontiers(
            _load(args.old_report),
            _load(args.new_report),
            include_identifiers=args.include_identifiers,
        )
        write_cross_version_javac_frontier(report, args.out)
    except CrossVersionJavacFrontierError as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            {
                "report_id": report["report_id"],
                "old_frontier_id": report["old_frontier_id"],
                "new_frontier_id": report["new_frontier_id"],
                "summary": report["summary"],
                "identifiers_included": report["identifiers_included"],
                "out": str(args.out),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
