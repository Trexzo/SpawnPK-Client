from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .member_safety_carryforward import (
    MemberSafetyCarryForwardError,
    carry_forward_member_safety_acceptance,
    write_json,
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MemberSafetyCarryForwardError(
            f"expected JSON object: {path}"
        )
    return value


def main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "Carry a reviewed member-safety acceptance to another exact "
            "build only when every member risk is semantically identical."
        )
    )
    p.add_argument("previous_plan", type=Path)
    p.add_argument("previous_report", type=Path)
    p.add_argument("previous_acceptance", type=Path)
    p.add_argument("target_plan", type=Path)
    p.add_argument("target_report", type=Path)
    p.add_argument("--report-out", type=Path, required=True)
    p.add_argument("--acceptance-out", type=Path, required=True)
    args = p.parse_args()

    try:
        report, acceptance = carry_forward_member_safety_acceptance(
            _load(args.previous_plan),
            _load(args.previous_report),
            _load(args.previous_acceptance),
            _load(args.target_plan),
            _load(args.target_report),
        )
        write_json(report, args.report_out)
        if acceptance is not None:
            write_json(acceptance, args.acceptance_out)
        elif args.acceptance_out.exists():
            args.acceptance_out.unlink()
    except (
        MemberSafetyCarryForwardError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print(
        "SPK_MEMBER_SAFETY_CARRY_FORWARD_PASS"
        if report["full_carryforward_ready"]
        else "SPK_MEMBER_SAFETY_CARRY_FORWARD_BLOCKED"
    )
    print(f"report_id={report['report_id']}")
    print(
        "full_carryforward_ready="
        + str(report["full_carryforward_ready"]).lower()
    )
    print(
        f"transferred_member_count={report['transferred_member_count']}"
    )
    print(
        f"blocked_member_count={report['blocked_member_count']}"
    )
    print(f"report_out={args.report_out}")
    if acceptance is not None:
        print(f"acceptance_out={args.acceptance_out}")
    return 0 if report["full_carryforward_ready"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
