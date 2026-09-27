from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .namespace_collision import (
    NamespaceCollisionError,
    analyze_namespace_collisions,
    write_namespace_collision_report,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-namespace-collision"
    )
    p.add_argument("readable_jar", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--include-identifiers",
        action="store_true",
    )
    args = p.parse_args(argv)

    try:
        report = analyze_namespace_collisions(
            args.readable_jar,
            include_identifiers=args.include_identifiers,
        )
        write_namespace_collision_report(
            report,
            args.out,
        )
    except (
        NamespaceCollisionError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_NAMESPACE_COLLISION_PASS")
    print(f"report_id={report['report_id']}")
    print(
        "class_count="
        f"{summary['class_count']}"
    )
    print(
        "affected_class_count="
        f"{summary['affected_class_count']}"
    )
    print(
        "blocking_class_count="
        f"{summary['blocking_class_count']}"
    )
    print(
        "collision_component_count="
        f"{summary['collision_component_count']}"
    )
    print(
        "collision_edge_count="
        f"{summary['collision_edge_count']}"
    )
    print(
        "blocking_depth_counts="
        + json.dumps(
            summary["blocking_depth_counts"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "max_blocking_prefixes_per_target="
        f"{summary['max_blocking_prefixes_per_target']}"
    )
    print(
        "identifiers_included="
        f"{report['identifiers_included']}"
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
