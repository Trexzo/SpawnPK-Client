from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from spk_recovery.dependency_reverse_transport_plan import (
    build_dependency_reverse_transport_plan,
)


class DependencyReverseTransportPlanTests(unittest.TestCase):
    def _docs(self):
        remap = {
            "schema_version": 1,
            "kind": "dependency_structural_remap_proof",
            "dependency_remap_proof_id": "DEPREMAP_" + "A" * 20,
            "reference_surface_id": "DEPREF_" + "B" * 20,
            "bundled_jar_sha256": "1" * 64,
            "member_results": [
                {
                    "status": "accepted_remap",
                    "old_owner": "old/A",
                    "old_name": "<init>",
                    "old_descriptor": "()V",
                    "new_owner": "new/A",
                    "new_name": "<init>",
                    "new_descriptor": "()V",
                },
                {
                    "status": "accepted_remap",
                    "old_owner": "old/A",
                    "old_name": "x",
                    "old_descriptor": "()V",
                    "new_owner": "new/A",
                    "new_name": "run",
                    "new_descriptor": "()V",
                },
                {
                    "status": "accepted_remap",
                    "old_owner": "old/A",
                    "old_name": "value",
                    "old_descriptor": "Lold/T;",
                    "new_owner": "new/A",
                    "new_name": "value",
                    "new_descriptor": "Lnew/T;",
                },
                {
                    "status": "accepted_identity",
                    "old_owner": "same/S",
                    "old_name": "id",
                    "old_descriptor": "I",
                    "new_owner": "same/S",
                    "new_name": "id",
                    "new_descriptor": "I",
                },
                {
                    "status": "accepted_identity",
                    "old_owner": "residual/R",
                    "old_name": "ok",
                    "old_descriptor": "()V",
                    "new_owner": "residual/R",
                    "new_name": "ok",
                    "new_descriptor": "()V",
                },
            ],
        }
        replacement = {
            "schema_version": 1,
            "kind": "dependency_replacement_boundary_plan",
            "replacement_plan_id": "DEPREPLACE_" + "C" * 20,
            "dependency_remap_proof_id": remap[
                "dependency_remap_proof_id"
            ],
            "bundled_jar_sha256": remap[
                "bundled_jar_sha256"
            ],
            "owners": [
                {
                    "owner_id": "DEPOWNER_00001",
                    "classification": "official_replaceable",
                    "old_owner": "old/A",
                    "new_owner": "new/A",
                },
                {
                    "owner_id": "DEPOWNER_00002",
                    "classification": "official_replaceable",
                    "old_owner": "same/S",
                    "new_owner": "same/S",
                },
                {
                    "owner_id": "DEPOWNER_00003",
                    "classification": "residual_bundled",
                    "old_owner": "residual/R",
                    "new_owner": None,
                },
            ],
            "identifiers_included": True,
        }
        return remap, replacement

    def _write(
        self,
        root: Path,
        remap: dict,
        replacement: dict,
    ):
        remap_path = root / "remap.json"
        replacement_path = root / "replacement.json"
        remap_path.write_text(
            json.dumps(remap, indent=2) + "\n",
            encoding="utf-8",
        )
        replacement_path.write_text(
            json.dumps(replacement, indent=2) + "\n",
            encoding="utf-8",
        )
        return remap_path, replacement_path

    def test_clean_reverse_transport_plan(self):
        with tempfile.TemporaryDirectory() as td:
            remap, replacement = self._docs()
            paths = self._write(
                Path(td),
                remap,
                replacement,
            )
            report = build_dependency_reverse_transport_plan(
                *paths,
                include_identifiers=True,
            )

            summary = report["summary"]
            self.assertTrue(
                summary["ready_for_bytecode_restore"]
            )
            self.assertEqual(summary["blocker_count"], 0)
            self.assertEqual(
                summary["class_reverse_count"],
                1,
            )
            self.assertEqual(
                summary["member_reverse_count"],
                2,
            )
            self.assertEqual(
                summary[
                    "owner_only_member_transport_count"
                ],
                1,
            )
            self.assertEqual(
                summary[
                    "member_identity_no_transport_count"
                ],
                1,
            )
            self.assertEqual(
                summary[
                    "ignored_nonreplaceable_accepted_member_count"
                ],
                1,
            )

            class_row = report["class_reverse"][0]
            self.assertEqual(
                class_row["official_owner"],
                "new/A",
            )
            self.assertEqual(
                class_row["bundled_owner"],
                "old/A",
            )

            member_names = {
                (
                    row["official_name"],
                    row["bundled_name"],
                )
                for row in report["member_reverse"]
            }
            self.assertIn(("run", "x"), member_names)
            self.assertIn(("value", "value"), member_names)

    def test_class_many_to_one_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            remap, replacement = self._docs()
            replacement["owners"].append(
                {
                    "owner_id": "DEPOWNER_00004",
                    "classification": "official_replaceable",
                    "old_owner": "old/B",
                    "new_owner": "new/A",
                }
            )
            paths = self._write(
                Path(td),
                remap,
                replacement,
            )
            report = build_dependency_reverse_transport_plan(
                *paths,
            )

            self.assertFalse(
                report["summary"][
                    "ready_for_bytecode_restore"
                ]
            )
            self.assertEqual(
                report["summary"]["blocker_counts"][
                    "class_reverse_many_to_one"
                ],
                1,
            )

    def test_class_target_also_source_owner_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            remap, replacement = self._docs()
            replacement["owners"].append(
                {
                    "owner_id": "DEPOWNER_00004",
                    "classification": "residual_bundled",
                    "old_owner": "new/A",
                    "new_owner": None,
                }
            )
            paths = self._write(
                Path(td),
                remap,
                replacement,
            )
            report = build_dependency_reverse_transport_plan(
                *paths,
            )

            self.assertFalse(
                report["summary"][
                    "ready_for_bytecode_restore"
                ]
            )
            self.assertEqual(
                report["summary"]["blocker_counts"][
                    "class_target_also_source_owner"
                ],
                1,
            )

    def test_member_many_to_one_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            remap, replacement = self._docs()
            remap["member_results"].append(
                {
                    "status": "accepted_remap",
                    "old_owner": "old/A",
                    "old_name": "y",
                    "old_descriptor": "()V",
                    "new_owner": "new/A",
                    "new_name": "run",
                    "new_descriptor": "()V",
                }
            )
            paths = self._write(
                Path(td),
                remap,
                replacement,
            )
            report = build_dependency_reverse_transport_plan(
                *paths,
            )

            self.assertFalse(
                report["summary"][
                    "ready_for_bytecode_restore"
                ]
            )
            self.assertEqual(
                report["summary"]["blocker_counts"][
                    "member_reverse_many_to_one"
                ],
                1,
            )

    def test_public_private_authority_matches_and_redacts(self):
        with tempfile.TemporaryDirectory() as td:
            remap, replacement = self._docs()
            paths = self._write(
                Path(td),
                remap,
                replacement,
            )
            public = build_dependency_reverse_transport_plan(
                *paths,
            )
            private = build_dependency_reverse_transport_plan(
                *paths,
                include_identifiers=True,
            )

            self.assertEqual(
                public["reverse_plan_id"],
                private["reverse_plan_id"],
            )
            encoded = json.dumps(public)
            self.assertNotIn("old/A", encoded)
            self.assertNotIn("new/A", encoded)
            self.assertNotIn('"run"', encoded)
            self.assertIn("old/A", json.dumps(private))
            self.assertIn("new/A", json.dumps(private))


if __name__ == "__main__":
    unittest.main()
