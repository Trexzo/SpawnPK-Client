"""R441 public-only exact full-inventory pin regressions.

Invented SHA maps only; no owner-private recovered source/class, installed
SpawnPK client, real player history or deletion evidence is accessed.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from tools.r441.approved_full_inventory import (
    Refused, inventory_digest, require_approved_baselines,
)
from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r432 import chain_private_process_acceptance as r432
from tools.r440 import read_only_private_acceptance_preflight as r440

ROOT = Path(__file__).resolve().parents[1]
SRC = {
    "rs/plugins/loottracker/LootHistoryStore.java": "a"*64,
    "rs/plugins/loottracker/Other.java": "b"*64,
    "rs/Other.java": "c"*64,
}
CLS = {
    "rs/plugins/loottracker/LootHistoryStore.class": "d"*64,
    "rs/plugins/loottracker/Other.class": "e"*64,
    "rs/Other.class": "f"*64,
}


def approved():
    return SimpleNamespace(
        approved_source_inventory_sha256=inventory_digest(SRC, "java"),
        approved_class_inventory_sha256=inventory_digest(CLS, "class"),
    )


class R441ApprovedFullInventory(unittest.TestCase):
    def test_01_expected_full_tree_digest_is_deterministic_and_64_lowercase(self):
        a = inventory_digest(SRC, "java")
        reverse = dict(reversed(list(SRC.items())))
        self.assertEqual(a, inventory_digest(reverse, "java"))
        self.assertRegex(a, r"^[0-9a-f]{64}$")
        self.assertEqual(a, inventory_digest(json.loads(json.dumps(SRC)), "java"))

    def test_02_domain_separation_for_java_and_class(self):
        self.assertNotEqual(inventory_digest(SRC, "java"),
                            inventory_digest(SRC, "class"))
        self.assertNotEqual(inventory_digest(SRC, "java"),
                            inventory_digest(CLS, "class"))

    def test_03_full_tree_acceptance_with_two_approved_references(self):
        require_approved_baselines(approved(), SRC, CLS)

    def test_04_unrelated_source_change_same_count_must_refuse(self):
        changed = dict(SRC)
        changed["rs/Other.java"] = "0"*64
        self.assertEqual(len(changed), len(SRC))
        with self.assertRaisesRegex(Refused, "R441_APPROVED_JAVA_INVENTORY_SHA_MISMATCH"):
            require_approved_baselines(approved(), changed, CLS)

    def test_05_unrelated_class_change_same_count_must_refuse(self):
        changed = dict(CLS)
        changed["rs/Other.class"] = "1"*64
        self.assertEqual(len(changed), len(CLS))
        with self.assertRaisesRegex(Refused, "R441_APPROVED_CLASS_INVENTORY_SHA_MISMATCH"):
            require_approved_baselines(approved(), SRC, changed)

    def test_06_path_rename_same_count_and_same_file_hash_must_refuse(self):
        renamed = dict(SRC)
        value = renamed.pop("rs/Other.java")
        renamed["rs/Another.java"] = value
        self.assertEqual(len(renamed), len(SRC))
        with self.assertRaisesRegex(Refused, "R441_APPROVED_JAVA_INVENTORY_SHA_MISMATCH"):
            require_approved_baselines(approved(), renamed, CLS)

    def test_07_source_class_digest_crossswap_refused(self):
        args = approved()
        args.approved_source_inventory_sha256, args.approved_class_inventory_sha256 = (
            args.approved_class_inventory_sha256, args.approved_source_inventory_sha256
        )
        with self.assertRaisesRegex(Refused, "R441_APPROVED_JAVA_INVENTORY_SHA_MISMATCH"):
            require_approved_baselines(args, SRC, CLS)

    def test_08_bad_or_missing_approved_digests_refused(self):
        for key, inventory, kind in (
            ("approved_source_inventory_sha256", SRC, "JAVA"),
            ("approved_class_inventory_sha256", CLS, "CLASS"),
        ):
            for bad in (None, "", "f"*63, "F"*64, "trusted", 12):
                args = approved()
                setattr(args, key, bad)
                with self.subTest(key=key, bad=bad):
                    with self.assertRaisesRegex(Refused,
                                               f"R441_APPROVED_{kind}_INVENTORY_SHA_REQUIRED"):
                        require_approved_baselines(args, SRC, CLS)

    def test_09_reject_invalid_relative_paths(self):
        bad_paths = (
            "/absolute.java", "../traversal.java", "rs/../file.java",
            "rs\\file.java", "", "./relative.java", "rs/evil\x00file.java",
        )
        for name in bad_paths:
            with self.subTest(name=repr(name)):
                with self.assertRaisesRegex(Refused, "INVALID_INVENTORY_RELATIVE_PATH"):
                    inventory_digest({name: "a"*64}, "java")

    def test_10_reject_invalid_member_hash_and_empty_mapping(self):
        for value in ("z"*64, "A"*64, "a"*63, "", 50):
            with self.subTest(value=value):
                with self.assertRaisesRegex(Refused, "R441_INVALID_MEMBER_SHA"):
                    inventory_digest({"rs/Valid.java": value}, "java")
        with self.assertRaisesRegex(Refused, "EMPTY_OR_INVALID_INVENTORY"):
            inventory_digest({}, "java")
        with self.assertRaisesRegex(Refused, "UNKNOWN_INVENTORY_KIND"):
            inventory_digest(SRC, "unknown")

    def test_11_public_r425_private_validate_blocks_same_count_tamper(self):
        code = inspect.getsource(r425.validate_inputs)
        self.assertIn("require_approved_baselines(args, source, classes)", code)
        self.assertIn('sha_inventory(prior_source, ".java")', code)
        self.assertIn('sha_inventory(prior_classes, ".class")', code)
        build = inspect.getsource(r425.verify_unchanged_build_inputs)
        self.assertIn("require_approved_baselines(", build)

    def test_12_public_r432_chain_rechecks_before_and_after_cross_jvm(self):
        refs = inspect.getsource(r432.validate_owner_references)
        body = inspect.getsource(r432.run)
        self.assertIn("approved_source_inventory_sha256=args.approved_source_inventory_sha256", refs)
        self.assertIn("approved_class_inventory_sha256=args.approved_class_inventory_sha256", refs)
        self.assertIn('args, before["baseline_source"], before["baseline_class"]', body)
        self.assertIn('args, after["baseline_source"], after["baseline_class"]', body)
        self.assertIn("R432_INPUT_OR_CANDIDATE_CHANGED_DURING_PROCESS_TESTS", body)

    def test_13_public_r440_read_only_audit_requires_full_pins(self):
        body = inspect.getsource(r440.audit)
        self.assertIn("require_approved_baselines(args, baseline_source, baseline_classes)", body)
        self.assertIn('"provided_reference_full_source_class_inventories_matched": True', body)
        self.assertIn('"candidate_created": False', body)
        self.assertIn('"private_java_compiled": False', body)
        self.assertIn('"release_authorized": False', body)

    def test_14_three_cli_parsers_require_both_hashes(self):
        for module in (r425, r432, r440):
            code = inspect.getsource(module.main)
            for item in ("approved-source-inventory-sha256",
                         "approved-class-inventory-sha256"):
                with self.subTest(module=module.__name__, item=item):
                    self.assertIn(f'parser.add_argument("--{item}", required=True)', code)

    def test_15_owner_ps1_never_auto_approves_tree_hashes(self):
        code = (ROOT / "tools/r425/owner_only_run_r425.ps1").read_text("utf-8")
        for item in ("ApprovedSourceInventorySha256", "ApprovedClassInventorySha256"):
            self.assertIn("[string]$" + item, code)
            self.assertEqual(code.count("--approved-" +
                            ("source" if "Source" in item else "class")
                            + "-inventory-sha256"), 3)
        self.assertIn("R441_REFUSED:", code)
        self.assertLess(code.index("@preflightArgs"), code.index("@arguments"))
        self.assertLess(code.index("@arguments"), code.index("@secondArgs"))
        self.assertNotIn("ApprovedSourceInventorySha256 = (Get-FileHash", code)
        self.assertNotIn("ApprovedClassInventorySha256 = (Get-FileHash", code)
        for flag in ("R425_RELEASE_GATE_REMAINS_CLOSED",
                     "R432_RELEASE_GATE_REMAINS_CLOSED"):
            self.assertIn(flag, code)

    def test_16_none_of_the_checks_weaken_owner_count_or_store_sha(self):
        source = inspect.getsource(r425.validate_inputs)
        for invariant in ("PINNED_R421_STORE_SHA", "PINNED_R421_STORE_CLASS",
                          "BASELINE_SOURCE_COUNT", "BASELINE_CLASS_COUNT"):
            self.assertIn(invariant, source)
        for module in (r425, r432, r440):
            cli = inspect.getsource(module.main)
            self.assertNotIn("--skip", cli)
            self.assertNotIn("--override-sha", cli)
            self.assertNotIn("--authorize-release", cli)


if __name__ == "__main__":
    unittest.main()
