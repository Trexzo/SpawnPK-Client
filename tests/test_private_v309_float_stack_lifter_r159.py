"""R159: generic straight-line JVM float-array return expression recovery."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.source_method_parity import _normalized_instructions
from spk_recovery.private_v309_float_stack_lifter_r159 import (
    OriginalFloatStackR159Error, private_float_array_expression,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("javap"),
                     "JDK needed for original JVM float-array bytecode")
class R159StrictFloatStackSourceRecovery(unittest.TestCase):
    OWNER = "example/Matrix"

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.jar = self.original_jar(
            "return ((this.e[0]*this.e[1]) + "
            "(this.e[2]*(this.e[3]-this.e[4])));",
            "normal.jar")
        with ZipFile(self.jar) as archive:
            self.original_class = archive.read(self.OWNER + ".class")
        profile = profile_class_field_accesses(self.original_class)
        method = next(m for m in profile["methods"]
                      if m["name"] == "g" and m["descriptor"] == "()F")
        self.n = len(method["instructions"])
        self.last = method["instructions"][-1]["offset"]

    @staticmethod
    def sha(file):
        return hashlib.sha256(Path(file).read_bytes()).hexdigest()

    def original_jar(self, expr, name):
        workspace = self.root / (name + "-src")
        source = workspace / (self.OWNER + ".java")
        source.parent.mkdir(parents=True)
        source.write_text(
            "package example; public class Matrix {public float[] e;"
            "float g() {" + expr + "}"
            "public int gameLink(rs.Game g){return g.value();}}",
            encoding="utf-8")
        game = workspace / "rs" / "Game.java"
        game.parent.mkdir(parents=True)
        game.write_text("package rs;public class Game {"
                        "public int value(){return 1;}}", encoding="utf-8")
        classes = workspace / "compiled"
        classes.mkdir()
        for p in (game, source):
            result = subprocess.run(
                [shutil.which("javac"), "--release", "9",
                 "-g:none", "-proc:none", "-classpath", str(classes),
                 "-d", str(classes), str(p)], capture_output=True)
            self.assertEqual(0, result.returncode,
                             result.stderr.decode("utf-8", errors="replace"))
        jar = self.root / name
        with ZipFile(jar, "w") as archive:
            for p in sorted(classes.rglob("*.class")):
                archive.write(p, p.relative_to(classes).as_posix())
        return jar

    def recover(self, jar=None, **overrides):
        jar = jar or self.jar
        return private_float_array_expression(
            jar, original_sha256=overrides.get("sha", self.sha(jar)),
            owner=self.OWNER, method_name="g", float_array_field="e",
            expected_instructions=overrides.get("count", self.n),
            expected_last_offset=overrides.get("last", self.last),
            original_owner_sha256=overrides.get(
                "class_sha", self.sha_bytes(self.original_class)))

    @staticmethod
    def sha_bytes(data):
        return hashlib.sha256(data).hexdigest()

    def test_reconstruct_ordered_float_stack_and_recompile_instructions(self):
        recovered = self.recover()
        self.assertEqual(self.n, recovered["original_instruction_count"])
        self.assertEqual(5, recovered["float_array_access_count"])
        self.assertTrue(recovered["source_only_not_recompiled_or_accepted"])
        self.assertNotIn("return this.e[0] * this.e[1] +", recovered[
            "private_java_method_source"])
        code = ("package example; public class Matrix { public float[] e;"
                + recovered["private_java_method_source"] + "}")
        source = self.root / "recovered" / (self.OWNER + ".java")
        source.parent.mkdir(parents=True)
        source.write_text(code, encoding="utf-8")
        output = self.root / "recompiled"
        output.mkdir()
        check = subprocess.run(
            [shutil.which("javac"), "--release", "9", "-proc:none",
             "-g:none", "-d", str(output), str(source)],
            capture_output=True)
        self.assertEqual(0, check.returncode,
                         check.stderr.decode("utf-8", errors="replace"))
        original = profile_class_field_accesses(self.original_class)
        rebuilt = profile_class_field_accesses(
            (output / (self.OWNER + ".class")).read_bytes())
        old = next(m for m in original["methods"] if m["name"] == "g")
        new = next(m for m in rebuilt["methods"] if m["name"] == "g")
        self.assertEqual(_normalized_instructions(original, old),
                         _normalized_instructions(rebuilt, new))
        self.assertEqual(old["code_length"], new["code_length"])

    def test_mismatched_original_jar_hash_fails_closed(self):
        with self.assertRaises(OriginalFloatStackR159Error):
            self.recover(sha="0"*64)

    def test_expected_opcode_count_drift_rejected(self):
        with self.assertRaises(OriginalFloatStackR159Error):
            self.recover(count=self.n + 1)

    def test_branching_float_method_not_lifted(self):
        branch = self.original_jar(
            "if(this.e[0]>0) return this.e[1];"
            "return this.e[2];", "branch.jar")
        with self.assertRaises(OriginalFloatStackR159Error):
            self.recover(jar=branch, count=18)

    def test_wrong_field_name_cannot_match_original(self):
        with self.assertRaises(OriginalFloatStackR159Error):
            private_float_array_expression(
                self.jar, original_sha256=self.sha(self.jar),
                owner=self.OWNER, method_name="g",
                float_array_field="invented", expected_instructions=self.n,
                expected_last_offset=self.last)


if __name__ == "__main__":
    unittest.main()
