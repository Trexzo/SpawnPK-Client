from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .missing_class_recovery import (
    MissingClassRecoveryError,
    build_missing_class_recovery_plan,
    stage_missing_class_recovery,
    write_recovery_report,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-missing-class-recovery"
    )
    sub = p.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan")
    stage = sub.add_parser("stage")

    for parser in (plan, stage):
        parser.add_argument("diagnostic_report", type=Path)
        parser.add_argument("readable_manifest", type=Path)
        parser.add_argument("readable_jar", type=Path)
        parser.add_argument("source_root", type=Path)
        parser.add_argument(
            "--expected-candidate-count",
            type=int,
        )
        parser.add_argument(
            "--include-identifiers",
            action="store_true",
        )
        parser.add_argument("--out", type=Path, required=True)

    stage.add_argument("decompiler_jar", type=Path)
    stage.add_argument(
        "--decompiler-sha256",
        required=True,
    )
    stage.add_argument(
        "--stage-dir",
        type=Path,
        required=True,
    )
    stage.add_argument(
        "--java-command",
        default="java",
    )

    args = p.parse_args(argv)

    try:
        diagnostic = json.loads(
            args.diagnostic_report.read_text(encoding="utf-8")
        )
        manifest = json.loads(
            args.readable_manifest.read_text(encoding="utf-8")
        )
        if args.command == "plan":
            report = build_missing_class_recovery_plan(
                diagnostic,
                manifest,
                args.readable_jar,
                args.source_root,
                expected_candidate_count=(
                    args.expected_candidate_count
                ),
                include_identifiers=args.include_identifiers,
            )
        else:
            report = stage_missing_class_recovery(
                diagnostic,
                manifest,
                args.readable_jar,
                args.source_root,
                args.decompiler_jar,
                expected_decompiler_sha256=args.decompiler_sha256,
                stage_dir=args.stage_dir,
                expected_candidate_count=(
                    args.expected_candidate_count
                ),
                java_command=args.java_command,
                include_identifiers=args.include_identifiers,
            )
        write_recovery_report(report, args.out)
    except (
        MissingClassRecoveryError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_MISSING_CLASS_RECOVERY_PASS")
    if args.command == "plan":
        s = report["summary"]
        print(f"plan_id={report['plan_id']}")
        print(f"candidate_count={s['candidate_count']}")
        print(
            "project_candidate_count="
            f"{s['project_candidate_count']}"
        )
        print(
            "nonproject_candidate_count="
            f"{s['nonproject_candidate_count']}"
        )
        print(
            "target_states="
            + json.dumps(
                s["target_states"],
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        print(
            "kinds="
            + json.dumps(
                s["kinds"],
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        print(f"diagnostic_count={s['diagnostic_count']}")
    else:
        s = report["summary"]
        print(f"stage_id={report['stage_id']}")
        print(f"plan_id={report['plan_id']}")
        print(f"candidate_count={s['candidate_count']}")
        print(
            "materialized_count="
            f"{s['materialized_count']}"
        )
        print(f"java_file_count={s['java_file_count']}")
        print(
            "decompiler_batch_count="
            f"{s['decompiler_batch_count']}"
        )
        print(
            "normalization_action_count="
            f"{s['normalization_action_count']}"
        )
        print(
            "target_states="
            + json.dumps(
                s["target_states"],
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    print(f"identifiers_included={report['identifiers_included']}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
