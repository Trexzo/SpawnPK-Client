from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery.advanced_field_evidence import (
    _frontier,
    build_advanced_field_evidence,
)
from spk_recovery.bytecode_profile import profile_class_field_accesses


class AdvancedFieldEvidenceTests(unittest.TestCase):
    def test_frontier_only_uses_target_build_field_reviews(self):
        members = {
            "unresolved": [
                {
                    "new_build_id": "v309",
                    "kind": "member_identity_review",
                    "member_kind": "field",
                    "candidate": {
                        "old_owner": "rs/a.class",
                        "new_owner": "rs/b.class",
                        "old": {"name": "x", "descriptor": "I"},
                        "new": {"name": "y", "descriptor": "I"},
                    },
                },
                {
                    "new_build_id": "v309",
                    "kind": "member_identity_review",
                    "member_kind": "method",
                    "candidate": {},
                },
                {
                    "new_build_id": "v310",
                    "kind": "member_identity_review",
                    "member_kind": "field",
                    "candidate": {
                        "old_owner": "rs/c.class",
                        "new_owner": "rs/d.class",
                        "old": {"name": "a", "descriptor": "I"},
                        "new": {"name": "b", "descriptor": "I"},
                    },
                },
            ]
        }
        out = _frontier(members, new_build_id="v309")
        self.assertEqual(
            out,
            {
                ("rs/a", "rs/b"): {
                    "old": {("x", "I")},
                    "new": {("y", "I")},
                }
            },
        )

    def test_report_is_research_only_and_does_not_mutate_lineage(self):
        old_sha = "1" * 64
        new_sha = "2" * 64
        classes = {
            "builds": [
                {"build_id": "v308", "sha256": old_sha},
                {"build_id": "v309", "sha256": new_sha},
            ],
            "classes": [
                {
                    "logical_id": "CLIENT_CLASS_000001",
                    "lineage": [
                        {
                            "build_id": "v308",
                            "internal_name": "rs/a",
                        },
                        {
                            "build_id": "v309",
                            "internal_name": "rs/b",
                        },
                    ],
                }
            ],
        }
        members = {
            "members": [],
            "unresolved": [
                {
                    "new_build_id": "v309",
                    "kind": "member_identity_review",
                    "member_kind": "field",
                    "candidate": {
                        "old_owner": "rs/a.class",
                        "new_owner": "rs/b.class",
                        "old": {"name": "x", "descriptor": "I"},
                        "new": {"name": "y", "descriptor": "I"},
                    },
                }
            ],
        }
        old_profile = {
            "internal_name": "rs/a",
            "fields": [
                {
                    "name": "x",
                    "descriptor": "I",
                    "access": 25,
                    "constant_value": 7,
                }
            ],
            "methods": [],
        }
        new_profile = {
            "internal_name": "rs/b",
            "fields": [
                {
                    "name": "y",
                    "descriptor": "I",
                    "access": 25,
                    "constant_value": 7,
                }
            ],
            "methods": [],
        }

        with (
            patch(
                "spk_recovery.advanced_field_evidence.validate_lineage"
            ),
            patch(
                "spk_recovery.advanced_field_evidence.validate_member_lineage"
            ),
            patch(
                "spk_recovery.advanced_field_evidence.sha256_file",
                side_effect=[old_sha, new_sha],
            ),
            patch(
                "spk_recovery.advanced_field_evidence.profile_jar_class",
                side_effect=[old_profile, new_profile],
            ),
        ):
            report = build_advanced_field_evidence(
                classes,
                members,
                {"sha256": old_sha},
                {"sha256": new_sha},
                Path("old.jar"),
                Path("new.jar"),
                old_build_id="v308",
                new_build_id="v309",
            )

        self.assertFalse(report["canonical"])
        self.assertEqual(report["summary"]["input_unresolved_fields"], 1)
        self.assertEqual(report["summary"]["candidate_fields"], 1)
        self.assertEqual(report["summary"]["constant_value_exact"], 1)
        self.assertEqual(
            report["summary"]["remaining_unresolved_fields"],
            0,
        )
        self.assertEqual(
            members["unresolved"][0]["candidate"]["old"]["name"],
            "x",
        )


@unittest.skipUnless(shutil.which("javac"), "Java compiler required")
class ConstantValueProfileTests(unittest.TestCase):
    def test_profile_exposes_exact_jvm_constant_values(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "A.java"
            classes = root / "classes"
            classes.mkdir()
            src.write_text(
                "public class A { "
                "static final int I = 7; "
                "static final long L = 9L; "
                "static final double D = 2.5; "
                "static final String S = \"ok\"; "
                "int plain; "
                "}",
                encoding="utf-8",
            )
            compiled = subprocess.run(
                ["javac", "-d", str(classes), str(src)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                compiled.returncode,
                0,
                compiled.stdout + compiled.stderr,
            )

            profile = profile_class_field_accesses(
                (classes / "A.class").read_bytes()
            )
            values = {
                row["name"]: row.get("constant_value")
                for row in profile["fields"]
            }
            self.assertEqual(values["I"], 7)
            self.assertEqual(values["L"], 9)
            self.assertEqual(values["D"], 2.5)
            self.assertEqual(values["S"], "ok")
            self.assertIsNone(values["plain"])


if __name__ == "__main__":
    unittest.main()
