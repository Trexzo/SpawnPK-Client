from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .collision_remap_apply import (
    CollisionRemapApplyError,
    apply_collision_remap_plan,
    write_collision_remap_application,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-collision-remap-apply"
    )
    p.add_argument("private_remap_plan", type=Path)
    p.add_argument("input_jar", type=Path)
    p.add_argument("output_jar", type=Path)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument(
        "--include-identifiers",
        action="store_true",
    )
    args = p.parse_args(argv)

    try:
        report = apply_collision_remap_plan(
            args.private_remap_plan,
            args.input_jar,
            args.output_jar,
            include_identifiers=args.include_identifiers,
        )
        write_collision_remap_application(
            report,
            args.report,
        )
    except (
        CollisionRemapApplyError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_COLLISION_REMAP_APPLY_PASS")
    print(f"application_id={report['application_id']}")
    print(
        "mapping_count="
        f"{summary['mapping_count']}"
    )
    print(
        "changed_class_entry_count="
        f"{summary['changed_class_entry_count']}"
    )
    print(
        "unchanged_entry_count="
        f"{summary['unchanged_entry_count']}"
    )
    print(
        "remaining_old_reference_count="
        f"{summary['remaining_old_reference_count']}"
    )
    print(
        "verified_target_count="
        f"{summary['verified_target_count']}"
    )
    print(
        "output_jar_sha256="
        f"{report['output_jar_sha256']}"
    )
    print(
        f"identifiers_included={report['identifiers_included']}"
    )
    print(f"report={args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
