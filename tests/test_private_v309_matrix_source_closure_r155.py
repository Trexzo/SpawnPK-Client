"""R155: original matrix selected Java source self-call closure and scaffolding veto.

Only synthetic classes, no proprietary recovered source or original bytes in CI.
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


@unittest.skipUnless(shutil.which("java") and shutil.which("javac"),
                     "JDK required for actual original-vs-Java source Code parity")
class R155MatrixSelectedSourceClosureTests(unittest.TestCase):
    OWNER = "ext/Matrix"

    def setUp(self):
        owner = tempfile.TemporaryDirectory()
        self.addCleanup(owner.cleanup)
        self.root = Path(owner.name)
        self.original = self.build_original()
        self.source_text = self.make_java(original=False)
        self.source = self.source_zip(self.source_text, "recovered-source.zip")
        self.full_selection = self.selection([
            ("c", "()[F"), ("d", "()[F"),
            ("toString", "()Ljava/lang/String;"),
        ], "full-method-selection.json")

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @staticmethod
    def make_java(*, original):
        s = (
            "package ext;\n"
            "public final class Matrix {\n"
            " public float[] e;\n"
            " float[] c() { return new float[]{e[0],e[1],e[2]}; }\n"
            " public float[] d() { return new float[]{e[3],e[4],e[5]}; }\n"
            " public String toString() { this.d(); this.c(); "
            "return Float.toString(this.e[0]); }\n"
        )
        if original:
            s += (" public int gameReference(rs.Game game) { "
                  "return game.value(); }\n")
        return s + "}\n"

    def build_original(self):
        classes = self.root / "classes"
        classes.mkdir()
        for internal, java, folder in [
            ("rs/Game", "package rs; public class Game {"
             "public int value() {return 42;}}", "game"),
            (self.OWNER, self.make_java(original=True), "matrix"),
        ]:
            file = self.root / folder / (internal + ".java")
            file.parent.mkdir(parents=True)
            file.write_text(java, encoding="utf-8")
            result = subprocess.run([
                shutil.which("javac"), "--release", "9", "-proc:none",
                "-implicit:none", "-g:none",
                "-classpath", str(classes), "-d", str(classes), str(file),
            ], capture_output=True)
            self.assertEqual(0, result.returncode,
                             result.stderr.decode("utf-8", errors="replace"))
        archive = self.root / "original.jar"
        with ZipFile(archive, "w") as output:
            for cls in sorted(classes.rglob("*.class")):
                output.write(cls, cls.relative_to(classes).as_posix())
        return archive

    def source_zip(self, java, name):
        archive = self.root / name
        with ZipFile(archive, "w") as output:
            output.writestr("src/main/java/"+self.OWNER+".java", java)
        return archive

    def selection(self, identities, name):
        path = self.root / name
        path.write_text(json.dumps([
            {"name": n, "descriptor": d} for n, d in identities
        ]), encoding="utf-8")
        return path

    def compare(self, source=None, selected=None, *, closure=True):
        source = source or self.source
        selected = selected or self.full_selection
        return verify_private_matrix_source_subset(
            self.original, source, selected,
            original_sha256=self.sha(self.original),
            recovered_source_sha256=self.sha(source),
            selection_sha256=self.sha(selected),
            original_owner=self.OWNER,
            require_selected_self_call_closure=closure)

    def test_three_original_methods_closed_and_independently_compilable(self):
        result = self.compare()
        self.assertEqual(3, result["verified_selected_method_count"])
        self.assertEqual(2, result["selected_original_self_call_edges_closed_and_checked"])
        self.assertTrue(result["selected_original_and_rebuilt_self_call_closure_required"])
        self.assertTrue(result["all_selected_core_method_code_equal"])
        self.assertFalse(result["unselected_private_methods_and_scaffolding_accepted"])
        self.assertFalse(result["original_game_class_binary_fallback_used"])
        self.assertFalse(result["complete_original_matrix_java_source_restored"])

    def test_missing_decomposition_helper_vetoes_even_matching_caller(self):
        only_caller = self.selection([
            ("toString", "()Ljava/lang/String;"),
        ], "just-caller.json")
        unclosed = self.compare(selected=only_caller, closure=False)
        self.assertTrue(unclosed["all_selected_core_method_code_equal"])
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.compare(selected=only_caller, closure=True)

    def test_one_helper_unselected_still_fails_closed(self):
        partial = self.selection([
            ("c", "()[F"), ("toString", "()Ljava/lang/String;"),
        ], "missing-d.json")
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.compare(selected=partial)

    def test_changed_recovered_helper_body_must_not_be_accepted(self):
        changed = self.source_zip(
            self.source_text.replace("e[3],e[4],e[5]", "e[3],e[4],e[6]"),
            "unverified-helper.zip")
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.compare(source=changed)

    def test_sha_mismatch_preflight(self):
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            verify_private_matrix_source_subset(
                self.original, self.source, self.full_selection,
                original_sha256="0"*64,
                recovered_source_sha256=self.sha(self.source),
                selection_sha256=self.sha(self.full_selection),
                original_owner=self.OWNER,
                require_selected_self_call_closure=True)


if __name__ == "__main__":
    unittest.main()
