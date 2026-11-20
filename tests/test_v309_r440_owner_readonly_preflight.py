"""R440 owner-private read-only gate tests using a completely invented R421 tree.

No private client files are available in hosted CI; these tests monkeypatch
only fixture-local SHA/count constants and mock javac/java version output.
"""
from __future__ import annotations

from contextlib import ExitStack
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.r440 import read_only_private_acceptance_preflight as r440
from tools.r424 import prepare_private_legacy_cleanup_patch as r424
from tools.r425 import compile_and_accept_private_overlay as r425

from test_v309_r426_full_mock_pipeline import FAKE_STORE

ROOT = Path(__file__).resolve().parents[1]


class R440ReadOnlyOwnerPrivatePreflight(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="R440-Invented-")
        self.addCleanup(self.scratch.cleanup)
        self.base = Path(self.scratch.name)
        owner = (self.base / "SpawnPK-R386-Isolated-Acceptance" /
                 "R421-Private-NoFollow-Cache-Directory-Preflight")
        self.source = owner / "Source-Candidate-R421" / "source"
        self.classes = owner / "R421-Compiled-Classes"
        self.source.mkdir(parents=True)
        self.classes.mkdir()
        self.store_file = self.source / r425.STORE
        self.store_file.parent.mkdir(parents=True)
        self.store_file.write_text(FAKE_STORE, encoding="utf-8")
        self.class_file = self.classes / r425.EXPECTED_CHANGED_EXISTING_CLASS
        self.class_file.parent.mkdir(parents=True)
        self.class_file.write_bytes(b"R440-fabricated-store-bytecode")
        self.depa = self.base / "R239_filtered.jar"
        self.depb = self.base / "R218.jar"
        self.depa.write_bytes(b"invented-A-dependency")
        self.depb.write_bytes(b"invented-B-dependency")
        self.args = SimpleNamespace(
            prior_source_root=self.source,
            prior_classes_root=self.classes,
            public_helper_source=ROOT / "tests/fixtures/r424/LootLegacyCleanupR424.java",
            public_acceptance_source=ROOT / "tests/fixtures/r425/R425ActualPrivateOverlayAcceptance.java",
            dependency_a=self.depa, dependency_b=self.depb,
            dependency_a_sha256=r425.hash_file(self.depa),
            dependency_b_sha256=r425.hash_file(self.depb),
            javac=Path(sys.executable),
            java=Path(sys.executable),
        )
        self.context = ExitStack()
        self.addCleanup(self.context.close)
        self.context.enter_context(
            patch.object(r440.tempfile, "gettempdir", return_value=str(self.base)))
        self.context.enter_context(
            patch.object(r425, "PINNED_R421_STORE_SHA",
                         r425.hash_file(self.store_file)))
        self.context.enter_context(
            patch.object(r424, "PINNED_R421_STORE_SHA",
                         r425.hash_file(self.store_file)))
        self.context.enter_context(
            patch.object(r425, "PINNED_R421_STORE_CLASS",
                         r425.hash_file(self.class_file)))
        self.context.enter_context(patch.object(r425, "BASELINE_SOURCE_COUNT", 1))
        self.context.enter_context(patch.object(r425, "BASELINE_CLASS_COUNT", 1))
        self.versions = self.context.enter_context(
            patch.object(r440.subprocess, "run", side_effect=self.good_version))

    @staticmethod
    def good_version(command, **kwargs):
        name = Path(command[0]).name.lower()
        if name.startswith("javac"):
            return SimpleNamespace(returncode=0, stdout="javac 21.0.6\n", stderr="")
        # Both filenames can be a Python executable in the fixture;
        # simulate java output by the order of calls in the test.
        return SimpleNamespace(returncode=0,
                               stdout="openjdk version \"21.0.6\" 2025-01-21\n",
                               stderr="")

    def version_pass(self):
        # Explicit mock for the two separate java-version invocations.
        self.versions.side_effect = [
            SimpleNamespace(returncode=0, stdout="javac 21.0.6\n", stderr=""),
            SimpleNamespace(returncode=0, stdout="",
                            stderr='openjdk version "21.0.6" 2025-01-21\n'),
        ]

    def audit(self):
        self.version_pass()
        return r440.audit(self.args)

    def test_01_accepted_invented_source_and_class_are_read_only(self):
        original = {
            p.relative_to(self.base).as_posix(): sha256(p.read_bytes()).hexdigest()
            for p in self.base.rglob("*") if p.is_file()
        }
        result = self.audit()
        self.assertEqual(result["status"], "R440_OWNER_PRIVATE_READ_ONLY_PREFLIGHT_PASS")
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["class_count"], 1)
        self.assertTrue(result["r424_source_shape_checked_in_memory"])
        self.assertTrue(result["provided_reference_dependency_digests_matched"])
        self.assertFalse(result["candidate_created"])
        self.assertFalse(result["private_java_compiled"])
        self.assertFalse(result["release_authorized"])
        self.assertFalse(result["live_history_opened"])
        current = {
            p.relative_to(self.base).as_posix(): sha256(p.read_bytes()).hexdigest()
            for p in self.base.rglob("*") if p.is_file()
        }
        self.assertEqual(original, current)

    def test_02_approved_jars_rejected_if_drifted(self):
        self.depa.write_bytes(b"changed-owner-dependency-synthetic")
        self.version_pass()
        with self.assertRaisesRegex(r425.Refused, "DEPENDENCY_A_SHA_DRIFT"):
            r440.audit(self.args)
        self.versions.assert_not_called()

    def test_03_self_derived_or_invalid_digest_is_not_accepted(self):
        for bad in ("", "0"*63, "Z"*64, None, "not-a-hash"):
            with self.subTest(bad=bad):
                self.args.dependency_a_sha256 = bad
                with self.assertRaisesRegex(r440.Refused, "APPROVED_DEPENDENCY"):
                    r440.audit(self.args)

    def test_04_identical_jars_need_explicit_review_not_automatic_pass(self):
        self.args.dependency_b_sha256=self.args.dependency_a_sha256
        with self.assertRaisesRegex(r440.Refused, "IDENTICAL_DEPENDENCY"):
            r440.audit(self.args)

    def test_05_unapproved_or_relocated_source_root_refused(self):
        altered=self.source
        self.args.prior_source_root=self.source.parent
        with self.assertRaisesRegex(r440.Refused, "EXACT_R421_TEMP"):
            r440.audit(self.args)
        self.args.prior_source_root=altered

    def test_06_class_sha_drift_refused_before_patch_audit(self):
        self.class_file.write_bytes(b"mutated-fabricated-private-store-class")
        self.version_pass()
        with self.assertRaisesRegex(r425.Refused, "R421_PRIVATE_CLASS_SHA_DRIFT"):
            r440.audit(self.args)
        self.versions.assert_not_called()

    def test_07_no_java17_or_unmatched_javac_major(self):
        self.versions.side_effect = [
            SimpleNamespace(returncode=0, stdout="javac 17.0.10\n", stderr="")]
        with self.assertRaisesRegex(r440.Refused, "JDK21_REQUIRED"):
            r440.audit(self.args)

    def test_08_owner_source_with_wrong_cleanup_method_refused(self):
        changed=FAKE_STORE.replace("deleteTree(parts)", "wrongDelete(parts)")
        self.store_file.write_text(changed, encoding="utf-8")
        with patch.object(r425,"PINNED_R421_STORE_SHA",
                          r425.hash_file(self.store_file)), patch.object(
             r424,"PINNED_R421_STORE_SHA",r425.hash_file(self.store_file)):
            self.version_pass()
            with self.assertRaisesRegex(r424.Refused, "OLD_STAGE_CHECK_CHANGED|UNSAFE_LEGACY_TREE_CALL_CHANGED"):
                r440.audit(self.args)

    def test_09_public_helper_tamper_refused(self):
        helper=self.base/"fabricated-helper.java"
        helper.write_bytes(self.args.public_helper_source.read_bytes()+b"\n//changed")
        self.args.public_helper_source=helper
        self.version_pass()
        with self.assertRaisesRegex(r424.Refused, "HELPER_SHA_PIN_MISMATCH"):
            r440.audit(self.args)

    def test_10_source_tree_symlink_refused(self):
        target=self.base/"outside"
        target.mkdir()
        link=self.source/"link-dir"
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation unavailable")
        with self.assertRaisesRegex(r440.Refused, "PRIVATE_TREE_LINK"):
            r440.audit(self.args)

    def test_11_all_explicit_approved_sha_and_audit_flags_in_owner_script(self):
        code=(ROOT/"tools/r425/owner_only_run_r425.ps1").read_text("utf-8")
        for check in ("[switch]$AuditOnly", "$ApprovedDependencyASha256",
                      "$ApprovedDependencyBSha256",
                      "R440_PRIVATE_PREFLIGHT_REFUSED",
                      "& $PythonExe -B @preflightArgs",
                      "R440_AUDIT_ONLY_COMPLETE",
                      "R432_RELEASE_GATE_REMAINS_CLOSED"):
            self.assertIn(check,code)
        self.assertLess(code.index("& $PythonExe -B @preflightArgs"),
                        code.index("& $PythonExe @arguments"))
        self.assertLess(code.index("& $PythonExe @arguments"),
                        code.index("& $PythonExe @secondArgs"))
        self.assertNotIn("$depAHash = (Get-FileHash", code)
        self.assertNotIn("$depBHash = (Get-FileHash", code)

    def test_12_no_private_paths_or_full_inventory_leak_in_receipt(self):
        receipt=self.audit()
        serialized=json.dumps(receipt, sort_keys=True)
        self.assertNotIn(str(self.base),serialized)
        self.assertNotIn("Source-Candidate-R421",serialized)
        self.assertNotIn("R239_filtered.jar",serialized)
        self.assertNotIn("records",serialized)
        self.assertFalse(receipt["merge_authorized"])


if __name__=="__main__":
    unittest.main()
