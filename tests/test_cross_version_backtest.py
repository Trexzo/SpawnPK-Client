import copy
from pathlib import Path
import tempfile
import unittest

from spk_recovery.cross_version_backtest import (
    CrossVersionBacktestError,
    build_cross_version_backtest,
)
from spk_recovery.cross_version_backtest_cli import (
    _load as _backtest_load,
)


OLD_SHA = "3" * 64
NEW_SHA = "4" * 64
OLD_TREE = "5" * 64
NEW_TREE = "6" * 64


def _release(build, sha, namespace, release_id):
    source_tree = OLD_TREE if build == "v307" else NEW_TREE
    return {
        "schema_version": 1,
        "kind": "recovery_release_manifest",
        "release_id": release_id,
        "build_id": build,
        "authority_sha256": sha,
        "final_source_tree_sha256": source_tree,
        "namespace_id": namespace,
        "ready_for_release": True,
        "blockers": [],
    }


def _intake():
    return {
        "schema_version": 1,
        "kind": "update_intake_report",
        "migration_id": "MIGRATION_TEST",
        "old_build_id": "v307",
        "new_build_id": "v308",
        "old_sha256": OLD_SHA,
        "new_sha256": NEW_SHA,
        "summary": {
            "old_scope_classes": 100,
            "new_scope_classes": 100,
            "matched_classes": 100,
            "class_identity_reuse_percent": 100.0,
            "changed_same_path_classes": 1,
            "analysis_queue_items": 0,
            "ambiguous_classes": 0,
            "unmatched_old_classes": 0,
            "unmatched_new_classes": 0,
        },
        "changed_same_path_classes": ["rs/f/a.class"],
        "classifications": {
            "byte_identical_same_path": 99,
            "structurally_equivalent_same_path": 1,
        },
        "class_delta_report": {
            "summary": {
                "byte_identical": 99,
                "structurally_equivalent": 1,
                "matched_classes": 100,
                "path_moved": 0,
                "ambiguous_classes": 0,
                "unmatched_old_classes": 0,
                "unmatched_new_classes": 0,
            }
        },
    }


def _semantic():
    return {
        "schema_version": 1,
        "kind": "semantic_carryforward_report",
        "report_id": "SEMCARRY_TEST",
        "old_build_id": "v307",
        "new_build_id": "v308",
        "old_sha256": OLD_SHA,
        "new_sha256": NEW_SHA,
        "namespace_id": "SEMNS_NEW",
        "ready_for_readable_build": True,
        "summary": {
            "accepted_carried": 10,
            "accepted_blocked_missing_new_identity": 0,
        },
    }


def _source_names():
    return {
        "schema_version": 1,
        "kind": "source_name_carryforward_report",
        "report_id": "SRCNAMECARRY_TEST",
        "old_build_id": "v307",
        "new_build_id": "v308",
        "old_source_authority_sha256": OLD_SHA,
        "new_source_authority_sha256": NEW_SHA,
        "full_carryforward_ready": True,
        "blocked": [],
    }


def _binary_delta():
    return {
        "schema_version": 1,
        "kind": "cross_version_binary_delta",
        "report_id": "XVERBIN_TEST",
        "old_build_id": "v307",
        "new_build_id": "v308",
        "old_sha256": OLD_SHA,
        "new_sha256": NEW_SHA,
        "summary": {
            "old_entry_count": 1000,
            "new_entry_count": 1000,
            "old_only_entries": 0,
            "new_only_entries": 0,
            "changed_entries": 1,
            "changed_class_entries": 1,
        },
        "old_only": [],
        "new_only": [],
        "changed": [
            {
                "path": "rs/f/a.class",
                "class_entry": True,
            }
        ],
    }


class CrossVersionBacktestTests(unittest.TestCase):
    def test_pass_is_deterministic(self):
        args = (
            _release("v307", OLD_SHA, "SEMNS_OLD", "RECOVERY_OLD"),
            _release("v308", NEW_SHA, "SEMNS_NEW", "RECOVERY_NEW"),
            _intake(),
            _semantic(),
        )
        expectations = {
            "matched_classes": 100,
            "changed_same_path_classes": 1,
            "analysis_queue_items": 0,
            "changed_same_path_class_paths": ["rs/f/a.class"],
            "classifications": {
                "byte_identical_same_path": 99,
                "structurally_equivalent_same_path": 1,
            },
            "class_delta_summary": {
                "byte_identical": 99,
                "structurally_equivalent": 1,
                "matched_classes": 100,
                "path_moved": 0,
                "ambiguous_classes": 0,
                "unmatched_old_classes": 0,
                "unmatched_new_classes": 0,
            },
            "binary_report_id": "XVERBIN_TEST",
            "binary_summary": {
                "old_entry_count": 1000,
                "new_entry_count": 1000,
                "old_only_entries": 0,
                "new_only_entries": 0,
                "changed_entries": 1,
                "changed_class_entries": 1,
            },
            "changed_entry_paths": ["rs/f/a.class"],
        }
        a = build_cross_version_backtest(
            *args,
            source_name_carryforward=_source_names(),
            binary_delta=_binary_delta(),
            expectations=expectations,
        )
        b = build_cross_version_backtest(
            *copy.deepcopy(args),
            source_name_carryforward=copy.deepcopy(_source_names()),
            binary_delta=copy.deepcopy(_binary_delta()),
            expectations=copy.deepcopy(expectations),
        )
        self.assertEqual(a, b)
        self.assertTrue(a["passed"])
        self.assertEqual(a["failed_required_check_count"], 0)
        self.assertEqual(a["old_source_tree_sha256"], OLD_TREE)
        self.assertEqual(a["new_source_tree_sha256"], NEW_TREE)
        self.assertEqual(a["binary_delta_id"], "XVERBIN_TEST")
        self.assertTrue(a["backtest_id"].startswith("XVER_"))

    def test_blocked_release_fails_closed(self):
        old = _release(
            "v307", OLD_SHA, "SEMNS_OLD", "RECOVERY_OLD"
        )
        old["ready_for_release"] = False
        report = build_cross_version_backtest(
            old,
            _release(
                "v308", NEW_SHA, "SEMNS_NEW", "RECOVERY_NEW"
            ),
            _intake(),
            _semantic(),
        )
        self.assertFalse(report["passed"])
        failed = {
            row["name"]
            for row in report["checks"]
            if not row["passed"]
        }
        self.assertIn("old_release.ready_for_release", failed)

    def test_mixed_authority_pair_fails(self):
        semantic = _semantic()
        semantic["new_sha256"] = "9" * 64
        report = build_cross_version_backtest(
            _release(
                "v307", OLD_SHA, "SEMNS_OLD", "RECOVERY_OLD"
            ),
            _release(
                "v308", NEW_SHA, "SEMNS_NEW", "RECOVERY_NEW"
            ),
            _intake(),
            semantic,
        )
        self.assertFalse(report["passed"])
        self.assertEqual(
            [
                row["name"]
                for row in report["checks"]
                if not row["passed"]
            ],
            ["semantic.new.sha256"],
        )

    def test_namespace_drift_fails(self):
        semantic = _semantic()
        semantic["namespace_id"] = "SEMNS_WRONG"
        report = build_cross_version_backtest(
            _release(
                "v307", OLD_SHA, "SEMNS_OLD", "RECOVERY_OLD"
            ),
            _release(
                "v308", NEW_SHA, "SEMNS_NEW", "RECOVERY_NEW"
            ),
            _intake(),
            semantic,
        )
        self.assertFalse(report["passed"])
        self.assertIn(
            "semantic.namespace_matches_new_release",
            {
                row["name"]
                for row in report["checks"]
                if not row["passed"]
            },
        )

    def test_expectation_drift_fails(self):
        report = build_cross_version_backtest(
            _release(
                "v307", OLD_SHA, "SEMNS_OLD", "RECOVERY_OLD"
            ),
            _release(
                "v308", NEW_SHA, "SEMNS_NEW", "RECOVERY_NEW"
            ),
            _intake(),
            _semantic(),
            expectations={"changed_same_path_classes": 2},
        )
        self.assertFalse(report["passed"])
        self.assertEqual(
            report["failed_required_check_count"],
            1,
        )

    def test_changed_path_drift_fails(self):
        report = build_cross_version_backtest(
            _release(
                "v307", OLD_SHA, "SEMNS_OLD", "RECOVERY_OLD"
            ),
            _release(
                "v308", NEW_SHA, "SEMNS_NEW", "RECOVERY_NEW"
            ),
            _intake(),
            _semantic(),
            expectations={
                "changed_same_path_class_paths": ["rs/x/y.class"]
            },
        )
        self.assertFalse(report["passed"])
        self.assertIn(
            "expectation.changed_same_path_class_paths",
            {
                row["name"]
                for row in report["checks"]
                if not row["passed"]
            },
        )

    def test_source_name_pair_is_required_when_supplied(self):
        source_names = _source_names()
        source_names["full_carryforward_ready"] = False
        report = build_cross_version_backtest(
            _release(
                "v307", OLD_SHA, "SEMNS_OLD", "RECOVERY_OLD"
            ),
            _release(
                "v308", NEW_SHA, "SEMNS_NEW", "RECOVERY_NEW"
            ),
            _intake(),
            _semantic(),
            source_name_carryforward=source_names,
        )
        self.assertFalse(report["passed"])
        self.assertIn(
            "source_names.full_carryforward_ready",
            {
                row["name"]
                for row in report["checks"]
                if not row["passed"]
            },
        )

    def test_binary_report_id_expectation_drift_fails(self):
        report = build_cross_version_backtest(
            _release(
                "v307", OLD_SHA, "SEMNS_OLD", "RECOVERY_OLD"
            ),
            _release(
                "v308", NEW_SHA, "SEMNS_NEW", "RECOVERY_NEW"
            ),
            _intake(),
            _semantic(),
            binary_delta=_binary_delta(),
            expectations={"binary_report_id": "XVERBIN_WRONG"},
        )
        self.assertFalse(report["passed"])
        self.assertIn(
            "expectation.binary_report_id",
            {
                row["name"]
                for row in report["checks"]
                if not row["passed"]
            },
        )

    def test_binary_authority_pair_drift_fails(self):
        binary = _binary_delta()
        binary["new_sha256"] = "9" * 64
        report = build_cross_version_backtest(
            _release(
                "v307", OLD_SHA, "SEMNS_OLD", "RECOVERY_OLD"
            ),
            _release(
                "v308", NEW_SHA, "SEMNS_NEW", "RECOVERY_NEW"
            ),
            _intake(),
            _semantic(),
            binary_delta=binary,
        )
        self.assertFalse(report["passed"])
        self.assertIn(
            "binary.new_sha256",
            {
                row["name"]
                for row in report["checks"]
                if not row["passed"]
            },
        )

    def test_binary_expectation_requires_binary_report(self):
        with self.assertRaises(CrossVersionBacktestError):
            build_cross_version_backtest(
                _release(
                    "v307", OLD_SHA, "SEMNS_OLD", "RECOVERY_OLD"
                ),
                _release(
                    "v308", NEW_SHA, "SEMNS_NEW", "RECOVERY_NEW"
                ),
                _intake(),
                _semantic(),
                expectations={
                    "changed_entry_paths": ["rs/f/a.class"]
                },
            )

    def test_same_build_pair_is_rejected(self):
        with self.assertRaises(CrossVersionBacktestError):
            build_cross_version_backtest(
                _release(
                    "v308", OLD_SHA, "SEMNS_OLD", "RECOVERY_OLD"
                ),
                _release(
                    "v308", NEW_SHA, "SEMNS_NEW", "RECOVERY_NEW"
                ),
                _intake(),
                _semantic(),
            )

    def test_unknown_expectation_is_rejected(self):
        with self.assertRaises(CrossVersionBacktestError):
            build_cross_version_backtest(
                _release(
                    "v307", OLD_SHA, "SEMNS_OLD", "RECOVERY_OLD"
                ),
                _release(
                    "v308", NEW_SHA, "SEMNS_NEW", "RECOVERY_NEW"
                ),
                _intake(),
                _semantic(),
                expectations={"invented_metric": 1},
            )


    def test_cli_loader_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "duplicate.json"
            path.write_text(
                '{"kind":"a","kind":"b"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                CrossVersionBacktestError,
                "duplicate JSON key: 'kind'",
            ):
                _backtest_load(path)


if __name__ == "__main__":
    unittest.main()
