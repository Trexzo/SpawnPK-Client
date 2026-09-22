from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.member_safety import (
    MemberSafetyError,
    build_member_safety_report,
    validate_member_safety_acceptance,
)


def _jar(root: Path) -> Path:
    path = root / "source.jar"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
        z.writestr(
            "rs/A.class",
            b"Lrs/eventbus/Subscribe; ordinary class bytes",
        )
        z.writestr(
            "rs/R.class",
            b"java/lang/Class getDeclaredMethod "
            b"java/lang/reflect/Method getName a",
        )
    return path


def _index(path: Path) -> dict:
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "sha256": sha,
        "classes": {
            "rs/A.class": {
                "internal_name": "rs/A",
                "literal_strings": [],
                "fields": [
                    {
                        "name": "x",
                        "descriptor": "I",
                        "access": 0x0001,
                    }
                ],
                "methods": [
                    {
                        "name": "a",
                        "descriptor": "()V",
                        "access": 0x0002,
                        "code_length": 5,
                    }
                ],
            },
            "rs/R.class": {
                "internal_name": "rs/R",
                "literal_strings": ["a"],
                "fields": [],
                "methods": [],
            },
        },
    }


def _plan(sha: str) -> dict:
    return {
        "schema_version": 1,
        "kind": "member_remap_plan",
        "build_id": "test",
        "source_sha256": sha,
        "field_count": 1,
        "method_count": 1,
        "member_count": 2,
        "members": [
            {
                "member_id": "CLIENT_FIELD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "field",
                "owner_internal_name": "rs/A",
                "source_name": "x",
                "descriptor": "I",
                "target_name": "value",
                "confidence": 0.99,
                "provenance": [{"source": "unit"}],
            },
            {
                "member_id": "CLIENT_METHOD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "method",
                "owner_internal_name": "rs/A",
                "source_name": "a",
                "descriptor": "()V",
                "target_name": "runTask",
                "confidence": 0.99,
                "provenance": [{"source": "unit"}],
            },
        ],
    }


class MemberSafetyTests(unittest.TestCase):
    def test_reports_visibility_reflection_and_eventbus_risks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _jar(root)
            index = _index(jar)
            report = build_member_safety_report(
                jar,
                index,
                _plan(index["sha256"]),
            )
            self.assertEqual(report["member_count"], 2)
            self.assertTrue(
                report["report_id"].startswith("MEMRISKREVIEW_")
            )
            by_id = {
                row["member_id"]: row
                for row in report["members"]
            }
            field_codes = {
                h["code"]
                for h in by_id["CLIENT_FIELD_000001"]["hazards"]
            }
            method_codes = {
                h["code"]
                for h in by_id["CLIENT_METHOD_000001"]["hazards"]
            }
            self.assertIn("public_api", field_codes)
            self.assertIn(
                "source_name_literal_in_reflection_surface",
                method_codes,
            )
            self.assertIn(
                "eventbus_subscribe_owner",
                method_codes,
            )
            self.assertEqual(
                by_id["CLIENT_METHOD_000001"]["risk_level"],
                "high",
            )

    def test_acceptance_must_cover_every_exact_risk_id(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _jar(root)
            index = _index(jar)
            plan = _plan(index["sha256"])
            report = build_member_safety_report(
                jar,
                index,
                plan,
            )
            one = report["members"][0]
            acceptance = {
                "schema_version": 1,
                "kind": "member_safety_acceptance",
                "report_id": report["report_id"],
                "allow": [
                    {
                        "risk_id": one["risk_id"],
                        "reason": "reviewed",
                    }
                ],
            }
            with self.assertRaises(MemberSafetyError):
                validate_member_safety_acceptance(
                    plan,
                    report,
                    acceptance,
                )

            acceptance["allow"] = [
                {
                    "risk_id": row["risk_id"],
                    "reason": "reviewed exact test fixture",
                }
                for row in report["members"]
            ]
            summary = validate_member_safety_acceptance(
                plan,
                report,
                acceptance,
            )
            self.assertEqual(summary["approved_members"], 2)

    def test_stale_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _jar(root)
            index = _index(jar)
            plan = _plan(index["sha256"])
            report = build_member_safety_report(jar, index, plan)
            acceptance = {
                "schema_version": 1,
                "kind": "member_safety_acceptance",
                "report_id": report["report_id"],
                "allow": [
                    {
                        "risk_id": row["risk_id"],
                        "reason": "reviewed",
                    }
                    for row in report["members"]
                ],
            }
            changed = copy.deepcopy(plan)
            changed["members"][0]["target_name"] = "differentName"
            with self.assertRaises(MemberSafetyError):
                validate_member_safety_acceptance(
                    changed,
                    report,
                    acceptance,
                )


if __name__ == "__main__":
    unittest.main()
