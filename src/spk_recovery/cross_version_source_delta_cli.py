from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .cross_version_source_delta import (
    CrossVersionSourceDeltaError,
    build_cross_version_source_delta,
    write_cross_version_source_delta,
)


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CrossVersionSourceDeltaError(
            f"failed to read JSON {path}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise CrossVersionSourceDeltaError(
            f"expected JSON object: {path}"
        )
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare two independently recovered Java source trees by "
            "stable SpawnPK logical class identity."
        )
    )
    parser.add_argument("old_release", type=Path)
    parser.add_argument("new_release", type=Path)
    parser.add_argument("class_lineage", type=Path)
    parser.add_argument("old_class_plan", type=Path)
    parser.add_argument("new_class_plan", type=Path)
    parser.add_argument("old_source_root", type=Path)
    parser.add_argument("new_source_root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    try:
        report = build_cross_version_source_delta(
            _load(args.old_release),
            _load(args.new_release),
            _load(args.class_lineage),
            _load(args.old_class_plan),
            _load(args.new_class_plan),
            args.old_source_root,
            args.new_source_root,
        )
        write_cross_version_source_delta(report, args.out)
    except CrossVersionSourceDeltaError as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            {
                "report_id": report["report_id"],
                "old_build_id": report["old_build_id"],
                "new_build_id": report["new_build_id"],
                "summary": report["summary"],
                "out": str(args.out),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
