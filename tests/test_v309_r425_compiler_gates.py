"""R425 public-only compiler/class-delta safety negatives, NO private bytecode.

The real R421 source/class trees are unavailable to hosted CI.  Exact class
delta assertions and SHA-pin failures are tested on invented dictionaries.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from tools.r425.compile_and_accept_private_overlay import (
    Refused, BASELINE_CLASS_COUNT, BASELINE_SOURCE_COUNT,
    EXPECTED_HELPER_CLASSES, EXPECTED_CHANGED_EXISTING_CLASS,
    PINNED_R421_STORE_CLASS, gate_source_inventory,
    gate_class_inventory, validate_inputs,
)

STORE="rs/plugins/loottracker/LootHistoryStore.java"
HELPER="rs/plugins/loottracker/LootLegacyCleanupR424.java"
CLASS="rs/plugins/loottracker/LootHistoryStore.class"


class R425ScopeGates(unittest.TestCase):
    def setUp(self):
        self.prior_sources={
            STORE:"0"*64,
            "rs/plugins/loottracker/LootTrackerPlugin.java":"1"*64,
        }
        self.new_sources=dict(self.prior_sources)
        self.new_sources[STORE]="a"*64
        self.new_sources[HELPER]="b"*64
        self.prior_classes={
            CLASS:"0"*64,
            "rs/plugins/loottracker/LootTrackerPlugin.class":"1"*64,
        }
        self.new_classes=dict(self.prior_classes)
        self.new_classes[CLASS]="a"*64
        for i,name in enumerate(sorted(EXPECTED_HELPER_CLASSES)):
            self.new_classes[name]=str(i+2)*64

    def bad_source(self,updates):
        candidate=dict(self.new_sources)
        updates(candidate)
        with self.assertRaises(Refused):
            gate_source_inventory(self.prior_sources,candidate,2)

    def bad_class(self,updates):
        candidate=dict(self.new_classes)
        updates(candidate)
        with self.assertRaises(Refused):
            gate_class_inventory(self.prior_classes,candidate,2)

    def test_01_exact_public_one_source_added(self):
        result=gate_source_inventory(self.prior_sources,self.new_sources,2)
        self.assertEqual(result["candidate_sources"],3)
        self.assertEqual(result["modified_private_sources"],[STORE])
        self.assertEqual(result["added_public_helper_sources"],[HELPER])

    def test_02_exact_five_new_helper_classes(self):
        result=gate_class_inventory(self.prior_classes,self.new_classes,2)
        self.assertEqual(result["parent_classes"],2)
        self.assertEqual(result["candidate_classes"],7)
        self.assertEqual(set(result["added_helper_classes"]),EXPECTED_HELPER_CLASSES)
        self.assertEqual(result["removed_classes"],[])

    def test_03_parent_source_count_mismatch_refused(self):
        with self.assertRaises(Refused):
            gate_source_inventory(self.prior_sources,self.new_sources,3)

    def test_04_parent_class_count_mismatch_refused(self):
        with self.assertRaises(Refused):
            gate_class_inventory(self.prior_classes,self.new_classes,3)

    def test_05_unchanged_old_store_refused(self):
        self.bad_source(lambda d:d.__setitem__(STORE,self.prior_sources[STORE]))

    def test_06_changed_plugin_source_refused(self):
        self.bad_source(lambda d:d.__setitem__(
            "rs/plugins/loottracker/LootTrackerPlugin.java","f"*64))

    def test_07_unexpected_private_source_added_refused(self):
        self.bad_source(lambda d:d.__setitem__("rs/private/Secret.java","4"*64))

    def test_08_missing_old_source_refused(self):
        self.bad_source(lambda d:d.pop(STORE))

    def test_09_helper_source_missing_refused(self):
        self.bad_source(lambda d:d.pop(HELPER))

    def test_10_changed_plugin_class_refused(self):
        self.bad_class(lambda d:d.__setitem__(
            "rs/plugins/loottracker/LootTrackerPlugin.class","f"*64))

    def test_11_unchanged_old_store_class_refused(self):
        self.bad_class(lambda d:d.__setitem__(CLASS,self.prior_classes[CLASS]))

    def test_12_added_unrelated_class_refused(self):
        self.bad_class(lambda d:d.__setitem__("rs/other/Unsafe.class","a"*64))

    def test_13_missing_expected_helper_nested_class_refused(self):
        self.bad_class(lambda d:d.pop(sorted(EXPECTED_HELPER_CLASSES)[0]))

    def test_14_missing_prior_class_refused(self):
        self.bad_class(lambda d:d.pop("rs/plugins/loottracker/LootTrackerPlugin.class"))

    def test_15_private_store_class_pin_is_specific_sha(self):
        self.assertEqual(PINNED_R421_STORE_CLASS,
                         "65272371272fdcf9142095880a042aa007a9a088f93c969a57878188fae37a09")

    def test_16_expected_production_scope_constants(self):
        self.assertEqual(BASELINE_SOURCE_COUNT,1277)
        self.assertEqual(BASELINE_CLASS_COUNT,1394)
        self.assertEqual(EXPECTED_CHANGED_EXISTING_CLASS,CLASS)
        self.assertEqual(len(EXPECTED_HELPER_CLASSES),5)

    def test_17_cannot_pass_missing_owner_inputs(self):
        with tempfile.TemporaryDirectory(prefix="r425-neg-gate-") as d:
            root=Path(d)
            fake=root/"nonexistent"
            args=SimpleNamespace(
                dependency_a_sha256="0"*64,dependency_b_sha256="1"*64,
                javac=fake,java=fake,dependency_a=fake,dependency_b=fake,
                public_helper_source=fake,public_acceptance_source=fake,
                prior_source_root=fake,prior_classes_root=fake)
            with self.assertRaises(Refused):
                validate_inputs(args)

    def test_18_invalid_dependency_sha_refused_early(self):
        with tempfile.TemporaryDirectory(prefix="r425-sha-gate-") as d:
            root=Path(d)
            args=SimpleNamespace(
                dependency_a_sha256="INVALID",dependency_b_sha256="0"*64,
                javac=root,java=root,dependency_a=root,dependency_b=root,
                public_helper_source=root,public_acceptance_source=root,
                prior_source_root=root,prior_classes_root=root)
            with self.assertRaises(Refused):
                validate_inputs(args)


if __name__=="__main__":
    unittest.main()
