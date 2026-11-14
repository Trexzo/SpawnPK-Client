"""R390 synthetic-only JDK21 resource classloader regression tests.

Creates tiny synthetic JARs and Java types in disposable directories.
Never uses original SpawnPK archives, opens network, or launches the game.
"""
from __future__ import annotations
import shutil
import subprocess
import tempfile
import unittest
import warnings
from pathlib import Path
from zipfile import ZipFile

PROBE = Path(__file__).resolve().parents[1] / "tools/r390/R390ResourceProbe.java"

class ResourceProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.javac = shutil.which("javac")
        cls.java = shutil.which("java")
        if not cls.javac or not cls.java:
            raise unittest.SkipTest("JDK required")
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.classes = cls.root / "compiled"
        launcher = cls.root / "rs/gui/Launcher.java"
        launcher.parent.mkdir(parents=True)
        launcher.write_text(
            'package rs.gui; public final class Launcher {'
            'static {System.out.println("SYNTHETIC_LAUNCHER_INITIALIZED");}}',
            encoding="utf-8",
        )
        subprocess.run(
            [cls.javac, "--release", "11", "-d", str(cls.classes),
             str(launcher), str(PROBE)],
            check=True, capture_output=True, text=True,
        )
        cls.launcher_bytes = (cls.classes / "rs/gui/Launcher.class").read_bytes()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "temp"):
            cls.temp.cleanup()

    def setUp(self):
        self.private = tempfile.TemporaryDirectory()
        self.addCleanup(self.private.cleanup)
        self.base = Path(self.private.name)
        self.candidate = self.base / "candidate.jar"
        self.primary = self.base / "primary.jar"
        self.companion = self.base / "resources.jar"
        self.candidate_items = [("rs/gui/Launcher.class", self.launcher_bytes)]
        self.primary_items = [("example.txt", b"not the requested resource")]
        self.resource_items = [("assets/icon.png", b"\x89PNGabc"), ("META-INF/example.txt", b"hello")]
        self.pack()

    def pack(self):
        for path, entries in (
            (self.candidate, self.candidate_items),
            (self.primary, self.primary_items),
            (self.companion, self.resource_items),
        ):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with ZipFile(path, "w") as archive:
                    for name, data in entries:
                        archive.writestr(name, data)

    def run_probe(self, expected=2):
        return subprocess.run(
            [self.java, "-cp", str(self.classes), "R390ResourceProbe",
             str(self.candidate), str(self.primary), str(self.companion),
             str(expected)],
            text=True, capture_output=True, timeout=20,
        )

    def test_resources_resolve_without_launcher_initialization(self):
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RESOURCE_ENTRIES=2 VISIBLE_IDENTICAL=2", result.stdout)
        self.assertIn("LAUNCHER_NO_INIT=PASS", result.stdout)
        self.assertNotIn("SYNTHETIC_LAUNCHER_INITIALIZED", result.stdout)

    def test_resource_shadowed_by_candidate_rejected(self):
        self.candidate_items.append(("assets/icon.png", b"other image"))
        self.pack()
        result = self.run_probe()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SHADOWED=1", result.stdout)

    def test_resource_shadowed_by_dependency_rejected(self):
        self.primary_items.append(("assets/icon.png", b"other image"))
        self.pack()
        result = self.run_probe()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SHADOWED=1", result.stdout)

    def test_unexpected_companion_class_rejected(self):
        self.resource_items.append(("example/Extra.class", b"fake"))
        self.pack()
        result = self.run_probe()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("COMPANION_CLASSES=1", result.stdout)

    def test_duplicate_resource_rejected(self):
        self.resource_items.append(("assets/icon.png", b"different"))
        self.pack()
        result = self.run_probe()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DUPLICATE_RESOURCE", result.stderr)

    def test_traversal_resource_rejected(self):
        self.resource_items.append(("../unsafe.txt", b"no"))
        self.pack()
        result = self.run_probe()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("UNSAFE_RESOURCE_PATH", result.stderr)

    def test_missing_launcher_rejected(self):
        self.candidate_items = []
        self.pack()
        result = self.run_probe()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ClassNotFoundException", result.stderr)

    def test_wrong_expected_resource_count_rejected(self):
        result = self.run_probe(expected=3)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RESOURCE_RESOLUTION_FAILED", result.stderr)

    def test_zero_expected_count_rejected(self):
        result = self.run_probe(expected=0)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("INVALID_COUNT", result.stderr)

    def test_companion_is_only_resource_provider(self):
        self.assertEqual(self.run_probe().returncode, 0)
        self.resource_items.append(("docs/additional.bin", b"payload"))
        self.pack()
        result = self.run_probe(expected=3)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RESOURCE_ENTRIES=3 VISIBLE_IDENTICAL=3", result.stdout)

if __name__ == "__main__":
    unittest.main()
