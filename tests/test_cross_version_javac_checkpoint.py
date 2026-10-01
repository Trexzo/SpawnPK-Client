from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from spk_recovery.cross_version_javac_checkpoint import (
    CrossVersionJavacCheckpointError,
    build_cross_version_javac_checkpoint,
    write_cross_version_javac_checkpoint,
)


def _digest(value) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _binding(
    *,
    build_id: str,
    authority: str,
    diagnostic_id: str,
    input_sha: str,
    frontier_id: str,
    tooling_commit: str,
    suffix: str,
) -> dict:
    material = {
        "tooling_commit": tooling_commit,
        "build_id": build_id,
        "source_authority_sha256": authority,
        "rebuild_id": "CLEANBUILD_" + suffix,
        "workspace_id": "SRCWS_" + suffix,
        "source_tree_sha256": (suffix.lower() * 4)[:64],
        "diagnostic_report_id": diagnostic_id,
        "diagnostic_input_sha256": input_sha,
        "frontier_id": frontier_id,
        "project_binary_fallback_count": 0,
        "clean_rebuild_status": "compile_failed",
        "clean_project_build": False,
    }
    return {
        "schema_version": 1,
        "kind": "javac_build_binding",
        "binding_id": "JAVACBIND_" + _digest(material)[:20].upper(),
        **material,
        "identifiers_included": False,
        "note": "redacted",
    }


def _comparison(
    *,
    old_diagnostic_id: str,
    new_diagnostic_id: str,
    old_input_sha: str,
    new_input_sha: str,
    old_frontier: str,
    new_frontier: str,
) -> dict:
    summary = {
        "old_total_errors": 1,
        "new_total_errors": 1,
        "shared_errors": 1,
        "old_only_errors": 0,
        "new_only_errors": 0,
        "shared_percent_of_old": 100.0,
        "shared_percent_of_new": 100.0,
        "old_affected_files": 1,
        "new_affected_files": 1,
        "shared_affected_files": 1,
        "old_categories": {"cannot_find_symbol": 1},
        "new_categories": {"cannot_find_symbol": 1},
        "shared_categories": {"cannot_find_symbol": 1},
        "old_only_categories": {},
        "new_only_categories": {},
        "exact_frontier_equal": True,
    }
    families = [
        {
            "family_id": "XJERR_000001",
            "file_id": "XJFILE_000001",
            "category": "cannot_find_symbol",
            "symbol_kind": "class",
            "symbol_shape": "identifier",
            "location_kind": "class",
            "old_count": 1,
            "new_count": 1,
            "shared_count": 1,
            "old_only_count": 0,
            "new_only_count": 0,
        }
    ]
    material = {
        "old_diagnostic_report_id": old_diagnostic_id,
        "new_diagnostic_report_id": new_diagnostic_id,
        "old_diagnostic_input_sha256": old_input_sha,
        "new_diagnostic_input_sha256": new_input_sha,
        "old_frontier_id": old_frontier,
        "new_frontier_id": new_frontier,
        "summary": summary,
        "families": families,
    }
    return {
        "schema_version": 1,
        "kind": "cross_version_javac_frontier",
        "report_id": (
            "XJAVACFRONTIER_" + _digest(material)[:20].upper()
        ),
        **material,
        "identifiers_included": False,
        "note": "redacted",
    }


def _refresh_comparison_id(report: dict) -> None:
    material = {
        "old_diagnostic_report_id": report["old_diagnostic_report_id"],
        "new_diagnostic_report_id": report["new_diagnostic_report_id"],
        "old_diagnostic_input_sha256": report[
            "old_diagnostic_input_sha256"
        ],
        "new_diagnostic_input_sha256": report[
            "new_diagnostic_input_sha256"
        ],
        "old_frontier_id": report["old_frontier_id"],
        "new_frontier_id": report["new_frontier_id"],
        "summary": report["summary"],
        "families": report["families"],
    }
    report["report_id"] = (
        "XJAVACFRONTIER_" + _digest(material)[:20].upper()
    )


def _refresh_binding_id(report: dict) -> None:
    material = {
        "tooling_commit": report["tooling_commit"],
        "build_id": report["build_id"],
        "source_authority_sha256": report["source_authority_sha256"],
        "rebuild_id": report["rebuild_id"],
        "workspace_id": report["workspace_id"],
        "source_tree_sha256": report["source_tree_sha256"],
        "diagnostic_report_id": report["diagnostic_report_id"],
        "diagnostic_input_sha256": report["diagnostic_input_sha256"],
        "frontier_id": report["frontier_id"],
        "project_binary_fallback_count": report[
            "project_binary_fallback_count"
        ],
        "clean_rebuild_status": report["clean_rebuild_status"],
        "clean_project_build": report["clean_project_build"],
    }
    report["binding_id"] = (
        "JAVACBIND_" + _digest(material)[:20].upper()
    )


class CrossVersionJavacCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tooling = "a" * 40
        self.old_diag = "JAVACDIAG_" + "A" * 20
        self.new_diag = "JAVACDIAG_" + "B" * 20
        self.old_input = "1" * 64
        self.new_input = "2" * 64
        self.frontier = "JAVACFRONTIER_" + "C" * 20

        self.old = _binding(
            build_id="v307",
            authority="3" * 64,
            diagnostic_id=self.old_diag,
            input_sha=self.old_input,
            frontier_id=self.frontier,
            tooling_commit=self.tooling,
            suffix="D" * 20,
        )
        self.new = _binding(
            build_id="v308",
            authority="4" * 64,
            diagnostic_id=self.new_diag,
            input_sha=self.new_input,
            frontier_id=self.frontier,
            tooling_commit=self.tooling,
            suffix="E" * 20,
        )
        self.comparison = _comparison(
            old_diagnostic_id=self.old_diag,
            new_diagnostic_id=self.new_diag,
            old_input_sha=self.old_input,
            new_input_sha=self.new_input,
            old_frontier=self.frontier,
            new_frontier=self.frontier,
        )

    def test_builds_deterministic_public_checkpoint(self):
        report = build_cross_version_javac_checkpoint(
            self.comparison,
            self.old,
            self.new,
            binary_backtest_id="XVERBIN_" + "F" * 20,
        )
        repeat = build_cross_version_javac_checkpoint(
            self.comparison,
            self.old,
            self.new,
            binary_backtest_id="XVERBIN_" + "F" * 20,
        )

        self.assertEqual(report, repeat)
        self.assertRegex(
            report["checkpoint_id"],
            r"^XJAVACCHECKPOINT_[0-9A-F]{20}$",
        )
        self.assertEqual(report["tooling_commit"], self.tooling)
        self.assertEqual(report["old"]["build_id"], "v307")
        self.assertEqual(report["new"]["build_id"], "v308")
        self.assertEqual(
            report["comparison"]["report_id"],
            self.comparison["report_id"],
        )
        self.assertTrue(
            report["comparison"]["summary"]["exact_frontier_equal"]
        )
        self.assertFalse(report["identifiers_included"])
        encoded = json.dumps(report, sort_keys=True)
        for forbidden in (
            "source_path",
            "\"message\"",
            "\"symbol\"",
            "\"location\"",
        ):
            self.assertNotIn(forbidden, encoded)

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "checkpoint.json"
            write_cross_version_javac_checkpoint(report, out)
            self.assertEqual(
                json.loads(out.read_text(encoding="utf-8")),
                report,
            )

    def test_rejects_tampered_binding_identity(self):
        bad = dict(self.old)
        bad["binding_id"] = "JAVACBIND_" + "0" * 20
        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointError,
            "binding ID does not match public authority",
        ):
            build_cross_version_javac_checkpoint(
                self.comparison,
                bad,
                self.new,
            )

    def test_rejects_private_family_fields(self):
        bad = json.loads(json.dumps(self.comparison))
        bad["families"][0]["source_path"] = "rs/Secret.java"

        material = {
            "old_diagnostic_report_id": bad["old_diagnostic_report_id"],
            "new_diagnostic_report_id": bad["new_diagnostic_report_id"],
            "old_diagnostic_input_sha256": (
                bad["old_diagnostic_input_sha256"]
            ),
            "new_diagnostic_input_sha256": (
                bad["new_diagnostic_input_sha256"]
            ),
            "old_frontier_id": bad["old_frontier_id"],
            "new_frontier_id": bad["new_frontier_id"],
            "summary": bad["summary"],
            "families": bad["families"],
        }
        bad["report_id"] = (
            "XJAVACFRONTIER_" + _digest(material)[:20].upper()
        )

        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointError,
            "public field contract",
        ):
            build_cross_version_javac_checkpoint(
                bad,
                self.old,
                self.new,
            )

    def test_rejects_unexpected_summary_fields(self):
        bad = json.loads(json.dumps(self.comparison))
        bad["summary"]["source_path"] = "rs/Secret.java"

        material = {
            "old_diagnostic_report_id": bad["old_diagnostic_report_id"],
            "new_diagnostic_report_id": bad["new_diagnostic_report_id"],
            "old_diagnostic_input_sha256": (
                bad["old_diagnostic_input_sha256"]
            ),
            "new_diagnostic_input_sha256": (
                bad["new_diagnostic_input_sha256"]
            ),
            "old_frontier_id": bad["old_frontier_id"],
            "new_frontier_id": bad["new_frontier_id"],
            "summary": bad["summary"],
            "families": bad["families"],
        }
        bad["report_id"] = (
            "XJAVACFRONTIER_" + _digest(material)[:20].upper()
        )

        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointError,
            "summary does not match the public field contract",
        ):
            build_cross_version_javac_checkpoint(
                bad,
                self.old,
                self.new,
            )

    def test_rejects_comparator_binding_mismatch(self):
        bad = json.loads(json.dumps(self.comparison))
        bad["old_diagnostic_input_sha256"] = "9" * 64
        material = {
            "old_diagnostic_report_id": bad["old_diagnostic_report_id"],
            "new_diagnostic_report_id": bad["new_diagnostic_report_id"],
            "old_diagnostic_input_sha256": (
                bad["old_diagnostic_input_sha256"]
            ),
            "new_diagnostic_input_sha256": (
                bad["new_diagnostic_input_sha256"]
            ),
            "old_frontier_id": bad["old_frontier_id"],
            "new_frontier_id": bad["new_frontier_id"],
            "summary": bad["summary"],
            "families": bad["families"],
        }
        bad["report_id"] = (
            "XJAVACFRONTIER_" + _digest(material)[:20].upper()
        )

        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointError,
            "binding does not match comparator diagnostic_input_sha256",
        ):
            build_cross_version_javac_checkpoint(
                bad,
                self.old,
                self.new,
            )

    def test_rejects_tooling_skew(self):
        bad = _binding(
            build_id="v308",
            authority="4" * 64,
            diagnostic_id=self.new_diag,
            input_sha=self.new_input,
            frontier_id=self.frontier,
            tooling_commit="b" * 40,
            suffix="E" * 20,
        )
        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointError,
            "recovery tooling commits differ",
        ):
            build_cross_version_javac_checkpoint(
                self.comparison,
                self.old,
                bad,
            )

    def test_rejects_tampered_redacted_comparison_identity(self):
        bad = json.loads(json.dumps(self.comparison))
        bad["summary"]["exact_frontier_equal"] = False
        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointError,
            "report ID does not match redacted authority",
        ):
            build_cross_version_javac_checkpoint(
                bad,
                self.old,
                self.new,
            )


    def test_rejects_recomputed_private_text_summary_scalar(self):
        bad = json.loads(json.dumps(self.comparison))
        bad["summary"]["old_total_errors"] = "rs/Secret.java"
        _refresh_comparison_id(bad)

        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointError,
            "old_total_errors must be a non-negative integer",
        ):
            build_cross_version_javac_checkpoint(
                bad,
                self.old,
                self.new,
            )

    def test_rejects_recomputed_private_text_category_key(self):
        bad = json.loads(json.dumps(self.comparison))
        bad["summary"]["old_categories"] = {"rs/Secret.java": 1}
        _refresh_comparison_id(bad)

        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointError,
            "category key is not public-safe",
        ):
            build_cross_version_javac_checkpoint(
                bad,
                self.old,
                self.new,
            )

    def test_rejects_recomputed_invalid_category_count(self):
        bad = json.loads(json.dumps(self.comparison))
        bad["summary"]["old_categories"] = {"cannot_find_symbol": "secret"}
        _refresh_comparison_id(bad)

        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointError,
            "must be a non-negative integer",
        ):
            build_cross_version_javac_checkpoint(
                bad,
                self.old,
                self.new,
            )

    def test_rejects_recomputed_private_workspace_identifier(self):
        bad = json.loads(json.dumps(self.old))
        bad["workspace_id"] = "rs/Secret.java"
        _refresh_binding_id(bad)

        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointError,
            "workspace_id has invalid format",
        ):
            build_cross_version_javac_checkpoint(
                self.comparison,
                bad,
                self.new,
            )

    def test_rejects_non_public_build_label(self):
        bad = _binding(
            build_id="../secret",
            authority="4" * 64,
            diagnostic_id=self.new_diag,
            input_sha=self.new_input,
            frontier_id=self.frontier,
            tooling_commit=self.tooling,
            suffix="E" * 20,
        )
        with self.assertRaisesRegex(
            CrossVersionJavacCheckpointError,
            "build_id has invalid format",
        ):
            build_cross_version_javac_checkpoint(
                self.comparison,
                self.old,
                bad,
            )


if __name__ == "__main__":
    unittest.main()
