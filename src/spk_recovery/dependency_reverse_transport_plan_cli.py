from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .dependency_reverse_transport_plan import (
    DependencyReverseTransportPlanError,
    build_dependency_reverse_transport_plan,
    write_dependency_reverse_transport_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-dependency-reverse-transport-plan"
    )
    parser.add_argument(
        "dependency_remap_report",
        type=Path,
    )
    parser.add_argument(
        "private_replacement_plan",
        type=Path,
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--include-identifiers",
        action="store_true",
    )
    args = parser.parse_args(argv)

    try:
        report = build_dependency_reverse_transport_plan(
            args.dependency_remap_report,
            args.private_replacement_plan,
            include_identifiers=args.include_identifiers,
        )
        write_dependency_reverse_transport_plan(
            report,
            args.out,
        )
    except (
        DependencyReverseTransportPlanError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_DEPENDENCY_REVERSE_TRANSPORT_PLAN_PASS")
    print(
        "reverse_plan_id="
        f"{report['reverse_plan_id']}"
    )
    print(
        "class_reverse_count="
        f"{summary['class_reverse_count']}"
    )
    print(
        "member_reverse_count="
        f"{summary['member_reverse_count']}"
    )
    print(
        "blocker_count="
        f"{summary['blocker_count']}"
    )
    print(
        "ready_for_bytecode_restore="
        f"{summary['ready_for_bytecode_restore']}"
    )
    print(
        "identifiers_included="
        f"{report['identifiers_included']}"
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
