"""R149: original and independently deobfuscated Java9 signed short parity.

Synthetic JVM binaries and Java source only. Cross-platform strict nested
JavacTask parse, isolated javac --release 9 and resolved CP operand check.
"""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_packet_signed_short_body_parity_r149 import (
    PrivateSignedShortBodyParityR149Error,
    prove_private_signed_short_body_rebuild,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "Real JDK required for independently compiled parity")
class R149OriginalPacketShortReaderBodyParity(unittest.TestCase):
    ORIGINAL = "obf/x/e"
    SOURCE = "rs/io/Packet.java"
    MATRIX = "obf/m/Matrix"
    MODULUS = "123456789" * 24 + "123456"

    BODY = (
        "{\n"
        "   this.caret += 2;\n"
        "   int var1 = ((this.payload[this.caret - 2] & 255) << 8)"
        " + (this.payload[this.caret - 1] & 255);\n"
        "   if (var1 > 32767) {\n"
        "      var1 -= 65536;\n"
        "   }\n"
        "   return var1;\n"
        "}\n"
    )

    def setUp(self):
        keeper = tempfile.TemporaryDirectory()
        self.addCleanup(keeper.cleanup)
        self.root = Path(keeper.name)
        self.original = self.original_jar("correct.jar", real_b=True)
        self.text = (
            "package rs.io;\nimport java.math.BigInteger;\n"
            "public class Packet {\n"
            f" private static final BigInteger rsaModulus = new BigInteger(\"{self.MODULUS}\");\n"
            " private static final BigInteger rsaExponent = new BigInteger(\"65537\");\n"
            " public byte[] payload;\n"
            " public int caret;\n"
            " public Packet() {}\n"
            " public int method2616() " + self.BODY + "\n"
            " public int method673() " + self.BODY + "\n"
            " public int otherMethod() { return 9; }\n"
            "}\n"
        )
        self.source = self.source_zip(self.text, "client-source.zip")

    def original_jar(self, name, *, real_b):
        staging = self.root / ("stage-" + name)
        classes = staging / "compiled"
        classes.mkdir(parents=True)
        original_body = self.BODY.replace(
            "this.caret", "this.h").replace("this.payload", "this.g")
        if not real_b:
            original_body = "{ return 0; }"
        for rel, code in [
            (self.ORIGINAL,
             "package obf.x;\nimport java.math.BigInteger;\n"
             "public class e {\n"
             f" private static final BigInteger x = new BigInteger(\"{self.MODULUS}\");\n"
             " private static final BigInteger y = new BigInteger(\"65537\");\n"
             " public byte[] g;\n"
             " public int h;\n"
             " public int B() " + original_body + "\n"
             " public int C() " + original_body + "\n"
             " public int D() { return 9; }\n"
             "}\n"),
            (self.MATRIX,
             "package obf.m;\n"
             "public class Matrix { public Matrix(obf.x.e reader) {} }\n"),
        ]:
            file = staging / (rel + ".java")
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(code, encoding="utf-8")
            run = subprocess.run(
                [shutil.which("javac"), "--release", "9",
                 "-proc:none", "-g:none", "-classpath", str(classes),
                 "-d", str(classes), str(file)], capture_output=True)
            self.assertEqual(0, run.returncode,
                             run.stderr.decode("utf-8", errors="replace"))
        output = self.root / name
        with ZipFile(output, "w") as out:
            for file in sorted(classes.rglob("*.class")):
                out.write(file, file.relative_to(classes).as_posix())
        return output

    def source_zip(self, content, name):
        output = self.root / name
        with ZipFile(output, "w") as archive:
            archive.writestr("src/main/java/" + self.SOURCE, content)
        return output

    @staticmethod
    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def run_proof(self, source=None, original=None):
        source = source or self.source
        original = original or self.original
        return prove_private_signed_short_body_rebuild(
            original, source,
            original_sha256=self.digest(original),
            source_sha256=self.digest(source),
            original_owner=self.ORIGINAL,
            source_file=self.SOURCE,
            original_method="B",
            original_dependent=self.MATRIX)

    def test_both_identical_source_bodies_match_original_exact_59byte_code(self):
        proof = self.run_proof()
        self.assertEqual(2, proof["distinct_identical_java_source_bodies_found"])
        self.assertEqual(2, proof["isolated_method_compilations_performed"])
        self.assertTrue(proof["each_isolated_method_all_checked_parity_properties_equal"])
        self.assertTrue(proof["per_method_exact_code_length"])
        self.assertTrue(proof["per_method_exact_decoded_instructions_resolved_cp"])
        self.assertTrue(proof["per_method_exact_stackmaps"])
        self.assertTrue(proof["each_isolated_method_core_instruction_parity_equal"])
        self.assertFalse(proof["whole_original_code_attribute_parity_accepted"])
        self.assertTrue(proof["jdk_java9_compilation_used_no_original_game_binary_classpath"])
        self.assertFalse(proof["original_to_source_member_identity_uniquely_determined"])
        self.assertFalse(proof["matrix_java_source_recovered"])
        self.assertFalse(proof["original_client_recompiled"])

    def test_altered_duplicate_body_is_rejected_without_guess(self):
        changed = self.source_zip(
            self.text.replace("public int method673() " + self.BODY,
                              "public int method673() " +
                              self.BODY.replace("var1 -= 65536;", "var1 -= 65535;")),
            "changed-body.zip")
        with self.assertRaises(PrivateSignedShortBodyParityR149Error):
            self.run_proof(source=changed)

    def test_original_nonmatching_method_body_rejected(self):
        altered = self.original_jar("bad-original.jar", real_b=False)
        with self.assertRaises(PrivateSignedShortBodyParityR149Error):
            self.run_proof(original=altered)

    def test_exact_full_jar_and_source_pins_fail_closed(self):
        with self.assertRaises(PrivateSignedShortBodyParityR149Error):
            prove_private_signed_short_body_rebuild(
                self.original, self.source,
                original_sha256="0" * 64,
                source_sha256=self.digest(self.source),
                original_owner=self.ORIGINAL,
                source_file=self.SOURCE,
                original_method="B",
                original_dependent=self.MATRIX)


if __name__ == "__main__":
    unittest.main()
