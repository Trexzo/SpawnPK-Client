"""R131: real JDK Trees/Elements source call edges, synthetic only."""
from pathlib import Path
import hashlib
import json
import shutil
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_source_ast_call_edges_r131 import (
    PrivateSourceCallEdgesR131Error,
    extract_private_source_call_edges,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "JDK required for symbol-aware AST fixture")
class PrivateSourceAstCallsR131Tests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.zip = self.root / "synthetic-source-candidate.zip"
        self.contents = {
            "rs/A.java": (
                "package rs; public class A { public void run() {"
                " B.ping(); B.ping(); B b = new B(); b.pong();"
                " C c=b; c.accept();"
                " Runnable callback=B::ping;"
                " } }"),
            "rs/B.java": (
                "package rs; public class B implements C {"
                " public static void ping() {}"
                " public void pong() {}"
                " public void accept() {}"
                " }"),
            "rs/C.java": (
                "package rs; public interface C {void accept();}"
            ),
        }
        self.make_zip()

    def make_zip(self):
        with ZipFile(self.zip, "w") as archive:
            for name, text in sorted(self.contents.items()):
                archive.writestr(
                    "candidate/client/src/main/java/" + name, text)
        return hashlib.sha256(self.zip.read_bytes()).hexdigest()

    def audit(self, *, include=False):
        return extract_private_source_call_edges(
            self.zip, source_sha256=hashlib.sha256(
                self.zip.read_bytes()).hexdigest(),
            include_private_edges=include)

    def test_jdk_resolved_static_virtual_constructor_interface_calls(self):
        report = self.audit(include=True)
        rows = {(r["caller"], r["callee"]): r["count"]
                for r in report["private_source_call_edges"]}
        self.assertEqual(rows["rs/A", "rs/B"], 4)
        self.assertEqual(rows["rs/A", "rs/C"], 1)
        self.assertEqual(report["source_java_file_count"], 3)
        self.assertGreaterEqual(
            report["source_method_reference_sites_excluded"], 1)
        self.assertTrue(report["source_call_owners_symbol_resolved"])
        self.assertTrue(report["ambient_project_classpath_disabled"])
        self.assertFalse(report["source_game_code_executed"])
        self.assertFalse(report["source_game_classes_generated"])

    def test_default_summary_suppresses_class_and_method_names(self):
        report = self.audit()
        text = json.dumps(report)
        self.assertNotIn("rs/A", text)
        self.assertNotIn("rs/B", text)
        self.assertNotIn("private_source_call_edges", report)
        self.assertFalse(report["method_opcode_dispatch_equivalence_proven"])

    def test_missing_source_dependency_rejects_all_edges(self):
        self.contents.pop("rs/B.java")
        self.make_zip()
        with self.assertRaisesRegex(
                PrivateSourceCallEdgesR131Error,
                "R131_AST_SYMBOL_RESOLUTION_FAILED_NO_EDGES_ACCEPTED"):
            self.audit()

    def test_ambiguous_source_declaration_rejects_all_edges(self):
        self.contents["rs/D.java"] = (
            "package rs; class B { static void ping(){} }")
        self.make_zip()
        with self.assertRaisesRegex(
                PrivateSourceCallEdgesR131Error,
                "R131_AST_SYMBOL_RESOLUTION_FAILED_NO_EDGES_ACCEPTED"):
            self.audit()

    def test_unsupported_compile_errors_not_used_as_partial_proof(self):
        self.contents["rs/A.java"] = (
            "package rs; public class A {"
            " void run() { MISSING.call(); } }")
        self.make_zip()
        with self.assertRaisesRegex(
                PrivateSourceCallEdgesR131Error,
                "R131_AST_SYMBOL_RESOLUTION_FAILED_NO_EDGES_ACCEPTED"):
            self.audit()

    def test_hash_pin_is_mandatory(self):
        with self.assertRaisesRegex(
                Exception, "PRIVATE_SOURCE_ARCHIVE_SHA256_MISMATCH"):
            extract_private_source_call_edges(
                self.zip, source_sha256="0" * 64)
