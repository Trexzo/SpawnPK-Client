"""R40 tests use only independently compiled synthetic Java, never SpawnPK code."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.source_class_method_matrix import build_class_method_matrix
from spk_recovery.source_gap_worklist import (
    SourceGapWorklistError, build_source_gap_worklist,
    compare_source_gap_profiles,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReconstructedSourceWorklistTests(unittest.TestCase):
    def _jar(self, root: Path, name: str, java: str) -> Path:
        src = root / name / "src" / "p"
        classes = root / name / "classes"
        src.mkdir(parents=True)
        classes.mkdir(parents=True)
        file = src / "A.java"
        file.write_text("package p; public class A {" + java + "}",
                        encoding="utf-8")
        run = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(file)],
            capture_output=True, text=True,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        jar = root / (name + ".jar")
        with ZipFile(jar, "w") as archive:
            archive.write(classes / "p" / "A.class", "p/A.class")
        return jar

    def _pair(self, root: Path, candidate=None):
        original_java = (
            "public int present; public int hidden; public int other;"
            "public int util(){return hidden + 1;}"
            "public int check(){return util() + other;}"
            "public int keep(){return present;}"
        )
        candidate_java = candidate if candidate is not None else (
            "public int present;"
            "public int util(){return present + 1;}"
            "public int keep(){return present;}"
        )
        return self._jar(root, "original", original_java), self._jar(
            root, "candidate", candidate_java,
        )

    def _run(self, original: Path, candidate: Path, *, old_sha=None,
             new_sha=None):
        return build_source_gap_worklist(
            original, candidate,
            original_sha256=old_sha or _sha(original),
            candidate_sha256=new_sha or _sha(candidate),
            class_entry="p/A.class",
        )

    def test_measures_incomplete_methods_and_field_dependencies(self):
        with tempfile.TemporaryDirectory() as d:
            old, new = self._pair(Path(d))
            result = self._run(old, new)
            self.assertEqual(result["method_gap_count"], 2)
            self.assertEqual(result["missing_field_count"], 2)
            self.assertEqual(result["changed_field_metadata_count"], 0)
            self.assertEqual(result["referenced_gap_field_count"], 2)
            self.assertEqual(len(result["method_worklist"]), 2)
            self.assertEqual(len(result["field_worklist"]), 2)
            methods = {x["classification"]: x for x in result["method_worklist"]}
            self.assertEqual(set(methods), {"missing_method", "body_difference"})
            self.assertEqual(
                methods["body_difference"]["incoming_same_owner_calls"], 1,
            )
            self.assertEqual(
                methods["missing_method"]["incoming_same_owner_calls"], 0,
            )
            self.assertEqual(methods["body_difference"]["missing_field_dependencies"], 1)
            self.assertEqual(methods["missing_method"]["missing_field_dependencies"], 1)
            self.assertEqual(result["method_worklist"][0]["classification"],
                             "body_difference")
            self.assertEqual(
                [row["suggested_review_order"] for row in result["method_worklist"]],
                [1, 2],
            )
            self.assertTrue(all(row["read_sites"] == 1 for row in result["field_worklist"]))
            self.assertTrue(all(row["write_sites"] == 0 for row in result["field_worklist"]))
            self.assertFalse(result["automatic_recovery_performed"])
            self.assertFalse(result["source_equivalence_certified"])

    def test_replay_is_deterministic_and_does_not_print_original_names(self):
        with tempfile.TemporaryDirectory() as d:
            old, new = self._pair(Path(d))
            first = self._run(old, new)
            second = self._run(old, new)
            self.assertEqual(first, second)
            encoded = json.dumps(first)
            for private in ("hidden", "other", "present", "util", "check",
                            "p/A", "return"):
                self.assertNotIn(private, encoded)
            for row in first["method_worklist"]:
                self.assertRegex(row["method_id"], r"^METHOD_[0-9A-F]{20}$")
                self.assertNotIn("name", row)
            for row in first["field_worklist"]:
                self.assertRegex(row["field_id"], r"^FIELD_[0-9A-F]{20}$")
                self.assertNotIn("descriptor", row)

    def test_completed_candidate_yields_empty_worklists_without_acceptance(self):
        with tempfile.TemporaryDirectory() as d:
            original, _ = self._pair(Path(d))
            clone = Path(d) / "exact-copy.jar"
            clone.write_bytes(original.read_bytes())
            result = self._run(original, clone)
            self.assertEqual(result["method_gap_count"], 0)
            self.assertEqual(result["missing_field_count"], 0)
            self.assertEqual(result["referenced_gap_field_count"], 0)
            self.assertEqual(result["method_worklist"], [])
            self.assertEqual(result["field_worklist"], [])
            self.assertFalse(result["canonical_identity_accepted"])
            self.assertFalse(result["source_equivalence_certified"])

    def test_strict_jar_pin_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as d:
            old, new = self._pair(Path(d))
            with self.assertRaises(SourceGapWorklistError):
                self._run(old, new, new_sha="0" * 64)
            self.assertTrue(old.is_file())
            self.assertTrue(new.is_file())

    def test_strict_matrix_missing_source_evidence_refused(self):
        with tempfile.TemporaryDirectory() as d:
            old, new = self._pair(Path(d))
            matrix = build_class_method_matrix(
                old, new, original_sha256=_sha(old),
                candidate_sha256=_sha(new), class_entry="p/A.class",
            )
            original = profile_jar_class(old, "p/A.class")
            candidate = profile_jar_class(new, "p/A.class")
            broken = copy.deepcopy(original)
            del broken["methods"][0]["field_accesses"]
            with self.assertRaisesRegex(
                SourceGapWorklistError, "FIELD_OR_CALLSITE_EVIDENCE_MISSING"
            ):
                compare_source_gap_profiles(
                    broken, candidate, matrix, original_sha256=_sha(old),
                )

    def test_accepted_matrix_claim_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            old, new = self._pair(Path(d))
            matrix = build_class_method_matrix(
                old, new, original_sha256=_sha(old),
                candidate_sha256=_sha(new), class_entry="p/A.class",
            )
            original = profile_jar_class(old, "p/A.class")
            candidate = profile_jar_class(new, "p/A.class")
            matrix["source_equivalence_certified"] = True
            with self.assertRaisesRegex(
                SourceGapWorklistError, "STRICT_MATRIX_AUTHORITY_UNEXPECTED"
            ):
                compare_source_gap_profiles(
                    original, candidate, matrix, original_sha256=_sha(old),
                )

    def test_missing_field_write_site_measured_separately(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old = self._jar(
                root, "old",
                "public static int absent;"
                "public static void update(){absent=42;}",
            )
            new = self._jar(
                root, "new",
                "public static void update(){}",
            )
            report = self._run(old, new)
            self.assertEqual(report["missing_field_count"], 1)
            self.assertEqual(report["method_gap_count"], 1)
            field, = report["field_worklist"]
            self.assertEqual(field["read_sites"], 0)
            self.assertEqual(field["write_sites"], 1)
            self.assertEqual(field["referencing_method_count"], 1)

    def test_duplicate_method_inventory_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            old, new = self._pair(Path(d))
            matrix = build_class_method_matrix(
                old, new, original_sha256=_sha(old),
                candidate_sha256=_sha(new), class_entry="p/A.class",
            )
            original = profile_jar_class(old, "p/A.class")
            candidate = profile_jar_class(new, "p/A.class")
            original["methods"].append(copy.deepcopy(original["methods"][0]))
            with self.assertRaisesRegex(SourceGapWorklistError,
                                        "INVALID_OR_DUPLICATE_METHOD"):
                compare_source_gap_profiles(
                    original, candidate, matrix, original_sha256=_sha(old),
                )


if __name__ == "__main__":
    unittest.main()
