"""R138: actual javac9 class/package shadow removal improves source javac."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_compiler_frontier_r137 import (
    private_source_compile_frontier,
)


@unittest.skipUnless(shutil.which("javac"), "JDK needed for class/package fixtures")
class PrivateR138NormalizedDependencyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.jar = self.root / "private-original-synthetic.jar"
        self.zip = self.root / "private-source.zip"
        self.classes = {}
        for name, body, label in [
            ("ext/a", "package ext; public class a {}", "shadow-type"),
            ("ext/a/b/Child", (
                "package ext.a.b; public class Child { "
                "public static int answer() { return 42; } }"
            ), "shadow-package"),
            ("rs/Game", (
                "package rs; public class Game { public static int play() "
                "{ return 2; } }"), "original-game"),
            ("ext/Bridge", (
                "package ext; public class Bridge { public static int game() "
                "{ return rs.Game.play(); } }"), "original-bridge"),
        ]:
            source = self.root / label / (name + ".java")
            source.parent.mkdir(parents=True)
            source.write_text(body, encoding="utf-8")
            classes = self.root / label / "classes"
            classes.mkdir()
            # The game-linked Bridge must be compiled against Game.
            cmd = [shutil.which("javac"), "--release", "9", "-g:none",
                   "-proc:none", "-d", str(classes)]
            if name == "ext/Bridge":
                game = self.root / "original-game" / "classes"
                cmd += ["-classpath", str(game)]
            cmd.append(str(source))
            proc = subprocess.run(cmd, capture_output=True)
            self.assertEqual(
                proc.returncode, 0,
                proc.stderr.decode("utf-8", errors="replace"))
            self.classes[name] = (classes / (name + ".class")).read_bytes()
        with ZipFile(self.jar, "w") as out:
            for name, binary in sorted(self.classes.items()):
                out.writestr(name + ".class", binary)
        self.candidate = (
            "package rs; import ext.a.b.Child; "
            "public class Probe { "
            " public int value() { return Child.answer(); } }"
        )
        self.rebuild()

    def rebuild(self):
        with ZipFile(self.zip, "w") as out:
            out.writestr(
                "candidate/client/src/main/java/rs/Probe.java",
                self.candidate)

    def audit(self, normalized):
        return private_source_compile_frontier(
            self.zip, self.jar,
            source_sha256=hashlib.sha256(self.zip.read_bytes()).hexdigest(),
            original_sha256=hashlib.sha256(self.jar.read_bytes()).hexdigest(),
            maximum_diagnostics=100,
            normalize_diagnostic_classpath=normalized)

    def test_normalizing_real_jvm_shadow_makes_source_compile(self):
        before = self.audit(False)
        after = self.audit(True)
        self.assertNotEqual(before["compiler_exit_code"], 0)
        self.assertGreater(before["observed_error_diagnostic_count"], 0)
        self.assertEqual(after["compiler_exit_code"], 0)
        self.assertEqual(after["observed_error_diagnostic_count"], 0)
        proof = after["diagnostic_namespace_remap_evidence"]
        self.assertGreater(proof["pre_collision_edges"], 0)
        self.assertEqual(proof["post_collision_edges"], 0)
        self.assertGreater(proof["classfile_remap_count"], 0)
        self.assertTrue(after["diagnostic_classpath_collision_normalized"])
        self.assertEqual(after["non_rs_game_bound_classfiles_excluded"], 1)
        self.assertFalse(
            after["complete_original_client_source_build_accepted"])
        self.assertFalse(
            after["original_project_binary_fallback_fully_ruled_out"])

    def test_game_linked_original_is_not_reintroduced_after_remap(self):
        self.candidate = (
            "package rs; import ext.Bridge; public class Probe { "
            " public int value() { return Bridge.game(); } }"
        )
        self.rebuild()
        report = self.audit(True)
        self.assertNotEqual(report["compiler_exit_code"], 0)
        self.assertGreater(report["observed_error_diagnostic_count"], 0)
        self.assertEqual(report["non_rs_game_bound_classfiles_excluded"], 1)
        self.assertFalse(
            report["candidate_source_compiled_with_independently_owned_deps"])

    def test_remapped_capsule_bytes_deterministic(self):
        first = self.audit(True)
        second = self.audit(True)
        self.assertEqual(first["private_diagnostic_classpath_sha256"],
                         second["private_diagnostic_classpath_sha256"])
        self.assertEqual(first["diagnostic_namespace_remap_evidence"],
                         second["diagnostic_namespace_remap_evidence"])
