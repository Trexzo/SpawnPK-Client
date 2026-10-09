from __future__ import annotations

from contextlib import ExitStack, redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import spk_recovery.v309_exact_private_concordance_replay as replay


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ExactPrivateReplayOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.old = self.root / "exact_old.jar"
        self.new = self.root / "exact_new.jar"
        self.old.write_bytes(b"synthetic old private jar")
        self.new.write_bytes(b"synthetic new private jar")
        self.exact = {
            "v308_sha256": replay.sha256_file(self.old),
            "v309_sha256": replay.sha256_file(self.new),
        }
        self.lineage = {"builds": [
            {"build_id": "v308", "sha256": self.exact["v308_sha256"]},
            {"build_id": "v309", "sha256": self.exact["v309_sha256"]},
        ], "classes": []}
        self.global_report = {
            "kind": "global_field_usage_identity_candidates",
            "report_id": "GLOBAL_EXACT",
            "canonical": False,
            "summary": {"descriptor_identity_guard_rejected": 26},
            "review_outcomes": [None] * 143,
            "old_sha256": self.exact["v308_sha256"],
            "new_sha256": self.exact["v309_sha256"],
        }
        self.lineage_path = self.root / "class-lineage.json"
        self.report_path = self.root / "global-field-usage.json"
        for path, value in (
            (self.lineage_path, self.lineage),
            (self.report_path, self.global_report),
        ):
            path.write_text(json.dumps(value), encoding="utf-8")
        self.frontier = {
            "kind": "v309_recovery_frontier",
            "state": "ACCEPTED_INCOMPLETE", "build_id": "v309",
            "frontier": {
                "unresolved": 143,
                "descriptor_identity_guard_rejected": 26,
            },
            "exact_clients": self.exact,
            "files": {
                "class_lineage": {
                    "sha256": replay.sha256_file(self.lineage_path),
                },
                "global_field_usage": {
                    "sha256": replay.sha256_file(self.report_path),
                    "report_id": self.global_report["report_id"],
                },
            },
        }
        self.frontier_path = self.root / "frontier.json"
        self.frontier_path.write_text(json.dumps(self.frontier), encoding="utf-8")
        self.struct = {
            "canonical": False,
            "state": "PINNED_STRUCTURAL_FINGERPRINTS_EXACT_MATCH_RESEARCH_ONLY",
            "summary": {"structural_hash_drifts": 0, "structural_hash_matches": 2221},
        }
        self.old_index = {
            "sha256": self.exact["v308_sha256"],
            "summary": {"class_parse_error_count": 0, "class_count": 10472},
        }
        self.new_index = {
            "sha256": self.exact["v309_sha256"],
            "summary": {"class_parse_error_count": 0, "class_count": 10502},
        }
        self.final = {
            "schema_version": 1,
            "kind": "v309_multilane_research_concordance",
            "canonical": False,
            "state": "CONCORDANCE_ONLY_NO_CLASS_OR_FIELD_ACCEPTANCE",
            "report_id": "V309CONCORDANCE_SAFE",
            "summary": {
                "descriptor_class_groups": 8,
                "blocked_field_relationships": 26,
                "supported_subset_reviewable": 0,
                "blocked_or_insufficient": 8,
                "canonical_unresolved_field_relationships": 143,
                "canonical_class_identities_accepted": 0,
                "canonical_field_identities_accepted": 0,
            },
            "rows": [],
        }

    def args(self, out=None):
        return [
            "--v308-jar", str(self.old),
            "--v309-jar", str(self.new),
            "--frontier", str(self.frontier_path),
            "--class-lineage", str(self.lineage_path),
            "--global-report", str(self.report_path),
            "--out", str(out if out is not None else self.root / "new.json"),
        ]

    def mocks(self, stack):
        stack.enter_context(patch.object(replay, "validate_lineage"))
        calls = {}
        calls["structural"] = stack.enter_context(
            patch.object(replay, "build_v309_pinned_structural_audit",
                         return_value=self.struct))
        calls["index"] = stack.enter_context(
            patch.object(replay, "index_jar",
                         side_effect=[self.old_index, self.new_index]))
        calls["literal"] = stack.enter_context(
            patch.object(replay, "build_v309_changed_class_literal_witness",
                         return_value={"kind": "literal"}))
        calls["shape"] = stack.enter_context(
            patch.object(replay, "build_v309_changed_class_method_shape_witness",
                         return_value={"kind": "shape"}))
        calls["cp_pair"] = stack.enter_context(
            patch.object(replay, "build_v309_cp_method_research",
                         return_value={"kind": "cp_pair"}))
        calls["cp_rivals"] = stack.enter_context(
            patch.object(replay, "build_v309_cp_rival_witness",
                         return_value={"kind": "cp_rivals"}))
        calls["join"] = stack.enter_context(
            patch.object(replay, "build_v309_multilane_concordance",
                         return_value=self.final))
        return calls

    def test_one_pass_emits_only_one_aggregate_report(self):
        before = [p.name for p in self.root.iterdir()]
        buf = io.StringIO()
        with ExitStack() as stack:
            calls = self.mocks(stack)
            with redirect_stdout(buf):
                code = replay.main(self.args())
        self.assertEqual(code, 0, buf.getvalue())
        self.assertIn("PASS_RESEARCH_ONLY", buf.getvalue())
        self.assertIn("no_canonical_changes=True", buf.getvalue())
        self.assertEqual(calls["structural"].call_count, 1)
        self.assertEqual(calls["index"].call_count, 2)
        self.assertEqual(calls["literal"].call_count, 1)
        self.assertEqual(calls["shape"].call_count, 1)
        self.assertEqual(calls["cp_pair"].call_count, 1)
        self.assertEqual(calls["cp_rivals"].call_count, 1)
        self.assertEqual(calls["join"].call_count, 1)
        created = set(p.name for p in self.root.iterdir()) - set(before)
        self.assertEqual(created, {"new.json"})
        public = (self.root / "new.json").read_text(encoding="utf-8")
        self.assertIn("V309CONCORDANCE_SAFE", public)
        self.assertNotIn("synthetic old private jar", public)
        self.assertNotIn("synthetic new private jar", public)

    def test_second_run_cannot_clobber_prior_result(self):
        target = self.root / "new.json"
        target.write_text("PRIOR_REPORT", encoding="utf-8")
        with ExitStack() as stack:
            calls = self.mocks(stack)
            with redirect_stdout(io.StringIO()) as buf:
                code = replay.main(self.args(target))
        self.assertEqual(code, 1)
        self.assertEqual(target.read_text(), "PRIOR_REPORT")
        self.assertEqual(calls["structural"].call_count, 0)

    def test_output_cannot_overwrite_protected_jars_or_frontier(self):
        for protected in (self.old, self.new, self.frontier_path,
                          self.lineage_path, self.report_path):
            with self.subTest(path=protected.name):
                with redirect_stdout(io.StringIO()) as buf:
                    code = replay.main(self.args(protected))
                self.assertEqual(code, 1)
                self.assertIn("FAIL_CLOSED", buf.getvalue())
                self.assertNotIn("synthetic old private jar", buf.getvalue())

    def test_mismatched_jar_sha_refuses_before_any_builder(self):
        self.new.write_bytes(b"tampered")
        with ExitStack() as stack:
            calls = self.mocks(stack)
            with redirect_stdout(io.StringIO()) as buf:
                code = replay.main(self.args())
        self.assertEqual(code, 1)
        self.assertEqual(calls["structural"].call_count, 0)
        self.assertFalse((self.root / "new.json").exists())

    def test_structural_drift_stops_before_public_indexing(self):
        self.struct["summary"]["structural_hash_drifts"] = 1
        with ExitStack() as stack:
            calls = self.mocks(stack)
            with redirect_stdout(io.StringIO()) as buf:
                code = replay.main(self.args())
        self.assertEqual(code, 1)
        self.assertEqual(calls["structural"].call_count, 1)
        self.assertEqual(calls["index"].call_count, 0)
        self.assertFalse((self.root / "new.json").exists())

    def test_private_error_messages_are_never_echoed(self):
        with ExitStack() as stack:
            calls = self.mocks(stack)
            calls["literal"].side_effect = ValueError(
                "PRIVATE_CLASS_NAME=rs/secret PRIVATE_LITERAL=something")
            with redirect_stdout(io.StringIO()) as buf:
                code = replay.main(self.args())
        self.assertEqual(code, 1)
        out = buf.getvalue()
        self.assertIn("FAIL_CLOSED", out)
        self.assertIn("error_category=ValueError", out)
        self.assertNotIn("PRIVATE_CLASS_NAME", out)
        self.assertNotIn("PRIVATE_LITERAL", out)
        self.assertFalse((self.root / "new.json").exists())

    def test_bogus_accepted_class_identity_fails_before_write(self):
        self.final["summary"]["canonical_class_identities_accepted"] = 1
        with ExitStack() as stack:
            self.mocks(stack)
            with redirect_stdout(io.StringIO()) as buf:
                code = replay.main(self.args())
        self.assertEqual(code, 1)
        self.assertFalse((self.root / "new.json").exists())

    def test_pinned_report_file_sha_mismatch_fails_closed(self):
        self.report_path.write_text("{}", encoding="utf-8")
        with ExitStack() as stack:
            calls = self.mocks(stack)
            with redirect_stdout(io.StringIO()) as buf:
                code = replay.main(self.args())
        self.assertEqual(code, 1)
        self.assertEqual(calls["structural"].call_count, 0)


if __name__ == "__main__":
    unittest.main()
