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


class MemberPromotionCliTests(unittest.TestCase):
    def test_command_writes_promoted_member_lineage(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            docs = {
                "classes": {"placeholder": True},
                "members": _member_lineage(),
                "index": {"sha256": "2" * 64},
                "spec": {
                    "schema_version": 1,
                    "kind": "new_member_promotion_spec",
                    "build_id": "v309",
                    "members": [
                        {
                            "owner_logical_id": "CLIENT_CLASS_000001",
                            "kind": "field",
                            "name": "y",
                            "descriptor": "J",
                        }
                    ],
                },
            }
            paths = {}
            for name, doc in docs.items():
                path = root / f"{name}.json"
                path.write_text(json.dumps(doc), encoding="utf-8")
                paths[name] = path

            returned = _member_lineage()
            returned["members"].append(
                {
                    "member_id": "CLIENT_FIELD_000002",
                    "owner_logical_id": "CLIENT_CLASS_000001",
                    "kind": "field",
                    "semantic_name": None,
                    "semantic_status": "UNKNOWN",
                    "semantic_confidence": 0.0,
                    "lineage": [
                        {
                            "build_id": "v309",
                            "owner_internal_name": "rs/b",
                            "name": "y",
                            "descriptor": "J",
                            "access": 2,
                            "relation": "MANUAL",
                            "confidence": 1.0,
                            "provenance": [],
                        }
                    ],
                    "semantic_provenance": [],
                }
            )
            summary = {
                "members": 2,
                "fields": 2,
                "methods": 0,
                "lineage_entries": 2,
                "unresolved": 0,
                "promoted_new_members": 1,
                "promoted_new_fields": 1,
                "promoted_new_methods": 0,
                "unresolved_removed": 1,
            }

            out = root / "promoted.json"
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
                    "spk_recovery.cli.promote_new_members",
                    return_value=(returned, summary),
                ) as promote,
            ):
                rc = main(
                    [
                        "member-promote-new",
                        str(paths["classes"]),
                        str(paths["members"]),
                        str(paths["index"]),
                        str(paths["spec"]),
                        "--out",
                        str(out),
                    ]
                )

            self.assertEqual(rc, 0)
            promote.assert_called_once()
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(
                saved["members"][-1]["member_id"],
                "CLIENT_FIELD_000002",
            )


if __name__ == "__main__":
    unittest.main()
