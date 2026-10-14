"""R131: real JDK symbol-attributed Java call graph, synthetic ZIP only."""
import base64
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_client_source_attributed_invokes_r131 import (
    PrivateSourceInvokeR131Error,
    extract_client_source_call_edges, parse_attributed_stdout,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "JDK required for JavacTask.analyze")
class PrivateSourceInvokeR131Tests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.archive = self.root / "candidate.zip"
        self.a = (
            "package rs; public class A {"
            "public int call() { return B.ping() + new B().pingAgain(); }"
            "}")
        self.b = (
            "package rs; public class B {"
            "public B() {}"
            "public static int ping() { return 1; }"
            "public int pingAgain() { return 2; }"
            "}")
        self.build()

    def build(self, extra=()):
        with ZipFile(self.archive, "w") as zipfile:
            zipfile.writestr(
                "candidate/client/src/main/java/rs/A.java", self.a)
            zipfile.writestr(
                "candidate/client/src/main/java/rs/B.java", self.b)
            for rel, body in extra:
                zipfile.writestr(
                    "candidate/client/src/main/java/" + rel, body)
        return hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def audit(self, include=False):
        return extract_client_source_call_edges(
            self.archive, source_sha256=hashlib.sha256(
                self.archive.read_bytes()).hexdigest(),
            include_identifiers=include)

    def test_attributed_static_instance_and_constructor_calls(self):
        report = self.audit(include=True)
        self.assertEqual(report["parsed_java_source_files"], 2)
        self.assertEqual(report["java_symbol_attribution_errors"], 0)
        self.assertEqual(report["direct_rs_to_rs_attributed_call_sites"], 3)
        self.assertEqual(
            report["private_source_call_edges"],
            [{"caller": "rs/A", "callee": "rs/B", "count": 3}])
        self.assertFalse(report["java_source_classfiles_generated"])
        self.assertFalse(report["original_rs_jar_used_for_symbol_resolution"])
        self.assertFalse(report["source_callgraph_complete"])
        self.assertFalse(report["class_lineage_accepted"])

    def test_unresolved_source_symbols_cannot_claim_complete_graph(self):
        self.a = self.a.replace("B.ping()", "Unknown.missing()")
        self.build()
        report = self.audit()
        self.assertGreater(
            report["java_symbol_attribution_errors"], 0)
        self.assertFalse(report["source_callgraph_complete"])
        self.assertFalse(report["independent_jvm_edge_parity_proven"])

    def test_no_private_source_class_names_or_calls_in_default_report(self):
        report = self.audit()
        dump = json.dumps(report)
        self.assertNotIn("rs/A", dump)
        self.assertNotIn("rs/B", dump)
        self.assertNotIn("private_source_call_edges", report)

    def test_bogus_base64_is_rejected(self):
        with self.assertRaisesRegex(
                PrivateSourceInvokeR131Error,
                "SOURCE_ATTRIBUTED_EDGE_PROTOCOL_BASE64_INVALID"):
            parse_attributed_stdout(
                b"SUMMARY\t2\t0\t1\t0\t0\nEDGE\t!!!\tcg==\t1\n")

    def test_duplicate_edge_protocol_is_rejected(self):
        a = base64.urlsafe_b64encode(b"rs/A").decode().rstrip("=")
        b = base64.urlsafe_b64encode(b"rs/B").decode().rstrip("=")
        line = f"EDGE\t{a}\t{b}\t1\n"
        packet = ("SUMMARY\t2\t0\t2\t0\t0\n"
                  + line + line).encode()
        with self.assertRaisesRegex(
                PrivateSourceInvokeR131Error,
                "ATTRIBUTED_GRAPH_DUPLICATE_SOURCE_EDGE"):
            parse_attributed_stdout(packet)

    def test_source_sha_mismatch_rejected(self):
        with self.assertRaisesRegex(
                Exception, "PRIVATE_SOURCE_ARCHIVE_SHA256_MISMATCH"):
            extract_client_source_call_edges(
                self.archive, source_sha256="f" * 64)
