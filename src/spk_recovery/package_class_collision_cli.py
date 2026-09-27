from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .package_class_collision import (
    PackageClassCollisionError,
    analyze_package_class_collisions,
    write_package_class_collision_report,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-package-class-collision"
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
        report = analyze_package_class_collisions(
            args.private_plan,
            args.jar,
            include_identifiers=args.include_identifiers,
        )
        write_package_class_collision_report(
            report,
            args.out,
        )
    except (
        PackageClassCollisionError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_PACKAGE_CLASS_COLLISION_PASS")
    print(
        "collision_topology_id="
        f"{report['collision_topology_id']}"
    )
    print(
        "candidate_count="
        f"{summary['candidate_count']}"
    )
    print(
        "colliding_candidate_count="
        f"{summary['colliding_candidate_count']}"
    )
    print(
        "unique_blocker_count="
        f"{summary['unique_blocker_count']}"
    )
    print(
        "component_count="
        f"{summary['component_count']}"
    )
    print(
        "blocking_prefix_counts="
        + json.dumps(
            summary["blocking_prefix_counts"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "direct_reference_holder_count="
        f"{summary['direct_reference_holder_count']}"
    )
    print(
        f"identifiers_included={report['identifiers_included']}"
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
