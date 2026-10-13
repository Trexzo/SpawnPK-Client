"""R129 Java9 source-first class replay: real synthetic Java/JVM integration."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_java9_source_class_matrix_r129 import (
    PrivateSourceJavacClassReplayR129Error,
    compile_and_compare_private_class,
)


@unittest.skipUnless(shutil.which("javac"),
                     "JDK required for Java9 source-built class replay")
class PrivateJava9ClassReplayR129Tests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.src = self.root / "private-originally-recovered-source"
        self.src.mkdir()
        self.original_source = self.root / "private-original-java"
        self.original_source.mkdir()
        self.original = self.root / "original-synthetic.jar"
        self.output = self.root / "new-private-research"
        self.text = (
            "package rs;\n"
            "public class Proof {\n"
            "  public static final int VALUE = 7;\n"
            "  public int add(int n) { return n + VALUE; }\n"
            "}\n"
        )
        self.source = self.src / "rs" / "Proof.java"
        self.source.parent.mkdir(parents=True)
        self.source.write_text(self.text, encoding="utf-8")
        self.build_reference()

    def build_reference(self):
        reference = self.original_source / "rs" / "Proof.java"
        reference.parent.mkdir(parents=True, exist_ok=True)
        reference.write_text(self.text, encoding="utf-8")
        output = self.root / "trusted-original-fixture-classes"
        output.mkdir(exist_ok=True)
        p = subprocess.run(
            [shutil.which("javac"), "--release", "9", "-g:none",
             "-proc:none", "-d", str(output), str(reference)],
            capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr.decode(errors="replace"))
        with ZipFile(self.original, "w") as z:
            z.write(output / "rs" / "Proof.class", "rs/Proof.class")
        self.original_hash = hashlib.sha256(
            self.original.read_bytes()).hexdigest()

    def audit(self, **kwargs):
        return compile_and_compare_private_class(
            self.src, self.original, self.output,
            original_sha256=self.original_hash,
            class_entry="rs/Proof.class", **kwargs)

    def test_java9_source_compile_exact_method_and_field_matrix(self):
        proof = self.audit()
        self.assertTrue(proof["source_compile_succeeded"])
        self.assertTrue(proof["class_header_exact"])
        self.assertTrue(proof["field_inventory_exact"])
        self.assertTrue(proof["all_method_bodies_instruction_parity"])
        self.assertTrue(proof["all_matrix_checks_exact"])
        self.assertFalse(proof["original_game_class_parity_accepted"])
        self.assertFalse(proof["whole_client_runtime_equivalent"])
        self.assertEqual(proof["original_declared_method_count"], 2)
        self.assertEqual(proof["compiled_java9_classfile_count"], 1)
        jar = self.output / "source-built.private.jar"
        self.assertEqual(hashlib.sha256(jar.read_bytes()).hexdigest(),
                         proof["independently_source_compiled_candidate_sha256"])
        self.assertEqual(len(list(self.output.iterdir())), 2)
        with ZipFile(jar) as z:
            b = z.read("rs/Proof.class")
        self.assertEqual(int.from_bytes(b[6:8], "big"), 53)

    def test_changed_method_body_is_reported_not_accepted(self):
        self.source.write_text(
            self.text.replace("return n + VALUE;", "return n + 42;"),
            encoding="utf-8")
        proof = self.audit()
        self.assertFalse(proof["all_method_bodies_instruction_parity"])
        self.assertFalse(proof["all_matrix_checks_exact"])
        self.assertFalse(proof["original_game_class_parity_accepted"])

    def test_wrong_original_sha_cannot_publish_candidate(self):
        with self.assertRaisesRegex(
                PrivateSourceJavacClassReplayR129Error,
                "PINNED_ORIGINAL_CLIENT_JAR_REQUIRED"):
            compile_and_compare_private_class(
                self.src, self.original, self.output,
                class_entry="rs/Proof.class",
                original_sha256="f" * 64)
        self.assertFalse(self.output.exists())

    def test_occupied_output_directory_never_overwritten(self):
        self.output.mkdir()
        (self.output / "keep").write_text("existing")
        with self.assertRaisesRegex(
                PrivateSourceJavacClassReplayR129Error,
                "FRESH_PRIVATE_OUTPUT_DIRECTORY_REQUIRED"):
            self.audit()
        self.assertEqual((self.output / "keep").read_text(), "existing")

    def test_invalid_java_source_fails_without_output(self):
        self.source.write_text("package rs; public class Proof { bad = ; }")
        with self.assertRaisesRegex(
                PrivateSourceJavacClassReplayR129Error,
                "PRIVATE_JAVA9_SOURCE_COMPILATION_FAILED"):
            self.audit()
        self.assertFalse(self.output.exists())

    def test_existing_binary_cannot_act_as_implicit_dependency(self):
        donor = self.src / "rs" / "OnlyBinary.java"
        donor.write_text(
            "package rs; public class OnlyBinary "
            "{ public static int magic() { return 5; } }",
            encoding="utf-8")
        compiled = subprocess.run(
            [shutil.which("javac"), "--release", "9", "-proc:none",
             "-d", str(self.src), str(donor)],
            capture_output=True)
        self.assertEqual(compiled.returncode, 0)
        donor.unlink()
        self.assertTrue((self.src / "rs" / "OnlyBinary.class").exists())
        self.source.write_text(self.text.replace(
            "return n + VALUE;", "return n + OnlyBinary.magic();"),
            encoding="utf-8")
        with self.assertRaisesRegex(
                PrivateSourceJavacClassReplayR129Error,
                "PRIVATE_JAVA9_SOURCE_COMPILATION_FAILED"):
            self.audit()
        self.assertFalse(self.output.exists())

    def test_non_rs_target_is_rejected(self):
        with self.assertRaisesRegex(
                PrivateSourceJavacClassReplayR129Error,
                "PRIVATE_RS_CLASS_ENTRY_REQUIRED"):
            compile_and_compare_private_class(
                self.src, self.original, self.output,
                class_entry="../Proof.class",
                original_sha256=self.original_hash)
        self.assertFalse(self.output.exists())

    def test_no_compiler_cannot_publish_output(self):
        with self.assertRaisesRegex(
                PrivateSourceJavacClassReplayR129Error,
                "JDK_JAVAC_REQUIRED"):
            self.audit(javac="nonexistent-r129-javac-fixture")
        self.assertFalse(self.output.exists())
