"""R126 synthetics: true JDK AST parsing, no user Java in hosted CI."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import warnings
from zipfile import ZipFile, ZipInfo

from spk_recovery.private_client_source_ast_census_r126 import (
    PrivateClientSourceAstR126Error,
    census_private_client_source, source_members,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "JDK required for JavacTask.parse")
class ClientAstCensusR126Tests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.zip = self.root / "synthetic-decompiled.zip"
        self.jar = self.root / "synthetic-original.jar"
        self.sources = [
            ("external/client/src/main/java/rs/A.java",
             "package rs;\n"
             "public class A {\n"
             "  class Child { }\n"
             "  public void fn() { class Local {} }\n"
             "}\n"),
            ("external/client/src/main/java/rs/B.java",
             "package rs;\n"
             "public interface B { }\n"),
            ("external/client/src/main/java/rs/Changed.java",
             "package rs;\n"
             "public enum Changed { ONE, TWO }\n"),
        ]
        self.classes = [
            ("rs/A.class", b"synthetic-original-class-A"),
            ("rs/A$Child.class", b"synthetic-original-inner"),
            ("rs/B.class", b"synthetic-original-B"),
            ("rs/Obfuscated.class", b"synthetic-renamed"),
            ("rs/A$1Local.class", b"synthetic-local-class"),
            ("org/thirdparty/Library.class", b"dependency"),
        ]

    def build(self, sources=None, classes=None):
        with ZipFile(self.zip, "w") as archive:
            for path, contents in (sources if sources is not None
                                   else self.sources):
                archive.writestr(path, contents)
        with ZipFile(self.jar, "w") as archive:
            for path, contents in (classes if classes is not None
                                   else self.classes):
                archive.writestr(path, contents)
        return (hashlib.sha256(self.zip.read_bytes()).hexdigest(),
                hashlib.sha256(self.jar.read_bytes()).hexdigest())

    def audit(self, *, identifiers=False):
        source_pin, original_pin = self.build()
        return census_private_client_source(
            self.zip, self.jar, source_sha256=source_pin,
            original_sha256=original_pin,
            include_identifiers=identifiers)

    def test_real_ast_finds_top_level_and_nested_but_not_locals(self):
        report = self.audit(identifiers=True)
        self.assertEqual(report["source_java_file_count"], 3)
        self.assertEqual(report["ast_named_rs_type_declaration_count"], 4)
        self.assertEqual(report["exact_spelling_original_rs_type_matches"], 3)
        self.assertEqual(report["rs_ast_types_not_matching_original_name"], 1)
        self.assertEqual(report["original_rs_classfile_names_not_ast_declared"],
                         2)
        sources = {row["java_internal_name"]
                   for row in report["private_ast_declarations"]}
        self.assertIn("rs/A$Child", sources)
        self.assertNotIn("rs/A$1Local", sources)
        self.assertFalse(report["complete_deobfuscated_client_source_accepted"])
        self.assertFalse(report["matched_spelling_is_proven_binary_lineage"])
        self.assertFalse(report["source_files_edited"])

    def test_public_summary_contains_no_source_identifiers(self):
        doc = self.audit()
        self.assertNotIn("private_ast_declarations", doc)
        self.assertNotIn("private_unmatched_original_rs_names", doc)
        self.assertNotIn("rs/Obfuscated", json.dumps(doc))
        self.assertNotIn("rs/A$Child", json.dumps(doc))
        self.assertEqual(doc["original_rs_classfile_count"], 5)

    def test_digest_is_stable(self):
        a = self.audit()["source_content_manifest_sha256"]
        b = self.audit()["source_content_manifest_sha256"]
        self.assertEqual(a, b)

    def test_bad_source_sha_is_refused(self):
        self.build()
        with self.assertRaisesRegex(
                PrivateClientSourceAstR126Error,
                "PRIVATE_SOURCE_ARCHIVE_SHA256_MISMATCH"):
            source_members(self.zip, "0" * 64)

    def test_invalid_java_syntax_fails_closed(self):
        broken = [(
            "external/client/src/main/java/rs/Bad.java",
            "package rs; public class Bad { int = ; }")]
        pin, original_pin = self.build(sources=broken)
        with self.assertRaisesRegex(
                PrivateClientSourceAstR126Error,
                "JAVA_AST_PARSE_OR_HELPER_FAILED"):
            census_private_client_source(
                self.zip, self.jar, source_sha256=pin,
                original_sha256=original_pin)

    def test_zip_slip_veto(self):
        sha, _ = self.build(sources=[(
            "external/client/src/main/java/../../escape.java", "x")])
        with self.assertRaisesRegex(
                PrivateClientSourceAstR126Error,
                "UNSAFE_SOURCE_ARCHIVE_PATH"):
            source_members(self.zip, sha)

    def test_windows_casefold_file_collision_is_refused(self):
        sha, _ = self.build(sources=[
            ("external/client/src/main/java/rs/A.java",
             "package rs; public class A {}"),
            ("external/client/src/main/java/rs/a.java",
             "package rs; public class a {}"),
        ])
        with self.assertRaisesRegex(
                PrivateClientSourceAstR126Error,
                "WINDOWS_SOURCE_FILENAME_CASEFOLD_COLLISION"):
            source_members(self.zip, sha)

    def test_duplicate_zip_member_veto(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            sha, _ = self.build(sources=[
                ("external/client/src/main/java/rs/A.java", "a"),
                ("external/client/src/main/java/rs/A.java", "b"),
            ])
        with self.assertRaisesRegex(
                PrivateClientSourceAstR126Error,
                "SOURCE_ZIP_DUPLICATE_PATH"):
            source_members(self.zip, sha)

    def test_zip_symlink_veto(self):
        self.build()
        with ZipFile(self.zip, "a") as archive:
            sym = ZipInfo("external/client/src/main/java/rs/Link.java")
            sym.create_system = 3
            sym.external_attr = 0o120777 << 16
            archive.writestr(sym, "alias")
        sha = hashlib.sha256(self.zip.read_bytes()).hexdigest()
        with self.assertRaisesRegex(
                PrivateClientSourceAstR126Error,
                "SOURCE_ARCHIVE_SYMLINK_REJECTED"):
            source_members(self.zip, sha)

    def test_duplicate_java_type_declarations_veto(self):
        sha, original_pin = self.build(sources=[
            ("external/client/src/main/java/rs/A.java",
             "package rs; class A {}"),
            ("external/client/src/main/java/rs/Other.java",
             "package rs; class A {}"),
        ])
        with self.assertRaisesRegex(
                PrivateClientSourceAstR126Error,
                "AST_DUPLICATE_JAVA_TYPE_DECLARATION"):
            census_private_client_source(
                self.zip, self.jar, source_sha256=sha,
                original_sha256=original_pin)
