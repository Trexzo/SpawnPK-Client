"""R154: strictly rebuild original matrix toString Java method only.

Tests deliberately give the original linked owner a genuine rs/Game dependent
method, while the recovered source contains different/unaccepted placeholder
c()/d() method bodies. Only toString() is selected for JVM Code comparison.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_matrix_source_method_parity_r150 import (
    PrivateMatrixMethodSourceR150Error,
    verify_private_matrix_source_subset,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "JDK required for original JVM Code comparison")
class R154MatrixStringSourceParityTests(unittest.TestCase):
    OWNER = "ext/Matrix"

    def setUp(self):
        owner = tempfile.TemporaryDirectory()
        self.addCleanup(owner.cleanup)
        self.root = Path(owner.name)
        self.jar = self.build_original()
        self.source_code = self.matrix_source(original=False)
        self.source = self.zip_source(self.source_code, "candidate-source.zip")
        self.selected = self.root / "one-method-selection.json"
        self.selected.write_text(json.dumps([
            {"name": "toString",
             "descriptor": "()Ljava/lang/String;"},
        ]), encoding="utf-8")

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @staticmethod
    def format_java():
        return (
            " public String toString() {\n"
            "   StringBuilder builder = new StringBuilder();\n"
            "   this.d();\n"
            "   this.c();\n"
            "   for (int row = 0; row < 4; ++row) {\n"
            "     for (int col = 0; col < 4; ++col) {\n"
            "       if (col > 0) builder.append(\"\\t\");\n"
            "       float v = this.e[col + 4 * row];\n"
            "       if (Math.sqrt((double)(v * v)) < (double) 1.0E-4F) {\n"
            "         v = 0.0F;\n"
            "       }\n"
            "       builder.append(v);\n"
            "     }\n"
            "     builder.append(\"\\n\");\n"
            "   }\n"
            "   return builder.toString();\n"
            " }\n"
        )

    def matrix_source(self, *, original):
        original_helpers = (
            "float[] c() { return new float[3]; }\n"
            "public float[] d() { return new float[3]; }\n"
        )
        provisional_helpers = (
            "float[] c() { return null; }\n"
            "public float[] d() { return null; }\n"
        )
        content = ("package ext;\npublic final class Matrix {\n"
                   " public float[] e;\n" +
                   (original_helpers if original else provisional_helpers) +
                   self.format_java())
        if original:
            content += ("public int gameLink(rs.Game game) {"
                        "return game.value();}\n")
        return content + "}\n"

    def build_original(self):
        classes = self.root / "original-classes"
        classes.mkdir()
        for internal, source, folder in [
            ("rs/Game",
             "package rs; public class Game { public int value(){return 1;} }",
             "game"),
            (self.OWNER, self.matrix_source(original=True), "matrix"),
        ]:
            target = self.root / folder / (internal + ".java")
            target.parent.mkdir(parents=True)
            target.write_text(source, encoding="utf-8")
            process = subprocess.run([
                shutil.which("javac"), "--release", "9", "-proc:none",
                "-implicit:none", "-g:none", "-classpath", str(classes),
                "-d", str(classes), str(target),
            ], capture_output=True, check=False)
            self.assertEqual(0, process.returncode,
                             process.stderr.decode("utf-8", errors="replace"))
        dest = self.root / "original.jar"
        with ZipFile(dest, "w") as output:
            for cls in sorted(classes.rglob("*.class")):
                output.write(cls, cls.relative_to(classes).as_posix())
        return dest

    def zip_source(self, source, name):
        result = self.root / name
        with ZipFile(result, "w") as output:
            output.writestr("src/main/java/" + self.OWNER + ".java", source)
        return result

    def prove(self, *, source=None, selection=None):
        source = source or self.source
        selection = selection or self.selected
        return verify_private_matrix_source_subset(
            self.jar, source, selection,
            original_sha256=self.sha(self.jar),
            recovered_source_sha256=self.sha(source),
            selection_sha256=self.sha(selection),
            original_owner=self.OWNER)

    def test_exact_original_string_method_compiles_with_untrusted_helpers(self):
        result = self.prove()
        self.assertEqual(1, result["verified_selected_method_count"])
        self.assertEqual(60, result["matched_opcode_count"])
        self.assertTrue(result["all_selected_core_method_code_equal"])
        self.assertEqual(0, result["verified_constructor_count"])
        self.assertFalse(result["unselected_private_methods_and_scaffolding_accepted"])
        self.assertFalse(result["complete_original_matrix_java_source_restored"])
        self.assertFalse(result["original_game_class_binary_fallback_used"])
        self.assertTrue(result["source_compiled_with_empty_original_external_classpath"])

    def test_different_print_threshold_is_a_real_bytecode_regression(self):
        changed = self.zip_source(
            self.source_code.replace("1.0E-4F", "2.0E-4F"),
            "wrong-float-threshold.zip")
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.prove(source=changed)

    def test_transposed_print_index_is_a_real_bytecode_regression(self):
        changed = self.zip_source(
            self.source_code.replace("col + 4 * row", "row + 4 * col"),
            "wrong-indexing.zip")
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.prove(source=changed)

    def test_unrecovered_helpers_cannot_be_marked_original(self):
        alternate = self.root / "invalid-selection.json"
        alternate.write_text(json.dumps([
            {"name": "c", "descriptor": "()[F"},
        ]), encoding="utf-8")
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.prove(selection=alternate)

    def test_wrong_source_sha_is_never_allowed(self):
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            verify_private_matrix_source_subset(
                self.jar, self.source, self.selected,
                original_sha256=self.sha(self.jar),
                recovered_source_sha256="0" * 64,
                selection_sha256=self.sha(self.selected),
                original_owner=self.OWNER)


if __name__ == "__main__":
    unittest.main()
