from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from .member_safety import (
    MemberSafetyError,
    validate_member_safety_acceptance,
)


EXPECTED_V308_SHA256 = (
    "854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
)
EXPECTED_REPORT_ID = "MEMRISKREVIEW_E4E67B1125E7AFA4F3B7"
EXPECTED_ACCEPTANCE_SHA256 = (
    "f4c6c2b3ee1da51ce76b89164abe5fc47960ad9eceee952619928190f1374351"
)
EXPECTED_ACCEPTANCE_SIZE = 2134
EXPECTED_MEMBER_COUNT = 10
EXPECTED_REASON = (
    "Exact-v308 local regeneration of previously reviewed Main/Core "
    "member-safety report "
    + EXPECTED_REPORT_ID
    + "."
)

EXPECTED_RISK_IDS = [
    "MEMRISK_0FAE7E6D84569593E31D",
    "MEMRISK_06FEF57C163A0FDDC705",
    "MEMRISK_46F4CA572E69324C9A59",
    "MEMRISK_E6A5496DF0F734733390",
    "MEMRISK_10EA60355B99C53A2B4F",
    "MEMRISK_202D62D688509824B0E8",
    "MEMRISK_4A1E709DF16D814A70C5",
    "MEMRISK_5737870A18D818D439A0",
    "MEMRISK_36BB826CFA7F04D8B008",
    "MEMRISK_8A6DC63EA7CEC5BEBCEA",
]


class SourceM1MemberSafetyRecoveryError(ValueError):
    pass


def _exact_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise SourceM1MemberSafetyRecoveryError(
                f"duplicate JSON key: {key!r}"
            )
        out[key] = value
    return out


def _load(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_exact_object,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceM1MemberSafetyRecoveryError(
            f"could not read JSON {path}: {exc}"
        ) from exc
    if not isinstance(doc, dict):
        raise SourceM1MemberSafetyRecoveryError(
            f"JSON root must be an object: {path}"
        )
    return doc


def build_historical_acceptance(
    report: dict[str, Any],
) -> dict[str, Any]:
    if report.get("schema_version") != 1:
        raise SourceM1MemberSafetyRecoveryError(
            "safety report schema_version must be 1"
        )
    if report.get("kind") != "member_safety_report":
        raise SourceM1MemberSafetyRecoveryError(
            "safety report kind mismatch"
        )
    if report.get("report_id") != EXPECTED_REPORT_ID:
        raise SourceM1MemberSafetyRecoveryError(
            "safety report is not the historically reviewed exact-v308 report"
        )
    if str(report.get("source_sha256", "")).lower() != EXPECTED_V308_SHA256:
        raise SourceM1MemberSafetyRecoveryError(
            "safety report is not bound to exact v308"
        )

    members = report.get("members")
    if not isinstance(members, list) or len(members) != EXPECTED_MEMBER_COUNT:
        raise SourceM1MemberSafetyRecoveryError(
            f"expected {EXPECTED_MEMBER_COUNT} reviewed safety members"
        )

    risk_ids = [row.get("risk_id") for row in members if isinstance(row, dict)]
    if risk_ids != EXPECTED_RISK_IDS:
        raise SourceM1MemberSafetyRecoveryError(
            "safety report risk ordering/identity does not match "
            "the historically reviewed exact-v308 report"
        )

    return {
        "schema_version": 1,
        "kind": "member_safety_acceptance",
        "report_id": EXPECTED_REPORT_ID,
        "allow": [
            {
                "risk_id": risk_id,
                "reason": EXPECTED_REASON,
            }
            for risk_id in risk_ids
        ],
    }


def historical_acceptance_bytes(
    acceptance: dict[str, Any],
) -> bytes:
    payload = (
        json.dumps(
            acceptance,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")
    if len(payload) != EXPECTED_ACCEPTANCE_SIZE:
        raise SourceM1MemberSafetyRecoveryError(
            "recovered safety acceptance byte size does not match "
            f"historical authority: {len(payload)} != "
            f"{EXPECTED_ACCEPTANCE_SIZE}"
        )
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_ACCEPTANCE_SHA256:
        raise SourceM1MemberSafetyRecoveryError(
            "recovered safety acceptance SHA-256 does not match "
            f"historical authority: {digest}"
        )
    return payload


def recover_v308_member_safety_acceptance(
    member_plan: dict[str, Any],
    report: dict[str, Any],
) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    acceptance = build_historical_acceptance(report)
    payload = historical_acceptance_bytes(acceptance)
    try:
        summary = validate_member_safety_acceptance(
            member_plan,
            report,
            acceptance,
        )
    except MemberSafetyError as exc:
        raise SourceM1MemberSafetyRecoveryError(str(exc)) from exc

    if summary.get("report_id") != EXPECTED_REPORT_ID:
        raise SourceM1MemberSafetyRecoveryError(
            "validated report identity drifted"
        )
    if summary.get("approved_members") != EXPECTED_MEMBER_COUNT:
        raise SourceM1MemberSafetyRecoveryError(
            "validated approval count drifted"
        )
    if summary.get("high_approved") != 7:
        raise SourceM1MemberSafetyRecoveryError(
            "validated high-risk approval count drifted"
        )
    if summary.get("critical_approved") != 0:
        raise SourceM1MemberSafetyRecoveryError(
            "validated critical-risk approval count drifted"
        )
    return acceptance, payload, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-source-m1-member-safety-recover",
        description=(
            "Recover the one historically reviewed exact-v308 "
            "member-safety acceptance and refuse any byte drift."
        ),
    )
    parser.add_argument("member_plan", type=Path)
    parser.add_argument("safety_report", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        acceptance, payload, summary = (
            recover_v308_member_safety_acceptance(
                _load(args.member_plan),
                _load(args.safety_report),
            )
        )
    except SourceM1MemberSafetyRecoveryError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(payload)

    print("SPK_SOURCE_M1_MEMBER_SAFETY_RECOVERY_PASS")
    print(f"report_id={acceptance['report_id']}")
    print(f"acceptance_sha256={EXPECTED_ACCEPTANCE_SHA256}")
    print(f"acceptance_bytes={len(payload)}")
    print(f"approved_members={summary['approved_members']}")
    print(f"high_approved={summary['high_approved']}")
    print(f"critical_approved={summary['critical_approved']}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
