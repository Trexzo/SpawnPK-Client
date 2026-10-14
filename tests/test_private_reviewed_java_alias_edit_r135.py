"""R135: actual Javac AST span edits plus synthetic original class/package shadow."""
import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from spk_recovery.private_reviewed_java_alias_edit_r135 import (
    ReviewedImportAliasR135Error, patch_private_candidate,
    TARGET, ORIGINAL_IMPORT,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "JDK required for AST and classfile tests")
class PrivateReviewedImportAliasR135Tests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.original = self.root / "synthetic-v309-original.jar"
        self.source = self.root / "private-synthetic-source.zip"
        self.target_text = (
            "package rs.plugins.configs;\n"
            "import org.apache.commons.a.d_;\n"
            "public class ConfigPanel {\n"
            " public int m(Object[] values, Object object) {\n"
            "  return d_.a((Object[]) values, object);\n"
            " }\n}\n"
        )
        self.build()

    def compile(self, name, text, folder):
        work = self.root / folder
        path = work / (name + ".java")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        output = work / "classes"
        output.mkdir()
        compiled = subprocess.run(
            [shutil.which("javac"), "--release", "9", "-g:none",
             "-proc:none", "-d", str(output), str(path)],
            capture_output=True)
        self.assertEqual(compiled.returncode, 0,
                         compiled.stderr.decode("utf-8", errors="replace"))
        return (output / (name + ".class")).read_bytes()

    def build(self, *, static=True, with_shadow=True):
        modifier = "static " if static else ""
        class_data = self.compile(
            "d", "package org.apache.commons.a; public final class d {"
            " public " + modifier + "int a(Object[] a, Object b) { return 1; }"
            " }", "original-parent")
        classes = [("org/apache/commons/a/d.class", class_data)]
        if with_shadow:
            child = self.compile(
                "Child", "package org.apache.commons.a.d;"
                " public final class Child {}", "original-package")
            classes.append(("org/apache/commons/a/d/Child.class", child))
        with ZipFile(self.original, "w") as jar:
            for name, blob in classes:
                jar.writestr(name, blob)
        with ZipFile(self.source, "w") as archive:
            archive.writestr(
                "candidate/client/src/main/java/" + TARGET,
                self.target_text)
            archive.writestr(
                "candidate/client/src/main/java/rs/Unchanged.java",
                "package rs; public final class Unchanged {}")
        return (hashlib.sha256(self.source.read_bytes()).hexdigest(),
                hashlib.sha256(self.original.read_bytes()).hexdigest())

    def repair(self):
        source_hash, original_hash = (
            hashlib.sha256(self.source.read_bytes()).hexdigest(),
            hashlib.sha256(self.original.read_bytes()).hexdigest())
        return patch_private_candidate(
            self.source, self.original,
            source_sha256=source_hash, original_sha256=original_hash,
            target_sha256=hashlib.sha256(
                self.target_text.encode("utf-8")).hexdigest())

    def test_original_jvm_guarded_ast_edit_changes_only_one_java_file(self):
        output, report = self.repair()
        self.assertEqual(len(output), 2)
        body = dict(output)[TARGET].decode("utf-8")
        self.assertNotIn(ORIGINAL_IMPORT, body)
        self.assertNotIn("d_.a(", body)
        self.assertIn("org.apache.commons.a.d__Type_", body)
        self.assertIn("__Type_", body)
        self.assertEqual(dict(output)["rs/Unchanged.java"],
                         b"package rs; public final class Unchanged {}")
        self.assertTrue(report["original_static_method_descriptor_verified"])
        self.assertTrue(report["ast_import_and_call_spans_verified"])
        self.assertEqual(report["changed_java_source_file_count"], 1)
        self.assertFalse(report["candidate_source_compiled"])
        self.assertFalse(report["alias_proven_same_semantic_class"])

    def test_missing_original_class_package_shadow_is_rejected(self):
        self.build(with_shadow=False)
        with self.assertRaisesRegex(
                ReviewedImportAliasR135Error,
                "EXPECTED_EXACT_ORIGINAL_CLASS_PACKAGE_SHADOW_REQUIRED"):
            self.repair()

    def test_incorrect_original_member_access_is_rejected(self):
        self.build(static=False)
        with self.assertRaisesRegex(
                ReviewedImportAliasR135Error,
                "ORIGINAL_STATIC_METHOD_DESCRIPTOR_NOT_PROVEN"):
            self.repair()

    def test_extra_unreviewed_d_alias_use_is_rejected(self):
        self.target_text = self.target_text.replace(
            "  return d_.a", "  System.out.println(d_); return d_.a")
        self.build()
        with self.assertRaisesRegex(
                ReviewedImportAliasR135Error,
                "ADDITIONAL_UNREVIEWED_ALIAS_REFERENCES"):
            self.repair()

    def test_unreviewed_signature_is_rejected_by_ast(self):
        self.target_text = self.target_text.replace(
            "d_.a((Object[]) values, object)",
            "d_.a(values, object)")
        self.build()
        with self.assertRaisesRegex(
                ReviewedImportAliasR135Error,
                "REVIEWED_AST_IMPORT_OR_CALL_NOT_PROVEN"):
            self.repair()

    def test_wrong_target_preimage_sha_is_rejected(self):
        source_hash, original_hash = self.build()
        with self.assertRaisesRegex(
                ReviewedImportAliasR135Error,
                "UNREVIEWED_CONFIG_PANEL_PREIMAGE_SHA256"):
            patch_private_candidate(
                self.source, self.original,
                source_sha256=source_hash,
                original_sha256=original_hash,
                target_sha256="0" * 64)

    def test_wrong_original_sha_is_rejected_before_inspection(self):
        source_hash, _ = self.build()
        with self.assertRaisesRegex(
                ReviewedImportAliasR135Error,
                "PINNED_PRIVATE_INPUT_SHA256_MISMATCH"):
            patch_private_candidate(
                self.source, self.original,
                source_sha256=source_hash,
                original_sha256="0" * 64,
                target_sha256=hashlib.sha256(
                    self.target_text.encode()).hexdigest())
