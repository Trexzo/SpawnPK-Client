from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery.cross_version_javac_checkpoint import _stable_digest
from spk_recovery.cross_version_javac_checkpoint_delta import (
    CrossVersionJavacCheckpointDeltaError,
    build_cross_version_javac_checkpoint_delta,
    verify_cross_version_javac_checkpoint_delta,
    write_cross_version_javac_checkpoint_delta,
)
from spk_recovery.cross_version_javac_checkpoint_delta_cli import (
    _load,
    main as checkpoint_delta_main,
)
from spk_recovery.cross_version_javac_checkpoint_delta_verify_cli import (
    _load as _verify_load,
)


def _summary(
    *,
    old_total: int,
    new_total: int,
    shared: int,
    old_files: int,
    new_files: int,
    shared_files: int,
    old_categories: dict[str, int],
    new_categories: dict[str, int],
    shared_categories: dict[str, int],
    exact: bool,
) -> dict:
    old_only = old_total - shared
    new_only = new_total - shared
    old_only_categories = {
        key: old_categories.get(key, 0) - shared_categories.get(key, 0)
        for key in sorted(set(old_categories) | set(shared_categories))
        if old_categories.get(key, 0) - shared_categories.get(key, 0)
    }
    new_only_categories = {
        key: new_categories.get(key, 0) - shared_categories.get(key, 0)
        for key in sorted(set(new_categories) | set(shared_categories))
        if new_categories.get(key, 0) - shared_categories.get(key, 0)
    }
    return {
        "old_total_errors": old_total,
        "new_total_errors": new_total,
        "shared_errors": shared,
        "old_only_errors": old_only,
        "new_only_errors": new_only,
        "shared_percent_of_old": round(shared * 100.0 / old_total, 4),
        "shared_percent_of_new": round(shared * 100.0 / new_total, 4),
        "old_affected_files": old_files,
        "new_affected_files": new_files,
        "shared_affected_files": shared_files,
        "old_categories": dict(old_categories),
        "new_categories": dict(new_categories),
        "shared_categories": dict(shared_categories),
        "old_only_categories": old_only_categories,
        "new_only_categories": new_only_categories,
        "exact_frontier_equal": exact,
    }


def _build(
    *,
    tooling: str,
    build_id: str,
    authority: str,
    suffix: str,
    frontier: str,
    source_tree: str,
) -> dict:
    material = {
        "tooling_commit": tooling,
        "build_id": build_id,
        "source_authority_sha256": authority,
        "rebuild_id": "CLEANBUILD_" + suffix,
        "workspace_id": "SRCWS_" + suffix,
        "source_tree_sha256": source_tree,
        "diagnostic_report_id": "JAVACDIAG_" + suffix,
        "diagnostic_input_sha256": suffix.lower() * 3 + suffix.lower()[:4],
        "frontier_id": frontier,
        "project_binary_fallback_count": 0,
        "clean_rebuild_status": "compile_failed",
        "clean_project_build": False,
    }
    return {
        "build_id": build_id,
        "source_authority_sha256": authority,
        "binding_id": (
            "JAVACBIND_" + _stable_digest(material)[:20].upper()
        ),
        "diagnostic_report_id": material["diagnostic_report_id"],
        "diagnostic_input_sha256": material["diagnostic_input_sha256"],
        "frontier_id": frontier,
        "rebuild_id": material["rebuild_id"],
        "workspace_id": material["workspace_id"],
        "source_tree_sha256": source_tree,
        "clean_rebuild_status": "compile_failed",
        "clean_project_build": False,
        "project_binary_fallback_count": 0,
    }


def _checkpoint(
    *,
    tooling: str,
    report_suffix: str,
    old_frontier: str,
    new_frontier: str,
    old_tree: str,
    new_tree: str,
    summary: dict,
) -> dict:
    old = _build(
        tooling=tooling,
        build_id="v307",
        authority="3" * 64,
        suffix="A" * 20,
        frontier=old_frontier,
        source_tree=old_tree,
    )
    new = _build(
        tooling=tooling,
        build_id="v308",
        authority="4" * 64,
        suffix="B" * 20,
        frontier=new_frontier,
        source_tree=new_tree,
    )
    material = {
        "tooling_commit": tooling,
        "binary_backtest_id": "XVERBIN_" + "F" * 20,
        "old": old,
        "new": new,
        "comparison": {
            "report_id": "XJAVACFRONTIER_" + report_suffix,
            "summary": summary,
        },
    }
    return {
        "schema_version": 1,
        "kind": "cross_version_javac_checkpoint",
        "checkpoint_id": (
            "XJAVACCHECKPOINT_" + _stable_digest(material)[:20].upper()
        ),
        **material,
        "identifiers_included": False,
        "note": "test checkpoint",
    }


class CrossVersionJavacCheckpointDeltaTests(unittest.TestCase):
    def setUp(self):
        base_categories = {
            "cannot_find_symbol": 154,
            "incompatible_types": 45,
        }
        self.baseline = _checkpoint(
            tooling="1" * 40,
            report_suffix="C" * 20,
            old_frontier="JAVACFRONTIER_" + "D" * 20,
            new_frontier="JAVACFRONTIER_" + "D" * 20,
            old_tree="5" * 64,
            new_tree="6" * 64,
            summary=_summary(
                old_total=199,
                new_total=199,
                shared=199,
                old_files=75,
                new_files=75,
                shared_files=75,
                old_categories=base_categories,
                new_categories=base_categories,
                shared_categories=base_categories,
                exact=True,
            ),
        )
        current_categories = {
            "cannot_find_symbol": 138,
            "incompatible_types": 45,
        }
        self.current = _checkpoint(
            tooling="2" * 40,
            report_suffix="E" * 20,
            old_frontier="JAVACFRONTIER_" + "E" * 20,
            new_frontier="JAVACFRONTIER_" + "E" * 20,
            old_tree="7" * 64,
            new_tree="8" * 64,
            summary=_summary(
                old_total=183,
                new_total=183,
                shared=183,
                old_files=74,
                new_files=74,
                shared_files=74,
                old_categories=current_categories,
                new_categories=current_categories,
                shared_categories=current_categories,
                exact=True,
            ),
        )

    def test_builds_deterministic_aggregate_delta(self):
        report = build_cross_version_javac_checkpoint_delta(
            self.baseline,
            self.current,
        )
        repeat = build_cross_version_javac_checkpoint_delta(
            self.baseline,
            self.current,
        )
        self.assertEqual(report, repeat)
        self.assertRegex(
            report["delta_id"],
            r"^XJAVACCHECKDELTA_[0-9A-F]{20}$",
        )
        self.assertEqual(report["scalar_delta"]["old_total_errors"], -16)
        self.assertEqual(report["scalar_delta"]["new_total_errors"], -16)
        self.assertEqual(report["scalar_delta"]["old_affected_files"], -1)
        self.assertEqual(report["scalar_delta"]["new_affected_files"], -1)
        self.assertEqual(
            report["category_delta"]["old_categories"],
            {"cannot_find_symbol": -16},
        )
        self.assertEqual(
            report["category_delta"]["new_categories"],
            {"cannot_find_symbol": -16},
        )
        self.assertEqual(
            report["exact_frontier_equality_transition"],
            "preserved_true",
        )
        self.assertTrue(report["old_frontier_changed"])
        self.assertTrue(report["new_frontier_changed"])
        self.assertTrue(report["old_source_tree_changed"])
        self.assertTrue(report["new_source_tree_changed"])
        self.assertFalse(report["identifiers_included"])

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "delta.json"
            write_cross_version_javac_checkpoint_delta(report, path)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                report,
            )

    def test_rejects_authority_pair_drift(self):
        bad = copy.deepcopy(self.current)
        bad["old"]["source_authority_sha256"] = "9" * 64
        binding_material = {
            "tooling_commit": bad["tooling_commit"],
            "build_id": bad["old"]["build_id"],
            "source_authority_sha256": bad["old"]["source_authority_sha256"],
            "rebuild_id": bad["old"]["rebuild_id"],
            "workspace_id": bad["old"]["workspace_id"],
            "source_tree_sha256": bad["old"]["source_tree_sha256"],
            "diagnostic_report_id": bad["old"]["diagnostic_report_id"],
            "diagnostic_input_sha256": bad["old"]["diagnostic_input_sha256"],
            "frontier_id": bad["old"]["frontier_id"],
            "project_binary_fallback_count": 0,
            "clean_rebuild_status": bad["old"]["clean_rebuild_status"],
            "clean_project_build": bad["old"]["clean_project_build"],
        }
        bad["old"]["binding_id"] = (
            "JAVACBIND_" + _stable_digest(binding_material)[:20].upper()
        )
        material = {
            "tooling_commit": bad["tooling_commit"],
            "binary_backtest_id": bad["binary_backtest_id"],
            "old": bad["old"],
            "new": bad["new"],
            "comparison": bad["comparison"],
        }
        bad["checkpoint_id"] = (
            "XJAVACCHECKPOINT_" + _stable_digest(material)[:20].upper()
        )
        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointDeltaError,
            "old source_authority_sha256 changed",
        ):
            build_cross_version_javac_checkpoint_delta(
                self.baseline,
                bad,
            )

    def test_rejects_stale_checkpoint_identity(self):
        bad = copy.deepcopy(self.current)
        bad["comparison"]["report_id"] = (
            "XJAVACFRONTIER_" + "9" * 20
        )
        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointDeltaError,
            "checkpoint ID does not match public authority",
        ):
            build_cross_version_javac_checkpoint_delta(
                self.baseline,
                bad,
            )

    def test_rejects_recomputed_malformed_redacted_build(self):
        bad = copy.deepcopy(self.current)
        bad["old"]["workspace_id"] = "rs/Secret.java"
        material = {
            "tooling_commit": bad["tooling_commit"],
            "binary_backtest_id": bad["binary_backtest_id"],
            "old": bad["old"],
            "new": bad["new"],
            "comparison": bad["comparison"],
        }
        bad["checkpoint_id"] = (
            "XJAVACCHECKPOINT_" + _stable_digest(material)[:20].upper()
        )
        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointDeltaError,
            "workspace_id has invalid format",
        ):
            build_cross_version_javac_checkpoint_delta(
                self.baseline,
                bad,
            )

    def test_rejects_recomputed_false_shared_percentage(self):
        bad = copy.deepcopy(self.current)
        bad["comparison"]["summary"]["shared_percent_of_old"] = 99.0
        material = {
            "tooling_commit": bad["tooling_commit"],
            "binary_backtest_id": bad["binary_backtest_id"],
            "old": bad["old"],
            "new": bad["new"],
            "comparison": bad["comparison"],
        }
        bad["checkpoint_id"] = (
            "XJAVACCHECKPOINT_" + _stable_digest(material)[:20].upper()
        )
        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointDeltaError,
            "shared_percent_of_old is inconsistent",
        ):
            build_cross_version_javac_checkpoint_delta(
                self.baseline,
                bad,
            )

    def test_rejects_recomputed_false_exact_flag(self):
        bad = copy.deepcopy(self.current)
        bad["comparison"]["summary"]["exact_frontier_equal"] = False
        material = {
            "tooling_commit": bad["tooling_commit"],
            "binary_backtest_id": bad["binary_backtest_id"],
            "old": bad["old"],
            "new": bad["new"],
            "comparison": bad["comparison"],
        }
        bad["checkpoint_id"] = (
            "XJAVACCHECKPOINT_" + _stable_digest(material)[:20].upper()
        )
        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointDeltaError,
            "exact_frontier_equal is inconsistent",
        ):
            build_cross_version_javac_checkpoint_delta(
                self.baseline,
                bad,
            )

    def test_rejects_recomputed_category_decomposition_drift(self):
        bad = copy.deepcopy(self.current)
        bad["comparison"]["summary"]["shared_categories"][
            "cannot_find_symbol"
        ] -= 1
        bad["comparison"]["summary"]["shared_categories"]["other"] = 1
        material = {
            "tooling_commit": bad["tooling_commit"],
            "binary_backtest_id": bad["binary_backtest_id"],
            "old": bad["old"],
            "new": bad["new"],
            "comparison": bad["comparison"],
        }
        bad["checkpoint_id"] = (
            "XJAVACCHECKPOINT_" + _stable_digest(material)[:20].upper()
        )
        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointDeltaError,
            "category decomposition is inconsistent",
        ):
            build_cross_version_javac_checkpoint_delta(
                self.baseline,
                bad,
            )

    def test_reports_equality_loss_without_family_claims(self):
        changed = copy.deepcopy(self.current)
        summary = changed["comparison"]["summary"]
        summary["new_total_errors"] += 1
        summary["new_only_errors"] += 1
        summary["new_categories"]["other"] = 1
        summary["new_only_categories"]["other"] = 1
        summary["shared_percent_of_new"] = round(
            summary["shared_errors"] * 100.0 / summary["new_total_errors"],
            4,
        )
        summary["exact_frontier_equal"] = False
        material = {
            "tooling_commit": changed["tooling_commit"],
            "binary_backtest_id": changed["binary_backtest_id"],
            "old": changed["old"],
            "new": changed["new"],
            "comparison": changed["comparison"],
        }
        changed["checkpoint_id"] = (
            "XJAVACCHECKPOINT_" + _stable_digest(material)[:20].upper()
        )

        report = build_cross_version_javac_checkpoint_delta(
            self.baseline,
            changed,
        )
        self.assertEqual(
            report["exact_frontier_equality_transition"],
            "lost",
        )
        self.assertNotIn("families", report)
        self.assertIn(
            "does not identify individual diagnostic-family transitions",
            report["note"],
        )


    def test_verifier_accepts_exact_emitted_delta(self):
        report = build_cross_version_javac_checkpoint_delta(
            self.baseline,
            self.current,
        )
        verified = verify_cross_version_javac_checkpoint_delta(
            self.baseline,
            self.current,
            report,
        )
        self.assertEqual(verified, report)

    def test_verifier_rejects_mutated_emitted_delta(self):
        report = build_cross_version_javac_checkpoint_delta(
            self.baseline,
            self.current,
        )
        mutations = (
            ("delta_id", "XJAVACCHECKDELTA_" + "0" * 20),
            ("identifiers_included", True),
            ("note", "mutated"),
        )
        for key, value in mutations:
            with self.subTest(key=key):
                bad = copy.deepcopy(report)
                bad[key] = value
                with self.assertRaisesRegex(
                    CrossVersionJavacCheckpointDeltaError,
                    "does not match deterministic recomputation",
                ):
                    verify_cross_version_javac_checkpoint_delta(
                        self.baseline,
                        self.current,
                        bad,
                    )

        bad = copy.deepcopy(report)
        bad["scalar_delta"]["old_total_errors"] += 1
        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointDeltaError,
            "does not match deterministic recomputation",
        ):
            verify_cross_version_javac_checkpoint_delta(
                self.baseline,
                self.current,
                bad,
            )

        bad = copy.deepcopy(report)
        bad["category_delta"]["old_categories"]["cannot_find_symbol"] = 999
        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointDeltaError,
            "does not match deterministic recomputation",
        ):
            verify_cross_version_javac_checkpoint_delta(
                self.baseline,
                self.current,
                bad,
            )

    def test_verify_cli_loader_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "duplicate-verify.json"
            path.write_text(
                '{"delta_id":"A","delta_id":"B"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                CrossVersionJavacCheckpointDeltaError,
                "duplicate JSON key: 'delta_id'",
            ):
                _verify_load(path)

    def test_rejects_swapped_build_sides(self):
        swapped = copy.deepcopy(self.current)
        swapped["old"], swapped["new"] = swapped["new"], swapped["old"]
        material = {
            "tooling_commit": swapped["tooling_commit"],
            "binary_backtest_id": swapped["binary_backtest_id"],
            "old": swapped["old"],
            "new": swapped["new"],
            "comparison": swapped["comparison"],
        }
        swapped["checkpoint_id"] = (
            "XJAVACCHECKPOINT_" + _stable_digest(material)[:20].upper()
        )
        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointDeltaError,
            "old build_id changed across checkpoints",
        ):
            build_cross_version_javac_checkpoint_delta(
                self.baseline,
                swapped,
            )

    def test_rejects_binary_backtest_authority_drift(self):
        bad = copy.deepcopy(self.current)
        bad["binary_backtest_id"] = "XVERBIN_" + "9" * 20
        material = {
            "tooling_commit": bad["tooling_commit"],
            "binary_backtest_id": bad["binary_backtest_id"],
            "old": bad["old"],
            "new": bad["new"],
            "comparison": bad["comparison"],
        }
        bad["checkpoint_id"] = (
            "XJAVACCHECKPOINT_" + _stable_digest(material)[:20].upper()
        )
        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointDeltaError,
            "binary_backtest_id changed across checkpoints",
        ):
            build_cross_version_javac_checkpoint_delta(
                self.baseline,
                bad,
            )

    def test_identical_checkpoints_emit_zero_delta(self):
        report = build_cross_version_javac_checkpoint_delta(
            self.baseline,
            copy.deepcopy(self.baseline),
        )
        self.assertTrue(
            all(value == 0 for value in report["scalar_delta"].values())
        )
        self.assertTrue(
            all(
                not values
                for values in report["category_delta"].values()
            )
        )
        self.assertEqual(
            report["exact_frontier_equality_transition"],
            "preserved_true",
        )
        self.assertFalse(report["old_frontier_changed"])
        self.assertFalse(report["new_frontier_changed"])
        self.assertFalse(report["old_source_tree_changed"])
        self.assertFalse(report["new_source_tree_changed"])
        self.assertEqual(
            report["baseline_tooling_commit"],
            report["current_tooling_commit"],
        )

    def test_category_present_only_in_current_uses_zero_baseline(self):
        changed = copy.deepcopy(self.current)
        summary = changed["comparison"]["summary"]

        summary["old_total_errors"] += 1
        summary["new_total_errors"] += 1
        summary["shared_errors"] += 1
        summary["old_categories"]["other"] = 1
        summary["new_categories"]["other"] = 1
        summary["shared_categories"]["other"] = 1
        summary["shared_percent_of_old"] = round(
            summary["shared_errors"] * 100.0 / summary["old_total_errors"],
            4,
        )
        summary["shared_percent_of_new"] = round(
            summary["shared_errors"] * 100.0 / summary["new_total_errors"],
            4,
        )

        material = {
            "tooling_commit": changed["tooling_commit"],
            "binary_backtest_id": changed["binary_backtest_id"],
            "old": changed["old"],
            "new": changed["new"],
            "comparison": changed["comparison"],
        }
        changed["checkpoint_id"] = (
            "XJAVACCHECKPOINT_" + _stable_digest(material)[:20].upper()
        )

        report = build_cross_version_javac_checkpoint_delta(
            self.baseline,
            changed,
        )
        self.assertEqual(
            report["category_delta"]["old_categories"]["other"],
            1,
        )
        self.assertEqual(
            report["category_delta"]["new_categories"]["other"],
            1,
        )
        self.assertEqual(
            report["category_delta"]["shared_categories"]["other"],
            1,
        )


    def test_cli_loader_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "duplicate.json"
            path.write_text(
                '{"schema_version":1,"schema_version":1}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                CrossVersionJavacCheckpointDeltaError,
                "duplicate JSON key: 'schema_version'",
            ):
                _load(path)


    def test_cli_reloads_and_verifies_written_delta(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            baseline = root / "baseline.json"
            current = root / "current.json"
            out = root / "delta.json"
            baseline.write_text(
                json.dumps(self.baseline, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            current.write_text(
                json.dumps(self.current, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            with patch(
                "sys.argv",
                [
                    "spk-cross-version-javac-checkpoint-delta",
                    str(baseline),
                    str(current),
                    "--out",
                    str(out),
                ],
            ):
                self.assertEqual(checkpoint_delta_main(), 0)

            emitted = _load(out)
            expected = build_cross_version_javac_checkpoint_delta(
                self.baseline,
                self.current,
            )
            self.assertEqual(emitted, expected)

    def test_cli_fails_closed_when_written_delta_is_corrupted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            baseline = root / "baseline.json"
            current = root / "current.json"
            out = root / "delta.json"
            baseline.write_text(
                json.dumps(self.baseline, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            current.write_text(
                json.dumps(self.current, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            def corrupt_write(report, path):
                bad = copy.deepcopy(report)
                bad["delta_id"] = "XJAVACCHECKDELTA_" + "0" * 20
                path.write_text(
                    json.dumps(bad, sort_keys=True) + "\n",
                    encoding="utf-8",
                )

            with patch(
                "spk_recovery.cross_version_javac_checkpoint_delta_cli."
                "write_cross_version_javac_checkpoint_delta",
                side_effect=corrupt_write,
            ), patch(
                "sys.argv",
                [
                    "spk-cross-version-javac-checkpoint-delta",
                    str(baseline),
                    str(current),
                    "--out",
                    str(out),
                ],
            ):
                with self.assertRaises(SystemExit) as raised:
                    checkpoint_delta_main()
                self.assertEqual(raised.exception.code, 2)


    def test_rejects_recomputed_stale_binding_identity(self):
        bad = copy.deepcopy(self.current)
        bad["old"]["workspace_id"] = "SRCWS_" + "9" * 20
        material = {
            "tooling_commit": bad["tooling_commit"],
            "binary_backtest_id": bad["binary_backtest_id"],
            "old": bad["old"],
            "new": bad["new"],
            "comparison": bad["comparison"],
        }
        bad["checkpoint_id"] = (
            "XJAVACCHECKPOINT_" + _stable_digest(material)[:20].upper()
        )
        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointDeltaError,
            "old binding ID does not match public authority",
        ):
            build_cross_version_javac_checkpoint_delta(
                self.baseline,
                bad,
            )


    def test_rejects_boolean_project_binary_fallback(self):
        bad = copy.deepcopy(self.current)
        bad["old"]["project_binary_fallback_count"] = False

        binding_material = {
            "tooling_commit": bad["tooling_commit"],
            "build_id": bad["old"]["build_id"],
            "source_authority_sha256": bad["old"]["source_authority_sha256"],
            "rebuild_id": bad["old"]["rebuild_id"],
            "workspace_id": bad["old"]["workspace_id"],
            "source_tree_sha256": bad["old"]["source_tree_sha256"],
            "diagnostic_report_id": bad["old"]["diagnostic_report_id"],
            "diagnostic_input_sha256": bad["old"]["diagnostic_input_sha256"],
            "frontier_id": bad["old"]["frontier_id"],
            "project_binary_fallback_count": False,
            "clean_rebuild_status": bad["old"]["clean_rebuild_status"],
            "clean_project_build": bad["old"]["clean_project_build"],
        }
        bad["old"]["binding_id"] = (
            "JAVACBIND_" + _stable_digest(binding_material)[:20].upper()
        )

        checkpoint_material = {
            "tooling_commit": bad["tooling_commit"],
            "binary_backtest_id": bad["binary_backtest_id"],
            "old": bad["old"],
            "new": bad["new"],
            "comparison": bad["comparison"],
        }
        bad["checkpoint_id"] = (
            "XJAVACCHECKPOINT_"
            + _stable_digest(checkpoint_material)[:20].upper()
        )

        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointDeltaError,
            "project binary fallback must be integer zero",
        ):
            build_cross_version_javac_checkpoint_delta(
                self.baseline,
                bad,
            )


if __name__ == "__main__":
    unittest.main()
