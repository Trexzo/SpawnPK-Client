from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.namespace_remap_boundary import (
    NamespaceRemapBoundaryError,
    build_namespace_remap_boundary,
)


class NamespaceRemapBoundaryTests(unittest.TestCase):
    def _jar(self, root: Path, names: list[str]) -> Path:
        jar = root / "readable.jar"
        with zipfile.ZipFile(
            jar,
            "w",
            zipfile.ZIP_STORED,
        ) as z:
            for name in names:
                z.writestr(name + ".class", b"x")
        return jar

    def _graph(self, rows):
        return {
            "schema_version": 1,
            "kind": "namespace_collision_graph",
            "graph_id": "NSCOLLISION_" + "6" * 20,
            "readable_jar_sha256": "a" * 64,
            "identifiers_included": True,
            "candidates": rows,
        }

    def test_ancestor_collision_node_emits_two_review_only_boundaries(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a",
                    "a/b/C",
                    "a/b/D",
                ],
            )
            graph = self._graph(
                [
                    {
                        "candidate_id": "JCLASSMISS_001",
                        "candidate_internal_name": "a/b/C",
                        "ancestor_collision_internal_names": ["a"],
                        "descendant_internal_names": [],
                    }
                ]
            )

            report = build_namespace_remap_boundary(
                graph,
                jar,
            )
            node = report["nodes"][0]

            self.assertEqual(
                node["selection_status"],
                "review_required",
            )
            self.assertEqual(
                node["package_subtree_class_count"],
                2,
            )
            self.assertEqual(
                node["boundary_options"][
                    "rename_colliding_class_identity"
                ]["class_identity_count"],
                1,
            )
            self.assertEqual(
                node["boundary_options"][
                    "rename_descendant_package_subtree"
                ]["class_identity_count"],
                2,
            )
            self.assertEqual(
                report["summary"][
                    "automatic_strategy_selection_count"
                ],
                0,
            )

    def test_shared_collision_node_groups_multiple_candidates(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a",
                    "a/b/C",
                    "a/c/D",
                ],
            )
            graph = self._graph(
                [
                    {
                        "candidate_id": "JCLASSMISS_001",
                        "candidate_internal_name": "a/b/C",
                        "ancestor_collision_internal_names": ["a"],
                        "descendant_internal_names": [],
                    },
                    {
                        "candidate_id": "JCLASSMISS_002",
                        "candidate_internal_name": "a/c/D",
                        "ancestor_collision_internal_names": ["a"],
                        "descendant_internal_names": [],
                    },
                ]
            )

            report = build_namespace_remap_boundary(
                graph,
                jar,
            )

            self.assertEqual(
                report["summary"]["collision_node_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["affected_candidate_count"],
                2,
            )
            self.assertEqual(
                report["nodes"][0]["affected_candidate_ids"],
                ["JCLASSMISS_001", "JCLASSMISS_002"],
            )

    def test_candidate_as_package_prefix_becomes_collision_node(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "x/Y",
                    "x/Y/Z",
                    "x/Y/q/R",
                ],
            )
            graph = self._graph(
                [
                    {
                        "candidate_id": "JCLASSMISS_001",
                        "candidate_internal_name": "x/Y",
                        "ancestor_collision_internal_names": [],
                        "descendant_internal_names": [
                            "x/Y/Z",
                            "x/Y/q/R",
                        ],
                    }
                ]
            )

            report = build_namespace_remap_boundary(
                graph,
                jar,
            )
            node = report["nodes"][0]

            self.assertEqual(
                node["collision_origins"],
                ["candidate_class_is_package_prefix"],
            )
            self.assertEqual(
                node["package_subtree_class_count"],
                2,
            )

    def test_public_private_boundary_id_stable_and_public_redacts_names(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a",
                    "a/b/C",
                ],
            )
            graph = self._graph(
                [
                    {
                        "candidate_id": "JCLASSMISS_001",
                        "candidate_internal_name": "a/b/C",
                        "ancestor_collision_internal_names": ["a"],
                        "descendant_internal_names": [],
                    }
                ]
            )

            public = build_namespace_remap_boundary(
                graph,
                jar,
            )
            private = build_namespace_remap_boundary(
                graph,
                jar,
                include_identifiers=True,
            )

            self.assertEqual(
                public["boundary_id"],
                private["boundary_id"],
            )
            self.assertNotIn("a/b/C", json.dumps(public))
            self.assertIn("a/b/C", json.dumps(private))

    def test_missing_collision_node_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(root, ["a/b/C"])
            graph = self._graph(
                [
                    {
                        "candidate_id": "JCLASSMISS_001",
                        "candidate_internal_name": "a/b/C",
                        "ancestor_collision_internal_names": ["a"],
                        "descendant_internal_names": [],
                    }
                ]
            )

            with self.assertRaises(NamespaceRemapBoundaryError):
                build_namespace_remap_boundary(
                    graph,
                    jar,
                )


if __name__ == "__main__":
    unittest.main()
