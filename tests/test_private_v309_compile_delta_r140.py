"""R140: cross-platform original-class-guarded *actual* javac delta fixture."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_compile_delta_r140 import (
    PrivateCompilerDeltaR140Error, compare_private_original_source_javac,
)


@unittest.skipUnless(shutil.which("java") and shutil.which("javac"),
                     "JDK required for real compiler replay")
class R140SourceCompilerDeltaTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name)
        original = {}
        java_classes = [
            ("ext/A/Target", "package ext.A; public class Target {}", "upper"),
            ("ext/a/Other", (
                "package ext.a; public class Other { "
                "public static int value() { return 25; } }"
            ), "lower"),
            ("rs/Game", "package rs; public class Game {}", "game"),
        ]
        for internal, source, label in java_classes:
            location = self.root / label
            file = location / (internal + ".java")
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(source, encoding="utf-8")
            classes = location / "classes"
            classes.mkdir()
            javac = subprocess.run(
                [shutil.which("javac"), "--release", "9", "-proc:none",
                 "-g:none", "-d", str(classes), str(file)],
                capture_output=True, check=False)
            self.assertEqual(0, javac.returncode,
                             javac.stderr.decode("utf-8", errors="replace"))
            original[internal + ".class"] = (
                classes / (internal + ".class")).read_bytes()
        self.original = self.root / "original-synthetic.jar"
        with ZipFile(self.original, "w") as archive:
            for path, raw in sorted(original.items()):
                archive.writestr(path, raw)
        self.original_hash = self._sha(self.original)

    @staticmethod
    def _sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def source_zip(self, text, name):
        archive = self.root / name
        with ZipFile(archive, "w") as data:
            data.writestr("src/main/java/rs/RecoveredClient.java", text)
        return archive

    def replay(self, source):
        return compare_private_original_source_javac(
            source, self.original, source_sha256=self._sha(source),
            original_sha256=self.original_hash)

    def test_two_real_javac_runs_show_a_guarded_import_repair(self):
        src = self.source_zip(
            "package rs;\n"
            "import ext.a.Other;\n"
            "public class RecoveredClient {\n"
            " public int read() { return Other.value(); }\n"
            "}\n",
            "client-source.zip")
        result = self.replay(src)
        self.assertEqual(1, result["input_source_java_file_count"])
        self.assertEqual(1, result["r139_edited_source_java_file_count"])
        self.assertEqual(1, result["r139_ast_verified_explicit_import_edits"])
        self.assertGreater(result["baseline_observed_errors"], 0)
        self.assertEqual(0, result["overlay_observed_errors"])
        self.assertLess(result["overlay_minus_baseline_observed_errors"], 0)
        self.assertEqual("decrease", result["observed_error_classification"])
        self.assertTrue(result["both_passes_used_same_normalized_classpath"])
        self.assertEqual(1, result["original_rs_classfiles_excluded"])
        self.assertFalse(
            result["remaining_original_nonrs_binary_dependency_certified"])
        self.assertFalse(result["complete_original_client_source_build_accepted"])
        self.assertFalse(result["canonical_recovered_source_tree_published"])

    def test_no_applicable_import_is_noop_not_fake_success(self):
        src = self.source_zip(
            "package rs;\n"
            "public class RecoveredClient {\n"
            " public int read() { return 25; }\n"
            "}\n",
            "clean-source.zip")
        result = self.replay(src)
        self.assertEqual(0, result["r139_edited_source_java_file_count"])
        self.assertEqual(0, result["r139_ast_verified_explicit_import_edits"])
        self.assertEqual(0, result["baseline_observed_errors"])
        self.assertEqual(0, result["overlay_observed_errors"])
        self.assertEqual("unchanged", result["observed_error_classification"])
        self.assertFalse(result["complete_original_client_source_build_accepted"])

    def test_both_inputs_have_exact_hash_guards(self):
        src = self.source_zip(
            "package rs; public class RecoveredClient {}\n",
            "reject-source.zip")
        with self.assertRaises(PrivateCompilerDeltaR140Error):
            compare_private_original_source_javac(
                src, self.original, source_sha256="0" * 64,
                original_sha256=self.original_hash)
        with self.assertRaises(PrivateCompilerDeltaR140Error):
            compare_private_original_source_javac(
                src, self.original, source_sha256=self._sha(src),
                original_sha256="0" * 64)


if __name__ == "__main__":
    unittest.main()
