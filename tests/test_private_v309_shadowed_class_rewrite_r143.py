"""R143: original JVM class/package-shadow source import repair tests."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_casefold_type_rewrite_r141 import patch_private_casefold_source
from spk_recovery.private_v309_compiler_frontier_r137 import _normalize_private_provisional_capsule
from spk_recovery.private_v309_three_stage_javac_r142 import compare_private_three_stage_source


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"), "Real JDK required")
class R143OriginalClassPackageShadowTests(unittest.TestCase):
    def setUp(self):
        keeper = tempfile.TemporaryDirectory()
        self.addCleanup(keeper.cleanup)
        self.root = Path(keeper.name)
        originals = [
            ("lib/node", "package lib; public class node { public node() {} public static int value() { return 11; } }", "type"),
            ("lib/node/Child", "package lib.node; public class Child {}", "package"),
            ("rs/Game", "package rs; public class Game {}", "game"),
        ]
        self.original = self.root / "synthetic-original.jar"
        with ZipFile(self.original, "w") as archive:
            for binary, java, label in originals:
                temp = self.root / label
                source = temp / (binary + ".java")
                source.parent.mkdir(parents=True)
                source.write_text(java, encoding="utf-8")
                compiled = temp / "classes"
                compiled.mkdir()
                run = subprocess.run(
                    [shutil.which("javac"), "--release", "9", "-proc:none",
                     "-g:none", "-d", str(compiled), str(source)],
                    capture_output=True)
                self.assertEqual(0, run.returncode,
                                 run.stderr.decode("utf-8", errors="replace"))
                archive.writestr(binary + ".class",
                                 (compiled / (binary + ".class")).read_bytes())

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def source_zip(self, code, name):
        path = self.root / name
        with ZipFile(path, "w") as z:
            z.writestr("src/main/java/rs/Recovered.java", code)
        return path

    def patch(self, source):
        return patch_private_casefold_source(
            source, self.original, source_sha256=self.sha(source),
            original_sha256=self.sha(self.original))

    def test_ast_source_repair_and_real_javac(self):
        source = self.source_zip(
            "package rs;\nimport lib.node;\n"
            "public class Recovered {\n"
            " public node field;\n"
            " public node echo(node value) { return value; }\n"
            " public node create() { return new node(); }\n"
            "}\n", "shadowed-import.zip")
        files, proof = self.patch(source)
        self.assertEqual(1, proof["source_java_file_count"])
        self.assertEqual(0, proof["eligible_original_nonrs_casefold_type_count"])
        self.assertEqual(1, proof["eligible_original_nonrs_shadow_type_count"])
        self.assertEqual(1, proof["changed_java_source_file_count"])
        self.assertEqual(1, proof["reviewed_rewritten_import_count"])
        self.assertEqual(5, proof["reviewed_rewritten_type_identifier_count"])
        self.assertIn("import lib.node__Type_", files[0][1].decode("utf-8"))

        provisional = self.root / "private-nonrs.jar"
        with ZipFile(provisional, "w") as output:
            with ZipFile(self.original) as original:
                for name in original.namelist():
                    if not name.startswith("rs/"):
                        output.writestr(name, original.read(name))
        normalized = self.root / "private-normalized.jar"
        evidence = _normalize_private_provisional_capsule(
            provisional, normalized, self.root)
        self.assertEqual(0, evidence["post_collision_edges"])
        self.assertGreaterEqual(evidence["classfile_remap_count"], 1)

        temporary = self.root / "Recovered.java"
        classes = self.root / "javac"
        classes.mkdir()
        command = [shutil.which("javac"), "--release", "11",
                   "-proc:none", "-implicit:none", "-classpath",
                   str(normalized), "-d", str(classes), str(temporary)]
        with ZipFile(source) as raw:
            temporary.write_bytes(raw.read("src/main/java/rs/Recovered.java"))
        old = subprocess.run(command, capture_output=True)
        self.assertNotEqual(0, old.returncode)
        temporary.write_bytes(files[0][1])
        repaired = subprocess.run(command, capture_output=True)
        self.assertEqual(0, repaired.returncode,
                         repaired.stderr.decode("utf-8", errors="replace"))

    def test_r142_stages_accept_class_package_shadow_edit_without_false_parity(self):
        source = self.source_zip(
            "package rs;\nimport lib.node;\n"
            "public class Recovered { public node create() { return new node(); } }\n",
            "combined-compile.zip")
        result = compare_private_three_stage_source(
            source, self.original, source_sha256=self.sha(source),
            original_sha256=self.sha(self.original))
        self.assertEqual(0, result["r139_changed_java_files"])
        self.assertEqual(1, result["r141_changed_java_files"])
        self.assertEqual(1, result["r141_class_imports_rewritten"])
        self.assertGreater(
            result["stages"]["unmodified_source"]["observed_errors"], 0)
        self.assertEqual(
            0, result["stages"]["after_r141_type_aliases"]["observed_errors"])
        self.assertEqual("improved", result["overall_delta_classification"])
        self.assertFalse(result["complete_original_client_source_build_accepted"])

    def test_expression_receiver_vetoes_whole_source(self):
        code = ("package rs;\nimport lib.node;\n"
                "public class Recovered { int read() { return node.value(); } }\n")
        source = self.source_zip(code, "expression-veto.zip")
        files, report = self.patch(source)
        self.assertEqual(code.encode("utf-8"), files[0][1])
        self.assertEqual(0, report["changed_java_source_file_count"])
        self.assertEqual(1, report["withheld_ambiguous_java_file_count"])

    def test_qualified_duplicate_name_vetoes_whole_source(self):
        code = ("package rs;\nimport lib.node;\n"
                "public class Recovered { node make() { return new lib.node(); } }\n")
        source = self.source_zip(code, "qualified-veto.zip")
        files, report = self.patch(source)
        self.assertEqual(code.encode("utf-8"), files[0][1])
        self.assertEqual(0, report["changed_java_source_file_count"])
        self.assertEqual(1, report["withheld_ambiguous_java_file_count"])


if __name__ == "__main__":
    unittest.main()
