"""R422 PUBLIC-ONLY opt-in harness contract tests.

This suite uses R422SyntheticStoreStub, an independent test double.
It NEVER loads or compiles actual recovered client code. GitHub CI success
proves the public harness works, NOT that private-client runtime is accepted.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile


REPO = Path(__file__).resolve().parents[1]
PUBLIC_STUB = REPO/"tests/fixtures/r422/R422SyntheticStoreStub.java"
PUBLIC_HARNESS = REPO/"tests/fixtures/r422/R422ActualStoreAcceptance.java"
RUNNER = REPO/"tools/r422/run_private_store_acceptance.py"
CLASS = Path("rs/plugins/loottracker/LootHistoryStore.class")


class R422PublicHarnessChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac") or not shutil.which("java"):
            raise RuntimeError("JDK 11+ is required")
        cls.tmp = tempfile.TemporaryDirectory(prefix="r422-public-shim-")
        cls.root = Path(cls.tmp.name)
        cls.classes = cls.root/"classes"
        cls.classes.mkdir()
        proc = subprocess.run(
            ["javac","--release","11","-proc:none","-d",str(cls.classes),
             str(PUBLIC_STUB)],
            capture_output=True,text=True,timeout=45,
        )
        if proc.returncode:
            raise RuntimeError("Synthetic mock failed compilation: "+proc.stderr)
        cls.sha = hashlib.sha256((cls.classes/CLASS).read_bytes()).hexdigest()
        cls.deps = []
        for name in ("fabricated-dependency-a.jar","fabricated-dependency-b.jar"):
            path = cls.root/name
            with zipfile.ZipFile(path,"w") as archive:
                archive.writestr("META-INF/MANIFEST.MF","Manifest-Version: 1.0\n")
            cls.deps.append(path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_runner(self,sha=None,source=None,deps=None):
        values = [
            sys.executable,str(RUNNER),
            "--java",shutil.which("java"),
            "--javac",shutil.which("javac"),
            "--private-classes",str(self.classes),
            "--dependency-a",str(self.deps[0]),
            "--dependency-b",str(self.deps[1] if deps is None else deps),
            "--public-java-source",str(PUBLIC_HARNESS if source is None else source),
            "--expected-store-class-sha256",self.sha if sha is None else sha,
        ]
        return subprocess.run(values,capture_output=True,text=True,timeout=90)

    def test_01_public_stub_complete_real_process_harness(self):
        result=self.run_runner()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        model=json.loads(result.stdout)
        self.assertEqual(model["status"],
                         "R422_OWNER_PRIVATE_ACTUAL_STORE_PROCESS_ACCEPTANCE_PASS")
        self.assertGreaterEqual(model["real_store_assertions"],73)
        self.assertGreaterEqual(model["checks"],15)
        self.assertFalse(model["original_game_started"])
        self.assertFalse(model["production_history_opened"])
        self.assertFalse(model["private_release_authorized"])
        print("R422_PUBLIC_SYNTHETIC_STUB_PROCESS_TEST_PASS "
              f"checks={model['checks']}, assertions={model['real_store_assertions']}")

    def test_02_wrong_sha_pin_is_refused(self):
        result=self.run_runner(sha="0"*64)
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertIn("PRIVATE_STORE_CLASS_SHA_PIN_MISMATCH",result.stdout)

    def test_03_short_sha_pin_is_refused(self):
        result=self.run_runner(sha="bad")
        self.assertEqual(result.returncode,2)
        self.assertIn("INVALID_EXPECTED_SHA",result.stdout)

    def test_04_missing_harness_source_is_refused(self):
        result=self.run_runner(source=self.root/"absent.java")
        self.assertEqual(result.returncode,2)
        self.assertIn("MISSING_OR_SYMLINK_INPUT",result.stdout)

    def test_05_missing_dependency_is_refused(self):
        result=self.run_runner(deps=self.root/"missing.jar")
        self.assertEqual(result.returncode,2)
        self.assertIn("MISSING_OR_SYMLINK_INPUT",result.stdout)

    def test_06_private_class_hash_does_not_change(self):
        before=self.sha
        result=self.run_runner(sha="0"*64)
        self.assertEqual(result.returncode,2)
        self.assertEqual(hashlib.sha256((self.classes/CLASS).read_bytes()).hexdigest(),
                         before)

    def test_07_harness_requires_explicit_synthetic_root_guard(self):
        source=PUBLIC_HARNESS.read_text("utf8")
        self.assertIn("R422_REFUSE_NON_SYNTHETIC_TEMP_ROOT",source)
        self.assertIn('startsWith("R422-Synthetic-")',source)
        self.assertIn("Files.isDirectory(root.getParent()",source)
        self.assertIn("Files.isSymbolicLink(root.getParent())",source)

    def test_08_original_private_class_not_bundled_in_public_repo(self):
        self.assertTrue(PUBLIC_STUB.is_file())
        self.assertFalse((REPO/"rs/plugins/loottracker/LootHistoryStore.java").exists())
        self.assertFalse((REPO/"rs/plugins/loottracker/LootHistoryStore.class").exists())

    def test_09_runner_cannot_use_default_private_class_without_pin(self):
        text=RUNNER.read_text("utf8")
        self.assertIn("--expected-store-class-sha256",text)
        self.assertIn("PRIVATE_STORE_CLASS_SHA_PIN_MISMATCH",text)
        self.assertLess(text.index("PRIVATE_STORE_CLASS_SHA_PIN_MISMATCH"),
                        text.index("tempfile.mkdtemp("))

    def test_10_runner_never_deletes_fixture_during_acceptance(self):
        text=RUNNER.read_text("utf8")
        self.assertNotIn("shutil.rmtree(",text)
        self.assertNotIn("unlink(",text)
        self.assertNotIn("os.remove(",text)
        self.assertIn("does not delete",text.lower())


if __name__=="__main__":
    unittest.main()
