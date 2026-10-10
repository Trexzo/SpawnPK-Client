"""R37 public aggregate frontier cannot imply certified recovered Java."""
from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
FRONTIER = ROOT / "research" / "v309-source-recovery" / "frontier.json"


class SourceRecoveryFrontierR37Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(FRONTIER.read_text(encoding="utf-8"))

    def test_sha_pins_and_stable_owner_id(self):
        d = self.data
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["kind"], "v309_private_source_recovery_frontier")
        self.assertEqual(d["owner_stable_id"], "CLIENT_CLASS_000167")
        for key in ("original_client_jar_sha256",):
            self.assertRegex(d[key], r"\A[0-9a-f]{64}\Z")
        for key in ("source_sha256", "compiled_class_sha256"):
            self.assertRegex(d["private_candidate"][key], r"\A[0-9a-f]{64}\Z")
        self.assertEqual(
            d["original_client_jar_sha256"],
            "ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38",
        )

    def test_no_acceptance_or_source_publication_claim(self):
        d = self.data
        for key in (
            "owner_lineage_accepted", "source_equivalence_certified",
            "runtime_equivalence_certified", "client_source_published",
        ):
            self.assertIs(d[key], False, key)
        self.assertEqual(d["canonical_member_or_field_mappings_promoted"], 0)
        self.assertGreaterEqual(len(d["vetoes"]), 6)

    def test_field_inventory_accounting(self):
        c = self.data["private_candidate"]
        self.assertEqual(c["original_field_declarations"], 126)
        self.assertEqual(c["candidate_field_declarations"], 4)
        self.assertEqual(c["shared_field_declarations"], 4)
        self.assertEqual(
            c["exact_field_declaration_metadata"]
            + c["changed_field_declaration_metadata"],
            c["shared_field_declarations"],
        )
        self.assertEqual(
            c["missing_original_field_declarations"] + c["shared_field_declarations"],
            c["original_field_declarations"],
        )
        self.assertEqual(
            c["extra_candidate_field_declarations"] + c["shared_field_declarations"],
            c["candidate_field_declarations"],
        )
        self.assertEqual(c["changed_field_declaration_metadata"], 1)

    def test_method_body_frontier_is_explicitly_incomplete(self):
        c = self.data["private_candidate"]
        self.assertEqual(c["original_method_declarations"], 10)
        self.assertEqual(c["candidate_method_declarations"], 8)
        self.assertEqual(c["original_method_bodies_reconstructed_instruction_level"], 7)
        self.assertEqual(
            c["corresponding_stackmap_metadata_equal"]
            + c["corresponding_stackmap_metadata_different"],
            c["original_method_bodies_reconstructed_instruction_level"],
        )
        self.assertEqual(
            c["original_method_declarations_missing_from_candidate"], 2,
        )
        self.assertEqual(c["placeholder_methods_not_recovered"], 1)
        self.assertEqual(c["original_substantive_method_bodies_unrecovered"], 3)
        self.assertLess(
            c["original_method_bodies_reconstructed_instruction_level"],
            c["original_method_declarations"],
        )

    def test_reconstructed_class_flags_are_not_class_equivalence(self):
        c = self.data["private_candidate"]
        self.assertEqual(c["original_classfile_major"], 53)
        self.assertEqual(c["candidate_classfile_major"], 53)
        for key in (
            "class_access_flags_equal", "superclass_equal", "ordered_interfaces_equal",
        ):
            self.assertIs(c[key], True)
        self.assertFalse(self.data["source_equivalence_certified"])

    def test_private_coordinates_and_source_not_committed(self):
        body = FRONTIER.read_text(encoding="utf-8")
        self.assertNotIn('"raw_class_path"', body)
        self.assertNotIn('"java_source"', body)
        self.assertNotIn('"decompiled_source"', body)
        self.assertNotIn("class rs.", body)
        self.assertNotIn("rs/f/a", body)
        self.assertNotIn("OriginalSource.java", body)
        self.assertNotRegex(body, r"-----BEGIN [A-Z ]+ PRIVATE KEY-----")
        self.assertNotIn("data:application/java-archive", body)


if __name__ == "__main__":
    unittest.main()
