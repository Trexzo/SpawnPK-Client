from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .dependency_source_edit_plan import (
    DependencySourceEditPlanError,
    build_dependency_source_edit_plan,
    write_dependency_source_edit_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-dependency-source-edit-plan"
    )
    parser.add_argument(
        "private_binding_inventory",
        type=Path,
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
        report = build_dependency_source_edit_plan(
            args.private_binding_inventory,
            args.dependency_remap_report,
            args.private_replacement_plan,
            include_identifiers=args.include_identifiers,
        )
        write_dependency_source_edit_plan(
            report,
            args.out,
        )
    except (
        DependencySourceEditPlanError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_DEPENDENCY_SOURCE_EDIT_PLAN_PASS")
    print(f"edit_plan_id={report['edit_plan_id']}")
    print(
        "action_counts="
        + json.dumps(
            summary["action_counts"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "blocker_count="
        f"{summary['blocker_count']}"
    )
    print(
        "ready_for_source_overlay="
        f"{summary['ready_for_source_overlay']}"
    )
    print(
        "identifiers_included="
        f"{report['identifiers_included']}"
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
