"""R142: real independent Java9 binary fixtures, three strict javac passes."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_three_stage_javac_r142 import (
    PrivateCombinedJavacR142Error, compare_private_three_stage_source,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "JDK required for actual Java source/compiler fixture")
class R142CombinedV309CompilerTests(unittest.TestCase):
    def setUp(self):
        keeper = tempfile.TemporaryDirectory()
        self.addCleanup(keeper.cleanup)
        self.root = Path(keeper.name)
        self.jar = self.root / "original-synthetic-v309.jar"
        classes = [
            ("ext/A/Target", "package ext.A; public class Target {}", "upperpackage"),
            ("ext/a/Other",
             "package ext.a; public class Other { "
             "public static int get() { return 42; } }",
             "lowerpackage"),
            ("lib/A", "package lib; public class A {}", "uppercaseclass"),
            ("lib/a", "package lib; public class a {}", "lowercaseclass"),
            ("rs/Game", "package rs; public class Game {}", "originalgame"),
        ]
        with ZipFile(self.jar, "w") as out:
            for cls, body, label in classes:
                scratch = self.root / label
                file = scratch / (cls + ".java")
                file.parent.mkdir(parents=True)
                file.write_text(body, encoding="utf-8")
                compiled = scratch / "classes"
                compiled.mkdir()
                result = subprocess.run(
                    [shutil.which("javac"), "--release", "9", "-g:none",
                     "-proc:none", "-d", str(compiled), str(file)],
                    capture_output=True, check=False)
                self.assertEqual(0, result.returncode,
                                 result.stderr.decode("utf8", errors="replace"))
                out.writestr(cls + ".class",
                             (compiled / (cls + ".class")).read_bytes())

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def source(self, files, name):
        target = self.root / name
        with ZipFile(target, "w") as archive:
            for rel, body in sorted(files.items()):
                archive.writestr("src/main/java/" + rel, body)
        return target

    def compare(self, source):
        return compare_private_three_stage_source(
            source, self.jar,
            source_sha256=self.sha(source),
            original_sha256=self.sha(self.jar))

    def test_real_java_three_stage_compiler_error_decrease(self):
        src = self.source({
            "rs/PackageClient.java": (
                "package rs;\n"
                "import ext.a.Other;\n"
                "public class PackageClient {\n"
                " public int get() { return Other.get(); }\n"
                "}\n"),
            "rs/TypeClient.java": (
                "package rs;\n"
                "import lib.a;\n"
                "public class TypeClient {\n"
                " public a field;\n"
                " public a echo(a value) { return value; }\n"
                " public a create() { return new a(); }\n"
                "}\n"),
        }, "private-source.zip")
        result = self.compare(src)
        self.assertEqual(2, result["source_java_file_count"])
        self.assertEqual(1, result["r139_package_imports_rewritten"])
        self.assertEqual(1, result["r141_class_imports_rewritten"])
        self.assertGreaterEqual(result["r141_java_type_identifiers_rewritten"], 4)
        baseline = result["stages"]["unmodified_source"]["observed_errors"]
        after_r139 = result["stages"]["after_r139_imports"]["observed_errors"]
        final = result["stages"]["after_r141_type_aliases"]["observed_errors"]
        self.assertGreater(baseline, after_r139)
        self.assertGreater(after_r139, final)
        self.assertEqual(0, final)
        self.assertTrue(result["all_stages_same_normalized_classpath_sha256"])
        self.assertEqual(1, result["original_rs_classfiles_excluded"])
        self.assertEqual("improved", result["overall_delta_classification"])
        self.assertFalse(result["complete_original_client_source_build_accepted"])
        self.assertFalse(result["original_nonrs_capsule_proven_external_third_party"])

    def test_no_changes_still_never_claims_original_verified(self):
        source = self.source({
            "rs/Plain.java": (
                "package rs;\n"
                "public class Plain { public int value() { return 1; } }\n")
        }, "private-plain.zip")
        result = self.compare(source)
        self.assertEqual(0, result["r139_changed_java_files"])
        self.assertEqual(0, result["r141_changed_java_files"])
        self.assertEqual(0, result["stages"]["unmodified_source"]["observed_errors"])
        self.assertEqual(0, result["stages"]["after_r141_type_aliases"]["observed_errors"])
        self.assertEqual("unchanged", result["overall_delta_classification"])
        self.assertFalse(result["complete_original_client_source_build_accepted"])

    def test_sha_drift_aborts_without_using_source(self):
        source = self.source({
            "rs/Plain.java": "package rs; public class Plain {}\n"
        }, "rejected.zip")
        with self.assertRaises(PrivateCombinedJavacR142Error):
            compare_private_three_stage_source(
                source, self.jar,
                source_sha256="0" * 64,
                original_sha256=self.sha(self.jar))
        with self.assertRaises(PrivateCombinedJavacR142Error):
            compare_private_three_stage_source(
                source, self.jar,
                source_sha256=self.sha(source),
                original_sha256="0" * 64)


if __name__ == "__main__":
    unittest.main()
