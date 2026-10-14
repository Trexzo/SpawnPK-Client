"""R152: exact original-linked JVM static pool, factory and release source proofs."""
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
                     "Real JDK required for original matrix pooling source tests")
class R152OriginalMatrixPoolSourceTests(unittest.TestCase):
    def setUp(self):
        keeper = tempfile.TemporaryDirectory()
        self.addCleanup(keeper.cleanup)
        self.root = Path(keeper.name)
        self.owner = "ext/Matrix"
        self.orig = self._compile_original()
        self.source = self._make_source_zip(self._matrix(game=False),
                                            "partial-matrix.zip")
        self.selection = self.root / "selected-pool-methods.json"
        self.selection.write_text(json.dumps([
            {"name": "acquire", "descriptor": "()Lext/Matrix;"},
            {"name": "recycle", "descriptor": "()V"},
            {"name": "<clinit>", "descriptor": "()V"},
        ]), encoding="utf-8")

    @staticmethod
    def _sha(file):
        return hashlib.sha256(Path(file).read_bytes()).hexdigest()

    def _matrix(self, *, game, capacity=100, release="++n - 1"):
        text = (
            "package ext;\npublic final class Matrix {\n"
            " public static final Matrix IDENTITY;\n"
            " static Matrix[] pool;\n"
            " static int capacity;\n"
            " static int n;\n"
            " public float[] elements;\n"
            " static {\n"
            "   pool = new Matrix[0];\n"
            f"   capacity = {capacity};\n"
            f"   pool = new Matrix[{capacity}];\n"
            "   n = 0;\n"
            "   IDENTITY = new Matrix();\n"
            " }\n"
            " public Matrix() { elements = new float[16]; reset(); }\n"
            " void reset() { elements[0] = " +
            ("1.0f" if game else "0.0f") + "; }\n"
            " public static Matrix acquire() {\n"
            "   synchronized(pool) {\n"
            "      if (n == 0) return new Matrix();\n"
            "      pool[--n].reset();\n"
            "      return pool[n];\n"
            "   }\n"
            " }\n"
            " public void recycle() {\n"
            "    synchronized (pool) {\n"
            "      if (n < capacity - 1) pool[" + release + "] = this;\n"
            "    }\n"
            " }\n"
        )
        if game:
            text += (" public int gameValue(rs.Game game) { "
                     "return game.value(); }\n")
        return text + "}\n"

    def _compile_original(self):
        classes = self.root / "classes-original"
        classes.mkdir()
        for internal, body, label in [
            ("rs/Game", "package rs; public class Game { public int value() { return 7; }}",
             "game"),
            (self.owner, self._matrix(game=True), "original"),
        ]:
            file = self.root / label / (internal + ".java")
            file.parent.mkdir(parents=True)
            file.write_text(body, encoding="utf-8")
            result = subprocess.run(
                [shutil.which("javac"), "--release", "9", "-proc:none",
                 "-g:none", "-classpath", str(classes), "-d", str(classes),
                 str(file)], capture_output=True)
            self.assertEqual(0, result.returncode,
                             result.stderr.decode("utf-8", errors="replace"))
        jar = self.root / "original.jar"
        with ZipFile(jar, "w") as archive:
            for cls in sorted(classes.rglob("*.class")):
                archive.write(cls, cls.relative_to(classes).as_posix())
        return jar

    def _make_source_zip(self, source, name):
        result = self.root / name
        with ZipFile(result, "w") as archive:
            archive.writestr("src/main/java/" + self.owner + ".java", source)
        return result

    def prove(self, source=None, *, class_init=True, constructor=False):
        source = source or self.source
        return verify_private_matrix_source_subset(
            self.orig, source, self.selection,
            original_sha256=self._sha(self.orig),
            recovered_source_sha256=self._sha(source),
            selection_sha256=self._sha(self.selection),
            original_owner=self.owner,
            allow_class_initializer=class_init,
            allow_constructor_methods=constructor)

    def test_factory_recycle_and_initializer_source_all_match_original(self):
        result = self.prove()
        self.assertEqual(3, result["verified_selected_method_count"])
        self.assertEqual(1, result["verified_selected_class_initializer_count"])
        self.assertEqual(0, result["verified_constructor_count"])
        self.assertGreaterEqual(result["matched_opcode_count"], 70)
        self.assertTrue(result["all_selected_core_method_code_equal"])
        self.assertTrue(result["source_compiled_with_empty_original_external_classpath"])
        self.assertFalse(result["unselected_constructors_or_initializers_recovered"])
        self.assertFalse(result["complete_original_matrix_java_source_restored"])
        self.assertFalse(result["original_game_class_binary_fallback_used"])

    def test_static_initializer_opt_in_is_explicitly_required(self):
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.prove(class_init=False)

    def test_wrong_pool_size_changes_original_class_initializer_code(self):
        source = self._make_source_zip(
            self._matrix(game=False, capacity=99), "wrong-capacity.zip")
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.prove(source)

    def test_different_increment_expression_changes_original_release_code(self):
        source = self._make_source_zip(
            self._matrix(game=False, release="n++"), "wrong-increment.zip")
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.prove(source)

    def test_constructor_requires_separate_opt_in(self):
        config = self.root / "with-constructor-selection.json"
        config.write_text(json.dumps([
            {"name": "<init>", "descriptor": "()V"}
        ]), encoding="utf-8")
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            verify_private_matrix_source_subset(
                self.orig, self.source, config,
                original_sha256=self._sha(self.orig),
                recovered_source_sha256=self._sha(self.source),
                selection_sha256=self._sha(config),
                original_owner=self.owner,
                allow_class_initializer=True,
                allow_constructor_methods=False)


if __name__ == "__main__":
    unittest.main()
