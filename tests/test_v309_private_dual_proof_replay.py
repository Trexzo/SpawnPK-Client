from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery.v309_private_dual_proof_replay import (
    V309DualProofReplayError,
    build_v309_dual_proof_replay,
    write_v309_dual_proof_bundle,
)


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dump(path, document):
    path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")


class V309PrivateDualProofReplayTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.old = self.root / "v308.jar"
        self.new = self.root / "v309.jar"
        self.old.write_bytes(b"exact-v308-unit-test-only")
        self.new.write_bytes(b"exact-v309-unit-test-only")
        self.cls = self.root / "class-lineage.json"
        self.member = self.root / "member-lineage.json"
        self.global_report = self.root / "global-field-usage.json"
        self.frontier = self.root / "frontier.json"
        _dump(self.cls, {"classes": [], "builds": []})
        _dump(self.member, {"members": []})
        _dump(self.global_report, {
            "kind": "global_field_usage_identity_candidates",
            "canonical": False,
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": _hash(self.old),
            "new_sha256": _hash(self.new),
            "report_id": "GLOBAL_TEST",
            "summary": {
                "empty_both": 68,
                "descriptor_identity_guard_rejected": 26,
            },
            "review_outcomes": [{} for _ in range(143)],
        })
        self.frontier_data = {
            "kind": "v309_recovery_frontier",
            "state": "ACCEPTED_INCOMPLETE",
            "build_id": "v309",
            "frontier": {
                "unresolved": 143,
                "descriptor_identity_guard_rejected": 26,
                "empty_both": 68,
            },
            "exact_clients": {
                "v308_sha256": _hash(self.old),
                "v309_sha256": _hash(self.new),
            },
            "files": {
                "class_lineage": {"sha256": _hash(self.cls)},
                "member_lineage": {"sha256": _hash(self.member)},
                "global_field_usage": {
                    "sha256": _hash(self.global_report),
                    "report_id": "GLOBAL_TEST",
                },
            },
        }
        _dump(self.frontier, self.frontier_data)

    def _inputs(self):
        return (self.old, self.new, self.frontier, self.cls, self.member, self.global_report)

    def _index(self, jar):
        return {"sha256": _hash(jar), "summary": {"class_parse_error_count": 0}}

    def _descriptor(self):
        return {
            "canonical": False,
            "state": "NO_CLASS_OR_MEMBER_IDENTITY_ACCEPTED",
            "report_id": "D_TEST",
            "summary": {
                "input_class_dependencies": 8,
                "candidate_fields_blocked": 0,
                "still_blocked_fields": 26,
            },
        }

    def _empty(self):
        return {
            "canonical": False,
            "kind": "empty_field_declaration_identity_candidates",
            "report_id": "E_TEST",
            "global_usage_report_id": "GLOBAL_TEST",
            "old_sha256": _hash(self.old),
            "new_sha256": _hash(self.new),
            "summary": {
                "input_empty_both_reviews": 68,
                "candidate_fields": 0,
                "remaining_without_declaration_proof": 68,
            },
        }

    def _run(self, descriptor=None, empty=None, indexer=None):
        descriptor = self._descriptor() if descriptor is None else descriptor
        empty = self._empty() if empty is None else empty
        with patch(
            "spk_recovery.v309_private_dual_proof_replay.index_jar",
            side_effect=indexer or self._index,
        ) as indexed, patch(
            "spk_recovery.v309_private_dual_proof_replay.build_descriptor_class_verified_replay",
            return_value=descriptor,
        ) as d, patch(
            "spk_recovery.v309_private_dual_proof_replay.build_empty_field_declaration_evidence",
            return_value=empty,
        ) as e:
            result = build_v309_dual_proof_replay(*self._inputs())
        return result, indexed, d, e

    def test_both_lanes_share_exactly_two_in_memory_indexes(self):
        reports, idx, d, e = self._run()
        self.assertEqual(idx.call_count, 2)
        self.assertEqual(d.call_count, 1)
        self.assertEqual(e.call_count, 1)
        descriptor_args = d.call_args.args
        empty_args = e.call_args.args
        self.assertIs(descriptor_args[2], empty_args[2])
        self.assertIs(descriptor_args[3], empty_args[3])
        self.assertFalse(reports["manifest"]["canonical"])
        self.assertEqual(reports["manifest"]["unresolved_accepted_frontier"], 143)
        self.assertEqual(reports["manifest"]["state"], "BOTH_LANES_RESEARCH_ONLY_NO_IDENTITIES_ACCEPTED")
        self.assertEqual(reports["manifest"]["empty_summary"]["input_empty_both_reviews"], 68)

    def test_reject_modified_member_lineage_before_index(self):
        self.member.write_text('{"tampered": true}', encoding="utf-8")
        with patch(
            "spk_recovery.v309_private_dual_proof_replay.index_jar",
        ) as mocked_index:
            with self.assertRaisesRegex(V309DualProofReplayError, "member_lineage"):
                build_v309_dual_proof_replay(*self._inputs())
            mocked_index.assert_not_called()

    def test_reject_wrong_exact_jar_before_index(self):
        self.new.write_bytes(b"altered-v309")
        with patch("spk_recovery.v309_private_dual_proof_replay.index_jar") as idx:
            with self.assertRaisesRegex(V309DualProofReplayError, "v309 exact client"):
                build_v309_dual_proof_replay(*self._inputs())
            idx.assert_not_called()

    def test_reject_unparsed_class(self):
        def parse_fail(jar):
            result = self._index(jar)
            result["summary"]["class_parse_error_count"] = 1
            return result
        with self.assertRaisesRegex(V309DualProofReplayError, "unparsed classes"):
            self._run(indexer=parse_fail)

    def test_reject_jar_digest_changed_during_index(self):
        def wrong(jar):
            result = self._index(jar)
            result["sha256"] = "0" * 64
            return result
        with self.assertRaisesRegex(V309DualProofReplayError, "changed during indexing"):
            self._run(indexer=wrong)

    def test_reject_forged_empty_both_candidate_accounting(self):
        bad = self._empty()
        bad["summary"]["candidate_fields"] = 1
        with self.assertRaisesRegex(V309DualProofReplayError, "accounting drift"):
            self._run(empty=bad)

    def test_reject_canonical_class_report(self):
        bad = self._descriptor()
        bad["canonical"] = True
        with self.assertRaisesRegex(V309DualProofReplayError, "accounting drift"):
            self._run(descriptor=bad)

    def test_exclusive_three_file_bundle_has_no_index(self):
        reports, _, _, _ = self._run()
        out = self.root / "private-output"
        write_v309_dual_proof_bundle(reports, out, self._inputs())
        self.assertEqual(sorted(p.name for p in out.iterdir()), [
            "BUNDLE.json", "descriptor-class-research.json",
            "empty-field-declaration-research.json",
        ])
        manifest = json.loads((out / "BUNDLE.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest, reports["manifest"])
        self.assertNotIn("classes", manifest)
        with self.assertRaises(FileExistsError):
            write_v309_dual_proof_bundle(reports, out, self._inputs())

    def test_cannot_overwrite_protected_input_parent_directory(self):
        reports, _, _, _ = self._run()
        with self.assertRaisesRegex(V309DualProofReplayError, "overlaps pinned"):
            write_v309_dual_proof_bundle(reports, self.root, self._inputs())
        self.assertTrue(self.old.is_file())
        self.assertTrue(self.member.is_file())

    def test_output_write_failure_removes_new_directory_only(self):
        reports, _, _, _ = self._run()
        out = self.root / "failed-output"
        with patch(
            "spk_recovery.v309_private_dual_proof_replay.write_research_report_no_clobber",
            side_effect=OSError("failed research output"),
        ):
            with self.assertRaisesRegex(OSError, "failed research output"):
                write_v309_dual_proof_bundle(reports, out, self._inputs())
        self.assertFalse(out.exists())
        self.assertTrue(self.old.is_file())


if __name__ == "__main__":
    unittest.main()
