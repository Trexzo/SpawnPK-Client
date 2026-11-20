"""R446 fabricated owner-private R421 source/class observation tests.

No real SpawnPK client, private source, player history, journals or dependency
JARs are available to CI. The explicit opt-in creates only a new fake TEMP
observation; source/class inputs are never edited by the R446 tool.
"""
from __future__ import annotations

from hashlib import sha256
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r440 import read_only_private_acceptance_preflight as r440
from tools.r442 import verify_prior_r421_manifest as r442
from tools.r446 import observe_owner_private_inventory as r446

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r446/observe_owner_private_inventory.py"


class R446CurrentObservedInventory(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory(prefix="R446-fabricated-")
        self.addCleanup(work.cleanup)
        self.temp = Path(work.name)
        parent = (self.temp / "SpawnPK-R386-Isolated-Acceptance" /
                  "R421-Private-NoFollow-Cache-Directory-Preflight")
        self.candidate_root = parent / "Source-Candidate-R421"
        self.src = self.candidate_root / "source"
        self.cls = parent / "R421-Compiled-Classes"
        self.deps = self.candidate_root / "dependencies"
        self.deps.mkdir(parents=True)
        self.store_src = self.src / r425.STORE
        self.store_cls = self.cls / r425.EXPECTED_CHANGED_EXISTING_CLASS
        self.store_src.parent.mkdir(parents=True)
        self.store_cls.parent.mkdir(parents=True)
        self.store_src.write_bytes(b"R446 completely fabricated Java Store")
        self.store_cls.write_bytes(b"R446 fabricated Store class bytes, not real JVM")
        self.src_other = self.src / "rs/InventedSecondary.java"
        self.cls_other = self.cls / "rs/InventedSecondary.class"
        self.src_other.write_bytes(b"R446 invented secondary Java")
        self.cls_other.write_bytes(b"R446 invented class bytes")
        self.depa = self.deps / "R239_filtered.jar"
        self.depb = self.deps / "R218.jar"
        self.depa.write_bytes(b"R446 fake dependency jar A")
        self.depb.write_bytes(b"R446 fake dependency jar B")
        self.patches = [
            patch.object(r446.tempfile, "gettempdir", return_value=str(self.temp)),
            patch.object(r425, "PINNED_R421_STORE_SHA",
                         sha256(self.store_src.read_bytes()).hexdigest()),
            patch.object(r425, "PINNED_R421_STORE_CLASS",
                         sha256(self.store_cls.read_bytes()).hexdigest()),
            patch.object(r425, "BASELINE_SOURCE_COUNT", 2),
            patch.object(r425, "BASELINE_CLASS_COUNT", 2),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def all_input_hashes(self):
        return {str(p.relative_to(self.temp)): sha256(p.read_bytes()).hexdigest()
                for root in (self.src, self.cls, self.deps)
                for p in root.rglob("*") if p.is_file()}

    def produced_dirs(self):
        return sorted(p for p in self.temp.iterdir()
                      if p.name.startswith(r446.OUTPUT_PREFIX))

    def test_01_readonly_observation_full_current_inventory(self):
        before = self.all_input_hashes()
        result = r446.run(emit=False)
        self.assertEqual(result["status"],
                         "R446_CURRENT_R421_INVENTORY_OBSERVED_UNAPPROVED")
        self.assertEqual(result["java_sources_observed"], 2)
        self.assertEqual(result["compiled_classes_observed"], 2)
        self.assertTrue(result["store_java_sha_matched_R421_pin"])
        self.assertTrue(result["store_class_sha_matched_R421_pin"])
        self.assertEqual(result["dependency_jars_observed"], 2)
        self.assertFalse(result["historical_R421_reference_proven"])
        self.assertFalse(result["private_observation_file_created"])
        self.assertFalse(result["private_javac_executed"])
        self.assertFalse(result["release_authorized"])
        self.assertFalse(result["merge_authorized"])
        self.assertEqual(self.produced_dirs(), [])
        self.assertEqual(self.all_input_hashes(), before)

    def test_02_explicit_emit_creates_only_new_private_unapproved_file(self):
        before = self.all_input_hashes()
        result = r446.run(emit=True)
        self.assertTrue(result["private_observation_file_created"])
        self.assertEqual(len(self.produced_dirs()), 1)
        output = self.produced_dirs()[0] / r446.OUTPUT_NAME
        self.assertTrue(output.is_file())
        self.assertEqual(result["private_quarantine_directory_name"],
                         output.parent.name)
        payload = json.loads(output.read_bytes())
        self.assertEqual(payload["schema"], r446.SCHEMA)
        self.assertEqual(payload["observation_status"], r446.STATUS)
        self.assertEqual(len(payload["source_inventory"]), 2)
        self.assertEqual(len(payload["class_inventory"]), 2)
        self.assertEqual(len(payload["dependency_sha256"]), 2)
        self.assertFalse(payload["independent_prior_manifest_custody_approved"])
        self.assertFalse(payload["compilation_authorized"])
        self.assertFalse(payload["release_authorized"])
        self.assertEqual(self.all_input_hashes(), before)

    def test_03_observed_file_cannot_pass_r442_even_with_matching_self_hash(self):
        r446.run(emit=True)
        observed = self.produced_dirs()[0] / r446.OUTPUT_NAME
        matching_observation_sha = sha256(observed.read_bytes()).hexdigest()
        with self.assertRaisesRegex(
                r442.Refused, "R442_REFERENCE_MANIFEST_SCHEMA_MISMATCH"):
            r442.read_approved_manifest(observed, matching_observation_sha)

    def test_04_observed_current_hashes_are_not_reported_as_approved(self):
        candidate, report = r446.observe()
        self.assertEqual(candidate["schema"], r446.SCHEMA)
        self.assertNotEqual(candidate["schema"], r442.SCHEMA)
        self.assertFalse(candidate["independent_prior_manifest_custody_approved"])
        self.assertFalse(candidate["historical_R421_reference_proven"])
        serialized = json.dumps(report)
        for file in (self.store_src, self.store_cls, self.depa, self.depb):
            self.assertNotIn(str(file), serialized)
            self.assertNotIn(sha256(file.read_bytes()).hexdigest(), serialized)
        self.assertNotIn("rs/InventedSecondary.java", serialized)

    def test_05_source_count_mismatch_refuses_without_output(self):
        self.src_other.unlink()
        with self.assertRaisesRegex(r446.Refused, "R446_ORIGINAL_INVENTORY_COUNT_MISMATCH"):
            r446.run(emit=True)
        self.assertEqual(self.produced_dirs(), [])

    def test_06_class_count_mismatch_refuses_without_output(self):
        self.cls_other.unlink()
        with self.assertRaisesRegex(r446.Refused, "R446_ORIGINAL_INVENTORY_COUNT_MISMATCH"):
            r446.run(emit=True)
        self.assertEqual(self.produced_dirs(), [])

    def test_07_tampered_original_store_java_pin_refused(self):
        self.store_src.write_bytes(b"R446 changed Store source")
        with self.assertRaisesRegex(r446.Refused, "R446_ORIGINAL_R421_STORE_SOURCE_PIN_MISMATCH"):
            r446.run()
        self.assertEqual(self.produced_dirs(), [])

    def test_08_tampered_original_store_class_pin_refused(self):
        self.store_cls.write_bytes(b"R446 changed Store class")
        with self.assertRaisesRegex(r446.Refused, "R446_ORIGINAL_R421_STORE_CLASS_PIN_MISMATCH"):
            r446.run()

    def test_09_missing_dependency_refused_not_self_approved(self):
        self.depa.unlink()
        with self.assertRaisesRegex(r446.Refused, "R446_DEPENDENCY_MISSING_OR_CHANGED"):
            r446.run(emit=True)
        self.assertEqual(self.produced_dirs(), [])

    def test_10_identical_dependency_bytes_flagged(self):
        self.depb.write_bytes(self.depa.read_bytes())
        with self.assertRaisesRegex(r446.Refused, "R446_IDENTICAL_JARS_REQUIRE_REVIEW"):
            r446.run(emit=True)

    def test_11_symlinked_java_source_member_is_refused(self):
        external = self.temp / "external.txt"
        external.write_bytes(b"not read")
        self.src_other.unlink()
        try:
            self.src_other.symlink_to(external)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink privileges unavailable")
        with self.assertRaisesRegex(r446.Refused, "R446_TREE_LINK_OR_SPECIAL_MEMBER_REFUSED"):
            r446.run()
        self.assertEqual(external.read_bytes(), b"not read")

    def test_12_casefold_source_path_collision_refused(self):
        extra = self.src / "rs/inventedsecondary.java"
        extra.write_bytes(b"not the same file")
        with self.assertRaisesRegex(r446.Refused, "R446_SOURCE_OR_CLASS_CASE_COLLISION"):
            r446.run()

    def test_13_source_directory_entry_budget_refusal(self):
        with patch.object(r446, "MAX_MEMBERS", 1):
            with self.assertRaisesRegex(r446.Refused, "R446_DIRECTORY_ENTRY_LIMIT"):
                r446.run()

    def test_14_large_file_or_total_budget_refusal(self):
        self.src_other.write_bytes(b"x"*200)
        with patch.object(r446, "MAX_FILE_BYTES", 64):
            with self.assertRaisesRegex(r446.Refused, "R446_CODE_FILE_TOO_LARGE"):
                r446.run()
        with patch.object(r446, "MAX_TOTAL_BYTES", 70):
            with self.assertRaisesRegex(r446.Refused, "R446_CODE_TOTAL_BYTES_EXCEEDED"):
                r446.run()

    def test_15_input_changed_between_sweeps_must_not_write(self):
        original = r446.observe
        calls = [0]
        def changing_observation():
            current = original()
            calls[0] += 1
            if calls[0] == 1:
                self.src_other.write_bytes(b"mutated UNRELATED Java after first snapshot")
            return current
        with patch.object(r446, "observe", side_effect=changing_observation):
            with self.assertRaisesRegex(
                    r446.Refused, "R446_ORIGINAL_INPUT_CHANGED_BETWEEN_SCANS"):
                r446.run(emit=True)
        self.assertEqual(calls[0], 2)
        self.assertEqual(self.produced_dirs(), [])

    def test_16_quarantine_manifest_write_is_bounded(self):
        with patch.object(r446, "MAX_MANIFEST_BYTES", 50):
            with self.assertRaisesRegex(r446.Refused, "R446_OBSERVED_MANIFEST_TOO_LARGE"):
                r446.run(emit=True)
        self.assertEqual(self.produced_dirs(), [])

    def test_17_output_is_not_overwritten_across_two_explicit_runs(self):
        first = r446.run(emit=True)
        old = self.produced_dirs()[0] / r446.OUTPUT_NAME
        data = old.read_bytes()
        second = r446.run(emit=True)
        self.assertEqual(len(self.produced_dirs()), 2)
        self.assertNotEqual(first["private_quarantine_directory_name"],
                            second["private_quarantine_directory_name"])
        self.assertEqual(old.read_bytes(), data)
        self.assertEqual(self.all_input_hashes(), self.all_input_hashes())

    def test_18_readonly_scanner_does_not_touch_live_client_or_history(self):
        source = inspect.getsource(r446)
        self.assertNotIn("LootTrackerPlugin.java", source)
        self.assertNotIn("client.jar", source)
        self.assertNotIn("history.json", source)
        self.assertNotIn("subprocess.run(", source)
        self.assertNotIn("shutil.copy(", source)
        self.assertNotIn(".unlink(", source)
        self.assertNotIn(".rmtree(", source)
        self.assertIn("independent_prior_manifest_custody_approved", source)
        self.assertIn("O_EXCL", source)
        self.assertIn("--emit-owner-private-unapproved-candidate", source)

    def test_19_public_cli_missing_real_r421_root_refuses_with_no_path(self):
        empty = self.temp / "empty-cli"
        empty.mkdir()
        env = dict(os.environ)
        for key in ("TMPDIR", "TEMP", "TMP"):
            env[key] = str(empty)
        proc = subprocess.run(
            [sys.executable, "-B", str(CLI), "--observe-isolated-r421"],
            env=env, capture_output=True, text=True, timeout=15, check=False)
        self.assertNotEqual(proc.returncode, 0)
        result = json.loads(proc.stdout)
        self.assertEqual(result["status"], "R446_PRIVATE_OBSERVATION_REFUSED")
        self.assertFalse(result["release_authorized"])
        self.assertFalse(result["compilation_authorized"])
        self.assertNotIn(str(empty), proc.stdout)
        self.assertEqual(list(empty.iterdir()), [])

    def test_20_cli_requires_explicit_observe_flag(self):
        proc = subprocess.run(
            [sys.executable, "-B", str(CLI)],
            capture_output=True, text=True, timeout=15, check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("R446_CURRENT_R421_INVENTORY_OBSERVED_UNAPPROVED",
                         proc.stdout)


if __name__ == "__main__":
    unittest.main()
