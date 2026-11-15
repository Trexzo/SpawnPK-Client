"""R425 public-only Java11 harness and owner-runner safety checks.

The harness is compiled against an independently authored R422 mock Store,
not any recovered game code. A successful hosted result only verifies test
machinery; it is NOT private/client runtime acceptance.
"""
from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
R422_PUBLIC_STUB = ROOT/"tests/fixtures/r422/R422SyntheticStoreStub.java"
R424_PUBLIC_HELPER = ROOT/"tests/fixtures/r424/LootLegacyCleanupR424.java"
R425_PUBLIC_HARNESS = ROOT/"tests/fixtures/r425/R425ActualPrivateOverlayAcceptance.java"
R425_OWNER_RUNNER = ROOT/"tools/r425/compile_and_accept_private_overlay.py"

INSERT_AT = "\n}\n\n/** Invented placeholder only;"
PATCH = """
    // R425 PUBLIC STAND-IN ONLY: not part of the recovered private Store.
    void deleteStale() {
        r419WithOwner(() -> LootLegacyCleanupR424.run(
            root, () -> r411StageState() == R411StageState.CLEAR, false));
    }
"""


class R425PublicSyntheticHarness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for name in ("java","javac"):
            if not shutil.which(name):
                raise RuntimeError("JDK11+ required")
        cls.build = tempfile.TemporaryDirectory(prefix="r425-public-classes-")
        root=Path(cls.build.name)
        cls.classes=root/"classes"
        cls.classes.mkdir()
        source=R422_PUBLIC_STUB.read_text("utf-8")
        if source.count(INSERT_AT) != 1:
            raise RuntimeError("R422_PUBLIC_STUB_CONTRACT_CHANGED")
        # Only fabricated classes, never recovered private Java.
        source=source.replace(INSERT_AT,"\n"+PATCH+INSERT_AT)
        stub=root/"R422SyntheticStoreStub.java"
        stub.write_text(source,encoding="utf-8")
        proc=subprocess.run(
            ["javac","--release","11","-proc:none","-d",str(cls.classes),
             str(stub),str(R424_PUBLIC_HELPER),str(R425_PUBLIC_HARNESS)],
            capture_output=True,text=True,timeout=50)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def setUp(self):
        self.root=tempfile.TemporaryDirectory(
            prefix="R425-Synthetic-",dir=tempfile.gettempdir())
        self.addCleanup(self.root.cleanup)

    def run_harness(self, location=None):
        dest=self.root.name if location is None else str(location)
        return subprocess.run(
            ["java","-Xmx512m","-Djava.awt.headless=true",
             "-Djava.io.tmpdir="+tempfile.gettempdir(),
             "-cp",str(self.classes),
             "rs.plugins.loottracker.R425ActualPrivateOverlayAcceptance",
             dest],
            capture_output=True,text=True,timeout=35)

    def test_01_public_standin_runs_actual_harness(self):
        r=self.run_harness()
        self.assertEqual(r.returncode,0,r.stderr)
        m=re.search(r"R425_ACTUAL_PATCHED_PRIVATE_STORE_PASS assertions=(\d+)",r.stdout)
        self.assertIsNotNone(m,r.stdout)
        self.assertGreaterEqual(int(m.group(1)),39)

    def test_02_public_standin_is_repeatable_in_new_scratch(self):
        r=self.run_harness()
        self.assertEqual(r.returncode,0,r.stderr)
        with tempfile.TemporaryDirectory(
                prefix="R425-Synthetic-",dir=tempfile.gettempdir()) as fresh:
            again=self.run_harness(fresh)
            self.assertEqual(again.returncode,0,again.stderr)

    def test_03_rejects_non_synthetic_temp_root(self):
        r=self.run_harness(tempfile.gettempdir())
        self.assertNotEqual(r.returncode,0)
        self.assertIn("R425_UNSAFE_SYNTHETIC_ROOT",r.stderr)

    def test_04_refuses_nonexistent_parent(self):
        missing=Path(self.root.name)/"R425-Synthetic-NotADirectTempChild"
        r=self.run_harness(missing)
        self.assertNotEqual(r.returncode,0)

    def test_05_public_mock_has_no_recovered_classes(self):
        self.assertTrue(R422_PUBLIC_STUB.exists())
        self.assertFalse((ROOT/"rs/plugins/loottracker/LootHistoryStore.java").exists())
        self.assertFalse((ROOT/"rs/plugins/loottracker/LootHistoryStore.class").exists())

    def test_06_public_harness_hardcodes_owner_synthetic_prefix(self):
        s=R425_PUBLIC_HARNESS.read_text("utf-8")
        self.assertIn('startsWith("R425-Synthetic-")',s)
        self.assertIn("R425_UNSAFE_SYNTHETIC_ROOT",s)
        self.assertIn("Files.isSymbolicLink(root)",s)

    def test_07_public_harness_does_not_launch_game(self):
        s=R425_PUBLIC_HARNESS.read_text("utf-8")
        self.assertNotIn("Client.main(",s)
        self.assertNotIn("LootTrackerPlugin(",s)
        self.assertNotIn("System.exit(",s)
        self.assertNotIn("Runtime.getRuntime().exec",s)

    def test_08_owner_runner_requires_exact_private_store_digest(self):
        s=R425_OWNER_RUNNER.read_text("utf-8")
        self.assertIn("PINNED_R421_STORE_CLASS",s)
        self.assertIn("R425_R421_PRIVATE_CLASS_SHA_DRIFT",s)
        self.assertIn("R425_PRIVATE_R421_SOURCE_PIN_DRIFT",s)

    def test_09_owner_runner_does_not_ship_a_jar(self):
        s=R425_OWNER_RUNNER.read_text("utf-8")
        self.assertNotIn("jar.exe",s)
        self.assertNotIn("JarOutputStream",s)
        self.assertNotIn("ZipFile(",s)

    def test_10_owner_runner_does_not_modify_real_history(self):
        s=R425_OWNER_RUNNER.read_text("utf-8")
        self.assertNotIn("loot-history.json",s)
        self.assertIn("R425-Synthetic-",s)
        self.assertIn('"legacy_deletion_enabled": False',s)

    def test_11_owner_runner_checks_compiled_class_set(self):
        s=R425_OWNER_RUNNER.read_text("utf-8")
        self.assertIn("gate_class_inventory(",s)
        self.assertIn("R425_HELPER_CLASS_ADDITIONS_UNEXPECTED",s)
        self.assertIn("R425_EXISTING_PRIVATE_CLASS_DELTA_UNEXPECTED",s)

    def test_12_owner_runner_exits_on_incomplete_inputs(self):
        p=subprocess.run([sys.executable,str(R425_OWNER_RUNNER)],
                         capture_output=True,text=True,timeout=15)
        self.assertNotEqual(p.returncode,0)

    def test_13_no_history_data_from_mock_escapes_temporary_tree(self):
        root=Path(self.root.name)
        r=self.run_harness()
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertTrue((root/"preserve-legacy"/"loot-history"/"nested"/"record.dat").exists())
        self.assertTrue((root/"preserve-legacy"/"loot-keys-seen.txt").exists())


if __name__=="__main__":
    unittest.main()
