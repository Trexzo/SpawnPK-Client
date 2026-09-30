from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.member_safety import build_member_safety_report
from spk_recovery.member_safety_carryforward import (
    carry_forward_member_safety_acceptance,
)


def _jar(root: Path, name: str, marker: bytes) -> Path:
    path = root / name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
        z.writestr("rs/A.class", b"ordinary class bytes")
        z.writestr("META-INF/build.txt", marker)
    return path


def _index(jar: Path) -> dict:
    sha = hashlib.sha256(jar.read_bytes()).hexdigest()
    return {
        "sha256": sha,
        "classes": {
            "rs/A.class": {
                "internal_name": "rs/A",
                "literal_strings": [],
                "fields": [],
                "methods": [
                    {
                        "name": "a",
                        "descriptor": "()V",
                        "access": 0x0002,
                        "code_length": 5,
                    }
                ],
            }
        },
    }


def _plan(sha: str, target: str = "runTask") -> dict:
    return {
        "schema_version": 1,
        "kind": "member_remap_plan",
        "build_id": "test",
        "source_sha256": sha,
        "field_count": 0,
        "method_count": 1,
        "member_count": 1,
        "members": [
            {
                "member_id": "CLIENT_METHOD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "method",
                "owner_internal_name": "rs/A",
                "source_name": "a",
                "descriptor": "()V",
                "target_name": target,
                "confidence": 0.99,
                "provenance": [{"source": "unit"}],
            }
        ],
    }


def _acceptance(report: dict) -> dict:
    return {
        "schema_version": 1,
        "kind": "member_safety_acceptance",
        "report_id": report["report_id"],
        "allow": [
            {
                "risk_id": report["members"][0]["risk_id"],
                "reason": "reviewed exact previous fixture",
            }
        ],
    }


class MemberSafetyCarryForwardTests(unittest.TestCase):
    def test_risk_equivalent_build_specific_ids_transfer(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old_jar = _jar(root, "old.jar", b"307")
            new_jar = _jar(root, "new.jar", b"308")
            old_index = _index(old_jar)
            new_index = _index(new_jar)
            old_plan = _plan(old_index["sha256"])
            new_plan = _plan(new_index["sha256"])
            old_report = build_member_safety_report(
                old_jar,
                old_index,
                old_plan,
            )
            new_report = build_member_safety_report(
                new_jar,
                new_index,
                new_plan,
            )

            self.assertNotEqual(
                old_report["report_id"],
                new_report["report_id"],
            )
            self.assertNotEqual(
                old_report["members"][0]["risk_id"],
                new_report["members"][0]["risk_id"],
            )

            report, acceptance = (
                carry_forward_member_safety_acceptance(
                    old_plan,
                    old_report,
                    _acceptance(old_report),
                    new_plan,
                    new_report,
                )
            )

            self.assertTrue(report["full_carryforward_ready"])
            self.assertEqual(report["transferred_member_count"], 1)
            self.assertEqual(report["blocked_member_count"], 0)
            self.assertIsNotNone(acceptance)
            self.assertEqual(
                acceptance["report_id"],
                new_report["report_id"],
            )
            self.assertEqual(
                acceptance["allow"][0]["risk_id"],
                new_report["members"][0]["risk_id"],
            )
            self.assertIn(
                old_report["report_id"],
                acceptance["allow"][0]["reason"],
            )

    def test_changed_rename_blocks_whole_transfer(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old_jar = _jar(root, "old.jar", b"307")
            new_jar = _jar(root, "new.jar", b"308")
            old_index = _index(old_jar)
            new_index = _index(new_jar)
            old_plan = _plan(old_index["sha256"])
            new_plan = _plan(
                new_index["sha256"],
                target="differentTask",
            )
            old_report = build_member_safety_report(
                old_jar,
                old_index,
                old_plan,
            )
            new_report = build_member_safety_report(
                new_jar,
                new_index,
                new_plan,
            )

            report, acceptance = (
                carry_forward_member_safety_acceptance(
                    old_plan,
                    old_report,
                    _acceptance(old_report),
                    new_plan,
                    new_report,
                )
            )

            self.assertFalse(report["full_carryforward_ready"])
            self.assertIsNone(acceptance)
            self.assertEqual(report["blocked_member_count"], 1)
            self.assertEqual(
                report["blockers"][0]["reason"],
                "risk_semantics_changed",
            )

    def test_changed_hazard_blocks_whole_transfer(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old_jar = _jar(root, "old.jar", b"307")
            new_jar = _jar(root, "new.jar", b"308")
            old_index = _index(old_jar)
            new_index = copy.deepcopy(_index(new_jar))
            new_index["classes"]["rs/A.class"][
                "methods"
            ][0]["access"] = 0x0001
            old_plan = _plan(old_index["sha256"])
            new_plan = _plan(new_index["sha256"])
            old_report = build_member_safety_report(
                old_jar,
                old_index,
                old_plan,
            )
            new_report = build_member_safety_report(
                new_jar,
                new_index,
                new_plan,
            )

            report, acceptance = (
                carry_forward_member_safety_acceptance(
                    old_plan,
                    old_report,
                    _acceptance(old_report),
                    new_plan,
                    new_report,
                )
            )

            self.assertFalse(report["full_carryforward_ready"])
            self.assertIsNone(acceptance)
            self.assertEqual(
                report["blockers"][0]["reason"],
                "risk_semantics_changed",
            )


if __name__ == "__main__":
    unittest.main()
