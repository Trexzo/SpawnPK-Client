from __future__ import annotations

import argparse
import json
from pathlib import Path

from .cross_version_binary_delta import (
    CrossVersionBinaryDeltaError,
    build_cross_version_binary_delta,
    write_cross_version_binary_delta,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic exact-entry delta for two client JARs."
        )
    )
    parser.add_argument("old_jar", type=Path)
    parser.add_argument("new_jar", type=Path)
    parser.add_argument("--old-build-id", required=True)
    parser.add_argument("--new-build-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    try:
        report = build_cross_version_binary_delta(
            args.old_jar,
            args.new_jar,
            old_build_id=args.old_build_id,
            new_build_id=args.new_build_id,
        )
        write_cross_version_binary_delta(report, args.out)
    except (CrossVersionBinaryDeltaError, OSError) as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            {
                "report_id": report["report_id"],
                "old_sha256": report["old_sha256"],
                "new_sha256": report["new_sha256"],
                "changed_entries": report["summary"][
                    "changed_entries"
                ],
                "out": str(args.out),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
