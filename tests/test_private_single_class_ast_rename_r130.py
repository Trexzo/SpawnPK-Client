"""R130: real javac symbol-safe class rename chained to R129 original matrix."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_single_class_ast_rename_r130 import (
    PrivateSingleClassRenameR130Error,
    rename_private_single_source_class,
    _verified_helper_replacements,
)
from spk_recovery.private_v309_java9_source_class_matrix_r129 import (
    compile_and_compare_private_class,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "JDK required for source-AST class rename")
class PrivateClassAstRenameR130Tests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source_root = self.root / "restored-source"
        self.source = self.source_root / "rs" / "Readable.java"
        self.source.parent.mkdir(parents=True)
        self.source.write_text(self.java_source("Readable"),
                               encoding="utf-8")
        self.out = self.root / "renamed-private-source"
        self.jar = self.root / "original-synthetic.jar"
        original = self.root / "original" / "rs" / "Obf.java"
        original.parent.mkdir(parents=True)
        original.write_text(self.java_source("Obf"), encoding="utf-8")
        compiled = self.root / "original-classes"
        compiled.mkdir()
        compiler = subprocess.run(
            [shutil.which("javac"), "--release", "9",
             "-g:none", "-proc:none", "-d", str(compiled), str(original)],
            capture_output=True)
        self.assertEqual(compiler.returncode, 0,
                         compiler.stderr.decode(errors="replace"))
        with ZipFile(self.jar, "w") as z:
            z.write(compiled / "rs" / "Obf.class", "rs/Obf.class")
        self.jarhash = hashlib.sha256(self.jar.read_bytes()).hexdigest()

    @staticmethod
    def java_source(name):
        return (
            "package rs;\n"
            "// Readable is a historical label; comments stay unchanged.\n"
            "public class " + name + " {\n"
            "  private final int value;\n"
            "  public " + name + "() { value = 3; }\n"
            "  public static " + name + " create() {\n"
            "    return new " + name + "();\n"
            "  }\n"
            "  public " + name + " same(" + name + " input) {\n"
            "    return input;\n"
            "  }\n"
            "  public String label() { return \"Readable\"; }\n"
            "}\n"
        )

    def rename(self, **kwargs):
        return rename_private_single_source_class(
            self.source_root, self.out,
            original_java_owner="rs/Readable",
            intended_jvm_owner="rs/Obf",
            source_sha256=hashlib.sha256(
                self.source.read_bytes()).hexdigest(),
            **kwargs)

    def test_semantic_ast_rename_recompiles_to_original_jvm_class(self):
        proof = self.rename()
        self.assertTrue(proof["renamed_source_java9_compiled"])
        self.assertFalse(proof["candidate_class_identity_original_proven"])
        self.assertFalse(proof["whole_client_source_tree_accepted"])
        self.assertGreaterEqual(proof["source_symbol_replacements"], 6)
        rewritten = self.out / "src" / "rs" / "Obf.java"
        text = rewritten.read_text(encoding="utf-8")
        self.assertIn("public class Obf", text)
        self.assertIn("public Obf()", text)
        self.assertIn("public static Obf create()", text)
        self.assertIn("new Obf()", text)
        self.assertIn("public Obf same(Obf input)", text)
        self.assertIn('return "Readable";', text)
        self.assertIn("// Readable is a historical label;", text)
        self.assertEqual(self.source.read_text(),
                         self.java_source("Readable"))
        result = compile_and_compare_private_class(
            self.out / "src", self.jar, self.root / "r129-replay",
            class_entry="rs/Obf.class",
            original_sha256=self.jarhash)
        self.assertTrue(result["all_method_bodies_instruction_parity"])
        self.assertTrue(result["field_inventory_exact"])
        self.assertTrue(result["all_matrix_checks_exact"])
        self.assertFalse(result["original_game_class_parity_accepted"])

    def test_java_helper_success_line_endings_are_platform_independent(self):
        for terminator in ("\\n", "\\r\\n", "\\r"):
            with self.subTest(terminator=repr(terminator)):
                raw = (
                    "R130_AST_SOURCE_CLASS_REWRITE_PASS" + terminator +
                    "source_symbol_replacements=6" + terminator
                ).encode("utf-8")
                self.assertEqual(_verified_helper_replacements(raw), 6)

    def test_duplicate_java_helper_success_count_is_rejected(self):
        raw = (
            b"R130_AST_SOURCE_CLASS_REWRITE_PASS\\r\\n"
            b"source_symbol_replacements=6\\r\\n"
            b"source_symbol_replacements=9\\r\\n")
        with self.assertRaisesRegex(
                PrivateSingleClassRenameR130Error,
                "CLASS_DECLARATION_OR_CONSTRUCTOR_NOT_REWRITTEN"):
            _verified_helper_replacements(raw)

    def test_wrong_sha_refuses_even_valid_source(self):
        with self.assertRaisesRegex(
                PrivateSingleClassRenameR130Error,
                "SOURCE_JAVA_SHA256_PIN_MISMATCH"):
            rename_private_single_source_class(
                self.source_root, self.out,
                original_java_owner="rs/Readable",
                intended_jvm_owner="rs/Obf",
                source_sha256="0" * 64)
        self.assertFalse(self.out.exists())

    def test_missing_original_source_veto(self):
        with self.assertRaisesRegex(
                PrivateSingleClassRenameR130Error,
                "EXACT_ONE_SOURCE_MATCHING_DECLARED_CLASS_REQUIRED"):
            rename_private_single_source_class(
                self.source_root, self.out,
                original_java_owner="rs/Nonexistent",
                intended_jvm_owner="rs/Obf",
                source_sha256="0" * 64)
        self.assertFalse(self.out.exists())

    def test_java_semantic_error_never_promotes_output(self):
        self.source.write_text(
            self.java_source("Readable").replace(
                "return input;", "return MissingType.INVALID;"),
            encoding="utf-8")
        with self.assertRaisesRegex(
                PrivateSingleClassRenameR130Error,
                "PRIVATE_AST_SOURCE_SYMBOL_REWRITE_REJECTED"):
            self.rename()
        self.assertFalse(self.out.exists())

    def test_extra_java_source_file_is_not_auto_renamed(self):
        other = self.source.parent / "Other.java"
        other.write_text("package rs; class Other {}\n")
        with self.assertRaisesRegex(
                PrivateSingleClassRenameR130Error,
                "EXACT_ONE_SOURCE_MATCHING_DECLARED_CLASS_REQUIRED"):
            self.rename()
        self.assertFalse(self.out.exists())

    def test_same_owner_or_package_rehome_not_silently_allowed(self):
        for old, new in [
            ("rs/Readable", "rs/Readable"),
            ("rs/Readable", "rs/sub/Obf"),
        ]:
            with self.subTest(old=old, new=new):
                with self.assertRaisesRegex(
                        PrivateSingleClassRenameR130Error,
                        "R130_DIFFERENT_PACKAGE_OR_IDENTITY_REMAP_NOT_SUPPORTED"):
                    rename_private_single_source_class(
                        self.source_root, self.out,
                        original_java_owner=old,
                        intended_jvm_owner=new,
                        source_sha256="0" * 64)
        self.assertFalse(self.out.exists())

    def test_output_never_overwrites_private_existing_files(self):
        self.out.mkdir()
        (self.out / "keep").write_text("unchanged")
        with self.assertRaisesRegex(
                PrivateSingleClassRenameR130Error,
                "FRESH_PRIVATE_OUTPUT_OUTSIDE_SOURCE_REQUIRED"):
            self.rename()
        self.assertEqual((self.out / "keep").read_text(), "unchanged")
