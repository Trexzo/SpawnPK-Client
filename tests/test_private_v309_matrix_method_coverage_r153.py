"""R153: count exact original-linked method frontier, not source acceptance."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_matrix_method_coverage_r153 import (
    MatrixCoverageR153Error, matrix_original_method_coverage,
)


@unittest.skipUnless(shutil.which("javac"), "JDK required")
class R153OriginalMatrixCoverageTests(unittest.TestCase):
    def setUp(self):
        keeper = tempfile.TemporaryDirectory()
        self.addCleanup(keeper.cleanup)
        self.root = Path(keeper.name)
        classes = self.root / "classes"
        classes.mkdir()
        source = [
            ("rs/Packet", "package rs; public class Packet { public int read(){return 1;} }"),
            ("rs/Game", "package rs; public class Game {}"),
            ("ext/Matrix", "package ext; public class Matrix { "
             "public Matrix(){} public void clear(){} "
             "public int scalar(){return 1;} "
             "public int read(rs.Packet p){return p.read();} "
             "public rs.Packet packet(rs.Packet p){return p;} "
             "public int other(rs.Game g){return 4;} }"),
        ]
        for name, body in source:
            file = self.root / (name + ".java")
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(body, encoding="utf-8")
            result = subprocess.run(
                [shutil.which("javac"), "--release", "11", "-proc:none",
                 "-g:none", "-classpath", str(classes), "-d", str(classes),
                 str(file)], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.jar = self.root / "original.jar"
        with ZipFile(self.jar, "w") as archive:
            for file in sorted(classes.rglob("*.class")):
                archive.write(file, file.relative_to(classes).as_posix())
        self.selection = self.root / "selection.json"
        self.selection.write_text(json.dumps([
            {"name":"clear","descriptor":"()V"},
            {"name":"scalar","descriptor":"()I"},
        ]), encoding="utf-8")

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def report(self, **overrides):
        return matrix_original_method_coverage(
            self.jar, self.selection,
            original_sha256=overrides.get("original_sha256", self.sha(self.jar)),
            selection_sha256=overrides.get("selection_sha256", self.sha(self.selection)),
            original_owner="ext/Matrix", original_packet="rs/Packet")

    def test_partition_packet_descriptor_and_invoke_without_original_fallback(self):
        r = self.report()
        self.assertEqual(6, r["original_declared_method_count"])
        self.assertEqual(2, r["selected_earlier_method_ids_not_reverified_by_this_tool"])
        self.assertEqual(4, r["remaining_method_count"])
        self.assertEqual(2, r["remaining_direct_original_packet_referencing_methods"])
        self.assertEqual(1, r["remaining_other_rs_direct_referencing_methods"])
        self.assertEqual(1, r["remaining_methods_without_direct_rs_descriptor_or_member_reference"])
        self.assertEqual(1, r["remaining_direct_packet_method_invocations"])
        self.assertFalse(r["selected_prior_methods_jvm_parity_reverified"])
        self.assertFalse(r["original_matrix_source_recovery_complete"])
        self.assertFalse(r["private_member_identifiers_exposed"])
        self.assertNotIn("read", str(r))

    def test_original_and_selection_hash_guards(self):
        with self.assertRaises(MatrixCoverageR153Error):
            self.report(original_sha256="0"*64)
        with self.assertRaises(MatrixCoverageR153Error):
            self.report(selection_sha256="0"*64)

    def test_private_selection_missing_member_rejected(self):
        self.selection.write_text('[{"name":"invented","descriptor":"()V"}]',
                                  encoding="utf-8")
        with self.assertRaises(MatrixCoverageR153Error):
            self.report()


if __name__ == "__main__":
    unittest.main()
