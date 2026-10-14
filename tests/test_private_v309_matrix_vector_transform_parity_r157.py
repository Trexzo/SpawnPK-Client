"""R157: source-only vector/transform original matrix method parity.

The two extra original auxiliary JVM classes are compiled from independent
Java source scaffolds, not taken from the original client classpath. Their
unselected behavior is intentionally different and NEVER accepted as original.
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
                     "JDK required to compile original-linked math helpers")
class R157MatrixVectorTransformOriginalMethodParity(unittest.TestCase):
    OWNER = "ext/Matrix"

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.original = self._original_jar()
        self.candidate = self.zip_source("matrix-source.zip", {
            "ext/Matrix.java": self.matrix_java(original=False),
        })
        self.scaffolds = self.zip_source("helper-sources.zip", {
            "ext/Transform.java":
                "package ext; public class Transform { public float x,y,z; }",
            "ext/Vector.java":
                "package ext; public class Vector {"
                " public Vector(float x,float y,float z){}"
                " public float norm(){return 0.0F;} }",
        })
        self.selection = self.root / "two-method-selection.json"
        self.selection.write_text(json.dumps([
            {"name":"assign", "descriptor":"(Lext/Transform;)V"},
            {"name":"scales", "descriptor":"()[F"},
        ]), encoding="utf-8")

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @staticmethod
    def matrix_java(*, original, wrong_matrix_index=False):
        second_index = 4 if wrong_matrix_index else 1
        source = (
            "package ext; public class Matrix {"
            " public float[] data;"
            " public void assign(ext.Transform t) {"
            "  this.data[0]=t.x;"
            f"  this.data[{second_index}]=t.y;"
            "  this.data[2]=t.z;"
            " }"
            " public float[] scales(){"
            "  float[] r = new float[3];"
            "  ext.Vector v1 = new ext.Vector(data[0],data[1],data[2]);"
            "  ext.Vector v2 = new ext.Vector(data[4],data[5],data[6]);"
            "  ext.Vector v3 = new ext.Vector(data[8],data[9],data[10]);"
            "  r[0]=v1.norm();"
            "  r[1]=v2.norm();"
            "  r[2]=v3.norm();"
            "  return r;"
            " }"
        )
        if original:
            source += (" public int gameOwnerReference(rs.Game game) {"
                       "return game.value();}")
        return source + "}"

    def _original_jar(self):
        classes = self.root / "original-classes"
        classes.mkdir()
        source = [
            ("rs/Game", "package rs; public class Game {"
             "public int value(){return 5;}}"),
            ("ext/Transform", "package ext; public class Transform {"
             "public float x,y,z; public int originalUnused(){return 1;}}"),
            ("ext/Vector", "package ext; public class Vector {"
             "float x,y,z; public Vector(float x,float y,float z){"
             "this.x=x;this.y=y;this.z=z;}"
             "public float norm(){return x*x+y*y+z*z;}}"),
            (self.OWNER, self.matrix_java(original=True)),
        ]
        for internal, code in source:
            file = self.root / "orig" / (internal + ".java")
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(code, encoding="utf-8")
            proc = subprocess.run(
                [shutil.which("javac"), "--release", "9",
                 "-proc:none", "-g:none", "-classpath", str(classes),
                 "-d", str(classes), str(file)],
                capture_output=True)
            self.assertEqual(0, proc.returncode,
                             proc.stderr.decode("utf-8", errors="replace"))
        archive = self.root / "original.jar"
        with ZipFile(archive, "w") as out:
            for binary in sorted(classes.rglob("*.class")):
                out.write(binary, binary.relative_to(classes).as_posix())
        return archive

    def zip_source(self, filename, source):
        archive = self.root / filename
        with ZipFile(archive, "w") as output:
            for name, body in sorted(source.items()):
                output.writestr("src/main/java/" + name, body)
        return archive

    def prove(self, *, source=None, helper=None, selected=None):
        source = source or self.candidate
        helper = helper or self.scaffolds
        selected = selected or self.selection
        return verify_private_matrix_source_subset(
            self.original, source, selected,
            original_sha256=self.sha(self.original),
            recovered_source_sha256=self.sha(source),
            selection_sha256=self.sha(selected),
            original_owner=self.OWNER,
            private_scaffold_java_zip=helper,
            private_scaffold_sha256=self.sha(helper))

    def test_two_real_javac_methods_with_two_unaccepted_source_helpers(self):
        proof = self.prove()
        self.assertEqual(2, proof["verified_selected_method_count"])
        self.assertEqual(2, proof["private_compilation_only_helper_source_count"])
        self.assertGreater(proof["matched_opcode_count"], 45)
        self.assertTrue(proof["all_selected_core_method_code_equal"])
        self.assertFalse(proof["helper_java_source_class_bodies_verified_original"])
        self.assertFalse(proof["original_helper_binary_classfiles_placed_on_classpath"])
        self.assertFalse(proof["complete_original_matrix_java_source_restored"])
        self.assertFalse(proof["original_game_class_binary_fallback_used"])

    def test_wrong_transform_array_index_rejected_by_bytecode(self):
        changed = self.zip_source("wrong-transform.zip", {
            "ext/Matrix.java":
                self.matrix_java(original=False, wrong_matrix_index=True),
        })
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.prove(source=changed)

    def test_missing_one_helper_source_never_uses_original_binary(self):
        reduced = self.zip_source("one-helper.zip", {
            "ext/Transform.java":
                "package ext; public class Transform {public float x,y,z;}",
        })
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.prove(helper=reduced)

    def test_wrong_vector_method_return_signature_rejected(self):
        changed = self.zip_source("wrong-return-helper.zip", {
            "ext/Transform.java":
                "package ext; public class Transform {public float x,y,z;}",
            "ext/Vector.java":
                "package ext; public class Vector {"
                "public Vector(float x,float y,float z){}"
                "public int norm(){return 0;}}",
        })
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            self.prove(helper=changed)

    def test_changed_original_source_sha_fails_closed(self):
        with self.assertRaises(PrivateMatrixMethodSourceR150Error):
            verify_private_matrix_source_subset(
                self.original, self.candidate, self.selection,
                original_sha256="0"*64,
                recovered_source_sha256=self.sha(self.candidate),
                selection_sha256=self.sha(self.selection),
                original_owner=self.OWNER,
                private_scaffold_java_zip=self.scaffolds,
                private_scaffold_sha256=self.sha(self.scaffolds))


if __name__ == "__main__":
    unittest.main()
