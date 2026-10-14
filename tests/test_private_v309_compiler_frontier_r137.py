"""R137: executable original-boundary javac frontier on synthetic Java9 clients."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_compiler_frontier_r137 import (
    PrivateCompilerFrontierR137Error,
    private_source_compile_frontier,
)


@unittest.skipUnless(shutil.which("javac"), "JDK required for actual Java compiler")
class PrivateV309CompilerFrontierR137Tests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.original = self.root / "synthetic-original.jar"
        self.source = self.root / "synthetic-client-source.zip"
        input_dir = self.root / "original-source"
        original = {
            "rs/Game.java": (
                "package rs; public final class Game { "
                "public static int play() { return 10; } }"),
            "ext/Clean.java": (
                "package ext; public final class Clean { "
                "public static int answer() { return 42; } }"),
            "ext/Bridge.java": (
                "package ext; public final class Bridge { "
                "public static int game() { return rs.Game.play(); } }"),
            "ext/Indirect.java": (
                "package ext; public final class Indirect { "
                "public static int game() { return Bridge.game(); } }"),
        }
        for name, contents in original.items():
            path = input_dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")
        binaries = self.root / "original-classes"
        binaries.mkdir()
        args = [shutil.which("javac"), "--release", "9", "-g:none",
                "-proc:none", "-d", str(binaries)] + [
                str(input_dir / name) for name in sorted(original)
            ]
        proc = subprocess.run(args, capture_output=True)
        self.assertEqual(proc.returncode, 0,
                         proc.stderr.decode("utf-8", errors="replace"))
        with ZipFile(self.original, "w") as jar:
            for name in sorted(original):
                jar.write(binaries / name.replace(".java", ".class"),
                          name.replace(".java", ".class"))
        self.source_contents = (
            "package rs; public final class Utility { "
            "public int compute() { return ext.Clean.answer(); } }")
        self.rebuild_source()

    def rebuild_source(self):
        with ZipFile(self.source, "w") as archive:
            archive.writestr(
                "fixture/client/src/main/java/rs/Utility.java",
                self.source_contents)

    def frontier(self):
        return private_source_compile_frontier(
            self.source, self.original,
            source_sha256=hashlib.sha256(
                self.source.read_bytes()).hexdigest(),
            original_sha256=hashlib.sha256(
                self.original.read_bytes()).hexdigest(),
            maximum_diagnostics=100)

    def test_private_compiler_uses_only_uncontaminated_original_preview(self):
        report = self.frontier()
        self.assertEqual(report["original_rs_classfiles_excluded"], 1)
        self.assertEqual(report["non_rs_game_bound_classfiles_excluded"], 2)
        self.assertEqual(report["provisional_non_rs_classpath_classfiles"], 1)
        self.assertEqual(report["compiler_exit_code"], 0)
        self.assertEqual(report["observed_error_diagnostic_count"], 0)
        self.assertFalse(
            report["complete_original_client_source_build_accepted"])
        self.assertFalse(
            report["candidate_source_compiled_with_independently_owned_deps"])
        self.assertFalse(
            report["original_project_binary_fallback_fully_ruled_out"])
        self.assertFalse(report["source_and_original_client_executed"])

    def test_compile_fails_if_source_needs_excluded_game_linked_original(self):
        self.source_contents = self.source_contents.replace(
            "ext.Clean.answer()", "ext.Bridge.game()")
        self.rebuild_source()
        report = self.frontier()
        self.assertNotEqual(report["compiler_exit_code"], 0)
        self.assertGreater(report["observed_error_diagnostic_count"], 0)
        self.assertGreater(report["error_categories"][
            "unresolved_symbol_errors"], 0)
        self.assertFalse(
            report["complete_original_client_source_build_accepted"])

    def test_private_hash_replay_is_deterministic(self):
        a = self.frontier()
        b = self.frontier()
        self.assertEqual(a["private_diagnostic_classpath_sha256"],
                         b["private_diagnostic_classpath_sha256"])
        self.assertEqual(a["error_categories"], b["error_categories"])
        self.assertEqual(a["private_full_stderr_sha256"],
                         b["private_full_stderr_sha256"])

    def test_wrong_original_hash_is_rejected_before_compile(self):
        with self.assertRaisesRegex(
                PrivateCompilerFrontierR137Error,
                "PRIVATE_COMPILER_INPUT_SHA256_MISMATCH"):
            private_source_compile_frontier(
                self.source, self.original,
                source_sha256=hashlib.sha256(
                    self.source.read_bytes()).hexdigest(),
                original_sha256="0" * 64)

    def test_wrong_source_hash_is_rejected_before_compile(self):
        with self.assertRaisesRegex(
                PrivateCompilerFrontierR137Error,
                "PRIVATE_COMPILER_INPUT_SHA256_MISMATCH"):
            private_source_compile_frontier(
                self.source, self.original,
                source_sha256="0" * 64,
                original_sha256=hashlib.sha256(
                    self.original.read_bytes()).hexdigest())
