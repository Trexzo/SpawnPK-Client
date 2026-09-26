from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .class_recovery_plan import (
    ClassRecoveryPlanError,
    build_class_recovery_plan,
    write_class_recovery_plan,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-class-recovery-plan")
    p.add_argument("diagnostic_report", type=Path)
    p.add_argument("readable_jar", type=Path)
    p.add_argument("source_root", type=Path)
    p.add_argument("recovered_manifest", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--include-identifiers",
        action="store_true",
    )
    args = p.parse_args(argv)

    try:
        diagnostic = json.loads(
            args.diagnostic_report.read_text(encoding="utf-8")
        )
        recovered = json.loads(
            args.recovered_manifest.read_text(encoding="utf-8")
        )
        report = build_class_recovery_plan(
            diagnostic,
            args.readable_jar,
            args.source_root,
            recovered,
            include_identifiers=args.include_identifiers,
        )
        write_class_recovery_plan(report, args.out)
    except (
        ClassRecoveryPlanError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_CLASS_RECOVERY_PLAN_PASS")
    print(f"plan_id={report['plan_id']}")
    print(
        "missing_unique_class_count="
        f"{summary['missing_unique_class_count']}"
    )
    print(
        "responsibility_counts="
        + json.dumps(
            summary["responsibility_counts"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "access_counts="
        + json.dumps(
            summary["access_counts"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "safe_source_recovery_candidate_count="
        f"{summary['safe_source_recovery_candidate_count']}"
    )
    print(
        "dependency_responsibility_count="
        f"{summary['dependency_responsibility_count']}"
    )
    print(
        "project_identity_mismatch_count="
        f"{summary['project_identity_mismatch_count']}"
    )
    print(
        "project_source_unit_missing_count="
        f"{summary['project_source_unit_missing_count']}"
    )
    print(f"identifiers_included={report['identifiers_included']}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
