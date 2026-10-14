"""R141 real Java casefold classfile fixture and guarded type-reference edits."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_casefold_type_rewrite_r141 import (
    PrivateImportedTypeAliasR141Error, patch_private_casefold_source,
)
from spk_recovery.private_v309_compiler_frontier_r137 import (
    _normalize_private_provisional_capsule,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "JDK required for actual AST / original classfile tests")
class PrivateR141TypeAliasTests(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root = Path(root.name)
        self.original = self.root / "original.jar"
        binaries = {
            "ext/A/A": self.compile_java(
                "ext/A/A", "package ext.A; public class A {}", "capital"),
            "ext/A/a": self.compile_java(
                "ext/A/a", "package ext.A; public class a {}", "lower"),
            "rs/Game": self.compile_java(
                "rs/Game", "package rs; public class Game {}", "game"),
        }
        with ZipFile(self.original, "w") as z:
            for path, blob in sorted(binaries.items()):
                z.writestr(path + ".class", blob)

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def compile_java(self, internal, code, label):
        root = self.root / label
        file = root / (internal + ".java")
        file.parent.mkdir(parents=True)
        file.write_text(code, encoding="utf-8")
        classes = root / "classes"
        classes.mkdir()
        proc = subprocess.run(
            [shutil.which("javac"), "--release", "9",
             "-g:none", "-proc:none", "-d", str(classes), str(file)],
            capture_output=True)
        self.assertEqual(0, proc.returncode,
                         proc.stderr.decode("utf-8", errors="replace"))
        return (classes / (internal + ".class")).read_bytes()

    def build_source(self, code, name):
        path = self.root / name
        with ZipFile(path, "w") as z:
            z.writestr("src/main/java/rs/Recovered.java", code)
        return path

    def patch(self, archive):
        return patch_private_casefold_source(
            archive, self.original,
            source_sha256=self.sha(archive),
            original_sha256=self.sha(self.original))

    def test_provisional_class_alias_rewrites_import_and_only_type_nodes(self):
        archive = self.build_source(
            "package rs;\n"
            "import ext.A.a;\n"
            "public class Recovered {\n"
            " public a field;\n"
            " public a echo(a value) { return value; }\n"
            " public a construct() { return new a(); }\n"
            "}\n",
            "private-source.zip")
        patched, report = self.patch(archive)
        self.assertEqual(1, report["changed_java_source_file_count"])
        self.assertEqual(1, report["reviewed_rewritten_import_count"])
        self.assertEqual(5, report["reviewed_rewritten_type_identifier_count"])
        self.assertTrue(report["eligible_original_nonrs_casefold_type_count"])
        text = patched[0][1].decode("utf-8")
        self.assertNotIn("import ext.A.a;", text)
        self.assertIn("import ext.A.a__Case_", text)
        self.assertNotIn("new a()", text)
        self.assertIn("return value;", text)
        self.assertFalse(report["whole_client_source_build_verified"])

        nonrs = self.root / "provisional.jar"
        with ZipFile(self.original) as original, ZipFile(nonrs, "w") as out:
            for member in original.namelist():
                if member.startswith("ext/"):
                    out.writestr(member, original.read(member))
        normalized = self.root / "normalized.jar"
        summary = _normalize_private_provisional_capsule(
            nonrs, normalized, self.root)
        self.assertEqual(0, summary["post_collision_edges"])
        file = self.root / "Recovered.java"
        classes = self.root / "compiled"
        classes.mkdir()
        with ZipFile(archive) as z:
            file.write_bytes(z.read("src/main/java/rs/Recovered.java"))
        cmd = [shutil.which("javac"), "--release", "11",
               "-proc:none", "-implicit:none",
               "-classpath", str(normalized), "-d", str(classes), str(file)]
        before = subprocess.run(cmd, capture_output=True)
        self.assertNotEqual(0, before.returncode)
        file.write_bytes(patched[0][1])
        after = subprocess.run(cmd, capture_output=True)
        self.assertEqual(0, after.returncode,
                         after.stderr.decode("utf-8", errors="replace"))

    def test_ambiguous_static_receiver_blocks_entire_source_file(self):
        code = (
            "package rs;\nimport ext.A.a;\n"
            "public class Recovered { public int get() { return a.value(); } }\n"
        )
        archive = self.build_source(code, "ambiguous-source.zip")
        changed, proof = self.patch(archive)
        self.assertEqual(code.encode("utf-8"), changed[0][1])
        self.assertEqual(0, proof["changed_java_source_file_count"])
        self.assertEqual(1, proof["withheld_ambiguous_java_file_count"])

    def test_type_parameter_shadow_blocks_file(self):
        code = (
            "package rs;\nimport ext.A.a;\n"
            "public class Recovered<a> { a field; }\n"
        )
        archive = self.build_source(code, "shadow-source.zip")
        changed, proof = self.patch(archive)
        self.assertEqual(code.encode(), changed[0][1])
        self.assertEqual(1, proof["withheld_ambiguous_java_file_count"])

    def test_pins_reject_original_and_source_changes(self):
        archive = self.build_source(
            "package rs; public class Recovered {}\n", "negative-source.zip")
        with self.assertRaises(PrivateImportedTypeAliasR141Error):
            patch_private_casefold_source(
                archive, self.original,
                source_sha256="0" * 64, original_sha256=self.sha(self.original))
        with self.assertRaises(PrivateImportedTypeAliasR141Error):
            patch_private_casefold_source(
                archive, self.original,
                source_sha256=self.sha(archive), original_sha256="0" * 64)


if __name__ == "__main__":
    unittest.main()
