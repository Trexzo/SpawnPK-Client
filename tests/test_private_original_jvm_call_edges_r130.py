"""R130 verifies direct JVM invoke edges from synthetic javac9 classfiles."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import warnings
from zipfile import ZipFile, ZipInfo

from spk_recovery.private_original_jvm_call_edges_r130 import (
    PrivateJvmCallEdgesR130Error, extract_jvm_call_edges,
)


@unittest.skipUnless(shutil.which("javac"),
                     "JDK needed to compile synthetic test classfiles")
class PrivateJvmCallEdgesR130Tests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.jar = self.root / "synthetic-private-original.jar"
        self.make_fixture()

    def make_fixture(self):
        src = self.root / "src" / "rs"
        src.mkdir(parents=True)
        (src / "A.java").write_text(
            "package rs; public class A {"
            " public static void run() {"
            " B.ping(); B.ping(); new B().pong();"
            " C x = new B(); x.accept();"
            " Runnable r = () -> B.ping(); r.run();"
            " } }", encoding="utf-8")
        (src / "B.java").write_text(
            "package rs; public class B implements C {"
            " public static void ping() {}"
            " public void pong() {}"
            " public void accept() {}"
            "}", encoding="utf-8")
        (src / "C.java").write_text(
            "package rs; public interface C { void accept(); }",
            encoding="utf-8")
        output = self.root / "classes"
        output.mkdir()
        compiled = subprocess.run(
            [shutil.which("javac"), "--release", "9", "-g:none",
             "-proc:none", "-d", str(output),
             str(src / "A.java"), str(src / "B.java"), str(src / "C.java")],
            capture_output=True, check=False)
        self.assertEqual(compiled.returncode, 0, compiled.stderr.decode(
            "utf-8", errors="replace"))
        with ZipFile(self.jar, "w") as jar:
            for name in ("A", "B", "C"):
                jar.write(output / "rs" / (name + ".class"),
                          "rs/" + name + ".class")
        return hashlib.sha256(self.jar.read_bytes()).hexdigest()

    def scan(self, *, show=False):
        return extract_jvm_call_edges(
            self.jar,
            original_sha256=hashlib.sha256(self.jar.read_bytes()).hexdigest(),
            include_private_edges=show)

    def test_compiled_jvm_edges_resolve_original_constant_pool_owners(self):
        proof = self.scan(show=True)
        edges = {(e["caller"], e["callee"]): e["count"]
                 for e in proof["private_original_call_edges"]}
        self.assertGreaterEqual(edges["rs/A", "rs/B"], 4)
        self.assertEqual(edges["rs/A", "rs/C"], 1)
        self.assertGreaterEqual(
            proof["unattributed_invokedynamic_site_count"], 1)
        self.assertEqual(proof["parsed_rs_class_count"], 3)
        self.assertGreaterEqual(proof["parsed_rs_method_count"], 7)
        self.assertFalse(proof["invokedynamic_callees_guessed"])
        self.assertFalse(proof["original_client_executed"])
        self.assertFalse(proof["original_source_identity_accepted"])
        self.assertFalse(proof["whole_client_recompiled"])

    def test_public_output_exposes_no_original_names(self):
        report = self.scan()
        s = json.dumps(report)
        self.assertNotIn("private_original_call_edges", report)
        self.assertNotIn("rs/A", s)
        self.assertNotIn("rs/B", s)
        self.assertEqual(len(report["private_edge_manifest_sha256"]), 64)

    def test_wrong_sha_fails_before_parsing_classfiles(self):
        with self.assertRaisesRegex(
                PrivateJvmCallEdgesR130Error,
                "ORIGINAL_JAR_SHA256_MISMATCH"):
            extract_jvm_call_edges(
                self.jar, original_sha256="0" * 64)

    def test_duplicated_archive_member_refused(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with ZipFile(self.jar, "a") as jar:
                jar.writestr("rs/A.class", b"duplicate")
        with self.assertRaisesRegex(
                PrivateJvmCallEdgesR130Error, "DUPLICATE_JAR_ENTRY"):
            self.scan()

    def test_zip_slip_member_refused(self):
        with ZipFile(self.jar, "a") as jar:
            jar.writestr("../unsafe.class", b"x")
        with self.assertRaisesRegex(
                PrivateJvmCallEdgesR130Error, "UNSAFE_JAR_PATH"):
            self.scan()

    def test_zip_symlink_member_refused(self):
        with ZipFile(self.jar, "a") as jar:
            link = ZipInfo("rs/Symlink.class")
            link.create_system = 3
            link.external_attr = 0o120777 << 16
            jar.writestr(link, b"rs/A.class")
        with self.assertRaisesRegex(
                PrivateJvmCallEdgesR130Error, "JAR_SYMLINK_REJECTED"):
            self.scan()

    def test_corrupted_jvm_classfile_never_yields_edges(self):
        with ZipFile(self.jar, "a") as jar:
            jar.writestr("rs/Bad.class", b"not a JVM classfile")
        with self.assertRaisesRegex(
                PrivateJvmCallEdgesR130Error,
                "ORIGINAL_RS_CLASSFILE_PARSE_FAILED"):
            self.scan()
