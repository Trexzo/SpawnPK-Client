"""R136: actual javac9 JVM class dependency closure fixtures; never run game."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import warnings
from zipfile import ZipFile, ZipInfo

from spk_recovery.private_v309_dependency_closure_r136 import (
    DependencyClosureR136Error, audit_external_class_graph,
    audit_pinned_original_jar,
)


@unittest.skipUnless(shutil.which("javac"), "JDK needed for synthetic classfiles")
class PrivateExternalDependencyClosureR136Tests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        src = self.root / "java"
        self.programs = {
            "rs/Game.java": (
                "package rs; public class Game {"
                " public static int identity() { return 9; }"
                " }"),
            "ext/Bridge.java": (
                "package ext; public final class Bridge {"
                " public static int call() { return rs.Game.identity(); }"
                " }"),
            "ext/Indirect.java": (
                "package ext; public final class Indirect {"
                " public static int call() { return Bridge.call(); }"
                " }"),
            "ext/Clean.java": (
                "package ext; public final class Clean {"
                " public static int call() { return 5; }"
                " }"),
        }
        for name, content in self.programs.items():
            target = src / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        output = self.root / "compiled"
        output.mkdir()
        process = subprocess.run(
            [shutil.which("javac"), "--release", "9", "-proc:none",
             "-g:none", "-d", str(output)] +
            [str(src / name) for name in sorted(self.programs)],
            capture_output=True)
        self.assertEqual(process.returncode, 0,
                         process.stderr.decode("utf-8", errors="replace"))
        self.classes = {
            name[:-5]: (output / name[:-5]).with_suffix(".class").read_bytes()
            for name in self.programs
        }
        self.jar = self.root / "private-synthetic-original.jar"
        self.recreate()

    def recreate(self, extra=()):
        with ZipFile(self.jar, "w") as out:
            for name, content in sorted(self.classes.items()):
                out.writestr(name + ".class", content)
            for name, content in extra:
                out.writestr(name, content)

    def scan(self, private=False):
        return audit_pinned_original_jar(
            self.jar,
            original_sha256=hashlib.sha256(self.jar.read_bytes()).hexdigest(),
            include_private_names=private)

    def test_direct_and_transitive_original_game_binary_fallback(self):
        report = self.scan(private=True)
        self.assertEqual(report["original_rs_game_classes"], 1)
        self.assertEqual(report["original_non_rs_classes"], 3)
        self.assertEqual(report["non_rs_directly_referencing_rs"], 1)
        self.assertEqual(report["non_rs_transitively_referencing_rs"], 1)
        self.assertEqual(report["non_rs_without_known_rs_dependency_chain"], 1)
        self.assertEqual(report["private_dependency_partition"][
            "direct_rs_dependent_non_rs"], ["ext/Bridge"])
        self.assertEqual(report["private_dependency_partition"][
            "transitively_rs_dependent_non_rs"], ["ext/Indirect"])
        self.assertEqual(report["private_dependency_partition"][
            "provisional_non_rs_untainted"], ["ext/Clean"])
        self.assertFalse(report[
            "provisional_non_rs_classes_certified_safe_compile_dependencies"])
        self.assertFalse(report["zero_game_binary_fallback_source_build_proven"])

    def test_no_original_class_names_in_default_report(self):
        report = self.scan()
        self.assertNotIn("private_dependency_partition", report)
        self.assertNotIn("ext/Bridge", str(report))
        self.assertNotIn("rs/Game", str(report))
        self.assertFalse(report["isolated_non_rs_classes_certified_third_party"])

    def test_wrong_original_pin_rejected(self):
        with self.assertRaisesRegex(
                DependencyClosureR136Error, "ORIGINAL_SHA256_PIN_MISMATCH"):
            audit_pinned_original_jar(
                self.jar, original_sha256="0" * 64)

    def test_original_class_name_mismatch_rejected(self):
        fake = dict(self.classes)
        fake["ext/Different"] = fake.pop("ext/Clean")
        with self.assertRaisesRegex(
                DependencyClosureR136Error,
                "ORIGINAL_JVM_CLASS_ENTRY_NAME_MISMATCH"):
            audit_external_class_graph(fake)

    def test_invalid_original_class_rejected(self):
        fake = dict(self.classes)
        fake["ext/Clean"] = b"not a class"
        with self.assertRaisesRegex(
                DependencyClosureR136Error,
                "ORIGINAL_JVM_CLASSFILE_NOT_PARSEABLE"):
            audit_external_class_graph(fake)

    def test_duplicate_zip_class_refused(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with ZipFile(self.jar, "a") as out:
                out.writestr("ext/Clean.class", b"duplicate")
        with self.assertRaisesRegex(
                DependencyClosureR136Error,
                "DUPLICATE_ORIGINAL_ARCHIVE_MEMBER"):
            self.scan()

    def test_zip_slip_member_refused(self):
        with ZipFile(self.jar, "a") as out:
            out.writestr("../other.class", b"ignored")
        with self.assertRaisesRegex(
                DependencyClosureR136Error, "UNSAFE_ORIGINAL_ARCHIVE_PATH"):
            self.scan()

    def test_archive_symlink_refused(self):
        with ZipFile(self.jar, "a") as out:
            sym = ZipInfo("ext/Link.class")
            sym.create_system = 3
            sym.external_attr = 0o120777 << 16
            out.writestr(sym, "ext/Clean.class")
        with self.assertRaisesRegex(
                DependencyClosureR136Error, "SYMLINK_IN_ORIGINAL_ARCHIVE"):
            self.scan()
