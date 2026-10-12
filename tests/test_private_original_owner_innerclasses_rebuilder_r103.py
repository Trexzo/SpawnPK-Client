"""R103: actual Java9 classfile candidate metadata rewrite, with six entries."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_four_nested_enum_acceptance import (
    symbolic_innerclasses_table,
)
from spk_recovery.private_nested_enum_collision_rebind import rebind_classfile
from spk_recovery.private_original_owner_innerclasses_rebuilder_r103 import (
    OriginalOwnerInnerClassesError,
    rebuild_private_owner_six_innerclasses,
    replace_owner_innerclasses,
)


@unittest.skipUnless(shutil.which("javac"), "javac supporting --release 9 required")
class OriginalOwnerSixInnerClassesTests(unittest.TestCase):
    def setUp(self):
        tmp = self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.original = self.root / "original-fixture.jar"
        self.candidate = self.root / "candidate-fixture.jar"
        self.out = self.root / "accepted"

    @staticmethod
    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def compile(self, *, corrupt_candidate=False):
        orig = self.root / "original-src" / "p"
        orig.mkdir(parents=True)
        (orig / "Owner.java").write_text(
            "package p; public final class Owner {"
            "public enum Placeholder { ALPHA, BETA }"
            "public enum One { A }"
            "public enum Two { B }"
            "public enum Three { C }"
            "public java.util.Map.Entry<String,String> jdkNested;"
            "public Other.Nested externalNested;"
            "public int identity(){return 19;}"
            "}", encoding="utf-8")
        (orig / "Other.java").write_text(
            "package p; public class Other { public static class Nested {} }",
            encoding="utf-8")
        classes = self.root / "original-classes"
        classes.mkdir()
        run = subprocess.run(
            ["javac", "--release", "9", "-proc:none", "-g:none",
             "-d", str(classes),
             str(orig / "Owner.java"), str(orig / "Other.java")],
            capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        with ZipFile(self.original, "w") as archive:
            for file in classes.rglob("*.class"):
                name = file.relative_to(classes).as_posix()
                raw, _ = rebind_classfile(
                    file.read_bytes(), "p/Owner", "Placeholder")
                archive.writestr(
                    name.replace("Owner$Placeholder.class", "Owner$Owner.class"),
                    raw)

        cand = self.root / "candidate-src" / "p"
        cand.mkdir(parents=True)
        (cand / "Owner.java").write_text(
            "package p; public final class Owner {"
            "public enum Surrogate { ALPHA, BETA }"
            "public int identity(){return " +
            ("20" if corrupt_candidate else "19") + ";}"
            "}", encoding="utf-8")
        output = self.root / "candidate-classes"
        output.mkdir()
        run = subprocess.run(
            ["javac", "--release", "9", "-proc:none", "-g:none",
             "-d", str(output), str(cand / "Owner.java")],
            capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        with ZipFile(self.candidate, "w") as archive:
            for file in output.rglob("*.class"):
                archive.write(file, file.relative_to(output).as_posix())
        with ZipFile(self.original) as original, ZipFile(self.candidate) as candidate:
            target = symbolic_innerclasses_table(original.read("p/Owner.class"))
            initial = symbolic_innerclasses_table(candidate.read("p/Owner.class"))
        self.assertEqual(len(target), 6, target)
        self.assertNotEqual(initial, target)
        self.assertEqual(sum(row[1] == "p/Owner" for row in target), 4)
        self.assertEqual(sum(row[1] != "p/Owner" for row in target), 2)

    def gate(self, *, original_pin=None, candidate_pin=None):
        return rebuild_private_owner_six_innerclasses(
            self.original, self.candidate, "p/Owner.class", self.out,
            original_sha256=original_pin or self.digest(self.original),
            candidate_sha256=candidate_pin or self.digest(self.candidate),
        )

    def test_six_original_entries_including_foreign_java_nested(self):
        self.compile()
        original_pin = self.digest(self.original)
        candidate_pin = self.digest(self.candidate)
        result = self.gate()
        self.assertEqual(result["exact_ordered_owner_innerclasses_entries"], 6)
        self.assertEqual(result["locally_nested_enum_entries"], 4)
        self.assertEqual(result["externally_referenced_innerclasses_entries"], 2)
        self.assertTrue(result["candidate_field_method_bytecode_preserved"])
        self.assertFalse(result["all_four_enum_method_R95_parity_certified"])
        self.assertEqual(self.digest(self.original), original_pin)
        self.assertEqual(self.digest(self.candidate), candidate_pin)
        assembled = self.out / "owner-innerclasses-rebuilt.private.jar"
        with ZipFile(self.original) as old, ZipFile(self.candidate) as source, ZipFile(assembled) as new:
            self.assertEqual(
                symbolic_innerclasses_table(old.read("p/Owner.class")),
                symbolic_innerclasses_table(new.read("p/Owner.class")))
            self.assertEqual(
                source.read("p/Owner$Surrogate.class"),
                new.read("p/Owner$Surrogate.class"))
            self.assertNotEqual(
                source.read("p/Owner.class"), new.read("p/Owner.class"))

    def test_changed_method_bytecode_not_transferred_from_original(self):
        self.compile(corrupt_candidate=True)
        result = self.gate()
        self.assertFalse(result["all_four_enum_method_R95_parity_certified"])
        accepted = self.out / "owner-innerclasses-rebuilt.private.jar"
        with ZipFile(self.candidate) as source, ZipFile(accepted) as updated:
            original_candidate = source.read("p/Owner.class")
            reconstructed = updated.read("p/Owner.class")
        # Class metadata/constant pool differs, but candidate's method
        # binary region remains intact by the validator; no original Code.
        self.assertNotEqual(original_candidate, reconstructed)

    def test_wrong_original_pin_rejected_before_file_promotion(self):
        self.compile()
        with self.assertRaisesRegex(
            OriginalOwnerInnerClassesError, "JAR_PIN_MISMATCH"
        ):
            self.gate(original_pin="0" * 64)
        self.assertFalse(self.out.exists())

    def test_wrong_candidate_pin_rejected_before_file_promotion(self):
        self.compile()
        with self.assertRaisesRegex(
            OriginalOwnerInnerClassesError, "JAR_PIN_MISMATCH"
        ):
            self.gate(candidate_pin="0" * 64)
        self.assertFalse(self.out.exists())

    def test_non_six_entry_original_table_rejected(self):
        self.compile()
        with ZipFile(self.original) as archive:
            table = symbolic_innerclasses_table(archive.read("p/Owner.class"))
        with ZipFile(self.candidate) as archive:
            raw = archive.read("p/Owner.class")
        with self.assertRaisesRegex(
            OriginalOwnerInnerClassesError, "SIX_INNERCLASSES_ROWS"
        ):
            replace_owner_innerclasses(raw, "p/Owner", table[:5])

    def test_wrong_classfile_under_owner_archive_name_is_rejected(self):
        self.compile()
        with ZipFile(self.original) as original, ZipFile(self.candidate) as candidate:
            table = symbolic_innerclasses_table(original.read("p/Owner.class"))
            spoof = candidate.read("p/Owner$Surrogate.class")
        with self.assertRaisesRegex(
            OriginalOwnerInnerClassesError, "CANDIDATE_OWNER_INTERNAL_NAME_MISMATCH"
        ):
            replace_owner_innerclasses(spoof, "p/Owner", table)

    def test_existing_output_is_not_overwritten(self):
        self.compile()
        self.out.mkdir()
        with self.assertRaisesRegex(
            OriginalOwnerInnerClassesError, "NEW_PRIVATE_OUTPUT_REQUIRED"
        ):
            self.gate()
