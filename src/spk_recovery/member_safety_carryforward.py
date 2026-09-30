from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .member_safety import (
    MemberSafetyError,
    validate_member_safety_acceptance,
)


class MemberSafetyCarryForwardError(ValueError):
    pass


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _risk_signature(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key)
        for key in (
            "member_id",
            "kind",
            "owner_internal_name",
            "source_name",
            "descriptor",
            "target_name",
            "access",
            "hazards",
            "risk_level",
        )
    }


def _load_decisions(
    report: dict[str, Any],
    acceptance: dict[str, Any],
) -> dict[str, str]:
    by_risk = {
        str(row.get("risk_id")): row
        for row in report.get("members", [])
        if isinstance(row, dict)
    }
    out: dict[str, str] = {}
    for decision in acceptance.get("allow", []):
        if not isinstance(decision, dict):
            continue
        risk_id = str(decision.get("risk_id") or "")
        if risk_id not in by_risk:
            continue
        member_id = str(by_risk[risk_id].get("member_id") or "")
        reason = str(decision.get("reason") or "")
        if member_id:
            out[member_id] = reason
    return out


def carry_forward_member_safety_acceptance(
    previous_plan: dict[str, Any],
    previous_report: dict[str, Any],
    previous_acceptance: dict[str, Any],
    target_plan: dict[str, Any],
    target_report: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Carry reviewed member-safety acceptance only across exact risk equivalence.

    Build-specific source SHA, plan digest, report ID and risk IDs may differ.
    All member identity, rename target, access, risk level and hazard evidence
    must remain exactly equal. Partial transfer is intentionally refused.
    """
    try:
        validate_member_safety_acceptance(
            previous_plan,
            previous_report,
            previous_acceptance,
        )
    except MemberSafetyError as exc:
        raise MemberSafetyCarryForwardError(
            f"previous acceptance is invalid: {exc}"
        ) from exc

    target_members = [
        row
        for row in target_report.get("members", [])
        if isinstance(row, dict)
    ]
    if not target_members:
        raise MemberSafetyCarryForwardError(
            "target member safety report has no members"
        )

    probe_acceptance = {
        "schema_version": 1,
        "kind": "member_safety_acceptance",
        "report_id": target_report.get("report_id"),
        "allow": [
            {
                "risk_id": row.get("risk_id"),
                "reason": "target report integrity probe",
            }
            for row in target_members
        ],
    }
    try:
        validate_member_safety_acceptance(
            target_plan,
            target_report,
            probe_acceptance,
        )
    except MemberSafetyError as exc:
        raise MemberSafetyCarryForwardError(
            f"target report is invalid for target plan: {exc}"
        ) from exc

    previous_rows = {
        str(row.get("member_id")): row
        for row in previous_report.get("members", [])
        if isinstance(row, dict)
        and isinstance(row.get("member_id"), str)
    }
    target_rows = {
        str(row.get("member_id")): row
        for row in target_members
        if isinstance(row.get("member_id"), str)
    }

    blockers: list[dict[str, Any]] = []
    old_ids = set(previous_rows)
    new_ids = set(target_rows)

    for member_id in sorted(old_ids - new_ids):
        blockers.append(
            {
                "member_id": member_id,
                "reason": "member_missing_from_target_report",
            }
        )
    for member_id in sorted(new_ids - old_ids):
        blockers.append(
            {
                "member_id": member_id,
                "reason": "new_member_not_present_in_previous_review",
            }
        )

    decisions = _load_decisions(
        previous_report,
        previous_acceptance,
    )

    transferred: list[dict[str, Any]] = []
    for member_id in sorted(old_ids & new_ids):
        old_row = previous_rows[member_id]
        new_row = target_rows[member_id]
        old_sig = _risk_signature(old_row)
        new_sig = _risk_signature(new_row)
        if old_sig != new_sig:
            blockers.append(
                {
                    "member_id": member_id,
                    "reason": "risk_semantics_changed",
                    "previous": old_sig,
                    "target": new_sig,
                }
            )
            continue

        old_reason = decisions.get(member_id)
        if not old_reason:
            blockers.append(
                {
                    "member_id": member_id,
                    "reason": "previous_review_reason_missing",
                }
            )
            continue

        transferred.append(
            {
                "member_id": member_id,
                "previous_risk_id": old_row.get("risk_id"),
                "target_risk_id": new_row.get("risk_id"),
                "previous_reason": old_reason,
            }
        )

    full_ready = (
        not blockers
        and len(transferred) == len(target_rows)
        and len(target_rows) == len(previous_rows)
    )

    acceptance: dict[str, Any] | None = None
    if full_ready:
        acceptance = {
            "schema_version": 1,
            "kind": "member_safety_acceptance",
            "report_id": target_report["report_id"],
            "allow": [
                {
                    "risk_id": row["target_risk_id"],
                    "reason": (
                        "Risk-equivalent carry-forward from "
                        f"{previous_report['report_id']}: "
                        + row["previous_reason"]
                    ),
                }
                for row in transferred
            ],
        }
        try:
            validate_member_safety_acceptance(
                target_plan,
                target_report,
                acceptance,
            )
        except MemberSafetyError as exc:
            raise MemberSafetyCarryForwardError(
                f"generated target acceptance failed validation: {exc}"
            ) from exc

    material = {
        "previous_report_id": previous_report.get("report_id"),
        "target_report_id": target_report.get("report_id"),
        "previous_source_sha256": previous_report.get("source_sha256"),
        "target_source_sha256": target_report.get("source_sha256"),
        "transferred": [
            (
                row["member_id"],
                row["previous_risk_id"],
                row["target_risk_id"],
            )
            for row in transferred
        ],
        "blockers": blockers,
    }
    report_id = (
        "MEMRISKCF_"
        + hashlib.sha256(_stable_json(material))
        .hexdigest()[:20]
        .upper()
    )

    report = {
        "schema_version": 1,
        "kind": "member_safety_carryforward_report",
        "report_id": report_id,
        "previous_report_id": previous_report.get("report_id"),
        "target_report_id": target_report.get("report_id"),
        "previous_source_sha256": previous_report.get("source_sha256"),
        "target_source_sha256": target_report.get("source_sha256"),
        "full_carryforward_ready": full_ready,
        "previous_member_count": len(previous_rows),
        "target_member_count": len(target_rows),
        "transferred_member_count": len(transferred),
        "blocked_member_count": len(blockers),
        "transferred": transferred,
        "blockers": blockers,
        "note": (
            "Carry-forward proves exact member-safety risk equivalence after "
            "excluding only build-specific source SHA, plan/report IDs and "
            "risk IDs. Any changed risk semantics require fresh review."
        ),
    }
    return report, acceptance


def write_json(doc: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
