"""R432 PUBLIC-ONLY tests for owner-private R425 -> R422 acceptance chaining.

Invented source/class bytes and in-process mocked R422 subprocess receipts only.
None of these tests compile, import, inspect, or run the recovered SpawnPK
private client. A hosted PASS is NOT real-client cross-process acceptance.
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
import uuid

from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r432 import chain_private_process_acceptance as r432
from tools.r441.approved_full_inventory import inventory_digest

ROOT = Path(__file__).resolve().parents[1]


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


class R432GateTests(unittest.TestCase):
    def setUp(self):
        self.fake_source_scope = {
            "parent_sources": 1277,
            "candidate_sources": 1278,
            "modified_private_sources": [r425.STORE.as_posix()],
            "added_public_helper_sources": [r425.HELPER.as_posix()],
        }
        self.fake_class_scope = {
            "parent_classes": 1394,
            "candidate_classes": 1399,
            "modified_existing_classes": [r425.EXPECTED_CHANGED_EXISTING_CLASS],
            "added_helper_classes": sorted(r425.EXPECTED_HELPER_CLASSES),
            "removed_classes": [],
        }
        self.store_digest = "a" * 64
        self.r425receipt = {
            "status": "R425_PRIVATE_OVERLAY_COMPILE_AND_ACTUAL_STORE_PASS",
            "private_source_patch":
                "R424_PRIVATE_DRY_RUN_LEGACY_CLEANUP_PATCH_PREPARED_NOT_COMPILED",
            "source_scope": self.fake_source_scope,
            "class_scope": self.fake_class_scope,
            "actual_private_store": {
                "status": "R425_ACTUAL_PRIVATE_STORE_DRY_RUN_TEMP_PASS",
                "real_class_assertions": 39,
            },
            "legacy_deletion_enabled": False,
            "real_history_read_or_changed": False,
            "private_game_launched": False,
            "release_authorized": False,
            "merge_authorized": False,
        }
        self.r422receipt = {
            "status": "R422_OWNER_PRIVATE_ACTUAL_STORE_PROCESS_ACCEPTANCE_PASS",
            "class_sha256_verified": self.store_digest,
            "real_store_assertions": 73,
            "checks": len(r432.REQUIRED_R422_CHECKS),
            "cases": sorted(r432.REQUIRED_R422_CHECKS),
            "original_game_started": False,
            "production_history_opened": False,
            "private_release_authorized": False,
        }

    def gate425(self, obj=None):
        r432.gate_existing_r425_receipt(
            self.r425receipt if obj is None else obj,
            self.fake_source_scope, self.fake_class_scope)

    def gate422(self, obj=None):
        return r432.gate_r422_process_receipt(
            self.r422receipt if obj is None else obj, self.store_digest)

    def test_01_exact_prior_private_acceptance_receipt(self):
        self.gate425()

    def test_02_prior_r425_missing_or_failed_refused(self):
        for state in ("R425_REFUSED", None, ""):
            with self.subTest(state=state):
                self.r425receipt["status"] = state
                with self.assertRaises(r432.Refused):
                    self.gate425()

    def test_03_prior_r425_no_durable_39_assertions_refused(self):
        self.r425receipt["actual_private_store"]["real_class_assertions"] = 38
        with self.assertRaisesRegex(r432.Refused, "ACTUAL_STORE"):
            self.gate425()

    def test_04_r425_wrong_or_missing_source_class_scope_refused(self):
        # Do not mutate the expected scope through a shared nested dict.
        corrupted = dict(self.r425receipt)
        corrupted["class_scope"] = {
            **self.fake_class_scope,
            "modified_existing_classes": [],
        }
        with self.assertRaisesRegex(r432.Refused, "CLASS_SCOPE"):
            self.gate425(corrupted)

    def test_05_r425_release_or_auto_cleanup_flags_must_be_false(self):
        for field in ("release_authorized", "merge_authorized",
                      "legacy_deletion_enabled",
                      "real_history_read_or_changed", "private_game_launched"):
            with self.subTest(field=field):
                source = dict(self.r425receipt)
                source[field] = True
                with self.assertRaises(r432.Refused):
                    self.gate425(source)

    def test_06_r422_all_17_exact_process_checks_required(self):
        result = self.gate422()
        self.assertEqual(result["checks"],17)
        self.assertEqual(result["real_store_assertions"],73)
        self.assertFalse(result["private_release_authorized"])

    def test_07_r422_rebuilt_private_class_sha_exact(self):
        self.r422receipt["class_sha256_verified"] = "b"*64
        with self.assertRaisesRegex(r432.Refused, "DIFFERENT_PRIVATE_CLASS"):
            self.gate422()

    def test_08_r422_partial_process_test_refused(self):
        self.r422receipt["cases"] = self.r422receipt["cases"][:-1]
        with self.assertRaisesRegex(r432.Refused, "MISSING_OR_DUPLICATE"):
            self.gate422()

    def test_09_r422_duplicate_process_check_refused(self):
        self.r422receipt["cases"][0] = self.r422receipt["cases"][1]
        with self.assertRaisesRegex(r432.Refused, "MISSING_OR_DUPLICATE"):
            self.gate422()

    def test_10_r422_real_store_below_73_refused(self):
        self.r422receipt["real_store_assertions"] = 72
        with self.assertRaisesRegex(r432.Refused, "INSUFFICIENT"):
            self.gate422()

    def test_11_r422_disclosure_flags_refused(self):
        self.r422receipt["production_history_opened"] = True
        with self.assertRaisesRegex(r432.Refused, "UNSAFE"):
            self.gate422()

    def test_12_r422_failed_state_refused(self):
        self.r422receipt["status"] = "R422_OWNER_PRIVATE_ACCEPTANCE_REFUSED"
        with self.assertRaisesRegex(r432.Refused, "CROSS_PROCESS_NOT_PASSED"):
            self.gate422()

    def test_13_direct_temp_non_synthetic_path_refused(self):
        with self.assertRaisesRegex(r432.Refused, "REFUSE_NONISOLATED"):
            r432.validate_fresh_candidate(Path(tempfile.gettempdir()))

    def test_14_missing_synthetic_candidate_refused(self):
        absent = (Path(tempfile.gettempdir()) /
                  ("R424-Private-Candidate-R425-Missing-"+uuid.uuid4().hex))
        with self.assertRaisesRegex(r432.Refused, "MISSING_OR_UNREADABLE"):
            r432.validate_fresh_candidate(absent)

    def test_15_old_r432_receipt_blocks_repeat_acceptance(self):
        with tempfile.TemporaryDirectory(
                prefix="R424-Private-Candidate-R425-",
                dir=tempfile.gettempdir()) as parent:
            target=Path(parent)
            (target/r432.R432_RECEIPT).write_bytes(b"prior synthetic proof")
            with self.assertRaisesRegex(r432.Refused, "ALREADY_ACCEPTED"):
                r432.validate_fresh_candidate(target)

    def test_16_owner_only_cli_has_no_skip_sha_or_release(self):
        source=(ROOT/"tools/r432/chain_private_process_acceptance.py"
               ).read_text(encoding="utf-8")
        self.assertNotIn("--skip",source)
        self.assertNotIn("--force-release",source)
        self.assertNotIn("Expand-Archive",source)
        self.assertNotIn("LootHistoryStore.class",source.split("R422_PROGRAM =")[0])
        self.assertIn("release_authorized",source)


class R432WholeMockGateTests(unittest.TestCase):
    """Exercise real R432 orchestration with fake source/class bytes.

    The ONLY patched values are in this test process and MUST NEVER be
    exposed as CLI overrides in the owner-facing script.
    """

    @staticmethod
    def write(root: Path, name: str, data: bytes) -> Path:
        p=root/name
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(data)
        return p

    def setUp(self):
        self.workspace=tempfile.TemporaryDirectory(prefix="R432-Invented-")
        self.addCleanup(self.workspace.cleanup)
        base=Path(self.workspace.name)
        isolated=(base/"SpawnPK-R386-Isolated-Acceptance"/
                  "R421-Private-NoFollow-Cache-Directory-Preflight")
        self.original_src=isolated/"Source-Candidate-R421"/"source"
        self.original_cls=isolated/"R421-Compiled-Classes"
        self.candidate=(Path(tempfile.gettempdir())/
                        ("R424-Private-Candidate-R425-Mock-"+uuid.uuid4().hex))
        self.candidate.mkdir()
        self.addCleanup(lambda: shutil.rmtree(self.candidate,ignore_errors=True))
        self.new_src=self.candidate/"source"
        self.new_cls=self.candidate/"R425-Compiled-Classes"

        self.old_source=b"fake-old-Store-Java-not-recovered"
        self.new_source=b"fake-patched-Store-Java-not-recovered"
        self.old_class=b"fake-old-Store-class-not-recovered"
        self.new_class=b"fake-patched-Store-class-not-recovered"
        self.write(self.original_src, r425.STORE.as_posix(), self.old_source)
        self.write(self.original_src, "rs/plugins/loottracker/Other.java",
                   b"synthetic unrelated")
        self.write(self.original_cls,
                   r425.EXPECTED_CHANGED_EXISTING_CLASS, self.old_class)
        self.write(self.original_cls, "rs/plugins/loottracker/Other.class",
                   b"synthetic-unrelated-class")

        self.write(self.new_src, r425.STORE.as_posix(), self.new_source)
        self.write(self.new_src, "rs/plugins/loottracker/Other.java",
                   b"synthetic unrelated")
        self.write(self.new_src, r425.HELPER.as_posix(),
                   r432.R424_HELPER.read_bytes().replace(b"\r\n", b"\n"))
        self.write(self.new_cls,
                   r425.EXPECTED_CHANGED_EXISTING_CLASS, self.new_class)
        self.write(self.new_cls, "rs/plugins/loottracker/Other.class",
                   b"synthetic-unrelated-class")
        for name in r425.EXPECTED_HELPER_CLASSES:
            self.write(self.new_cls, name, name.encode("ascii"))

        self.d1=self.write(base,"deps-A.jar",b"synthetic-jar-a")
        self.d2=self.write(base,"deps-B.jar",b"synthetic-jar-b")
        self.args=SimpleNamespace(
            candidate_temp_root=self.candidate,
            prior_source_root=self.original_src,
            prior_classes_root=self.original_cls,
            dependency_a=self.d1,
            dependency_b=self.d2,
            dependency_a_sha256=r425.hash_file(self.d1),
            dependency_b_sha256=r425.hash_file(self.d2),
            approved_source_inventory_sha256=inventory_digest(
                r425.sha_inventory(self.original_src, ".java"), "java"),
            approved_class_inventory_sha256=inventory_digest(
                r425.sha_inventory(self.original_cls, ".class"), "class"),
            javac=Path(sys.executable).resolve(),
            java=Path(sys.executable).resolve(),
        )
        self.old_source_sha=digest(self.old_source)
        self.old_class_sha=digest(self.old_class)
        self.new_class_sha=digest(self.new_class)
        self.src_scope={
            "parent_sources":2,"candidate_sources":3,
            "modified_private_sources":[r425.STORE.as_posix()],
            "added_public_helper_sources":[r425.HELPER.as_posix()],
        }
        self.cls_scope={
            "parent_classes":2,"candidate_classes":7,
            "modified_existing_classes":[r425.EXPECTED_CHANGED_EXISTING_CLASS],
            "added_helper_classes":sorted(r425.EXPECTED_HELPER_CLASSES),
            "removed_classes":[],
        }
        self.prior_receipt={
            "status":"R425_PRIVATE_OVERLAY_COMPILE_AND_ACTUAL_STORE_PASS",
            "private_source_patch":
                "R424_PRIVATE_DRY_RUN_LEGACY_CLEANUP_PATCH_PREPARED_NOT_COMPILED",
            "source_scope":self.src_scope,
            "class_scope":self.cls_scope,
            "actual_private_store":{
                "status":"R425_ACTUAL_PRIVATE_STORE_DRY_RUN_TEMP_PASS",
                "real_class_assertions":39,
            },
            "legacy_deletion_enabled":False,
            "real_history_read_or_changed":False,
            "private_game_launched":False,
            "release_authorized":False,
            "merge_authorized":False,
        }
        self.write(self.candidate,r432.R425_RECEIPT,
                   json.dumps(self.prior_receipt).encode("utf-8"))
        self.r422receipt={
            "status":"R422_OWNER_PRIVATE_ACTUAL_STORE_PROCESS_ACCEPTANCE_PASS",
            "class_sha256_verified":self.new_class_sha,
            "real_store_assertions":73,
            "checks":17,
            "cases":sorted(r432.REQUIRED_R422_CHECKS),
            "original_game_started":False,
            "production_history_opened":False,
            "private_release_authorized":False,
        }

    def fixture_patch(self):
        ctx=ExitStack()
        self.addCleanup(ctx.close)
        ctx.enter_context(patch.object(
            r425,"PINNED_R421_STORE_SHA",self.old_source_sha))
        ctx.enter_context(patch.object(
            r425,"PINNED_R421_STORE_CLASS",self.old_class_sha))
        ctx.enter_context(patch.object(
            r425,"BASELINE_SOURCE_COUNT",2))
        ctx.enter_context(patch.object(
            r425,"BASELINE_CLASS_COUNT",2))
        return ctx

    def r422_subprocess(self,*args,**kwargs):
        command=args[0]
        self.assertIn("--expected-store-class-sha256",command)
        idx=command.index("--expected-store-class-sha256")
        self.assertEqual(command[idx+1],self.new_class_sha)
        self.assertIn(str(self.new_cls),command)
        return SimpleNamespace(
            returncode=0,stdout=json.dumps(self.r422receipt),stderr="")

    def test_17_full_mock_chain_accepts_all_gates_and_no_release(self):
        with self.fixture_patch(),patch.object(r432.subprocess,"run",
                                             side_effect=self.r422_subprocess):
            result=r432.run(self.args)
        self.assertEqual(result["status"],
                         "R432_OWNER_PRIVATE_CROSS_PROCESS_CHAIN_PASS")
        self.assertEqual(result["r422_process_acceptance"]["checks"],17)
        self.assertFalse(result["release_authorized"])
        self.assertFalse(result["merge_authorized"])
        self.assertEqual(
            json.loads((self.candidate/r432.R432_RECEIPT).read_text())["status"],
            result["status"])
        self.assertEqual((self.original_src/r425.STORE).read_bytes(),
                         self.old_source)

    def test_18_mock_r422_failure_does_not_write_success_receipt(self):
        with self.fixture_patch(),patch.object(
                r432.subprocess,"run",
                return_value=SimpleNamespace(
                    returncode=2,stdout='{"status":"FAILED"}',stderr="fake")):
            with self.assertRaisesRegex(r432.Refused,"R422_TEST_FAILED"):
                r432.run(self.args)
        self.assertFalse((self.candidate/r432.R432_RECEIPT).exists())

    def test_19_mock_compiled_class_mutation_during_subprocess_refused(self):
        def mutation(*args,**kwargs):
            self.write(self.new_cls,r425.EXPECTED_CHANGED_EXISTING_CLASS,
                       b"fake-changed-during-r422")
            return self.r422_subprocess(*args,**kwargs)
        with self.fixture_patch(),patch.object(r432.subprocess,"run",
                                             side_effect=mutation):
            with self.assertRaises(r432.Refused):
                r432.run(self.args)
        self.assertFalse((self.candidate/r432.R432_RECEIPT).exists())

    def test_20_r425_acceptance_receipt_tamper_refused(self):
        prior=dict(self.prior_receipt)
        prior["release_authorized"]=True
        self.write(self.candidate,r432.R425_RECEIPT,
                   json.dumps(prior).encode("utf-8"))
        with self.fixture_patch(), patch.object(r432.subprocess,"run") as mock:
            with self.assertRaisesRegex(r432.Refused,"UNSAFE_RECEIPT"):
                r432.run(self.args)
        mock.assert_not_called()

    def test_21_private_store_class_mismatch_refused_before_cross_process(self):
        self.write(self.new_cls,r425.EXPECTED_CHANGED_EXISTING_CLASS,
                   self.old_class)
        with self.fixture_patch(), patch.object(r432.subprocess,"run") as mock:
            with self.assertRaisesRegex(
                    r425.Refused, "R425_EXISTING_PRIVATE_CLASS_DELTA_UNEXPECTED"):
                r432.run(self.args)
        mock.assert_not_called()

    def test_22_dependency_changed_refused_without_running_java(self):
        self.d1.write_bytes(b"changed synthetic dependency")
        with self.fixture_patch(), patch.object(r432.subprocess,"run") as mock:
            with self.assertRaises(r425.Refused):
                r432.run(self.args)
        mock.assert_not_called()


if __name__=="__main__":
    unittest.main()
