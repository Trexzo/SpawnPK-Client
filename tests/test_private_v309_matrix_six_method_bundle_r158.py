"""R158: six selected Java matrix methods compiled with only three source helpers."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_matrix_six_method_bundle_r158 import (
    verify_six_matrix_methods,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "JDK required for original and reconstructed Java class")
class R158MatrixSixSelectedMethodBundleTests(unittest.TestCase):
    OWNER = "ext/Matrix"
    METHOD_IDS = [
        ("c", "()[F"), ("d", "()[F"),
        ("toString", "()Ljava/lang/String;"),
        ("write", "(Lext/Components;)V"),
        ("scales", "()[F"),
        ("rotate", "(Lext/Quaternion;)V"),
    ]

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.original = self._compile_original_jar()
        self.source_text = self._matrix_source(game=False)
        self.source = self._archive("source.zip", {
            self.OWNER + ".java": self.source_text,
        })
        self.helpers = self._archive("helpers.zip", {
            "ext/Components.java":
                "package ext; public class Components {public float x,y,z;}",
            "ext/Quaternion.java":
                "package ext; public class Quaternion {public float x,y,z,w;}",
            "ext/Vector.java":
                "package ext; public class Vector {"
                "public Vector(float x,float y,float z){}"
                "public float norm(){return 0.0F;}}",
        })
        self.selection = self.root / "selection.json"
        self.selection.write_text(
            json.dumps([{"name": n, "descriptor": d}
                        for n, d in self.METHOD_IDS]),
            encoding="utf-8")
        with ZipFile(self.original) as z:
            original_binary = z.read(self.OWNER + ".class")
        self.owner_sha = hashlib.sha256(original_binary).hexdigest()
        profile = profile_class_field_accesses(original_binary)
        self.instructions = sum(
            len(m["instructions"]) for m in profile["methods"]
            if (m["name"], m["descriptor"]) in self.METHOD_IDS)

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @staticmethod
    def _matrix_source(*, game, changed_quaternion=False):
        operand = "q.y + q.z" if changed_quaternion else "q.y * q.z"
        text = (
            "package ext; public final class Matrix {\n"
            "public float[] data;\n"
            "float[] c() {return new float[]{data[0],data[1],data[2]};}\n"
            "public float[] d() {return new float[]{data[3],data[4],data[5]};}\n"
            "public String toString() {this.d();this.c();return \"matrix\";}\n"
            "public void write(Components p) {"
            "data[0]=p.x;data[1]=p.y;data[2]=p.z;}\n"
            "public float[] scales() {"
            "Vector v1=new Vector(data[0],data[1],data[2]);"
            "Vector v2=new Vector(data[4],data[5],data[6]);"
            "Vector v3=new Vector(data[8],data[9],data[10]);"
            "return new float[]{v1.norm(),v2.norm(),v3.norm()};}\n"
            "public void rotate(Quaternion q) {"
            "data[0]=q.x*q.x;data[1]=" + operand + ";"
            "data[2]=q.z*q.w;}\n")
        if game:
            text += "public int linked(rs.Game g){return g.value();}\n"
        return text + "}\n"

    def _compile_original_jar(self):
        classes = self.root / "original-classes"
        classes.mkdir()
        original = [
            ("rs/Game", "package rs; public class Game {"
             "public int value(){return 1;}}"),
            ("ext/Components",
             "package ext; public class Components {"
             "public float x,y,z;public int unused(){return 8;}}"),
            ("ext/Quaternion",
             "package ext; public class Quaternion {"
             "public float x,y,z,w;public int unused(){return 9;}}"),
            ("ext/Vector",
             "package ext; public class Vector {"
             "public float x,y,z;"
             "public Vector(float x,float y,float z) {"
             "this.x=x;this.y=y;this.z=z;}"
             "public float norm(){return x*x+y*y+z*z;}}"),
            (self.OWNER, self._matrix_source(game=True)),
        ]
        for internal, code in original:
            p = self.root / "original-src" / (internal + ".java")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(code, encoding="utf-8")
            result = subprocess.run(
                [shutil.which("javac"), "--release", "9",
                 "-proc:none", "-g:none", "-classpath", str(classes),
                 "-d", str(classes), str(p)], capture_output=True)
            self.assertEqual(0, result.returncode,
                             result.stderr.decode("utf-8", errors="replace"))
        target = self.root / "original.jar"
        with ZipFile(target, "w") as jar:
            for p in sorted(classes.rglob("*.class")):
                jar.write(p, p.relative_to(classes).as_posix())
        return target

    def _archive(self, name, sources):
        target = self.root / name
        with ZipFile(target, "w") as output:
            for rel, body in sorted(sources.items()):
                output.writestr("src/main/java/" + rel, body)
        return target

    def prove(self, *, source=None, helpers=None,
              expected_instructions=None):
        source = source or self.source
        helpers = helpers or self.helpers
        if expected_instructions is None:
            expected_instructions = self.instructions
        return verify_six_matrix_methods(
            self.original, source, helpers, self.selection,
            original_sha256=self.sha(self.original),
            source_sha256=self.sha(source),
            helper_sha256=self.sha(helpers),
            selection_sha256=self.sha(self.selection),
            matrix_owner=self.OWNER,
            expected_matrix_sha256=self.owner_sha,
            expected_method_count=6,
            expected_instructions=expected_instructions,
            expected_helper_count=3,
            expected_self_calls=2)

    def test_six_methods_and_three_helpers_closed_and_recompiled(self):
        result = self.prove()
        self.assertEqual(6, result["verified_matrix_method_count"])
        self.assertEqual(self.instructions, result["verified_jvm_instruction_count"])
        self.assertEqual(2, result["verified_internal_source_call_edges"])
        self.assertFalse(result["helper_java_bodies_original_proven"])
        self.assertFalse(result["full_matrix_or_client_original_source_complete"])
        self.assertFalse(result["original_source_publication_authorized"])

    def test_original_method_instruction_count_drift_refused(self):
        with self.assertRaises(ValueError):
            self.prove(expected_instructions=self.instructions + 1)

    def test_mutated_quaternion_expression_refused(self):
        changed = self._archive("wrong-quaternion.zip", {
            self.OWNER + ".java":
                self._matrix_source(game=False, changed_quaternion=True),
        })
        with self.assertRaises(ValueError):
            self.prove(source=changed)

    def test_missing_third_helper_cannot_fall_back_to_binary(self):
        reduced = self._archive("missing-quaternion-helper.zip", {
            "ext/Components.java":
                "package ext; public class Components {public float x,y,z;}",
            "ext/Vector.java":
                "package ext; public class Vector {"
                "public Vector(float x,float y,float z){}"
                "public float norm(){return 0.0F;}}",
        })
        with self.assertRaises(ValueError):
            self.prove(helpers=reduced)


if __name__ == "__main__":
    unittest.main()
