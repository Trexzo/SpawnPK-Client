from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .package_class_remap_plan import (
    PackageClassRemapPlanError,
    build_package_class_remap_plan,
    write_package_class_remap_plan,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-package-class-remap-plan"
    )
    p.add_argument("private_plan", type=Path)
    p.add_argument("jar", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--include-identifiers",
        action="store_true",
    )
    args = p.parse_args(argv)

    try:
        report = build_package_class_remap_plan(
            args.private_plan,
            args.jar,
            include_identifiers=args.include_identifiers,
        )
        write_package_class_remap_plan(
            report,
            args.out,
        )
    except (
        PackageClassRemapPlanError,
        PackageClassCollisionError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_PACKAGE_CLASS_REMAP_PLAN_PASS")
    print(f"remap_plan_id={report['remap_plan_id']}")
    print(f"remap_count={summary['remap_count']}")
    print(
        "affected_candidate_count="
        f"{summary['affected_candidate_count']}"
    )
    print(
        "bytecode_reference_holder_count="
        f"{summary['bytecode_reference_holder_count']}"
    )
    print(
        "same_package_remap_count="
        f"{summary['same_package_remap_count']}"
    )
    print(
        "collision_free_target_count="
        f"{summary['collision_free_target_count']}"
    )
    print(
        f"identifiers_included={report['identifiers_included']}"
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
