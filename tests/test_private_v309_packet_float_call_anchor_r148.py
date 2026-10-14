"""R148 actual JVM opcode + source Javac AST float-to-int call-edge fixtures."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_packet_float_call_anchor_r148 import (
    PrivatePacketCallAnchorR148Error,
    private_packet_float_callee_anchor,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "JDK required for JVM method call-edge fixture")
class R148PrivateFloatCallEdgeTests(unittest.TestCase):
    MODULUS = "123456789" * 24 + "123456"
    ORIGINAL_OWNER = "obf/data/B"
    MATRIX = "obf/data/Matrix"
    SOURCE_OWNER = "restored/Packet.java"

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.original = self.create_original(
            "return Float.intBitsToFloat(this.r());", "original.jar")
        self.source_text = (
            "package restored;\nimport java.math.BigInteger;\n"
            "public class Packet {\n"
            f" private static final BigInteger rsaModulus = new BigInteger(\"{self.MODULUS}\");\n"
            " private static final BigInteger rsaExponent = new BigInteger(\"65537\");\n"
            " public int cursor;\n"
            " public byte[] payload;\n"
            " public Packet() {}\n"
            " public int readInt() { return 1; }\n"
            " public int otherInt() { return 2; }\n"
            " public float readFloat() { return Float.intBitsToFloat(this.readInt()); }\n"
            "}\n"
        )
        self.source = self.source_zip(self.source_text, "source.zip")

    def create_original(self, float_body, name):
        output = self.root / name
        classes = self.root / (name + "-classes")
        classes.mkdir()
        for internal, body, folder in [
            (self.ORIGINAL_OWNER,
             "package obf.data;\nimport java.math.BigInteger;\n"
             "public class B {\n"
             f" private static final BigInteger x = new BigInteger(\"{self.MODULUS}\");\n"
             " private static final BigInteger y = new BigInteger(\"65537\");\n"
             " public int d;\npublic byte[] e;\n"
             " public B() {}\n"
             " public int r() { return 1; }\n"
             " public int q() { return 2; }\n"
             " public float s() { " + float_body + " }\n"
             "}\n", "original"),
            (self.MATRIX,
             "package obf.data; public class Matrix { public Matrix(B b) {} }\n",
             "matrix"),
        ]:
            path = self.root / (name + "-" + folder) / (internal + ".java")
            path.parent.mkdir(parents=True)
            path.write_text(body, encoding="utf-8")
            p = subprocess.run(
                [shutil.which("javac"), "--release", "11",
                 "-proc:none", "-g:none", "-classpath", str(classes),
                 "-d", str(classes), str(path)],
                capture_output=True)
            self.assertEqual(0, p.returncode,
                             p.stderr.decode("utf-8", errors="replace"))
        with ZipFile(output, "w") as archive:
            for cls in sorted(classes.rglob("*.class")):
                archive.write(cls, cls.relative_to(classes).as_posix())
        return output

    def source_zip(self, text, name):
        path = self.root / name
        with ZipFile(path, "w") as zip_:
            zip_.writestr("src/main/java/" + self.SOURCE_OWNER, text)
        return path

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def review(self, src=None, original=None, private=False):
        src = src or self.source
        original = original or self.original
        return private_packet_float_callee_anchor(
            original, src, source_sha256=self.sha(src),
            original_sha256=self.sha(original),
            original_buffer=self.ORIGINAL_OWNER,
            source_file=self.SOURCE_OWNER,
            original_dependent=self.MATRIX,
            include_private_identifiers=private)

    def test_original_opcode_and_source_ast_anchor_one_ambiguous_reader(self):
        report = self.review()
        self.assertTrue(report["source_float_method_uniquely_structurally_anchored"])
        self.assertTrue(report["original_float_bytecode_exact_four_instruction_shape"])
        self.assertTrue(report["candidate_java_exact_float_int_call_ast_pattern"])
        self.assertEqual(2, report["original_int_reader_erased_shape_group_size"])
        self.assertEqual(1, report["additional_ambiguity_narrowed_callee_candidates"])
        self.assertFalse(report["original_int_reader_method_body_parity_verified"])
        self.assertFalse(report["caller_exact_compiled_source_instruction_parity_verified"])
        self.assertFalse(report["java_type_and_member_alias_mapping_accepted"])
        self.assertNotIn("private_original_to_source_callee_candidate", report)

    def test_private_map_contains_only_original_reader_call_chain_candidate(self):
        report = self.review(private=True)
        candidate = report["private_original_to_source_callee_candidate"]
        self.assertEqual("s", candidate["original_caller"])
        self.assertEqual("readFloat", candidate["source_caller"])
        self.assertEqual("r", candidate["original_ambiguous_int_callee"])
        self.assertEqual("readInt", candidate["source_candidate_int_callee"])
        self.assertEqual("call_edge_correlated_candidate_not_method_parity",
                         candidate["mapping_status"])

    def test_source_receiver_must_be_explicit_this(self):
        source = self.source_zip(
            self.source_text.replace("this.readInt()", "readInt()"),
            "implicit-receiver-source.zip")
        with self.assertRaises(PrivatePacketCallAnchorR148Error):
            self.review(src=source)

    def test_source_call_wrapper_changes_are_withheld(self):
        source = self.source_zip(
            self.source_text.replace(
                "Float.intBitsToFloat(this.readInt())",
                "Float.intBitsToFloat(this.otherInt() + 1)"),
            "altered-argument.zip")
        with self.assertRaises(PrivatePacketCallAnchorR148Error):
            self.review(src=source)

    def test_original_nonforwarding_float_method_rejected(self):
        alternate = self.create_original(
            "return 0.0f;", "original-nonforwarding.jar")
        with self.assertRaises(PrivatePacketCallAnchorR148Error):
            self.review(original=alternate)

    def test_changed_original_owner_rsa_aborts_upstream(self):
        source = self.source_zip(
            self.source_text.replace(self.MODULUS, "9" + self.MODULUS[1:]),
            "source-wrong-rsa.zip")
        with self.assertRaises(ValueError):
            self.review(src=source)

    def test_bad_whole_original_hash_rejected(self):
        with self.assertRaises(PrivatePacketCallAnchorR148Error):
            private_packet_float_callee_anchor(
                self.original, self.source,
                original_sha256="0"*64,
                source_sha256=self.sha(self.source),
                original_buffer=self.ORIGINAL_OWNER,
                source_file=self.SOURCE_OWNER,
                original_dependent=self.MATRIX)


if __name__ == "__main__":
    unittest.main()
