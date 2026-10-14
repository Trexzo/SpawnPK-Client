"""R160 synthetic original Java to reconstructed local-float bytecode parity."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.source_method_parity import _normalized_instructions
from spk_recovery.private_v309_float_locals_lifter_r160 import (
    PrivateJVMFloatLocalsR160Error, recover_original_float_local_method)


@unittest.skipUnless(shutil.which("javac") and shutil.which("javap"), "JDK required")
class R160MatrixLocalFloatTest(unittest.TestCase):
    OWNER = "example/Matrix"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        src = {
            "rs/Game.java": "package rs; public class Game {}",
            "example/Matrix.java": (
                "package example; public class Matrix {public float[] e;"
                "float g(){return 3f;}"
                "public void c(Matrix other){"
                "float v2=other.e[12]*this.e[3]+this.e[0]*other.e[0];"
                "float v3=other.e[13]*this.e[3]+this.e[0]*other.e[1];"
                "this.e[0]=v2;this.e[1]=v3;}"
                "public void h(){float v1=1.0F/this.g();"
                "float v2=((this.e[3]*this.e[5])-(this.e[10]*(-this.e[7])))*v1;"
                "this.e[0]=v2;}"
                "public int link(rs.Game g){return 1;}}"),
        }
        cls = self.root / "cls"
        cls.mkdir()
        for name, body in src.items():
            file = self.root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(body)
            proc = subprocess.run(
                [shutil.which("javac"), "--release", "9", "-proc:none",
                 "-g:none", "-classpath", str(cls), "-d", str(cls), str(file)],
                capture_output=True)
            self.assertEqual(0, proc.returncode, proc.stderr.decode())
        self.jar = self.root / "original.jar"
        with ZipFile(self.jar, "w") as zip_:
            for file in cls.rglob("*.class"):
                zip_.write(file, file.relative_to(cls).as_posix())
        self.original_bytes = (cls / "example/Matrix.class").read_bytes()
        self.profile = profile_class_field_accesses(self.original_bytes)

    def lift(self, name, desc, **kwargs):
        method = next(m for m in self.profile["methods"]
                      if m["name"] == name and m["descriptor"] == desc)
        return recover_original_float_local_method(
            self.jar, original_sha256=kwargs.get(
                "sha", hashlib.sha256(self.jar.read_bytes()).hexdigest()),
            owner=self.OWNER, name=name, descriptor=desc,
            java_header="public void " +
                ("c(example.Matrix)" if name == "c" else "h()"),
            matrix_float_array_field="e",
            expected_instruction_count=len(method["instructions"]) +
                                       kwargs.get("extra", 0),
            expected_final_offset=method["instructions"][-1]["offset"],
            exact_original_owner_sha256=hashlib.sha256(
                self.original_bytes).hexdigest(),
            parameter_type=self.OWNER if name == "c" else None,
            allow_float_reader=kwargs.get(
                "reader", "g" if name == "h" else None))

    def test_exact_source_recompilation_of_both_methods(self):
        one = self.lift("c", "(Lexample/Matrix;)V")
        two = self.lift("h", "()V")
        code = ("package example; public class Matrix {float[] e;"
                "float g(){return 0f;}" +
                one["private_java_method_source_not_accepted"] +
                two["private_java_method_source_not_accepted"] + "}")
        source = self.root / "rebuilt/example/Matrix.java"
        source.parent.mkdir(parents=True)
        source.write_text(code)
        out = self.root / "rebuilt-classes"
        out.mkdir()
        proc = subprocess.run([shutil.which("javac"), "--release", "9",
            "-proc:none", "-g:none", "-d", str(out), str(source)],
            capture_output=True)
        self.assertEqual(0, proc.returncode, proc.stderr.decode())
        compiled = profile_class_field_accesses(
            (out / "example/Matrix.class").read_bytes())
        for name, desc in [("c","(Lexample/Matrix;)V"), ("h","()V")]:
            a = next(m for m in self.profile["methods"] if
                     (m["name"],m["descriptor"]) == (name,desc))
            b = next(m for m in compiled["methods"] if
                     (m["name"],m["descriptor"]) == (name,desc))
            self.assertEqual(a["code_length"], b["code_length"])
            self.assertEqual(_normalized_instructions(self.profile,a),
                             _normalized_instructions(compiled,b))

    def test_hash_and_opcode_count_guards(self):
        with self.assertRaises(PrivateJVMFloatLocalsR160Error):
            self.lift("c", "(Lexample/Matrix;)V", sha="0"*64)
        with self.assertRaises(PrivateJVMFloatLocalsR160Error):
            self.lift("h", "()V", extra=1)

    def test_unapproved_original_self_method_rejected(self):
        with self.assertRaises(PrivateJVMFloatLocalsR160Error):
            self.lift("h", "()V", reader=None)


if __name__ == "__main__":
    unittest.main()
