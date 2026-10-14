"""R156: source-only compile scaffold for legitimate original linked Java owner.

Scaffolding only supplies compile-time types; its original implementation
remains explicitly *unverified* and original .class is never on javac classpath.
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
                     "Real javac required for original helper source test")
class R156PrivateOriginalMatrixSourceHelpersTests(unittest.TestCase):
    OWNER = "ext/Matrix"
    HELPER = "ext/Helper"

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.original = self.build_original()
        self.source = self.write_zip(
            "candidate-matrix.zip", {
                self.OWNER + ".java":
                "package ext; public class Matrix { "
                "public float[] data; "
                "public float combine(ext.Helper other) {"
                "return other.x + other.y + this.data[0]; } }",
            })
        self.helper = self.write_zip(
            "candidate-helper.zip", {
                self.HELPER + ".java":
                "package ext; public class Helper { public float x, y; }",
            })
        self.selection = self.root / "selection.json"
        self.selection.write_text(json.dumps([{
            "name": "combine", "descriptor": "(Lext/Helper;)F"
        }]), encoding="utf8")

    @staticmethod
    def sha(file):
        return hashlib.sha256(Path(file).read_bytes()).hexdigest()

    def build_original(self):
        classes = self.root / "classes"
        classes.mkdir()
        items = [
            ("rs/Game", "package rs; public class Game {"
             "public int value() {return 1;}}"),
            (self.HELPER,
             "package ext; public class Helper {public float x, y;"
             "public int originalExtraBehavior(){return 13;} }"),
            (self.OWNER,
             "package ext; public class Matrix {"
             "public float[] data; "
             "public float combine(ext.Helper other) {"
             "return other.x + other.y + this.data[0]; }"
             "public int originalGameLink(rs.Game game){ return game.value(); }"
             "}"),
        ]
        for internal, body in items:
            target = self.root / (internal + ".java")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
            javac = subprocess.run([
                shutil.which("javac"), "--release", "9", "-g:none",
                "-proc:none", "-classpath", str(classes), "-d",
                str(classes), str(target),
            ], capture_output=True)
            self.assertEqual(0, javac.returncode,
                             javac.stderr.decode("utf8", errors="replace"))
        dest = self.root / "original.jar"
        with ZipFile(dest, "w") as out:
            for file in sorted(classes.rglob("*.class")):
                out.write(file, file.relative_to(classes).as_posix())
        return dest

    def write_zip(self, filename, sources):
        dest = self.root / filename
        with ZipFile(dest, "w") as output:
            for name, contents in sorted(sources.items()):
                output.writestr("src/main/java/"+name, contents)
        return dest

    def verify(self, helper=None, *, helper_sha=None):
        helper = self.helper if helper is None else helper
        if helper_sha is None and helper is not None:
            helper_sha = self.sha(helper)
        return verify_private_matrix_source_subset(
            self.original, self.source, self.selection,
            original_sha256=self.sha(self.original),
            recovered_source_sha256=self.sha(self.source),
            selection_sha256=self.sha(self.selection),
            original_owner=self.OWNER,
            private_scaffold_java_zip=helper,
            private_scaffold_sha256=helper_sha)

    def test_strict_selected_method_code_with_source_only_helper(self):
        report = self.verify()
        self.assertEqual(1, report["verified_selected_method_count"])
        self.assertEqual(1, report["private_compilation_only_helper_source_count"])
        self.assertTrue(report["all_selected_core_method_code_equal"])
        self.assertFalse(report["helper_java_source_class_bodies_verified_original"])
        self.assertFalse(report["original_helper_binary_classfiles_placed_on_classpath"])
        self.assertFalse(report["complete_original_matrix_java_source_restored"])
        self.assertFalse(report["unselected_private_methods_and_scaffolding_accepted"])

    def test_missing_source_helper_cannot_fallback_to_original_binary(self):
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.verify(helper=None)

    def test_wrong_helper_field_type_cannot_silently_match(self):
        incorrect = self.write_zip("incorrect-helper.zip", {
            self.HELPER+".java":
            "package ext; public class Helper {public int x; public float y;}",
        })
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.verify(incorrect)

    def test_original_game_owner_as_fake_helper_is_forbidden(self):
        incorrect = self.write_zip("wrong-owner-helper.zip", {
            "rs/Game.java": "package rs; public class Game {}",
        })
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.verify(incorrect)

    def test_unlisted_original_helper_owner_is_not_accepted(self):
        incorrect = self.write_zip("unknown-owner-helper.zip", {
            "ext/Invented.java": "package ext; public class Invented {}",
        })
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.verify(incorrect)

    def test_helper_hash_drift_rejected(self):
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.verify(helper_sha="0"*64)


if __name__ == "__main__":
    unittest.main()
