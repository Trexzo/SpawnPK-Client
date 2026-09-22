from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery.cli import main


def _member_lineage():
    return {
        "schema_version": 1,
        "kind": "member_lineage",
        "class_namespace": "spawnpk-client",
        "baseline_build_id": "v308",
        "source_sha256": "1" * 64,
        "members": [
            {
                "member_id": "CLIENT_FIELD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "field",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "owner_internal_name": "rs/a",
                        "name": "x",
                        "descriptor": "I",
                        "access": 2,
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


class UpdateMemberTransferCliTests(unittest.TestCase):
    def test_command_loads_inputs_and_writes_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            docs = {
                "classes": {"placeholder": True},
                "members": _member_lineage(),
                "old": {"sha256": "1" * 64},
                "new": {"sha256": "2" * 64},
                "candidates": {
                    "schema_version": 1,
                    "kind": "member_identity_candidates",
                },
            }
            paths = {}
            for name, doc in docs.items():
                path = root / f"{name}.json"
                path.write_text(json.dumps(doc), encoding="utf-8")
                paths[name] = path

            out = root / "members-v309.json"
            summary_out = root / "summary.json"
            returned = _member_lineage()
            summary = {
                "members": 1,
                "fields": 1,
                "methods": 0,
                "lineage_entries": 1,
                "unresolved": 0,
                "applied_member_relationships": 0,
                "review_only_relationships": 0,
                "unresolved_added": 0,
            }

            with (
                patch(
                    "spk_recovery.cli.load_lineage",
                    return_value={"placeholder": True},
                ),
                patch(
                    "spk_recovery.cli.load_member_lineage",
                    return_value=_member_lineage(),
                ),
                patch(
                    "spk_recovery.cli.transfer_member_identity_candidates",
                    return_value=(returned, summary),
                ) as transfer,
            ):
                rc = main(
                    [
                        "update-transfer-members",
                        str(paths["classes"]),
                        str(paths["members"]),
                        str(paths["old"]),
                        str(paths["new"]),
                        str(paths["candidates"]),
                        "--old-build-id",
                        "v308",
                        "--new-build-id",
                        "v309",
                        "--out",
                        str(out),
                        "--summary-out",
                        str(summary_out),
                    ]
                )

            self.assertEqual(rc, 0)
            transfer.assert_called_once()
            self.assertTrue(out.is_file())
            self.assertTrue(summary_out.is_file())
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(saved["members"][0]["member_id"], "CLIENT_FIELD_000001")


if __name__ == "__main__":
    unittest.main()
