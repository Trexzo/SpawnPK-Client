from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .namespace_collision_plan import (
    NamespaceCollisionPlanError,
    build_namespace_collision_plan,
    write_namespace_collision_plan,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-namespace-collision-plan"
    )
    p.add_argument("readable_jar", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--include-identifiers",
        action="store_true",
    )
    args = p.parse_args(argv)

    try:
        report = build_namespace_collision_plan(
            args.readable_jar,
            include_identifiers=args.include_identifiers,
        )
        write_namespace_collision_plan(
            report,
            args.out,
        )
    except (
        NamespaceCollisionPlanError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_NAMESPACE_COLLISION_PLAN_PASS")
    print(f"plan_id={report['plan_id']}")
    print(
        "collision_report_id="
        f"{report['collision_report_id']}"
    )
    print(
        "blocker_remap_count="
        f"{summary['blocker_remap_count']}"
    )
    print(
        "affected_target_count="
        f"{summary['affected_target_count']}"
    )
    print(
        "pre_collision_edge_count="
        f"{summary['pre_collision_edge_count']}"
    )
    print(
        "post_collision_edge_count="
        f"{summary['post_collision_edge_count']}"
    )
    print(
        "parent_package_preserved_count="
        f"{summary['parent_package_preserved_count']}"
    )
    print(
        "plan_eliminates_all_collisions="
        f"{summary['plan_eliminates_all_collisions']}"
    )
    print(
        "identifiers_included="
        f"{report['identifiers_included']}"
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
