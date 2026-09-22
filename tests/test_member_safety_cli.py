from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.cli import main


class MemberSafetyCliTests(unittest.TestCase):
    def test_scan_and_validate_commands_execute(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = root / "source.jar"
            with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
                z.writestr("rs/A.class", b"ordinary class bytes")

            sha = hashlib.sha256(jar.read_bytes()).hexdigest()
            index = {
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
            plan = {
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
                        "target_name": "runTask",
                        "confidence": 0.99,
                        "provenance": [{"source": "unit"}],
                    }
                ],
            }

            index_path = root / "index.json"
            plan_path = root / "plan.json"
            report_path = root / "report.json"
            acceptance_path = root / "acceptance.json"
            index_path.write_text(json.dumps(index), encoding="utf-8")
            plan_path.write_text(json.dumps(plan), encoding="utf-8")

            rc = main(
                [
                    "member-safety-scan",
                    str(jar),
                    str(index_path),
                    str(plan_path),
                    "--out",
                    str(report_path),
                ]
            )
            self.assertEqual(rc, 0)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["member_count"], 1)

            acceptance = {
                "schema_version": 1,
                "kind": "member_safety_acceptance",
                "report_id": report["report_id"],
                "allow": [
                    {
                        "risk_id": report["members"][0]["risk_id"],
                        "reason": "reviewed exact unit fixture",
                    }
                ],
            }
            acceptance_path.write_text(
                json.dumps(acceptance),
                encoding="utf-8",
            )

            rc = main(
                [
                    "member-safety-validate",
                    str(plan_path),
                    str(report_path),
                    str(acceptance_path),
                ]
            )
            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
