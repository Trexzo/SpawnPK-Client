from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from spk_recovery.dependency_source_binding import _mapping_rows
from spk_recovery.dependency_source_edit_plan import (
    build_dependency_source_edit_plan,
)


class DependencySourceEditPlanTests(unittest.TestCase):
    def _fixture(self, root: Path, *, unmatched: bool = False):
        remap = {
            "schema_version": 1,
            "kind": "dependency_structural_remap_proof",
            "dependency_remap_proof_id": "DEPREMAP_" + "A" * 20,
            "reference_surface_id": "DEPREF_" + "B" * 20,
            "bundled_jar_sha256": "1" * 64,
            "java_release": 9,
            "project_prefixes": ["app/"],
            "official_artifacts": [],
            "member_results": [
                {
                    "kind": "method",
                    "old_owner": "dep/A",
                    "old_name": "<init>",
                    "old_descriptor": "()V",
                    "reference_count": 1,
                    "status": "accepted_remap",
                    "new_owner": "official/A",
                    "new_name": "<init>",
                    "new_descriptor": "()V",
                    "artifact": "official.jar",
                },
                {
                    "kind": "method",
                    "old_owner": "dep/A",
                    "old_name": "x",
                    "old_descriptor": "()V",
                    "reference_count": 1,
                    "status": "accepted_remap",
                    "new_owner": "official/A",
                    "new_name": "run",
                    "new_descriptor": "()V",
                    "artifact": "official.jar",
                },
                {
                    "kind": "field",
                    "old_owner": "dep/A",
                    "old_name": "value",
                    "old_descriptor": "Ldep/T;",
                    "reference_count": 1,
                    "status": "accepted_remap",
                    "new_owner": "official/A",
                    "new_name": "value",
                    "new_descriptor": "Lofficial/T;",
                    "artifact": "official.jar",
                },
                {
                    "kind": "field",
                    "old_owner": "dep/Same",
                    "old_name": "id",
                    "old_descriptor": "I",
                    "reference_count": 1,
                    "status": "accepted_identity",
                    "new_owner": "dep/Same",
                    "new_name": "id",
                    "new_descriptor": "I",
                    "artifact": "official.jar",
                },
            ],
        }
        replacement = {
            "schema_version": 1,
            "kind": "dependency_replacement_boundary_plan",
            "replacement_plan_id": "DEPREPLACE_" + "C" * 20,
            "reference_surface_id": remap["reference_surface_id"],
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
                    "old_owner": "dep/A",
                    "new_owner": "official/A",
                    "artifact": "official.jar",
                },
                {
                    "owner_id": "DEPOWNER_00002",
                    "classification": "official_replaceable",
                    "old_owner": "dep/Same",
                    "new_owner": "dep/Same",
                    "artifact": "official.jar",
                },
                {
                    "owner_id": "DEPOWNER_00003",
                    "classification": "residual_bundled",
                    "old_owner": "dep/B",
                    "new_owner": None,
                    "artifact": None,
                },
            ],
            "identifiers_included": True,
        }

        _owners, members = _mapping_rows(remap, replacement)
        member_ids = {
            (
                row["old_owner"],
                row["old_name"],
                row["old_descriptor"],
            ): row["member_id"]
            for row in members
        }

        bindings = [
            {
                "binding_id": "DEPSRCBIND_000001",
                "source_file_id": "SRCFILE_0001",
                "source_file": "app/Use.java",
                "start": 104,
                "end": 105,
                "syntax_kind": "identifier",
                "element_kind": "class",
                "old_owner": "dep/A",
                "old_name": "",
                "old_descriptor": "",
                "match_status": "exact_approved_class",
                "mapping_id": "DEPOWNER_00001",
                "owner_classification": "official_replaceable",
            },
            {
                "binding_id": "DEPSRCBIND_000002",
                "source_file_id": "SRCFILE_0001",
                "source_file": "app/Use.java",
                "start": 100,
                "end": 110,
                "syntax_kind": "new_class",
                "element_kind": "constructor",
                "old_owner": "dep/A",
                "old_name": "<init>",
                "old_descriptor": "()V",
                "match_status": "exact_approved_member",
                "mapping_id": member_ids[
                    ("dep/A", "<init>", "()V")
                ],
                "owner_classification": "official_replaceable",
            },
            {
                "binding_id": "DEPSRCBIND_000003",
                "source_file_id": "SRCFILE_0001",
                "source_file": "app/Use.java",
                "start": 200,
                "end": 203,
                "syntax_kind": "member_select",
                "element_kind": "method",
                "old_owner": "dep/A",
                "old_name": "x",
                "old_descriptor": "()V",
                "match_status": "exact_approved_member",
                "mapping_id": member_ids[
                    ("dep/A", "x", "()V")
                ],
                "owner_classification": "official_replaceable",
            },
            {
                "binding_id": "DEPSRCBIND_000004",
                "source_file_id": "SRCFILE_0001",
                "source_file": "app/Use.java",
                "start": 300,
                "end": 307,
                "syntax_kind": "member_select",
                "element_kind": "field",
                "old_owner": "dep/A",
                "old_name": "value",
                "old_descriptor": "Ldep/T;",
                "match_status": "exact_approved_member",
                "mapping_id": member_ids[
                    ("dep/A", "value", "Ldep/T;")
                ],
                "owner_classification": "official_replaceable",
            },
            {
                "binding_id": "DEPSRCBIND_000005",
                "source_file_id": "SRCFILE_0001",
                "source_file": "app/Use.java",
                "start": 400,
                "end": 408,
                "syntax_kind": "member_select",
                "element_kind": "field",
                "old_owner": "dep/Same",
                "old_name": "id",
                "old_descriptor": "I",
                "match_status": "exact_approved_member",
                "mapping_id": member_ids[
                    ("dep/Same", "id", "I")
                ],
                "owner_classification": "official_replaceable",
            },
            {
                "binding_id": "DEPSRCBIND_000006",
                "source_file_id": "SRCFILE_0001",
                "source_file": "app/Use.java",
                "start": 500,
                "end": 501,
                "syntax_kind": "identifier",
                "element_kind": "class",
                "old_owner": "dep/B",
                "old_name": "",
                "old_descriptor": "",
                "match_status": "non_replaceable_owner",
                "mapping_id": "DEPOWNER_00003",
                "owner_classification": "residual_bundled",
            },
        ]

        if unmatched:
            bindings.append(
                {
                    "binding_id": "DEPSRCBIND_000007",
                    "source_file_id": "SRCFILE_0001",
                    "source_file": "app/Use.java",
                    "start": 600,
                    "end": 610,
                    "syntax_kind": "member_select",
                    "element_kind": "method",
                    "old_owner": "dep/A",
                    "old_name": "unknown",
                    "old_descriptor": "()V",
                    "match_status": "approved_owner_unmatched_member",
                    "mapping_id": "DEPOWNER_00001",
                    "owner_classification": "official_replaceable",
                }
            )

        binding = {
            "schema_version": 1,
            "kind": "dependency_source_binding_inventory",
            "binding_inventory_id": "DEPSRCBIND_" + "D" * 20,
            "source_tree_sha256": "2" * 64,
            "dependency_remap_proof_id": remap[
                "dependency_remap_proof_id"
            ],
            "replacement_plan_id": replacement[
                "replacement_plan_id"
            ],
            "bundled_jar_sha256": remap[
                "bundled_jar_sha256"
            ],
            "bindings": bindings,
            "identifiers_included": True,
        }

        paths = {}
        for name, doc in (
            ("binding", binding),
            ("remap", remap),
            ("replacement", replacement),
        ):
            path = root / f"{name}.json"
            path.write_text(
                json.dumps(doc, indent=2) + "\n",
                encoding="utf-8",
            )
            paths[name] = path
        return paths

    def test_derives_edit_obligations_and_constructor_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            paths = self._fixture(Path(td))
            report = build_dependency_source_edit_plan(
                paths["binding"],
                paths["remap"],
                paths["replacement"],
                include_identifiers=True,
            )

            self.assertTrue(
                report["summary"]["ready_for_source_overlay"]
            )
            self.assertEqual(
                report["summary"]["blocker_count"],
                0,
            )

            actions = {
                row["edit_binding_id"]: row["action"]
                for row in report["obligations"]
            }
            self.assertEqual(
                actions["DEPSRCBIND_000001"],
                "class_type_rename_required",
            )
            self.assertEqual(
                actions["DEPSRCBIND_000002"],
                "constructor_covered_by_type_edit",
            )
            self.assertEqual(
                actions["DEPSRCBIND_000003"],
                "member_name_rename_required",
            )
            self.assertEqual(
                actions["DEPSRCBIND_000004"],
                "mapped_signature_no_direct_edit",
            )
            self.assertEqual(
                actions["DEPSRCBIND_000005"],
                "identity_no_edit",
            )
            self.assertEqual(
                actions["DEPSRCBIND_000006"],
                "non_replaceable_no_edit",
            )

    def test_unmatched_member_blocks_overlay_readiness(self):
        with tempfile.TemporaryDirectory() as td:
            paths = self._fixture(
                Path(td),
                unmatched=True,
            )
            report = build_dependency_source_edit_plan(
                paths["binding"],
                paths["remap"],
                paths["replacement"],
            )

            self.assertFalse(
                report["summary"]["ready_for_source_overlay"]
            )
            self.assertEqual(
                report["summary"]["blocker_counts"],
                {"approved_owner_unmatched_member": 1},
            )

    def test_public_private_authority_matches_and_redacts(self):
        with tempfile.TemporaryDirectory() as td:
            paths = self._fixture(Path(td))
            public = build_dependency_source_edit_plan(
                paths["binding"],
                paths["remap"],
                paths["replacement"],
            )
            private = build_dependency_source_edit_plan(
                paths["binding"],
                paths["remap"],
                paths["replacement"],
                include_identifiers=True,
            )

            self.assertEqual(
                public["edit_plan_id"],
                private["edit_plan_id"],
            )
            encoded = json.dumps(public)
            self.assertNotIn("dep/A", encoded)
            self.assertNotIn("official/A", encoded)
            self.assertNotIn("Use.java", encoded)
            self.assertIn("official/A", json.dumps(private))


if __name__ == "__main__":
    unittest.main()
