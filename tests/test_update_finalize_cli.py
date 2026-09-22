from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery.cli import main


def _report(ready: bool) -> dict:
    return {
        "schema_version": 1,
        "kind": "authority_candidate_report",
        "report_id": "AUTHCAND_" + "A" * 20,
        "migration_id": "MIGRATION_" + "B" * 20,
        "build_id": "v309",
        "target_sha256": "2" * 64,
        "scope_prefix": "rs/",
        "ready_for_authority": ready,
        "summary": {
            "target_classes": 1,
            "canonical_target_classes": 1 if ready else 0,
            "class_coverage_percent": 100.0 if ready else 0.0,
            "target_fields": 0,
            "canonical_target_fields": 0,
            "target_methods": 0,
            "canonical_target_methods": 0,
            "target_members": 0,
            "canonical_target_members": 0,
            "member_coverage_percent": 100.0,
            "accepted_semantic_classes_carried": 0,
            "accepted_semantic_members_carried": 0,
            "class_parse_errors": 0,
            "blocking_unresolved_classes": 0,
            "blocking_unresolved_members": 0,
            "informational_removed_class_items": 0,
            "informational_removed_member_items": 0,
            "blocker_count": 0 if ready else 1,
        },
        "blockers": [] if ready else [
            {"kind": "missing_canonical_classes", "count": 1}
        ],
        "missing_classes": [] if ready else ["rs/a.class"],
        "stale_classes": [],
        "missing_members": [],
        "stale_members": [],
        "blocking_class_unresolved": [],
        "blocking_member_unresolved": [],
        "informational_class_removals": [],
        "informational_member_removals": [],
    }


class UpdateFinalizeCliTests(unittest.TestCase):
    def _run(self, root: Path, *, ready: bool) -> tuple[int, Path]:
        docs = {
            "classes": {"placeholder": True},
            "members": {"placeholder": True},
            "index": {"sha256": "2" * 64},
            "intake": {
                "schema_version": 1,
                "kind": "update_intake_report",
            },
        }
        paths = {}
        for name, doc in docs.items():
            path = root / f"{name}.json"
            path.write_text(json.dumps(doc), encoding="utf-8")
            paths[name] = path

        out = root / ("ready.json" if ready else "blocked.json")
        with (
            patch(
                "spk_recovery.cli.load_lineage",
                return_value={"placeholder": True},
            ),
            patch(
                "spk_recovery.cli.load_member_lineage",
                return_value={"placeholder": True},
            ),
            patch(
                "spk_recovery.cli.build_authority_candidate_report",
                return_value=_report(ready),
            ) as finalize,
        ):
            rc = main(
                [
                    "update-finalize",
                    str(paths["classes"]),
                    str(paths["members"]),
                    str(paths["index"]),
                    str(paths["intake"]),
                    "--build-id",
                    "v309",
                    "--out",
                    str(out),
                ]
            )
        finalize.assert_called_once()
        return rc, out

    def test_ready_report_returns_zero_and_is_written(self):
        with tempfile.TemporaryDirectory() as td:
            rc, out = self._run(Path(td), ready=True)
            self.assertEqual(rc, 0)
            self.assertTrue(out.is_file())
            self.assertTrue(
                json.loads(out.read_text(encoding="utf-8"))[
                    "ready_for_authority"
                ]
            )

    def test_blocked_report_returns_one_but_is_still_written(self):
        with tempfile.TemporaryDirectory() as td:
            rc, out = self._run(Path(td), ready=False)
            self.assertEqual(rc, 1)
            self.assertTrue(out.is_file())
            self.assertFalse(
                json.loads(out.read_text(encoding="utf-8"))[
                    "ready_for_authority"
                ]
            )


if __name__ == "__main__":
    unittest.main()
