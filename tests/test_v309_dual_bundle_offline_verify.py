from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from spk_recovery.descriptor_class_dependencies import (
    build_descriptor_class_dependency_report,
)
from spk_recovery.v309_private_dual_proof_replay import _digest
from spk_recovery.v309_dual_bundle_offline_verify import (
    V309DualBundleOfflineVerifyError,
    verify_v309_dual_bundle_offline,
)


FRONTIER = Path(__file__).resolve().parents[1] / "research" / "v309-field-recovery"


def _documents():
    frontier = json.loads((FRONTIER / "frontier.json").read_text(encoding="utf-8"))
    classes = json.loads((FRONTIER / "class-lineage.json").read_text(encoding="utf-8"))
    members = json.loads((FRONTIER / "member-lineage.json").read_text(encoding="utf-8"))
    global_report = json.loads((FRONTIER / "global-field-usage.json").read_text(encoding="utf-8"))
    dep = build_descriptor_class_dependency_report(global_report)
    old_owners = {
        c["logical_id"]: entry["internal_name"]
        for c in classes["classes"]
        for entry in c["lineage"]
        if entry["build_id"] == "v308"
    }
    descriptor_body = {
        "schema_version": 1,
        "kind": "v309_descriptor_class_verified_replay_research",
        "canonical": False,
        "state": "NO_CLASS_OR_MEMBER_IDENTITY_ACCEPTED",
        "global_field_report_id": global_report["report_id"],
        "global_field_report_digest": _digest(global_report),
        "class_lineage_digest": _digest(classes),
        "old_index_sha256": frontier["exact_clients"]["v308_sha256"],
        "new_index_sha256": frontier["exact_clients"]["v309_sha256"],
        "dependency_report_digest": _digest(dep),
        "summary": {
            "input_class_dependencies": 8,
            "candidate_classes": 0,
            "rejected_classes": 8,
            "candidate_fields_blocked": 0,
            "still_blocked_fields": 26,
        },
        "candidates": [],
        "rejected": [
            {
                "old_canonical_class_id": group["old_canonical_class_id"],
                "old_class": old_owners[group["old_canonical_class_id"]],
                "blocked_relationship_ids": group["relationship_ids"],
                "blocked_fields": group["blocked_fields"],
                "reason": "no_independent_global_index_identity_witness",
            }
            for group in dep["class_dependencies"]
        ],
        "note": "Synthetic test report; no independently measured class witnesses.",
    }
    descriptor = {
        "report_id": "DESCCLASSREPLAY_" + _digest(descriptor_body)[:20].upper(),
        **descriptor_body,
    }
    empty_rows = [
        q for q in global_report["review_outcomes"]
        if q["outcome"] == "empty_both"
    ]
    assert len(empty_rows) == 68
    empty_rejected = [
        {
            "relationship_id": q["relationship_id"],
            "logical_class_id": q["logical_class_id"],
            "old_owner": q["old_owner"],
            "new_owner": q["new_owner"],
            "reason": "missing_two_sided_canonical_anchor",
        }
        for q in sorted(empty_rows, key=lambda v: v["relationship_id"])
    ]
    empty_material = {
        "old_build_id": "v308",
        "new_build_id": "v309",
        "old_sha256": frontier["exact_clients"]["v308_sha256"],
        "new_sha256": frontier["exact_clients"]["v309_sha256"],
        "member_lineage_digest": _digest(members),
        "global_usage_report_id": global_report["report_id"],
        "candidates": [],
        "rejected": empty_rejected,
    }
    empty = {
        "schema_version": 1,
        "kind": "empty_field_declaration_identity_candidates",
        "canonical": False,
        "report_id": "EMPTYFIELDDECL_" + _digest(empty_material)[:20].upper(),
        **{k: empty_material[k] for k in (
            "old_build_id", "new_build_id", "old_sha256", "new_sha256",
            "member_lineage_digest", "global_usage_report_id",
        )},
        "summary": {
            "input_empty_both_reviews": 68,
            "candidate_fields": 0,
            "remaining_without_declaration_proof": 68,
            "raw_source_guard_rejected": 0,
            "global_class_topology_guard_rejected": 0,
            "missing_two_sided_canonical_anchor": 68,
            "canonical_anchor_identity_mismatch": 0,
            "declaration_interval_length_mismatch": 0,
            "declaration_interval_shape_mismatch": 0,
            "target_interval_offset_mismatch": 0,
            "target_declaration_signature_not_unique": 0,
        },
        "candidates": [],
        "rejected": empty_rejected,
        "note": "Synthetic unit test; not independently measured private bytecode evidence.",
    }
    manifest_body = {
        "schema_version": 1,
        "kind": "v309_private_dual_proof_research_bundle",
        "canonical": False,
        "state": "BOTH_LANES_RESEARCH_ONLY_NO_IDENTITIES_ACCEPTED",
        "global_report_id": global_report["report_id"],
        "v308_sha256": frontier["exact_clients"]["v308_sha256"],
        "v309_sha256": frontier["exact_clients"]["v309_sha256"],
        "descriptor_report_id": descriptor["report_id"],
        "descriptor_report_digest": _digest(descriptor),
        "empty_report_id": empty["report_id"],
        "empty_report_digest": _digest(empty),
        "descriptor_summary": descriptor["summary"],
        "empty_summary": empty["summary"],
        "unresolved_accepted_frontier": 143,
        "warning": "Synthetic bundle; no mappings accepted.",
    }
    manifest = {
        "bundle_id": "V309DUAL_" + _digest(manifest_body)[:20].upper(),
        **manifest_body,
    }
    return frontier, classes, members, global_report, manifest, descriptor, empty


def _rebind_empty(empty):
    material = {
        k: empty[k] for k in (
            "old_build_id", "new_build_id", "old_sha256", "new_sha256",
            "member_lineage_digest", "global_usage_report_id",
            "candidates", "rejected",
        )
    }
    empty["report_id"] = "EMPTYFIELDDECL_" + _digest(material)[:20].upper()


def _rebind_bundle(manifest, descriptor, empty):
    manifest["descriptor_report_id"] = descriptor["report_id"]
    manifest["descriptor_report_digest"] = _digest(descriptor)
    manifest["empty_report_id"] = empty["report_id"]
    manifest["empty_report_digest"] = _digest(empty)
    manifest["descriptor_summary"] = descriptor["summary"]
    manifest["empty_summary"] = empty["summary"]
    material = {k: v for k, v in manifest.items() if k != "bundle_id"}
    manifest["bundle_id"] = "V309DUAL_" + _digest(material)[:20].upper()


class V309DualBundleOfflineVerifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = _documents()

    def run_verify(self, args):
        return verify_v309_dual_bundle_offline(*args)

    def test_complete_synthetic_research_bundle_consistency_not_proof(self):
        result = self.run_verify(self.base)
        self.assertEqual(result, self.run_verify(self.base))
        self.assertEqual(
            result["state"],
            "CONSISTENCY_ONLY_NO_PRIVATE_JAR_PROOF_NO_IDENTITIES_ACCEPTED",
        )
        self.assertFalse(result["canonical"])
        self.assertEqual(result["descriptor_summary"]["still_blocked_fields"], 26)
        self.assertEqual(result["empty_summary"]["remaining_without_declaration_proof"], 68)
        self.assertEqual(result["accepted_frontier_unresolved"], 143)

    def test_changed_descriptor_payload_fails_manifest_binding(self):
        args = list(self.base)
        args[5] = copy.deepcopy(args[5])
        args[5]["note"] = "changed"
        with self.assertRaisesRegex(V309DualBundleOfflineVerifyError, "binding mismatch"):
            self.run_verify(args)

    def test_changed_empty_payload_fails_manifest_binding(self):
        args = list(self.base)
        args[6] = copy.deepcopy(args[6])
        args[6]["note"] = "changed"
        with self.assertRaisesRegex(V309DualBundleOfflineVerifyError, "binding mismatch"):
            self.run_verify(args)

    def test_forged_bundle_id_rejected(self):
        args = list(self.base)
        args[4] = copy.deepcopy(args[4])
        args[4]["bundle_id"] = "V309DUAL_FAKE"
        with self.assertRaisesRegex(V309DualBundleOfflineVerifyError, "deterministic ID"):
            self.run_verify(args)

    def test_bundle_canonical_claim_rejected_even_with_rebound_id(self):
        args = list(self.base)
        args[4] = copy.deepcopy(args[4])
        args[4]["canonical"] = True
        _rebind_bundle(args[4], args[5], args[6])
        with self.assertRaisesRegex(V309DualBundleOfflineVerifyError, "binding mismatch"):
            self.run_verify(args)

    def test_hidden_bundle_acceptance_metadata_rejected(self):
        args = list(self.base)
        args[4] = copy.deepcopy(args[4])
        args[4]["accepted_class_ids"] = ["CLIENT_CLASS_000029"]
        _rebind_bundle(args[4], args[5], args[6])
        with self.assertRaisesRegex(V309DualBundleOfflineVerifyError, "unexpected bundle metadata"):
            self.run_verify(args)

    def test_missing_empty_relationship_rejected_even_if_digests_rebound(self):
        args = list(self.base)
        args[4] = copy.deepcopy(args[4])
        args[6] = copy.deepcopy(args[6])
        args[6]["rejected"].pop()
        args[6]["summary"]["remaining_without_declaration_proof"] -= 1
        args[6]["summary"]["missing_two_sided_canonical_anchor"] -= 1
        _rebind_empty(args[6])
        _rebind_bundle(args[4], args[5], args[6])
        with self.assertRaisesRegex(V309DualBundleOfflineVerifyError, "omit source relationships"):
            self.run_verify(args)

    def test_changed_empty_relationship_owner_rejected_with_rebound_digests(self):
        args = list(self.base)
        args[4] = copy.deepcopy(args[4])
        args[6] = copy.deepcopy(args[6])
        args[6]["rejected"][0]["old_owner"] = "FAKE"
        _rebind_empty(args[6])
        _rebind_bundle(args[4], args[5], args[6])
        with self.assertRaisesRegex(V309DualBundleOfflineVerifyError, "canonical owner"):
            self.run_verify(args)

    def test_unsupported_rejection_reason_rejected_with_rebound_digests(self):
        args = list(self.base)
        args[4] = copy.deepcopy(args[4])
        args[6] = copy.deepcopy(args[6])
        args[6]["rejected"][0]["reason"] = "ACCEPTED"
        _rebind_empty(args[6])
        _rebind_bundle(args[4], args[5], args[6])
        with self.assertRaisesRegex(V309DualBundleOfflineVerifyError, "unknown empty-field rejection"):
            self.run_verify(args)

    def test_accepted_field_stays_143_even_when_synthetic_candidate_exists(self):
        args = list(self.base)
        args[4] = copy.deepcopy(args[4])
        args[6] = copy.deepcopy(args[6])
        first = args[6]["rejected"].pop()
        original = next(x for x in args[3]["review_outcomes"] if x.get("relationship_id") == first["relationship_id"])
        candidate = {
            "relationship_id": first["relationship_id"],
            "logical_class_id": first["logical_class_id"],
            "old_owner": first["old_owner"],
            "new_owner": first["new_owner"],
            "old": original["old"],
            "new": original["new"],
            "strategy": "canonical_anchor_declaration_interval_exact",
            "confidence": "INFERRED_HIGH",
            "score": 0.99,
            "supports_existing_review": True,
            "left_anchor_member_id": "CLIENT_FIELD_111111",
            "right_anchor_member_id": "CLIENT_FIELD_222222",
            "old_field_ordinal": 2,
            "new_field_ordinal": 2,
            "interval_offset": 0,
            "interval_length": 1,
            "interval_digest": "a" * 64,
            "global_source_class_topology": [],
            "global_observations": 0,
        }
        args[6]["candidates"] = [candidate]
        args[6]["summary"]["candidate_fields"] = 1
        args[6]["summary"]["remaining_without_declaration_proof"] = 67
        args[6]["summary"]["missing_two_sided_canonical_anchor"] = 67
        _rebind_empty(args[6])
        _rebind_bundle(args[4], args[5], args[6])
        result = self.run_verify(args)
        self.assertEqual(result["empty_summary"]["candidate_fields"], 1)
        self.assertEqual(result["accepted_frontier_unresolved"], 143)
        self.assertIn("NO_PRIVATE_JAR_PROOF", result["state"])


if __name__ == "__main__":
    unittest.main()
