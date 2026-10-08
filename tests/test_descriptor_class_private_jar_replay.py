from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from spk_recovery.descriptor_class_private_jar_replay import (
    ExactJarDescriptorClassReplayError,
    build_exact_jar_descriptor_class_replay,
    write_research_report_no_clobber,
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


class ExactJarDescriptorClassReplayTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.old = root / "v308.jar"
        self.new = root / "v309.jar"
        self.old.write_bytes(b"fake-old-client-for-unit-test")
        self.new.write_bytes(b"fake-new-client-for-unit-test")
        self.lineage = root / "class-lineage.json"
        self.field = root / "global-field-usage.json"
        self.frontier = root / "frontier.json"
        _write(self.lineage, {"fixture": "unmodified"})
        _write(self.field, {
            "report_id": "GLOBAL_TEST",
            "old_sha256": _hash(self.old),
            "new_sha256": _hash(self.new),
        })
        self.frontier_data = {
            "kind": "v309_recovery_frontier",
            "state": "ACCEPTED_INCOMPLETE",
            "build_id": "v309",
            "frontier": {"unresolved": 143},
            "exact_clients": {
                "v308_sha256": _hash(self.old),
                "v309_sha256": _hash(self.new),
            },
            "files": {
                "class_lineage": {"sha256": _hash(self.lineage)},
                "global_field_usage": {
                    "sha256": _hash(self.field),
                    "report_id": "GLOBAL_TEST",
                },
            },
        }
        _write(self.frontier, self.frontier_data)

    def _replay(self, **extra):
        return build_exact_jar_descriptor_class_replay(
            self.old, self.new, self.frontier, self.lineage, self.field,
        )

    def _mock_index(self, path):
        return {
            "sha256": _hash(path),
            "summary": {"class_parse_error_count": 0},
        }

    def _success_report(self):
        return {
            "canonical": False,
            "state": "NO_CLASS_OR_MEMBER_IDENTITY_ACCEPTED",
            "report_id": "RESEARCH_TEST",
            "summary": {
                "candidate_fields_blocked": 14,
                "still_blocked_fields": 12,
                "input_class_dependencies": 8,
            },
        }

    def test_local_replay_pins_all_inputs_and_writes_no_full_indexes(self):
        with patch(
            "spk_recovery.descriptor_class_private_jar_replay.index_jar",
            side_effect=self._mock_index,
        ) as mocked_index, patch(
            "spk_recovery.descriptor_class_private_jar_replay.build_descriptor_class_verified_replay",
            return_value=self._success_report(),
        ) as mocked_replay:
            actual = self._replay()
        self.assertEqual(actual["summary"]["candidate_fields_blocked"], 14)
        self.assertEqual(mocked_index.call_count, 2)
        self.assertEqual(mocked_replay.call_count, 1)
        self.assertEqual(
            sorted(p.name for p in Path(self.temp.name).iterdir()),
            sorted([
                "v308.jar", "v309.jar", "class-lineage.json",
                "global-field-usage.json", "frontier.json",
            ]),
        )

    def test_wrong_client_hash_refuses_indexing(self):
        self.new.write_bytes(b"wrong-new-client")
        with patch(
            "spk_recovery.descriptor_class_private_jar_replay.index_jar"
        ) as index:
            with self.assertRaisesRegex(
                ExactJarDescriptorClassReplayError, "v309 exact client SHA-256 mismatch",
            ):
                self._replay()
            index.assert_not_called()

    def test_lineage_file_drift_refuses_indexing(self):
        self.lineage.write_text('{"changed":true}', encoding="utf-8")
        with patch(
            "spk_recovery.descriptor_class_private_jar_replay.index_jar"
        ) as index:
            with self.assertRaisesRegex(
                ExactJarDescriptorClassReplayError, "tracked class_lineage SHA-256 differs",
            ):
                self._replay()
            index.assert_not_called()

    def test_global_report_id_must_match_pinned_frontier(self):
        self.frontier_data["files"]["global_field_usage"]["report_id"] = "WRONG"
        _write(self.frontier, self.frontier_data)
        with patch(
            "spk_recovery.descriptor_class_private_jar_replay.index_jar"
        ) as index:
            with self.assertRaisesRegex(
                ExactJarDescriptorClassReplayError, "global report build hashes or report ID",
            ):
                self._replay()
            index.assert_not_called()

    def test_indexer_parse_error_refuses_replay(self):
        def broken(path):
            index = self._mock_index(path)
            index["summary"]["class_parse_error_count"] = 1
            return index
        with patch(
            "spk_recovery.descriptor_class_private_jar_replay.index_jar",
            side_effect=broken,
        ), patch(
            "spk_recovery.descriptor_class_private_jar_replay.build_descriptor_class_verified_replay"
        ) as witness:
            with self.assertRaisesRegex(
                ExactJarDescriptorClassReplayError, "unparsed classes",
            ):
                self._replay()
            witness.assert_not_called()

    def test_index_sha_mismatch_after_preflight_fails(self):
        def mismatched(path):
            index = self._mock_index(path)
            index["sha256"] = "0" * 64
            return index
        with patch(
            "spk_recovery.descriptor_class_private_jar_replay.index_jar",
            side_effect=mismatched,
        ):
            with self.assertRaisesRegex(
                ExactJarDescriptorClassReplayError, "JAR changed between preflight",
            ):
                self._replay()

    def test_proof_must_remain_research_only(self):
        wrong = self._success_report()
        wrong["canonical"] = True
        with patch(
            "spk_recovery.descriptor_class_private_jar_replay.index_jar",
            side_effect=self._mock_index,
        ), patch(
            "spk_recovery.descriptor_class_private_jar_replay.build_descriptor_class_verified_replay",
            return_value=wrong,
        ):
            with self.assertRaisesRegex(
                ExactJarDescriptorClassReplayError, "research-only replay safety",
            ):
                self._replay()

    def test_26_8_accounting_drift_refuses_replay(self):
        wrong = self._success_report()
        wrong["summary"]["still_blocked_fields"] = 11
        with patch(
            "spk_recovery.descriptor_class_private_jar_replay.index_jar",
            side_effect=self._mock_index,
        ), patch(
            "spk_recovery.descriptor_class_private_jar_replay.build_descriptor_class_verified_replay",
            return_value=wrong,
        ):
            with self.assertRaisesRegex(
                ExactJarDescriptorClassReplayError, "accounting changed",
            ):
                self._replay()

    def test_research_output_written_once_and_does_not_contain_full_index(self):
        out = Path(self.temp.name) / "proof.json"
        report = self._success_report()
        write_research_report_no_clobber(
            report, out, (self.old, self.new, self.frontier, self.lineage, self.field),
        )
        self.assertEqual(json.loads(out.read_text(encoding="utf-8")), report)
        self.assertNotIn("classes", report)
        with self.assertRaisesRegex(
            ExactJarDescriptorClassReplayError, "already exists"
        ):
            write_research_report_no_clobber(
                report, out, (self.old, self.new, self.frontier, self.lineage, self.field),
            )

    def test_output_cannot_overwrite_pinned_frontier_or_jar(self):
        report = self._success_report()
        protected = (self.old, self.new, self.frontier, self.lineage, self.field)
        before = {str(p): p.read_bytes() for p in protected}
        for path in protected:
            with self.subTest(path=path):
                with self.assertRaisesRegex(
                    ExactJarDescriptorClassReplayError, "must not overwrite"
                ):
                    write_research_report_no_clobber(report, path, protected)
        for path in protected:
            self.assertEqual(path.read_bytes(), before[str(path)])

    def test_output_refuses_existing_symlink(self):
        out = Path(self.temp.name) / "existing.txt"
        out.write_text("keep me", encoding="utf-8")
        with self.assertRaisesRegex(
            ExactJarDescriptorClassReplayError, "already exists"
        ):
            write_research_report_no_clobber(
                self._success_report(), out, (self.frontier,),
            )
        self.assertEqual(out.read_text(encoding="utf-8"), "keep me")
