"""R146 source structural evidence, exact originals; no game binary fallback."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_packet_original_source_shape_r146 import (
    PrivatePacketStructuralR146Error,
    corroborate_private_packet_source,
)


@unittest.skipUnless(shutil.which("java") and shutil.which("javac"),
                     "Real JDK required for classfile and Java AST proof")
class R146PacketOwnerStructuralLinkage(unittest.TestCase):
    MODULUS = ("123456789" * 24) + "123456"
    ORIGINAL = "obf/b/Original"
    SOURCE = "clean/Packet.java"
    MATRIX = "obf/m/Matrix"

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name)
        self.original = self.root / "original-client.jar"
        classes = self.root / "compiled-classes"
        classes.mkdir()

        def javac_original(internal, text, work, extra=False):
            source = self.root / work / (internal + ".java")
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(text, encoding="utf-8")
            cmd = [shutil.which("javac"), "--release", "11",
                   "-proc:none", "-g:none", "-d", str(classes)]
            if extra:
                cmd.extend(["-classpath", str(classes)])
            result = subprocess.run(cmd + [str(source)], capture_output=True)
            self.assertEqual(0, result.returncode,
                             result.stderr.decode("utf-8", errors="replace"))

        javac_original(self.ORIGINAL, (
            "package obf.b;\n"
            "import java.math.BigInteger;\n"
            "public class Original {\n"
            f" private static final BigInteger o = new BigInteger(\"{self.MODULUS}\");\n"
            " private static final BigInteger p = new BigInteger(\"65537\");\n"
            " public int a;\n"
            " public byte[] b;\n"
            " public Original() {}\n"
            " public Original(byte[] b) { this.b = b; }\n"
            " public int c() { return a; }\n"
            " public void d(int val) { a = val; }\n"
            "}\n"), "original-buffer")
        javac_original(self.MATRIX, (
            "package obf.m;\n"
            "public class Matrix {\n"
            " public Matrix(obf.b.Original data, boolean copy) {}\n"
            "}\n"), "original-matrix", extra=True)
        javac_original("obf/m/Clean", (
            "package obf.m; public class Clean { public int ok() { return 4; }}\n"
        ), "original-clean")
        with ZipFile(self.original, "w") as output:
            for file in sorted(classes.rglob("*.class")):
                output.write(file, file.relative_to(classes).as_posix())
        self.source_text = (
            "package clean;\n"
            "import java.math.BigInteger;\n"
            "public class Packet {\n"
            f" private static final BigInteger rsaModulus = new BigInteger(\"{self.MODULUS}\");\n"
            " private static final BigInteger rsaExponent = new BigInteger(\"65537\");\n"
            " public int caret;\n"
            " public byte[] payload;\n"
            " public Packet() {}\n"
            " public Packet(byte[] payload) { this.payload = payload; }\n"
            " public int read() { return caret; }\n"
            " public void write(int value) { caret = value; }\n"
            "}\n")
        self.source = self._source_zip(self.source_text, "candidate-source.zip")

    def _source_zip(self, java_text, name):
        archive = self.root / name
        with ZipFile(archive, "w") as out:
            out.writestr("src/main/java/" + self.SOURCE, java_text)
        return archive

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def prove(self, archive=None, dependent=MATRIX):
        archive = archive or self.source
        return corroborate_private_packet_source(
            self.original, archive,
            original_sha256=self.sha(self.original),
            source_sha256=self.sha(archive),
            original_buffer=self.ORIGINAL,
            source_file=self.SOURCE,
            original_dependent=dependent)

    def test_exact_erased_shape_and_decimal_literals_and_matrix_ref(self):
        proof = self.prove()
        self.assertTrue(proof["provisional_source_identity_structurally_corroborated"])
        self.assertTrue(proof["original_dependent_class_references_buffer"])
        self.assertEqual(4, proof["original_declared_method_and_constructor_count"])
        self.assertEqual(4, proof["method_access_arity_and_erased_descriptor_shapes_common"])
        self.assertEqual(4, proof["original_field_count"])
        self.assertEqual(4, proof["field_access_and_erased_descriptor_shapes_common"])
        self.assertTrue(proof["original_and_source_rsa_bigint_literals_exactly_equal"])
        self.assertFalse(proof["original_bytecode_body_parity_verified"])
        self.assertFalse(proof["candidate_import_aliases_accepted"])
        self.assertFalse(proof["whole_client_compilation_accepted"])
        self.assertFalse(proof["original_derived_code_release_authorized"])
        self.assertNotIn("rsaModulus", proof)
        self.assertNotIn(self.MODULUS, str(proof))

    def test_changed_method_arity_is_a_negative_structural_result(self):
        changed = self._source_zip(
            self.source_text.replace("public int read()", "public int read(int ignored)"),
            "wrong-arity.zip")
        result = self.prove(changed)
        self.assertFalse(result["full_erased_member_shape_multiset_match"])
        self.assertFalse(result["provisional_source_identity_structurally_corroborated"])
        self.assertTrue(result["original_and_source_rsa_bigint_literals_exactly_equal"])

    def test_changed_rsa_digit_blocks_provisional_identity(self):
        changed = self._source_zip(
            self.source_text.replace(self.MODULUS, "9" + self.MODULUS[1:]),
            "wrong-rsa.zip")
        result = self.prove(changed)
        self.assertTrue(result["full_erased_member_shape_multiset_match"])
        self.assertFalse(result["original_and_source_rsa_bigint_literals_exactly_equal"])
        self.assertFalse(result["provisional_source_identity_structurally_corroborated"])

    def test_original_dependent_without_reference_is_not_accepted(self):
        result = self.prove(dependent="obf/m/Clean")
        self.assertFalse(result["original_dependent_class_references_buffer"])
        self.assertFalse(result["provisional_source_identity_structurally_corroborated"])

    def test_mismatched_source_hash_aborts(self):
        with self.assertRaises(PrivatePacketStructuralR146Error):
            corroborate_private_packet_source(
                self.original, self.source,
                original_sha256=self.sha(self.original),
                source_sha256="0"*64,
                original_buffer=self.ORIGINAL,
                source_file=self.SOURCE,
                original_dependent=self.MATRIX)

    def test_wrong_top_level_declared_source_owner_aborts(self):
        changed = self._source_zip(
            self.source_text.replace("public class Packet", "public class Other"),
            "wrong-owner.zip")
        with self.assertRaises(PrivatePacketStructuralR146Error):
            self.prove(changed)


if __name__ == "__main__":
    unittest.main()
