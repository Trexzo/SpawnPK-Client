"""R147 tested original binary→source unique shape seeding; no name guessing."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_packet_member_seeds_r147 import (
    private_packet_member_seeds,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "Real JDK required for original member bytecode")
class R147MemberSeedCandidateTests(unittest.TestCase):
    MODULUS = "123456789" * 24 + "123456"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.classes = self.root / "classes"
        self.classes.mkdir()
        def compile_original(internal, text, label):
            file = self.root / label / (internal + ".java")
            file.parent.mkdir(parents=True)
            file.write_text(text, encoding="utf-8")
            proc = subprocess.run([
                shutil.which("javac"), "--release", "11", "-proc:none",
                "-g:none", "-classpath", str(self.classes),
                "-d", str(self.classes), str(file)
            ], capture_output=True)
            self.assertEqual(0, proc.returncode,
                             proc.stderr.decode("utf-8", errors="replace"))
        compile_original("obf/data/B", (
            "package obf.data;\nimport java.math.BigInteger;\n"
            "public class B {\n"
            f" private static final BigInteger k = new BigInteger(\"{self.MODULUS}\");\n"
            " private static final BigInteger e = new BigInteger(\"65537\");\n"
            " public int f;\n"
            " public byte[] g;\n"
            " public B() {}\n"
            " public int a() { return 1; }\n"
            " public int b() { return 2; }\n"
            " public void c(int x) { f = x; }\n"
            " public long d() { return 7L; }\n"
            "}\n"
        ), "original")
        compile_original("obf/data/Matrix", (
            "package obf.data; public class Matrix { "
            "public Matrix(B b, boolean f) {} }\n"
        ), "dependent")
        self.jar = self.root / "original.jar"
        with ZipFile(self.jar, "w") as jar:
            for binary in self.classes.rglob("*.class"):
                jar.write(binary, binary.relative_to(self.classes).as_posix())
        self.java = (
            "package restored;\nimport java.math.BigInteger;\n"
            "public class Packet {\n"
            f" private static final BigInteger rsaModulus = new BigInteger(\"{self.MODULUS}\");\n"
            " private static final BigInteger rsaExponent = new BigInteger(\"65537\");\n"
            " public int cursor;\n"
            " public byte[] payload;\n"
            " public Packet() {}\n"
            " public int read() { return 1; }\n"
            " public int peek() { return 2; }\n"
            " public void write(int value) { cursor = value; }\n"
            " public long readLong() { return 7L; }\n"
            "}\n")
        self.source = self.make_zip(self.java, "candidate.zip")

    def make_zip(self, text, name):
        target = self.root / name
        with ZipFile(target, "w") as archive:
            archive.writestr("src/main/java/restored/Packet.java", text)
        return target

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def review(self, archive=None, identities=False):
        archive = archive or self.source
        return private_packet_member_seeds(
            self.jar, archive, original_sha256=self.sha(self.jar),
            source_sha256=self.sha(archive), original_buffer="obf/data/B",
            source_file="restored/Packet.java",
            original_dependent="obf/data/Matrix",
            include_private_identifiers=identities)

    def test_only_unique_erase_signature_seeded(self):
        report = self.review()
        self.assertEqual(9, report["original_total_structurally_corroborated_members"])
        self.assertEqual(9, report["source_total_structurally_corroborated_members"])
        self.assertEqual(5, report["unique_member_shape_candidates_total"])
        self.assertEqual(2, report["unique_field_shape_candidates"])
        self.assertEqual(1, report["unique_constructor_shape_candidates"])
        self.assertEqual(2, report["unique_method_shape_candidates"])
        self.assertEqual(4, report["ambiguous_member_count_not_assigned"])
        self.assertTrue(report["all_members_partitioned_without_guessing"])
        self.assertNotIn("private_member_seed_candidates", report)
        self.assertFalse(report["original_method_bytecode_parity_verified"])
        self.assertFalse(report["unique_signature_proves_exact_original_method_mapping"])
        self.assertFalse(report["whole_client_compilation_accepted"])

    def test_private_candidate_map_seeds_only_unique_shapes(self):
        report = self.review(identities=True)
        mappings = report["private_member_seed_candidates"]
        self.assertEqual(5, len(mappings))
        self.assertTrue(all(
            item["mapping_status"] ==
            "unique_shape_candidate_not_semantically_accepted"
            for item in mappings))
        self.assertEqual(0, sum(item["source_candidate_member_name"]
                                in ("read", "peek") for item in mappings))
        self.assertTrue(any(item["source_candidate_member_name"] == "readLong"
                            for item in mappings))
        self.assertTrue(any(item["source_candidate_member_name"] == "write"
                            for item in mappings))

    def test_changed_member_shape_must_abort_before_candidate_seeding(self):
        wrong = self.make_zip(
            self.java.replace("public long readLong()", "public int readLong()"),
            "nonmatching-member.zip")
        with self.assertRaises(ValueError):
            self.review(wrong)

    def test_changed_cryptographic_literal_must_abort_owner_gate(self):
        wrong = self.make_zip(
            self.java.replace(self.MODULUS, "9" + self.MODULUS[1:]),
            "nonmatching-sentinel.zip")
        with self.assertRaises(ValueError):
            self.review(wrong)


if __name__ == "__main__":
    unittest.main()
