"""R127 tests: real Java AST and real Javac classfile shapes, synthetic only."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_source_jvm_shape_singletons_r127 import (
    PrivateSourceShapeR127Error,
    conservative_singletons,
    source_vs_original_shape_research,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "JDK with javac required")
class PrivateShapeSingletonR127Tests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.source_zip = self.root / "candidate.zip"
        self.original = self.root / "original.jar"
        self.source = (
            "package rs; public final class Readable {\n"
            "  private int amount; public static boolean active;\n"
            "  public long compute(int amount, String note) "
            "{ return (long) amount; }\n"
            "}\n"
        )
        self.original_code = self.source.replace(
            "Readable", "Obf").replace("compute", "a")
        self.build()

    def build(self, extra_source=(), original_code=None):
        with ZipFile(self.source_zip, "w") as source:
            source.writestr(
                "candidate/client/src/main/java/rs/Readable.java",
                self.source)
            for path, value in extra_source:
                source.writestr(
                    "candidate/client/src/main/java/" + path, value)
        javac = shutil.which("javac")
        self.java = self.root / "java"
        self.java.mkdir(exist_ok=True)
        path = self.java / "rs" / "Obf.java"
        path.parent.mkdir(exist_ok=True)
        path.write_text(
            self.original_code if original_code is None else original_code,
            encoding="utf-8")
        binary = self.root / "classes"
        binary.mkdir(exist_ok=True)
        result = subprocess.run(
            [javac, "--release", "11", "-proc:none", "-g:none",
             "-d", str(binary), str(path)],
            capture_output=True)
        self.assertEqual(result.returncode, 0)
        with ZipFile(self.original, "w") as jar:
            jar.write(binary / "rs" / "Obf.class", "rs/Obf.class")
        return (hashlib.sha256(self.source_zip.read_bytes()).hexdigest(),
                hashlib.sha256(self.original.read_bytes()).hexdigest())

    def audit(self, include=False):
        sha, pin = (hashlib.sha256(self.source_zip.read_bytes()).hexdigest(),
                    hashlib.sha256(self.original.read_bytes()).hexdigest())
        return source_vs_original_shape_research(
            self.source_zip, self.original,
            source_sha256=sha, original_sha256=pin,
            include_identifiers=include)

    def test_actual_java_compiled_original_matches_renamed_source(self):
        result = self.audit(include=True)
        self.assertEqual(result["source_ast_named_declarations"], 1)
        self.assertEqual(result["original_rs_jvm_classfiles"], 1)
        self.assertEqual(result["unique_undecided_shape_proposals"], 1)
        self.assertEqual(
            result["private_review_only_proposals"][0]["source_java_type"],
            "rs/Readable")
        self.assertEqual(
            result["private_review_only_proposals"][0]["original_jvm_class"],
            "rs/Obf")
        self.assertFalse(result["candidate_proposals_are_identity_accepted"])
        self.assertFalse(result["source_files_rewritten_or_built"])

    def test_ambiguous_source_shapes_are_not_auto_matched(self):
        self.build(extra_source=[(
            "rs/Second.java",
            self.source.replace("Readable", "Second"))])
        report = self.audit()
        self.assertEqual(report["unique_undecided_shape_proposals"], 0)
        self.assertEqual(report["ambiguous_shared_shape_buckets"], 1)

    def test_changed_source_method_shape_is_not_matched(self):
        self.source = self.source.replace(
            "compute(int amount, String note)",
            "compute(short amount, String note)")
        self.build()
        report = self.audit()
        self.assertEqual(report["unique_undecided_shape_proposals"], 0)

    def test_public_report_has_only_digests_and_counts(self):
        report = self.audit()
        self.assertNotIn("private_review_only_proposals", report)
        self.assertNotIn("rs/Obf", json.dumps(report))
        self.assertNotIn("rs/Readable", json.dumps(report))
        self.assertFalse(report["whole_client_deobfuscation_complete"])

    def test_pure_matcher_does_not_propose_ambiguous_classes(self):
        shape = ("CLASS", tuple(), ("I:()V",))
        result = conservative_singletons(
            {"rs/a": shape, "rs/b": shape},
            {"rs/o": shape})
        self.assertEqual(result["unique_undecided_shape_proposals"], 0)
        self.assertEqual(result["ambiguous_shared_shape_buckets"], 1)

    def test_private_source_sha_mismatch_refused(self):
        with self.assertRaisesRegex(
                Exception, "PRIVATE_SOURCE_ARCHIVE_SHA256_MISMATCH"):
            source_vs_original_shape_research(
                self.source_zip, self.original,
                source_sha256="f" * 64,
                original_sha256=hashlib.sha256(
                    self.original.read_bytes()).hexdigest())
