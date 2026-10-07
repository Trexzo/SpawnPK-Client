from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery.cli import main


class ReviewedMemberIdentityCliTests(unittest.TestCase):
    def test_command_writes_revised_member_lineage(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            docs = {
                "classes": {"placeholder": True},
                "members": {
                    "schema_version": 1,
                    "kind": "member_lineage",
                    "members": [],
                    "unresolved": [],
                },
                "old": {"sha256": "1" * 64},
                "new": {"sha256": "2" * 64},
                "spec": {
                    "schema_version": 1,
                    "kind": "reviewed_member_identity_acceptance_spec",
                },
            }
            paths = {}
            for name, doc in docs.items():
                path = root / f"{name}.json"
                path.write_text(json.dumps(doc), encoding="utf-8")
                paths[name] = path

            returned = {
                "schema_version": 1,
                "kind": "member_lineage",
                "members": [],
                "unresolved": [],
            }
            summary = {
                "members": 1,
                "fields": 1,
                "methods": 0,
                "lineage_entries": 2,
                "unresolved": 0,
                "accepted_reviewed_member_identities": 1,
                "accepted_reviewed_fields": 1,
                "unresolved_removed": 1,
            }
            out = root / "accepted.json"

            with (
                patch(
                    "spk_recovery.cli.load_lineage",
                    return_value={"placeholder": True},
                ),
                patch(
                    "spk_recovery.cli.load_member_lineage",
                    return_value=docs["members"],
                ),
                patch(
                    "spk_recovery.cli.accept_reviewed_member_identities",
                    return_value=(returned, summary),
                ) as accept,
                patch("spk_recovery.cli.write_member_lineage") as write,
            ):
                rc = main(
                    [
                        "member-accept-review",
                        str(paths["classes"]),
                        str(paths["members"]),
                        str(paths["old"]),
                        str(paths["new"]),
                        str(paths["spec"]),
                        "--out",
                        str(out),
                    ]
                )

            self.assertEqual(rc, 0)
            accept.assert_called_once()
            write.assert_called_once_with(returned, out)


if __name__ == "__main__":
    unittest.main()
