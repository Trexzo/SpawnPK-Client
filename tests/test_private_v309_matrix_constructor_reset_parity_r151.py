"""R151: original constructor + identity/zero source-only matrix recovery."""
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
                     "JDK required for real Java constructor bytecode tests")
class R151MatrixConstructorResetRecoveryTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.TemporaryDirectory()
        self.addCleanup(handle.cleanup)
        self.root = Path(handle.name)
        self.owner = "ext/Matrix"
        self.original = self._original_jar()
        self.source = self._java_zip(self._matrix_java(game=False), "source.zip")
        self.selected = self._selection()

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def _matrix_java(self, *, game, bad_reset=False):
        # Entirely synthetic Java fixtures, not private SpawnPK source.
        text = (
            "package ext;\n"
            "public final class Matrix {\n"
            " public float[] entries;\n"
            " public Matrix() { this.entries = new float[16]; this.reset(); }\n"
            " public Matrix(Matrix source) { this.entries = new float[16]; "
            "System.arraycopy(source.entries, 0, this.entries, 0, 16); }\n"
            " void reset() {\n"
        )
        for index in range(16):
            value = "1.0f" if index in (0, 5, 10, 15) else "0.0f"
            if bad_reset and index == 5:
                value = "0.0f"
            text += f"this.entries[{index}]={value};\n"
        text += "}\npublic void zero() {\n"
        for index in range(16):
            text += f"this.entries[{index}]=0.0f;\n"
        text += "}\n"
        if game:
            text += "public int dependent(rs.Game game) { return game.value(); }\n"
        return text + "}\n"

    def _original_jar(self):
        compiled = self.root / "original-classes"
        compiled.mkdir()
        for name, content, label in [
            ("rs/Game",
             "package rs; public class Game { public int value() { return 3; }}",
             "game"),
            (self.owner, self._matrix_java(game=True), "matrix"),
        ]:
            target = self.root / label / (name + ".java")
            target.parent.mkdir(parents=True)
            target.write_text(content, encoding="utf-8")
            result = subprocess.run(
                [shutil.which("javac"), "--release", "9",
                 "-proc:none", "-g:none", "-classpath", str(compiled),
                 "-d", str(compiled), str(target)],
                capture_output=True, check=False)
            self.assertEqual(0, result.returncode,
                             result.stderr.decode("utf8", errors="replace"))
        out = self.root / "original-synthetic.jar"
        with ZipFile(out, "w") as archive:
            for name in sorted(compiled.rglob("*.class")):
                archive.write(name, name.relative_to(compiled).as_posix())
        return out

    def _java_zip(self, code, name):
        dest = self.root / name
        with ZipFile(dest, "w") as zip_:
            zip_.writestr("src/main/java/" + self.owner + ".java", code)
        return dest

    def _selection(self):
        out = self.root / "four-exact-method-ids.json"
        out.write_text(json.dumps([
            {"name": "<init>", "descriptor": "()V"},
            {"name": "<init>", "descriptor": "(Lext/Matrix;)V"},
            {"name": "reset", "descriptor": "()V"},
            {"name": "zero", "descriptor": "()V"},
        ]), encoding="utf-8")
        return out

    def review(self, source=None, *, allow=True, selection=None):
        source = source or self.source
        selection = selection or self.selected
        return verify_private_matrix_source_subset(
            self.original, source, selection,
            original_sha256=self.sha(self.original),
            recovered_source_sha256=self.sha(source),
            selection_sha256=self.sha(selection),
            original_owner=self.owner,
            allow_constructor_methods=allow)

    def test_two_constructors_reset_and_zero_recompile_without_game_binaries(self):
        r = self.review()
        self.assertEqual(4, r["verified_selected_method_count"])
        self.assertEqual(2, r["verified_constructor_count"])
        self.assertGreaterEqual(r["matched_opcode_count"], 170)
        self.assertEqual(0, r["core_method_bytecode_differences"])
        self.assertTrue(r["all_selected_core_method_code_equal"])
        self.assertTrue(r["source_compiled_with_empty_original_external_classpath"])
        self.assertFalse(r["original_game_class_binary_fallback_used"])
        self.assertFalse(r["unselected_constructors_or_initializers_recovered"])
        self.assertFalse(r["complete_original_matrix_java_source_restored"])

    def test_no_silent_constructor_acceptance_without_opt_in(self):
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.review(allow=False)

    def test_modified_identity_reset_is_rejected(self):
        src = self._java_zip(
            self._matrix_java(game=False, bad_reset=True),
            "incorrect-reset-source.zip")
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.review(src)

    def test_selected_static_class_initializer_is_forbidden(self):
        selection = self.root / "forbidden-class-init.json"
        selection.write_text(json.dumps([{
            "name": "<clinit>", "descriptor": "()V"
        }]), encoding="utf-8")
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.review(selection=selection)

    def test_wrong_source_hash_refused_before_javac(self):
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            verify_private_matrix_source_subset(
                self.original, self.source, self.selected,
                original_sha256=self.sha(self.original),
                recovered_source_sha256="0" * 64,
                selection_sha256=self.sha(self.selected),
                original_owner=self.owner,
                allow_constructor_methods=True)


if __name__ == "__main__":
    unittest.main()
