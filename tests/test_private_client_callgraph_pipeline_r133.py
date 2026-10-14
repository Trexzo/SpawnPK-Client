"""R133: complete synthetic Java11 source → JVM → R129 evidence replay."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_client_callgraph_pipeline_r133 import (
    PrivateCallGraphPipelineR133Error,
    replay_original_source_callgraph,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "JDK needed for full synthetic source/JVM evidence replay")
class PrivateV309CallGraphPipelineR133Tests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.zip = self.root / "private-source-fixture.zip"
        self.jar = self.root / "private-original-fixture.jar"
        self.classes = {
            "A.java": (
                "package rs; public class A {"
                " public void run() {"
                "  B.ping(); B b = new B(); C c = b; c.accept();"
                " } }"),
            "B.java": (
                "package rs; public class B implements C {"
                " public static void ping() {}"
                " public void accept() {}"
                " }"),
            "C.java": (
                "package rs; public interface C { void accept(); }"),
        }
        self.build()

    def build(self, *, missing_source=None):
        with ZipFile(self.zip, "w") as archive:
            for name, body in sorted(self.classes.items()):
                if name != missing_source:
                    archive.writestr(
                        "fixture/client/src/main/java/rs/" + name, body)
        inputs = self.root / "java" / "rs"
        inputs.mkdir(parents=True, exist_ok=True)
        for name, body in self.classes.items():
            (inputs / name).write_text(body, encoding="utf-8")
        output = self.root / "classes"
        output.mkdir(exist_ok=True)
        proc = subprocess.run(
            [shutil.which("javac"), "--release", "11", "-g:none",
             "-proc:none", "-d", str(output)] +
            [str(inputs / name) for name in sorted(self.classes)],
            capture_output=True)
        self.assertEqual(proc.returncode, 0,
                         proc.stderr.decode("utf-8", errors="replace"))
        with ZipFile(self.jar, "w") as archive:
            for name in ("A", "B", "C"):
                archive.write(
                    output / "rs" / (name + ".class"),
                    "rs/" + name + ".class")
        return (hashlib.sha256(self.zip.read_bytes()).hexdigest(),
                hashlib.sha256(self.jar.read_bytes()).hexdigest())

    def replay(self, *, private=False, source_pin=None):
        sha = hashlib.sha256(self.zip.read_bytes()).hexdigest()
        pin = hashlib.sha256(self.jar.read_bytes()).hexdigest()
        return replay_original_source_callgraph(
            self.zip, self.jar,
            source_sha256=sha if source_pin is None else source_pin,
            original_sha256=pin,
            include_private_rows=private)

    def test_real_javac_end_to_end_single_private_replay(self):
        report = self.replay(private=True)
        self.assertEqual(report["source_java_files_parsed"], 3)
        self.assertEqual(report["original_rs_classfiles_parsed"], 3)
        self.assertEqual(report["proposal_count"], 3)
        self.assertGreaterEqual(
            report["review_tier_counts"]["multi_anchor_call_corrob"], 1)
        self.assertTrue(report["source_symbol_resolution_completed"])
        self.assertFalse(report["original_client_jar_executed"])
        self.assertFalse(report["candidate_source_executed"])
        self.assertFalse(report["class_lineage_accepted"])
        self.assertFalse(report["whole_client_deobfuscated_source_built"])
        self.assertEqual(len(report["private_review_only_rows"]), 3)

    def test_public_report_does_not_disclose_private_identifiers(self):
        report = self.replay()
        raw = json.dumps(report)
        self.assertNotIn("rs/A", raw)
        self.assertNotIn("rs/B", raw)
        self.assertNotIn("private_review_only_rows", report)

    def test_wrong_source_pin_blocks_before_jdk_execution(self):
        with self.assertRaisesRegex(
                PrivateCallGraphPipelineR133Error,
                "PRIVATE_CLIENT_INPUT_SHA256_MISMATCH"):
            self.replay(source_pin="0" * 64)

    def test_missing_source_type_aborts_without_partial_edges(self):
        self.build(missing_source="B.java")
        with self.assertRaisesRegex(
                Exception,
                "R131_AST_SYMBOL_RESOLUTION_FAILED_NO_EDGES_ACCEPTED"):
            self.replay()
