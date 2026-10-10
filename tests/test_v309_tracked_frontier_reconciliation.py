"""R12: keep the tracked v309 canonical frontier ahead of stale private research.

This test reads only public tracked metadata; no proprietary JARs, private
research reports or remapped client sources are required in hosted CI.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest

from spk_recovery.external_field_witness_research import (
    ExternalWitnessError,
    _candidate_fields,
)

ROOT = Path(__file__).resolve().parent.parent
FRONTIER = ROOT / "research" / "v309-field-recovery"
FIELD_IDS = ("CLIENT_FIELD_002107", "CLIENT_FIELD_002108")


def _validate_frontier_sha_pin(raw: bytes, expected: str) -> str:
    """Allow only actual pinned CRLF bytes or Git's exact LF normalization.

    The frontier manifest pins hashes generated on Windows from CRLF JSON,
    while Git stores those same tracked text files with LF. Never replace
    this check with a parsed-JSON equality or an unpinned hash update.
    """
    want = expected.lower()
    if hashlib.sha256(raw).hexdigest() == want:
        return "exact_raw_bytes"
    if b"\r" in raw or not raw.endswith(b"\n"):
        raise AssertionError("FRONTIER_SHA256_MISMATCH")
    crlf = raw.replace(b"\n", b"\r\n")
    if hashlib.sha256(crlf).hexdigest() != want:
        raise AssertionError("FRONTIER_SHA256_MISMATCH")
    return "verified_git_lf_to_pinned_crlf"


class TrackedV309FieldReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frontier = json.loads((FRONTIER / "frontier.json").read_text(encoding="utf-8"))
        cls.documents = {}
        for role in ("class_lineage", "member_lineage"):
            record = cls.frontier["files"][role]
            path = ROOT / record["path"]
            raw = path.read_bytes()
            _validate_frontier_sha_pin(raw, record["sha256"])
            cls.documents[role] = json.loads(raw)
        cls.classes = cls.documents["class_lineage"]
        cls.members = cls.documents["member_lineage"]
        cls.by_class = {x["logical_id"]: x for x in cls.classes["classes"]}
        cls.by_member = {x["member_id"]: x for x in cls.members["members"]}

    def test_frontier_hash_rejects_tampered_json(self):
        # A legitimate CRLF-vs-LF Git checkout must pass, but a single
        # non-EOL byte change must still fail even after normalization.
        for role in ("class_lineage", "member_lineage"):
            with self.subTest(role=role):
                record = self.frontier["files"][role]
                raw = (ROOT / record["path"]).read_bytes()
                self.assertIn(
                    _validate_frontier_sha_pin(raw, record["sha256"]),
                    ("exact_raw_bytes", "verified_git_lf_to_pinned_crlf"),
                )
                tampered = raw.replace(b'"schema_version"', b'"schema_Version"', 1)
                self.assertNotEqual(tampered, raw)
                with self.assertRaisesRegex(AssertionError, "FRONTIER_SHA256_MISMATCH"):
                    _validate_frontier_sha_pin(tampered, record["sha256"])

    def test_tracked_authority_and_exact_client_hashes(self):
        self.assertEqual(self.frontier["state"], "ACCEPTED_INCOMPLETE")
        self.assertEqual(self.frontier["frontier"]["unresolved"], len(self.members["unresolved"]))
        self.assertEqual(self.frontier["exact_clients"]["v308_sha256"], self.classes["builds"][0]["sha256"])
        self.assertEqual(self.frontier["exact_clients"]["v309_sha256"], self.classes["builds"][1]["sha256"])
        self.assertGreaterEqual(len(self.classes["classes"]), 1129)
        self.assertGreaterEqual(len(self.members["members"]), 13811)

    def test_already_accepted_fields_are_not_unresolved(self):
        for member_id in FIELD_IDS:
            with self.subTest(member_id=member_id):
                field = self.by_member[member_id]
                self.assertEqual(field["kind"], "field")
                self.assertEqual(field["owner_logical_id"], "CLIENT_CLASS_000141")
                versions = {}
                for relation in field["lineage"]:
                    self.assertNotIn(relation["build_id"], versions)
                    versions[relation["build_id"]] = relation
                self.assertEqual(set(versions), {"v308", "v309"})
                self.assertEqual(versions["v309"]["relation"], "MANUAL")
                enclosing = self.by_class[field["owner_logical_id"]]
                for build in ("v308", "v309"):
                    entry, = [x for x in enclosing["lineage"] if x["build_id"] == build]
                    self.assertEqual(
                        versions[build]["owner_internal_name"], entry["internal_name"]
                    )
                for unresolved in self.members["unresolved"]:
                    candidate = unresolved.get("candidate", {})
                    if unresolved.get("member_kind") != "field" or not isinstance(candidate, dict):
                        continue
                    old = candidate.get("old", {})
                    if not isinstance(old, dict):
                        continue
                    self.assertFalse(
                        candidate.get("old_owner", "").removesuffix(".class")
                        == versions["v308"]["owner_internal_name"]
                        and old.get("name") == versions["v308"]["name"]
                        and old.get("descriptor") == versions["v308"]["descriptor"],
                        "ACCEPTED_FIELD_REAPPEARED_AS_UNRESOLVED",
                    )

    def test_config_owner_has_no_accepted_v309_class_relation(self):
        # Same obfuscated classfile path in both JARs is not an accepted
        # identity. These fields cannot be promoted by the external-witness
        # evaluator while the target owner is absent from canonical lineage.
        owner = self.by_class["CLIENT_CLASS_000167"]
        old_entries = [x for x in owner["lineage"] if x["build_id"] == "v308"]
        new_entries = [x for x in owner["lineage"] if x["build_id"] == "v309"]
        self.assertEqual(len(old_entries), 1)
        self.assertEqual(new_entries, [])
        path = old_entries[0]["entry_path"]
        self.assertIn(
            ("unmatched_old", path),
            {(x["kind"], x.get("candidate")) for x in self.classes["unresolved"]
             if x.get("kind") in ("unmatched_old", "unmatched_new")},
        )
        self.assertIn(
            ("unmatched_new", path),
            {(x["kind"], x.get("candidate")) for x in self.classes["unresolved"]
             if x.get("kind") in ("unmatched_old", "unmatched_new")},
        )
        for member_id in ("CLIENT_FIELD_002195", "CLIENT_FIELD_002241", "CLIENT_FIELD_002299"):
            with self.subTest(member_id=member_id):
                field = self.by_member[member_id]
                self.assertEqual(field["owner_logical_id"], "CLIENT_CLASS_000167")
                self.assertEqual({x["build_id"] for x in field["lineage"]}, {"v308"})

    def test_old_research_attempt_to_promote_accepted_field_is_refused(self):
        # Construct a stale R10/R11-style review row using canonical values;
        # the research helper must not classify an already-assigned v309
        # target as a fresh unresolved relationship.
        for member_id in FIELD_IDS:
            with self.subTest(member_id=member_id):
                rec = copy.deepcopy(self.by_member[member_id])
                old, = [x for x in rec["lineage"] if x["build_id"] == "v308"]
                new, = [x for x in rec["lineage"] if x["build_id"] == "v309"]
                stale = {
                    "kind": "member_identity_review",
                    "member_kind": "field",
                    "new_build_id": "v309",
                    "candidate": {
                        "old_owner": old["owner_internal_name"] + ".class",
                        "new_owner": new["owner_internal_name"] + ".class",
                        "old": {"name": old["name"], "descriptor": old["descriptor"]},
                        "new": {"name": new["name"], "descriptor": new["descriptor"]},
                    },
                }
                member_subset = {"members": [rec], "unresolved": [stale]}
                with self.assertRaisesRegex(ExternalWitnessError, "FIELD_ALREADY_ACCEPTED"):
                    _candidate_fields(
                        member_subset, "v308", "v309", rec["owner_logical_id"],
                        old["owner_internal_name"], new["owner_internal_name"]
                    )


if __name__ == "__main__":
    unittest.main()
