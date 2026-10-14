"""R130 synthetic real-javac original-JVM call-edge extraction tests."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import warnings
from zipfile import ZipFile

from spk_recovery.private_original_jvm_invoke_edges_r130 import (
    PrivateOriginalInvokeR130Error, collect_jvm_invoke_edges,
)


@unittest.skipUnless(shutil.which("javac"),
                     "JDK required to create synthetic JVM classfiles")
class OriginalJvmInvokeR130Tests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "src"
        self.classes = self.root / "classes"
        self.source.mkdir()
        self.classes.mkdir()
        self.jar = self.root / "synthetic-original.jar"

    def build(self, *, include_target=True, modified_entry=None):
        a = self.source / "rs" / "A.java"
        b = self.source / "rs" / "B.java"
        a.parent.mkdir(parents=True)
        a.write_text(
            "package rs; public class A { public int foo() {"
            " return B.one() + B.one(); }"
            " public Runnable lambda() { return () -> B.one(); } }",
            encoding="utf-8")
        b.write_text(
            "package rs; public class B {"
            " public static int one() { return 2; } }",
            encoding="utf-8")
        compile_result = subprocess.run(
            [shutil.which("javac"), "--release", "9", "-g:none",
             "-proc:none", "-d", str(self.classes), str(a), str(b)],
            capture_output=True)
        self.assertEqual(
            compile_result.returncode, 0,
            compile_result.stderr.decode(errors="replace"))
        with ZipFile(self.jar, "w") as archive:
            archive.write(
                self.classes / "rs" / "A.class",
                modified_entry or "rs/A.class")
            if include_target:
                archive.write(self.classes / "rs" / "B.class", "rs/B.class")
        return hashlib.sha256(self.jar.read_bytes()).hexdigest()

    def test_real_direct_calls_keep_lambda_indy_separate(self):
        pin = self.build()
        result = collect_jvm_invoke_edges(
            self.jar, expected_sha=pin, include_identifiers=True)
        self.assertEqual(result["game_rs_classfiles_parsed"], 2)
        self.assertEqual(result["direct_rs_to_rs_invoke_sites"], 2)
        self.assertEqual(result["distinct_rs_to_rs_owner_edges"], 1)
        self.assertGreaterEqual(
            result[
                "invokedynamic_sites_excluded_for_independent_bootstrap_proof"
            ], 1)
        self.assertEqual(
            result["private_original_call_edges"],
            [{"caller": "rs/A", "callee": "rs/B", "count": 2}])
        self.assertFalse(result["source_class_identity_accepted"])
        self.assertFalse(
            result["source_to_original_callgraph_comparison_performed"])
        self.assertFalse(result["original_jar_executed"])

    def test_original_side_public_report_never_exposes_names(self):
        pin = self.build()
        report = collect_jvm_invoke_edges(self.jar, expected_sha=pin)
        self.assertNotIn("private_original_call_edges", report)
        self.assertNotIn("private_original_method_targets", report)
        self.assertFalse(report["private_identifiers_included"])

    def test_target_not_in_jar_is_counted_not_implicitly_resolved(self):
        pin = self.build(include_target=False)
        result = collect_jvm_invoke_edges(self.jar, expected_sha=pin)
        self.assertEqual(
            result["rs_target_edges_without_corresponding_original_classfile"],
            1)
        self.assertEqual(result["direct_rs_to_rs_invoke_sites"], 2)

    def test_hash_mismatch_is_rejected(self):
        self.build()
        with self.assertRaisesRegex(
                PrivateOriginalInvokeR130Error,
                "ORIGINAL_JAR_SHA256_MISMATCH"):
            collect_jvm_invoke_edges(
                self.jar, expected_sha="0" * 64)

    def test_archive_entry_class_header_mismatch_veto(self):
        pin = self.build(modified_entry="rs/Wrong.class")
        with self.assertRaisesRegex(
                PrivateOriginalInvokeR130Error,
                "ORIGINAL_CLASS_HEADER_PATH_MISMATCH"):
            collect_jvm_invoke_edges(self.jar, expected_sha=pin)

    def test_archive_duplicate_entries_rejected(self):
        self.build()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with ZipFile(self.jar, "a") as archive:
                archive.write(
                    self.classes / "rs" / "A.class", "rs/A.class")
        pin = hashlib.sha256(self.jar.read_bytes()).hexdigest()
        with self.assertRaisesRegex(
                PrivateOriginalInvokeR130Error,
                "ORIGINAL_ARCHIVE_DUPLICATE_PATH"):
            collect_jvm_invoke_edges(self.jar, expected_sha=pin)

    def test_zip_traversal_rejected(self):
        self.build()
        with ZipFile(self.jar, "a") as archive:
            archive.writestr("../leak.class", b"not a class")
        pin = hashlib.sha256(self.jar.read_bytes()).hexdigest()
        with self.assertRaisesRegex(
                PrivateOriginalInvokeR130Error,
                "ORIGINAL_ARCHIVE_UNSAFE_PATH"):
            collect_jvm_invoke_edges(self.jar, expected_sha=pin)
