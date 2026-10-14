"""R144: atomic multi-import original class-identity source repair."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_casefold_type_rewrite_r141 import (
    patch_private_casefold_source,
)
from spk_recovery.private_v309_three_stage_javac_r142 import (
    compare_private_three_stage_source,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "JDK required for actual Java source AST tests")
class R144AtomicMultiImportedTypes(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        classes = [
            ("lib/A", "package lib; public class A {}", "uppercase"),
            ("lib/a", "package lib; public class a { public a() {} }", "lowercase"),
            ("lib/node", "package lib; public class node { "
             "public node() {} public static int value() { return 7; } }",
             "shadowtype"),
            ("lib/node/Child", "package lib.node; public class Child {}", "shadowpackage"),
            ("rs/Game", "package rs; public class Game {}", "game"),
        ]
        self.original = self.root / "original-synthetic.jar"
        with ZipFile(self.original, "w") as archive:
            for internal, code, folder in classes:
                target = self.root / folder
                source = target / (internal + ".java")
                source.parent.mkdir(parents=True)
                source.write_text(code, encoding="utf-8")
                output = target / "classes"
                output.mkdir()
                process = subprocess.run(
                    [shutil.which("javac"), "--release", "9", "-proc:none",
                     "-g:none", "-d", str(output), str(source)],
                    capture_output=True)
                self.assertEqual(0, process.returncode,
                                 process.stderr.decode("utf-8", errors="replace"))
                archive.writestr(internal + ".class",
                                 (output / (internal + ".class")).read_bytes())

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def source(self, code, filename):
        archive = self.root / filename
        with ZipFile(archive, "w") as zip_:
            zip_.writestr("src/main/java/rs/Recovered.java", code)
        return archive

    def private_patch(self, src):
        return patch_private_casefold_source(
            src, self.original, source_sha256=self.sha(src),
            original_sha256=self.sha(self.original))

    def test_two_unambiguous_original_class_aliases_atomically_recompile(self):
        src = self.source(
            "package rs;\n"
            "import lib.a;\n"
            "import lib.node;\n"
            "public class Recovered {\n"
            " public a first;\n"
            " public node second;\n"
            " public a one() { return new a(); }\n"
            " public node two() { return new node(); }\n"
            "}\n", "two-independent-imports.zip")
        edited, result = self.private_patch(src)
        self.assertEqual(1, result["changed_java_source_file_count"])
        self.assertEqual(2, result["reviewed_rewritten_import_count"])
        self.assertEqual(6, result["reviewed_rewritten_type_identifier_count"])
        changed = edited[0][1].decode("utf-8")
        self.assertIn("import lib.a__Case_", changed)
        self.assertIn("import lib.node__Type_", changed)
        self.assertNotIn("import lib.a;", changed)
        self.assertNotIn("import lib.node;", changed)

        compilation = compare_private_three_stage_source(
            src, self.original, source_sha256=self.sha(src),
            original_sha256=self.sha(self.original))
        self.assertEqual(1, compilation["source_java_file_count"])
        self.assertEqual(0, compilation["r139_changed_java_files"])
        self.assertEqual(1, compilation["r141_changed_java_files"])
        self.assertEqual(2, compilation["r141_class_imports_rewritten"])
        self.assertEqual(0, compilation["stages"][
            "after_r141_type_aliases"]["observed_errors"])
        self.assertGreater(compilation["stages"][
            "unmodified_source"]["observed_errors"], 0)
        self.assertEqual(1, compilation["original_rs_classfiles_excluded"])
        self.assertFalse(compilation["complete_original_client_source_build_accepted"])

    def test_one_unsafe_receiver_vetoes_both_import_changes(self):
        code = (
            "package rs;\nimport lib.a;\nimport lib.node;\n"
            "public class Recovered {\n"
            " a first;\n"
            " int value() { return node.value(); }\n"
            "}\n"
        )
        src = self.source(code, "unsafe-second-import.zip")
        preview, result = self.private_patch(src)
        self.assertEqual(code.encode("utf-8"), preview[0][1])
        self.assertEqual(0, result["changed_java_source_file_count"])
        self.assertEqual(0, result["reviewed_rewritten_import_count"])
        self.assertEqual(1, result["withheld_ambiguous_java_file_count"])

    def test_qualified_prefix_overlap_vetoes_all_changes(self):
        code = (
            "package rs;\nimport lib.a;\nimport lib.node;\n"
            "public class Recovered {\n"
            " a first;\n"
            " node make() { return new lib.node(); }\n"
            "}\n"
        )
        src = self.source(code, "overlapping-qualification.zip")
        preview, result = self.private_patch(src)
        self.assertEqual(code.encode("utf-8"), preview[0][1])
        self.assertEqual(0, result["changed_java_source_file_count"])
        self.assertEqual(1, result["withheld_ambiguous_java_file_count"])


if __name__ == "__main__":
    unittest.main()
