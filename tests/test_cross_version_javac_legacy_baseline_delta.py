from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from spk_recovery.cross_version_javac_legacy_baseline_delta import (
    CrossVersionJavacLegacyBaselineDeltaError,
    build_cross_version_javac_legacy_baseline_delta,
)
from spk_recovery.cross_version_javac_legacy_baseline_delta_cli import _load


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "fixtures" / (
    "v307-v308-source-m1-exact-javac-parity-07ed6f9.json"
)


def _digest(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _build(
    tooling: str,
    build_id: str,
    authority: str,
    suffix: str,
    frontier: str,
    source_tree: str,
) -> dict:
    build = {
        "build_id": build_id,
        "source_authority_sha256": authority,
        "rebuild_id": "CLEANBUILD_" + suffix,
        "workspace_id": "SRCWS_" + suffix,
        "source_tree_sha256": source_tree,
        "diagnostic_report_id": "JAVACDIAG_" + suffix,
        "diagnostic_input_sha256": hashlib.sha256(
            (build_id + suffix).encode()
        ).hexdigest(),
        "frontier_id": frontier,
        "project_binary_fallback_count": 0,
        "clean_rebuild_status": "compile_failed",
        "clean_project_build": False,
    }
    binding_material = {
        "tooling_commit": tooling,
        **build,
    }
    return {
        "binding_id": (
            "JAVACBIND_" + _digest(binding_material)[:20].upper()
        ),
        **build,
    }


def _current_checkpoint() -> dict:
    tooling = "1" * 40
    old = _build(
        tooling,
        "v307",
        "6232bae206846a4ba8d09766a2dee886"
        "b69016066a3f50f83b201bf705f93662",
        "A" * 20,
        "JAVACFRONTIER_" + "C" * 20,
        "5" * 64,
    )
    new = _build(
        tooling,
        "v308",
        "854f26ff9f134b0317572e7ac1688e6f"
        "40a231d5a4c66f8db5d655b7f45ce7c6",
        "B" * 20,
        "JAVACFRONTIER_" + "C" * 20,
        "6" * 64,
    )
    cats = {
        "bad_operand_type": 2,
        "cannot_apply_arguments": 11,
        "cannot_be_dereferenced": 42,
        "cannot_find_symbol": 138,
        "incompatible_types": 45,
        "non_static_from_static_context": 39,
        "other": 38,
        "package_does_not_exist": 9,
        "private_access": 9,
        "protected_access": 1,
    }
    summary = {
        "old_total_errors": 334,
        "new_total_errors": 334,
        "shared_errors": 334,
        "old_only_errors": 0,
        "new_only_errors": 0,
        "shared_percent_of_old": 100.0,
        "shared_percent_of_new": 100.0,
        "old_affected_files": 75,
        "new_affected_files": 75,
        "shared_affected_files": 75,
        "old_categories": cats,
        "new_categories": cats,
        "shared_categories": cats,
        "old_only_categories": {},
        "new_only_categories": {},
        "exact_frontier_equal": True,
    }
    comparison = {
        "report_id": "XJAVACFRONTIER_" + "D" * 20,
        "summary": summary,
    }
    material = {
        "tooling_commit": tooling,
        "binary_backtest_id": "XVERBIN_E56BD2FB8CCC172D6184",
        "old": old,
        "new": new,
        "comparison": comparison,
    }
    return {
        "schema_version": 1,
        "kind": "cross_version_javac_checkpoint",
        "checkpoint_id": (
            "XJAVACCHECKPOINT_" + _digest(material)[:20].upper()
        ),
        **material,
        "identifiers_included": False,
        "note": "synthetic modern checkpoint",
    }


class CrossVersionJavacLegacyBaselineDeltaTests(unittest.TestCase):
    def setUp(self):
        self.baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        self.current = _current_checkpoint()

    def test_compares_canonical_legacy_baseline_without_fabricated_checkpoint(self):
        report = build_cross_version_javac_legacy_baseline_delta(
            self.baseline,
            self.current,
        )
        repeat = build_cross_version_javac_legacy_baseline_delta(
            self.baseline,
            self.current,
        )
        self.assertEqual(report, repeat)
        self.assertRegex(
            report["delta_id"],
            r"^XJAVACLEGACYDELTA_[0-9A-F]{20}$",
        )
        self.assertEqual(
            report["baseline_fixture_id"],
            "SPK_V307_V308_EXACT_JAVAC_PARITY_07ED6F9_20261001",
        )
        self.assertNotIn("baseline_checkpoint_id", report)
        self.assertEqual(report["scalar_delta"]["old_total_errors"], -16)
        self.assertEqual(report["scalar_delta"]["new_total_errors"], -16)
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

    def test_rejects_legacy_baseline_field_shape_drift(self):
        cases = (
            (None, "source_path", "rs/Secret.java", "top-level"),
            ("bindings", "message", "private", "bindings"),
            ("comparison", "symbol", "secret", "comparison"),
            ("run_state", "location", "secret", "run_state"),
        )
        for section, key, value, label in cases:
            with self.subTest(section=section, key=key):
                bad = copy.deepcopy(self.baseline)
                target = bad if section is None else bad[section]
                target[key] = value
                with self.assertRaisesRegex(
                    CrossVersionJavacLegacyBaselineDeltaError,
                    rf"{label} does not match canonical field contract",
                ):
                    build_cross_version_javac_legacy_baseline_delta(
                        bad,
                        self.current,
                    )

    def test_rejects_missing_legacy_baseline_field(self):
        bad = copy.deepcopy(self.baseline)
        del bad["bindings"]["old_rebuild_id"]
        with self.assertRaisesRegex(
            CrossVersionJavacLegacyBaselineDeltaError,
            "bindings does not match canonical field contract",
        ):
            build_cross_version_javac_legacy_baseline_delta(
                bad,
                self.current,
            )

    def test_legacy_delta_schema_restricts_public_categories(self):
        schema = json.loads(
            (
                ROOT
                / "schemas"
                / "cross-version-javac-legacy-baseline-delta.schema.json"
            ).read_text(encoding="utf-8")
        )
        actual = set(
            schema["$defs"]["signedCategoryCounts"][
                "propertyNames"
            ]["enum"]
        )
        expected = {
            "cannot_find_symbol",
            "package_does_not_exist",
            "incompatible_types",
            "cannot_be_converted",
            "ambiguous_reference",
            "private_access",
            "protected_access",
            "cannot_apply_arguments",
            "cannot_be_dereferenced",
            "override_mismatch",
            "name_clash",
            "bad_operand_type",
            "non_static_from_static_context",
            "already_assigned",
            "other",
        }
        self.assertEqual(actual, expected)

    def test_rejects_legacy_baseline_narrative_drift(self):
        cases = (
            ("truth_boundary", "proves"),
            ("truth_boundary", "does_not_prove"),
            ("notes", None),
        )
        for section, key in cases:
            with self.subTest(section=section, key=key):
                bad = copy.deepcopy(self.baseline)
                if section == "truth_boundary":
                    bad[section][key][0] += " MUTATED"
                else:
                    bad[section][0] += " MUTATED"
                with self.assertRaisesRegex(
                    CrossVersionJavacLegacyBaselineDeltaError,
                    "complete semantic content does not match canonical authority",
                ):
                    build_cross_version_javac_legacy_baseline_delta(
                        bad,
                        self.current,
                    )

    def test_legacy_baseline_semantic_digest_ignores_object_key_order(self):
        reordered = {
            key: self.baseline[key]
            for key in reversed(list(self.baseline))
        }
        report = build_cross_version_javac_legacy_baseline_delta(
            reordered,
            self.current,
        )
        self.assertEqual(
            report["baseline_fixture_id"],
            self.baseline["fixture_id"],
        )

    def test_rejects_mutated_legacy_baseline(self):
        bad = copy.deepcopy(self.baseline)
        bad["comparison"]["old_total_errors"] = 349
        with self.assertRaisesRegex(
            CrossVersionJavacLegacyBaselineDeltaError,
            "comparison.old_total_errors does not match canonical authority",
        ):
            build_cross_version_javac_legacy_baseline_delta(
                bad,
                self.current,
            )

    def test_rejects_current_authority_pair_drift(self):
        bad = copy.deepcopy(self.current)
        bad["old"]["source_authority_sha256"] = "9" * 64
        binding_material = {
            "tooling_commit": bad["tooling_commit"],
            **{
                key: bad["old"][key]
                for key in (
                    "build_id",
                    "source_authority_sha256",
                    "rebuild_id",
                    "workspace_id",
                    "source_tree_sha256",
                    "diagnostic_report_id",
                    "diagnostic_input_sha256",
                    "frontier_id",
                    "project_binary_fallback_count",
                    "clean_rebuild_status",
                    "clean_project_build",
                )
            },
        }
        bad["old"]["binding_id"] = (
            "JAVACBIND_" + _digest(binding_material)[:20].upper()
        )
        material = {
            "tooling_commit": bad["tooling_commit"],
            "binary_backtest_id": bad["binary_backtest_id"],
            "old": bad["old"],
            "new": bad["new"],
            "comparison": bad["comparison"],
        }
        bad["checkpoint_id"] = (
            "XJAVACCHECKPOINT_" + _digest(material)[:20].upper()
        )
        with self.assertRaisesRegex(
            CrossVersionJavacLegacyBaselineDeltaError,
            "old source_authority_sha256 changed",
        ):
            build_cross_version_javac_legacy_baseline_delta(
                self.baseline,
                bad,
            )

    def test_cli_loader_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "duplicate.json"
            path.write_text(
                '{"schema_version":1,"schema_version":1}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                CrossVersionJavacLegacyBaselineDeltaError,
                "duplicate JSON key",
            ):
                _load(path)


if __name__ == "__main__":
    unittest.main()
