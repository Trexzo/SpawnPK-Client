from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery.cli import main


class UpdateTransferCliTests(unittest.TestCase):
    def test_exact_class_identity_appends_new_build_relation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            lineage = {
                "schema_version": 1,
                "namespace": "spawnpk-client",
                "id_format": "CLIENT_CLASS_%06d",
                "baseline_build_id": "v308",
                "builds": [
                    {
                        "build_id": "v308",
                        "build_number": 308,
                        "sha256": "1" * 64,
                        "source_name": "old.jar",
                        "authority": "EXACT_CURRENT_CLIENT",
                    }
                ],
                "classes": [
                    {
                        "logical_id": "CLIENT_CLASS_000001",
                        "semantic_name": None,
                        "semantic_status": "UNKNOWN",
                        "semantic_confidence": 0.0,
                        "lineage": [
                            {
                                "build_id": "v308",
                                "internal_name": "rs/a",
                                "entry_path": "rs/a.class",
                                "entry_sha256": "a" * 64,
                                "structural_sha256": "b" * 64,
                                "relation": "BASELINE",
                                "confidence": 1.0,
                                "provenance": [],
                            }
                        ],
                        "semantic_provenance": [],
                    }
                ],
                "unresolved": [],
            }

            old_index = {
                "sha256": "1" * 64,
                "source_name": "old.jar",
                "entries": {
                    "rs/a.class": {"sha256": "a" * 64}
                },
                "classes": {
                    "rs/a.class": {
                        "internal_name": "rs/a",
                        "structural_sha256": "b" * 64,
                    }
                },
            }
            new_index = {
                "sha256": "2" * 64,
                "source_name": "new.jar",
                "entries": {
                    "rs/a.class": {"sha256": "a" * 64}
                },
                "classes": {
                    "rs/a.class": {
                        "internal_name": "rs/a",
                        "structural_sha256": "b" * 64,
                    }
                },
            }
            intake = {
                "schema_version": 1,
                "kind": "update_intake_report",
                "migration_id": "MIGRATION_" + "A" * 20,
                "old_build_id": "v308",
                "new_build_id": "v309",
                "old_sha256": "1" * 64,
                "new_sha256": "2" * 64,
                "scope_prefix": "rs/",
            }
            matcher = {
                "schema_version": 1,
                "old_sha256": "1" * 64,
                "new_sha256": "2" * 64,
                "scope_prefix": "rs/",
                "thresholds": {},
                "package_anchors": {},
                "summary": {
                    "old_class_count": 1,
                    "new_class_count": 1,
                    "matched": 1,
                    "exact_sha256": 1,
                    "structural_unique": 0,
                    "package_anchor": 0,
                    "weighted_mutual_best": 0,
                    "ambiguous": 0,
                    "unmatched_old": 0,
                    "unmatched_new": 0,
                },
                "matches": [
                    {
                        "old": "rs/a.class",
                        "new": "rs/a.class",
                        "strategy": "exact_sha256",
                        "score": 1.0,
                        "confidence": "EXACT",
                        "evidence": {},
                    }
                ],
                "ambiguous": [],
                "unmatched_old": [],
                "unmatched_new": [],
            }

            paths = {}
            for name, doc in (
                ("lineage", lineage),
                ("old", old_index),
                ("new", new_index),
                ("intake", intake),
            ):
                path = root / f"{name}.json"
                path.write_text(json.dumps(doc), encoding="utf-8")
                paths[name] = path

            out = root / "v309-lineage.json"
            summary_out = root / "transfer-summary.json"

            with patch(
                "spk_recovery.update_transfer.match_classes",
                return_value=matcher,
            ):
                rc = main(
                    [
                        "update-transfer-classes",
                        str(paths["lineage"]),
                        str(paths["old"]),
                        str(paths["new"]),
                        str(paths["intake"]),
                        "--old-build-id",
                        "v308",
                        "--new-build-id",
                        "v309",
                        "--new-build-number",
                        "309",
                        "--out",
                        str(out),
                        "--summary-out",
                        str(summary_out),
                    ]
                )

            self.assertEqual(rc, 0)
            result = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(len(result["builds"]), 2)
            self.assertEqual(
                result["classes"][0]["lineage"][1]["build_id"],
                "v309",
            )
            self.assertEqual(
                result["classes"][0]["lineage"][1]["relation"],
                "EXACT_HASH",
            )
            summary = json.loads(summary_out.read_text(encoding="utf-8"))
            self.assertEqual(summary["trusted_applied"], 1)
            self.assertEqual(summary["review_only_matches"], 0)


if __name__ == "__main__":
    unittest.main()
