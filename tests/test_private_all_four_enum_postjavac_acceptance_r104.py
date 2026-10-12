"""R104: synthetic Java9 full-four-enum exact R95 acceptance after two transforms."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_all_four_enum_postjavac_acceptance_r104 import (
    AllFourPrivateEnumAcceptanceError,
    assemble_private_four_enum_candidate,
)
from spk_recovery.private_four_nested_enum_acceptance import (
    symbolic_innerclasses_table,
)
from spk_recovery.private_nested_enum_collision_rebind import rebind_classfile


@unittest.skipUnless(shutil.which("javac"), "javac --release 9 required")
class AllFourOriginalEnumPostjavacTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.original = self.root / "original.jar"
        self.candidate = self.root / "candidate.jar"
        self.output = self.root / "accepted"

    @staticmethod
    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def compile(self, *, changed_constant=False,
                missing_candidate_enum=False,
                corrupt_owner_method=False):
        original_src = self.root / "original-source" / "p"
        original_src.mkdir(parents=True)
        (original_src / "Owner.java").write_text(
            "package p; public final class Owner {"
            "public enum Placeholder { ALPHA, BETA }"
            "public enum One { A, B }"
            "public enum Two { C }"
            "public enum Three { D }"
            "public java.util.Map.Entry<String,String> firstForeign;"
            "public Other.Nested secondForeign;"
            "public int identity(){return 19;}"
            "}", encoding="utf-8")
        (original_src / "Other.java").write_text(
            "package p; public final class Other {"
            "public static class Nested {} }", encoding="utf-8")
        original_classes = self.root / "original-classes"
        original_classes.mkdir()
        compiled = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(original_classes),
             str(original_src / "Owner.java"),
             str(original_src / "Other.java")],
            capture_output=True, text=True)
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        with ZipFile(self.original, "w") as dest:
            for path in sorted(original_classes.rglob("*.class")):
                filename = path.relative_to(original_classes).as_posix()
                data, _ = rebind_classfile(
                    path.read_bytes(), "p/Owner", "Placeholder")
                if filename == "p/Owner$Placeholder.class":
                    filename = "p/Owner$Owner.class"
                dest.writestr(filename, data)

        candidate_src = self.root / "candidate-source" / "p"
        candidate_src.mkdir(parents=True)
        (candidate_src / "Owner.java").write_text(
            "package p; public final class Owner {"
            'public enum Surrogate { ALPHA, ' +
            ('GAMMA' if changed_constant else 'BETA') + ' }'
            "public enum One { A, B }"
            "public enum Two { C }"
            "public enum Three { D }"
            "public int identity(){return " +
            ("20" if corrupt_owner_method else "19") + ";}"
            "}", encoding="utf-8")
        candidate_classes = self.root / "candidate-classes"
        candidate_classes.mkdir()
        compiled = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(candidate_classes),
             str(candidate_src / "Owner.java")],
            capture_output=True, text=True)
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        with ZipFile(self.candidate, "w") as dest:
            for path in sorted(candidate_classes.rglob("*.class")):
                filename = path.relative_to(candidate_classes).as_posix()
                if missing_candidate_enum and filename == "p/Owner$Two.class":
                    continue
                dest.writestr(filename, path.read_bytes())
        with ZipFile(self.original) as a, ZipFile(self.candidate) as b:
            self.assertEqual(
                len(symbolic_innerclasses_table(a.read("p/Owner.class"))), 6)
            self.assertNotEqual(
                symbolic_innerclasses_table(a.read("p/Owner.class")),
                symbolic_innerclasses_table(b.read("p/Owner.class")))

    def run_gate(self, *, wrong_sha=False):
        return assemble_private_four_enum_candidate(
            self.original, self.candidate, "p/Owner.class",
            "Surrogate", self.output,
            original_sha256=("0" * 64 if wrong_sha else self.digest(self.original)),
            candidate_sha256=self.digest(self.candidate),
        )

    def test_four_enum_methods_and_six_owner_rows_pass_exact_R95(self):
        self.compile()
        result = self.run_gate()
        self.assertTrue(result["R95_all_four_enums_exact_parity_passed"])
        self.assertEqual(result["accepted_original_nested_enum_classes"], 4)
        self.assertEqual(result["exact_ordered_owner_InnerClasses_rows"], 6)
        self.assertFalse(result["R97_complete_owner_source_gate_passed"])
        self.assertFalse(result["whole_client_runtime_equivalence_certified"])
        accepted = self.output / "all-four-enums-r95-accepted.private.jar"
        with ZipFile(self.original) as original, ZipFile(accepted) as candidate:
            names = candidate.namelist()
            self.assertIn("p/Owner$Owner.class", names)
            self.assertNotIn("p/Owner$Surrogate.class", names)
            self.assertEqual(
                symbolic_innerclasses_table(original.read("p/Owner.class")),
                symbolic_innerclasses_table(candidate.read("p/Owner.class")))
            for suffix in ("Owner", "One", "Two", "Three"):
                entry = "p/Owner$" + suffix + ".class"
                self.assertEqual(
                    symbolic_innerclasses_table(original.read(entry)),
                    symbolic_innerclasses_table(candidate.read(entry)))

    def test_changed_enum_constant_rejected_by_R95_no_output(self):
        self.compile(changed_constant=True)
        with self.assertRaisesRegex(
            AllFourPrivateEnumAcceptanceError,
            "R95_ALL_FOUR_ORIGINAL_ENUM_PARITY_NOT_ACCEPTED",
        ):
            self.run_gate()
        self.assertFalse(self.output.exists())

    def test_missing_nested_enum_rejected_before_classfile_transform(self):
        self.compile(missing_candidate_enum=True)
        with self.assertRaisesRegex(
            AllFourPrivateEnumAcceptanceError,
            "FOUR_ORIGINAL_AND_CANDIDATE_ENUM_CLASSFILES_REQUIRED",
        ):
            self.run_gate()
        self.assertFalse(self.output.exists())

    def test_wrong_original_sha_rejected_without_output(self):
        self.compile()
        with self.assertRaisesRegex(
            AllFourPrivateEnumAcceptanceError,
            "COMPLETE_JAR_SHA256_MISMATCH",
        ):
            self.run_gate(wrong_sha=True)
        self.assertFalse(self.output.exists())

    def test_changed_candidate_outer_method_remains_uncertified(self):
        self.compile(corrupt_owner_method=True)
        result = self.run_gate()
        self.assertTrue(result["R95_all_four_enums_exact_parity_passed"])
        self.assertFalse(result["R97_complete_owner_source_gate_passed"])
        # R95 correctly accepts enum methods only; it does not certify
        # changed outer-owner instruction semantics.
        self.assertFalse(result["whole_client_runtime_equivalence_certified"])
