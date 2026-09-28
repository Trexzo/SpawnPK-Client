from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .dependency_replacement_plan import (
    DependencyReplacementPlanError,
    build_dependency_replacement_plan,
    write_dependency_replacement_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-dependency-replacement-plan"
    )
    parser.add_argument("reference_surface", type=Path)
    parser.add_argument("dependency_remap_report", type=Path)
    parser.add_argument("bundled_jar", type=Path)
    parser.add_argument("artifact", type=Path, nargs="+")
    parser.add_argument("--retention-report", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--include-identifiers",
        action="store_true",
    )
    args = parser.parse_args(argv)

    try:
        report = build_dependency_replacement_plan(
            args.reference_surface,
            args.dependency_remap_report,
            args.bundled_jar,
            args.artifact,
            retention_report_path=args.retention_report,
            include_identifiers=args.include_identifiers,
        )
        write_dependency_replacement_plan(
            report,
            args.out,
        )
    except (
        DependencyReplacementPlanError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_DEPENDENCY_REPLACEMENT_PLAN_PASS")
    print(
        "replacement_plan_id="
        f"{report['replacement_plan_id']}"
    )
    print(
        "referenced_owner_count="
        f"{summary['referenced_owner_count']}"
    )
    print(
        "classification_counts="
        + json.dumps(
            summary["classification_counts"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "weighted_member_reference_counts="
        + json.dumps(
            summary["weighted_member_reference_counts"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "used_official_artifact_count="
        f"{summary['used_official_artifact_count']}"
    )
    print(
        "identifiers_included="
        f"{report['identifiers_included']}"
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
