from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .lineage import load_lineage
from .member_lineage import load_member_lineage
from .source_name_carryforward import (
    SourceNameCarryForwardError,
    carry_forward_source_names,
    write_carryforward_outputs,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-source-name-carry-forward")
    p.add_argument("previous_plan", type=Path)
    p.add_argument("old_inventory", type=Path)
    p.add_argument("new_inventory", type=Path)
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("--class-delta", type=Path)
    p.add_argument("--member-delta", type=Path)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report, candidates, review, acceptance, plan = (
            carry_forward_source_names(
                _load(args.previous_plan),
                _load(args.old_inventory),
                _load(args.new_inventory),
                load_lineage(args.class_lineage),
                load_member_lineage(args.member_lineage),
                class_delta_report=(
                    _load(args.class_delta)
                    if args.class_delta
                    else None
                ),
                member_delta_report=(
                    _load(args.member_delta)
                    if args.member_delta
                    else None
                ),
            )
        )
        write_carryforward_outputs(
            report,
            candidates,
            review,
            acceptance,
            plan,
            args.out_dir,
        )
    except (
        SourceNameCarryForwardError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_RECOVERY_SOURCE_NAME_CARRY_FORWARD_COMPLETE")
    print(f"report_id={report['report_id']}")
    print(
        "full_carryforward_ready="
        + str(report["full_carryforward_ready"]).lower()
    )
    print(
        "safe_rewrite_plan_available="
        + str(report["safe_rewrite_plan_available"]).lower()
    )
    for key, value in report["summary"].items():
        print(f"{key}={value}")
    print(f"out_dir={args.out_dir}")
    return 0 if report["full_carryforward_ready"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
