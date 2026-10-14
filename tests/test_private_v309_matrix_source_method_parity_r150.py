"""R150: independent Java-source rebuild of six selected synthetic JVM methods."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_matrix_source_method_parity_r150 import (
    PrivateMatrixMethodSourceR150Error, verify_private_matrix_source_subset,
)


@unittest.skipUnless(shutil.which("java") and shutil.which("javac"),
                     "JDK required for original-JVM source parity fixtures")
class R150LinkedMatrixPartialSourceTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name)
        self.owner = "ext/Matrix"
        self.original_body = self._matrix_source(original=True)
        self.private_source_body = self._matrix_source(original=False)
        self.original_jar = self._original_jar()
        self.private_source_zip = self.source_zip(
            self.private_source_body, "partial-source.zip")
        self.selection = self._selection_file()

    @staticmethod
    def _matrix_source(*, original):
        # These are entirely synthetic generic math fixtures, not real
        # SpawnPK original source or proprietary matrix implementation.
        body = (
            "package ext;\n"
            "import java.util.Arrays;\n"
            "public final class Matrix {\n"
            " public float[] values;\n"
            " public Matrix() { values = new float[16]; reset(); }\n"
            " void reset() { " +
            ("Arrays.fill(values, 1f);" if original else
             "Arrays.fill(values, 0f);") +
            " }\n"
            " public void copyTo(Matrix dest) { "
            "System.arraycopy(this.values,0,dest.values,0,16); }\n"
            " public void uniform(float v) { this.three(v,v,v); }\n"
            " public void three(float x,float y,float z) { "
            "this.reset(); this.values[0]=x;this.values[5]=y;"
            "this.values[10]=z; }\n"
            " public void add(Matrix m) { "
            "for (int i=0;i<values.length;i++) values[i]+=m.values[i]; }\n"
            " public int hashCode() { int a=1; int b=1; "
            "return b*31+Arrays.hashCode(this.values); }\n"
            " public boolean equals(Object obj) { "
            "if (!(obj instanceof Matrix)) return false; "
            "Matrix m=(Matrix)obj; for(int i=0;i<16;i++) { "
            "if (m.values[i]!=this.values[i]) return false; "
            "} return true; }\n"
        )
        if original:
            body += (" public int useGame(rs.Game g) { "
                     "return g.value(); }\n")
        return body + "}\n"

    @staticmethod
    def _sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def _original_jar(self):
        classes = self.root / "original-classes"
        classes.mkdir()
        for internal, source, label in [
            ("rs/Game", "package rs; public class Game { "
             "public int value() { return 21; }}", "game"),
            (self.owner, self.original_body, "matrix"),
        ]:
            target = self.root / label / (internal + ".java")
            target.parent.mkdir(parents=True)
            target.write_text(source, encoding="utf-8")
            cmd = [shutil.which("javac"), "--release", "9", "-proc:none",
                   "-g:none", "-d", str(classes), "-classpath", str(classes),
                   str(target)]
            result = subprocess.run(cmd, capture_output=True, check=False)
            self.assertEqual(0, result.returncode,
                             result.stderr.decode("utf-8", errors="replace"))
        jar = self.root / "synthetic-original.jar"
        with ZipFile(jar, "w") as output:
            for cls in sorted(classes.rglob("*.class")):
                output.write(cls, cls.relative_to(classes).as_posix())
        return jar

    def source_zip(self, code, name):
        archive = self.root / name
        with ZipFile(archive, "w") as zip_:
            zip_.writestr("src/main/java/" + self.owner + ".java", code)
        return archive

    def _selection_file(self):
        ids = [
            ("copyTo", "(Lext/Matrix;)V"),
            ("uniform", "(F)V"),
            ("three", "(FFF)V"),
            ("add", "(Lext/Matrix;)V"),
            ("hashCode", "()I"),
            ("equals", "(Ljava/lang/Object;)Z"),
        ]
        path = self.root / "private-selected-methods.json"
        path.write_text(json.dumps(
            [{"name": n, "descriptor": d} for n, d in ids]),
            encoding="utf-8")
        return path

    def prove(self, source=None, selection=None):
        source = source or self.private_source_zip
        selection = selection or self.selection
        return verify_private_matrix_source_subset(
            self.original_jar, source, selection,
            original_sha256=self._sha(self.original_jar),
            recovered_source_sha256=self._sha(source),
            selection_sha256=self._sha(selection),
            original_owner=self.owner)

    def test_independent_six_method_rebuild_without_original_game_binary(self):
        report = self.prove()
        self.assertEqual(6, report["verified_selected_method_count"])
        self.assertGreater(report["matched_opcode_count"], 60)
        self.assertTrue(report["all_selected_core_method_code_equal"])
        self.assertTrue(report["source_compiled_with_empty_original_external_classpath"])
        self.assertFalse(report["original_game_class_binary_fallback_used"])
        self.assertFalse(report["complete_original_matrix_java_source_restored"])
        self.assertFalse(report["unselected_private_methods_and_scaffolding_accepted"])
        self.assertFalse(report["derived_original_source_publication_authorized"])
        self.assertNotIn("private_methods", report)

    def test_differing_original_reset_scaffold_is_not_accidentally_accepted(self):
        report = self.prove()
        self.assertTrue(report["all_selected_core_method_code_equal"])
        self.assertFalse(report["unselected_private_methods_and_scaffolding_accepted"])

    def test_changed_selected_add_body_is_rejected(self):
        modified = self.source_zip(
            self.private_source_body.replace(
                "values[i]+=m.values[i]", "values[i]-=m.values[i]"),
            "incorrect-add.zip")
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.prove(source=modified)

    def test_selection_cannot_include_unrecovered_original_game_method(self):
        config = self.root / "bad-method-selection.json"
        config.write_text(json.dumps([{
            "name": "useGame", "descriptor": "(Lrs/Game;)I"
        }]), encoding="utf-8")
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.prove(selection=config)

    def test_original_sha_preflight_aborts(self):
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            verify_private_matrix_source_subset(
                self.original_jar, self.private_source_zip,
                self.selection, original_sha256="0"*64,
                recovered_source_sha256=self._sha(self.private_source_zip),
                selection_sha256=self._sha(self.selection),
                original_owner=self.owner)

    def test_source_hash_preflight_aborts(self):
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            verify_private_matrix_source_subset(
                self.original_jar, self.private_source_zip,
                self.selection,
                original_sha256=self._sha(self.original_jar),
                recovered_source_sha256="0"*64,
                selection_sha256=self._sha(self.selection),
                original_owner=self.owner)

    def test_constructor_as_synthetic_scaffold_never_promoted(self):
        config = self.root / "constructor-selection.json"
        config.write_text(json.dumps([{
            "name": "<init>", "descriptor": "()V"
        }]), encoding="utf-8")
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.prove(selection=config)


if __name__ == "__main__":
    unittest.main()
