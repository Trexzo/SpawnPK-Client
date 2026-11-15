"""R424 public helper and patcher acceptance; fabricated temporary directories only."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "tests/fixtures/r424/LootLegacyCleanupR424.java"
HARNESS = ROOT / "tests/fixtures/r424/R424LegacyCleanupHarness.java"
EXPECTED_SHA = "10b547561a7631315c5f44db118376c1a94f6a4cf259f7744f79af8453df18d7"


class R424HelperAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("java") or not shutil.which("javac"):
            raise RuntimeError("JDK11+ required")
        cls.temp = tempfile.TemporaryDirectory(prefix="r424-jdk11-classes-")
        cls.classes = Path(cls.temp.name)
        p = subprocess.run(
            ["javac", "--release", "11", "-proc:none", "-d", str(cls.classes),
             str(JAVA), str(HARNESS)], capture_output=True, text=True, timeout=40)
        if p.returncode:
            raise RuntimeError(p.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="R424-Synthetic-", dir=tempfile.gettempdir())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def command(self, root=None):
        return ["java", "-Djava.awt.headless=true",
                "-Djava.io.tmpdir=" + tempfile.gettempdir(),
                "-cp", str(self.classes),
                "rs.plugins.loottracker.R424LegacyCleanupHarness",
                str(self.root if root is None else root)]

    def test_01_java11_helper_real_filesystem_acceptance(self):
        p = subprocess.run(self.command(), capture_output=True,
                           text=True, timeout=25)
        self.assertEqual(p.returncode, 0, p.stderr)
        match = re.search(r"R424_PUBLIC_HELPER_PASS assertions=(\d+)", p.stdout)
        self.assertIsNotNone(match, p.stdout)
        # Windows may not permit symlink creation without elevated privileges.
        self.assertGreaterEqual(int(match.group(1)), 20)

    def test_02_non_synthetic_root_is_refused(self):
        p = subprocess.run(self.command(Path(tempfile.gettempdir())),
                           capture_output=True, text=True, timeout=12)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("R424_REFUSED_NON_SYNTHETIC_TEMP_ROOT", p.stderr)

    def test_03_helper_sha_matches_pinned_public_source(self):
        self.assertEqual(sha256(JAVA.read_bytes()).hexdigest(), EXPECTED_SHA)

    def test_04_helper_source_contains_no_game_imports(self):
        imports = [x.strip() for x in JAVA.read_text("utf-8").splitlines()
                   if x.startswith("import ")]
        self.assertTrue(all("rs." not in x and "runelite" not in x.lower()
                            for x in imports))

    def test_05_helper_is_not_game_release_jar(self):
        self.assertFalse((ROOT/"rs/plugins/loottracker/LootLegacyCleanupR424.class").exists())
        self.assertFalse((ROOT/"rs/plugins/loottracker/LootLegacyCleanupR424.java").exists())


if __name__ == "__main__":
    unittest.main()
