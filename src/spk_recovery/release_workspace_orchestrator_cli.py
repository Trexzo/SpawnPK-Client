from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .lineage import load_lineage
from .member_lineage import load_member_lineage
from .release_orchestrator import (
    ExistingAuthorityReleaseError,
    build_existing_authority_release_from_workspace,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-release-build-recovered"
    )
    p.add_argument("source_jar", type=Path)
    p.add_argument("source_index", type=Path)
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("recovered_manifest", type=Path)
    p.add_argument("recovered_source_root", type=Path)
    p.add_argument("private_collision_plan", type=Path)
    p.add_argument("--build-id", required=True)
    p.add_argument(
        "--target-package",
        default="recovered/spawnpk/client",
    )
    p.add_argument("--source-safe-fallback", action="store_true")
    p.add_argument(
        "--fallback-name-prefix",
        default="Recovered_",
    )
    p.add_argument("--member-safety-acceptance", type=Path)
    p.add_argument(
        "--allow-package-resource-risk",
        action="store_true",
    )
    p.add_argument(
        "--rewrite-class-name-strings",
        action="store_true",
    )
    p.add_argument(
        "--source-prefix",
        action="append",
        dest="source_prefixes",
    )
    p.add_argument("--java-command", default="java")
    p.add_argument("--javac-command", default="javac")
    p.add_argument(
        "--private-diagnostic-report-out",
        type=Path,
        help=(
            "write a private identifier-bearing javac classification report; "
            "never commit this artifact"
        ),
    )
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = build_existing_authority_release_from_workspace(
            args.source_jar,
            _load(args.source_index),
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            _load(args.recovered_manifest),
            args.recovered_source_root,
            args.private_collision_plan,
            build_id=args.build_id,
            out_dir=args.out_dir,
            target_package=args.target_package,
            source_safe_fallback=args.source_safe_fallback,
            fallback_name_prefix=args.fallback_name_prefix,
            member_safety_acceptance=(
                _load(args.member_safety_acceptance)
                if args.member_safety_acceptance
                else None
            ),
            allow_package_resource_risk=(
                args.allow_package_resource_risk
            ),
            rewrite_class_name_strings=(
                args.rewrite_class_name_strings
            ),
            source_prefixes=args.source_prefixes,
            private_diagnostic_report_out=(
                args.private_diagnostic_report_out
            ),
            java_command=args.java_command,
            javac_command=args.javac_command,
        )
    except (
        ExistingAuthorityReleaseError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_RECOVERY_RELEASE_BUILD_RECOVERED")
    print(f"run_id={report['run_id']}")
    print(f"status={report['status']}")
    print(
        "ready_for_release="
        + str(report["ready_for_release"]).lower()
    )
    print(f"terminal_stage={report['terminal_stage']}")
    collision_plan_id = report.get(
        "stage_ids",
        {},
    ).get("collision_plan_id")
    if collision_plan_id is not None:
        print(f"collision_plan_id={collision_plan_id}")
    collision_transform_id = report.get(
        "stage_ids",
        {},
    ).get("collision_transform_id")
    if collision_transform_id is not None:
        print(
            "collision_transform_id="
            f"{collision_transform_id}"
        )
    if args.private_diagnostic_report_out is not None:
        print(
            "private_diagnostic_report_out="
            f"{args.private_diagnostic_report_out.resolve()}"
        )
    print(f"out_dir={args.out_dir}")
    return 0 if report["ready_for_release"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
