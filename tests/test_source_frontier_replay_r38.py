"""R38: private v309 source frontier replay must remeasure facts, not trust notes."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.source_frontier_replay import (
    SourceFrontierReplayError,
    replay_frontier,
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac is required")
class SourceFrontierReplayTests(unittest.TestCase):
    def _jar(self, root: Path, name: str, *, fields: str, body: str) -> Path:
        src = root / name / "src" / "p"
        output = root / name / "classes"
        src.mkdir(parents=True)
        output.mkdir(parents=True)
        java = src / "A.java"
        java.write_text(
            "package p; public class A { " + fields +
            " public int get() { " + body + " } }",
            encoding="utf-8",
        )
        run = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(output), str(java)],
            capture_output=True, text=True,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        jar = root / (name + ".jar")
        with ZipFile(jar, "w") as archive:
            archive.write(output / "p" / "A.class", "p/A.class")
        return jar

    def _pair(self, root: Path, *, candidate_body="return 1;"):
        original = self._jar(
            root, "original",
            fields="public int value; public int missing;",
            body="return 1;",
        )
        candidate = self._jar(
            root, "candidate",
            fields="public int value;",
            body=candidate_body,
        )
        return original, candidate

    def _run(self, old: Path, new: Path, *, original_pin=None,
             candidate_pin=None, frontier=None):
        return replay_frontier(
            old, new, original_sha256=original_pin or _digest(old),
            candidate_sha256=candidate_pin or _digest(new),
            class_entry="p/A.class", frontier_path=frontier,
        )

    def test_measured_field_shortfall_not_hidden_by_exact_method_bodies(self):
        with tempfile.TemporaryDirectory() as d:
            old, new = self._pair(Path(d))
            report = self._run(old, new)
            m = report["measured"]
            self.assertEqual(m["original_field_declarations"], 2)
            self.assertEqual(m["candidate_field_declarations"], 1)
            self.assertEqual(m["missing_original_field_declarations"], 1)
            self.assertEqual(m["shared_field_declarations"], 1)
            self.assertEqual(m["exact_field_declaration_metadata"], 1)
            self.assertEqual(m["original_method_declarations"], 2)
            self.assertEqual(m["candidate_method_declarations"], 2)
            self.assertEqual(m["strict_method_body_instruction_parity_count"], 2)
            self.assertEqual(m["original_classfile_major"], 53)
            self.assertEqual(m["candidate_classfile_major"], 53)
            self.assertTrue(m["class_access_flags_equal"])
            self.assertFalse(report["source_equivalence_certified"])
            self.assertFalse(report["canonical_identity_accepted"])
            self.assertFalse(report["historical_R24_seven_method_claims_recertified"])
            self.assertNotIn("p/A", json.dumps(report))
            self.assertEqual(report, self._run(old, new))

    def test_changed_compiled_java_affects_strict_method_counts(self):
        with tempfile.TemporaryDirectory() as d:
            old, new = self._pair(Path(d), candidate_body="return 2;")
            report = self._run(old, new)
            self.assertEqual(report["measured"]["strict_method_body_instruction_parity_count"], 1)
            self.assertEqual(report["measured"]["strict_method_body_difference_count"], 1)

    def test_recorded_frontier_expected_dimensions_are_rechecked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old, new = self._pair(root)
            direct = self._run(old, new)
            m = direct["measured"]
            pin = {
                "schema_version": 1,
                "owner_lineage_accepted": False,
                "source_equivalence_certified": False,
                "client_source_published": False,
                "original_client_jar_sha256": direct["original_client_jar_sha256"],
                "private_candidate": {
                    key: m[key] for key in (
                        "compiled_class_sha256",
                        "original_field_declarations", "candidate_field_declarations",
                        "original_method_declarations", "candidate_method_declarations",
                        "missing_original_field_declarations",
                        "extra_candidate_field_declarations",
                        "shared_field_declarations",
                        "exact_field_declaration_metadata",
                        "changed_field_declaration_metadata",
                        "original_classfile_major",
                        "candidate_classfile_major",
                        "class_access_flags_equal", "superclass_equal",
                        "ordered_interfaces_equal",
                    )
                },
            }
            path = root / "frontier.json"
            path.write_text(json.dumps(pin), encoding="utf-8")
            checked = self._run(old, new, frontier=path)
            self.assertTrue(checked["recorded_frontier_remeasurable_dimensions_match"])
            self.assertFalse(checked["source_equivalence_certified"])
            pin["private_candidate"]["candidate_field_declarations"] = 2
            path.write_text(json.dumps(pin), encoding="utf-8")
            with self.assertRaisesRegex(
                SourceFrontierReplayError,
                "FRONTIER_REMEASURED_DRIFT_CANDIDATE_FIELD_DECLARATIONS",
            ):
                self._run(old, new, frontier=path)

    def test_changed_jar_hash_fails_before_parsing(self):
        with tempfile.TemporaryDirectory() as d:
            old, new = self._pair(Path(d))
            with self.assertRaisesRegex(
                SourceFrontierReplayError, "ORIGINAL_OR_CANDIDATE_JAR_PIN_MISMATCH",
            ):
                self._run(old, new, candidate_pin="0" * 64)

    def test_unverified_frontier_authority_claim_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old, new = self._pair(root)
            path = root / "frontier.json"
            path.write_text(json.dumps({
                "schema_version": 1,
                "owner_lineage_accepted": True,
                "source_equivalence_certified": False,
                "client_source_published": False,
            }), encoding="utf-8")
            with self.assertRaisesRegex(
                SourceFrontierReplayError, "FRONTIER_AUTHORITY_UNEXPECTED",
            ):
                self._run(old, new, frontier=path)

    def test_duplicate_class_member_zip_entry_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old, new = self._pair(root)
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with ZipFile(new, "a") as archive:
                    archive.writestr("p/A.class", b"invalid duplicate")
            with self.assertRaisesRegex(
                SourceFrontierReplayError, "CLASSFILE_ENTRY_MISSING_OR_DUPLICATE",
            ):
                self._run(old, new)


if __name__ == "__main__":
    unittest.main()
