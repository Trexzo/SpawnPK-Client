from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.namespace_collision_graph import (
    NamespaceCollisionError,
    build_namespace_collision_graph,
)


class NamespaceCollisionGraphTests(unittest.TestCase):
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

    def _plan(self, candidates: list[tuple[str, str]]):
        return {
            "schema_version": 1,
            "kind": "javac_missing_class_recovery_plan",
            "plan_id": "JCLASSPLAN_" + "5" * 20,
            "identifiers_included": True,
            "candidates": [
                {
                    "candidate_id": candidate_id,
                    "candidate_internal_name": internal,
                }
                for candidate_id, internal in candidates
            ],
        }

    def test_ancestor_class_blocks_candidate_package(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a",
                    "a/b/C",
                ],
            )
            report = build_namespace_collision_graph(
                self._plan(
                    [("JCLASSMISS_001", "a/b/C")]
                ),
                jar,
            )

            row = report["candidates"][0]
            self.assertEqual(
                row["relation"],
                "ancestor_class_blocks_package",
            )
            self.assertEqual(
                row["ancestor_collision_count"],
                1,
            )
            self.assertEqual(
                row["ancestor_collision_depths"],
                [1],
            )
            self.assertEqual(
                row["nearest_ancestor_distance"],
                2,
            )
            self.assertEqual(
                report["summary"][
                    "global_collision_node_count"
                ],
                1,
            )

    def test_nearest_ancestor_collision_is_reported(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a",
                    "a/b",
                    "a/b/c/D",
                ],
            )
            report = build_namespace_collision_graph(
                self._plan(
                    [("JCLASSMISS_001", "a/b/c/D")]
                ),
                jar,
            )
            row = report["candidates"][0]

            self.assertEqual(
                row["ancestor_collision_count"],
                2,
            )
            self.assertEqual(
                row["ancestor_collision_depths"],
                [1, 2],
            )
            self.assertEqual(
                row["nearest_ancestor_distance"],
                2,
            )

    def test_candidate_class_can_also_be_package_prefix(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "x/Y",
                    "x/Y/Z",
                ],
            )
            report = build_namespace_collision_graph(
                self._plan(
                    [("JCLASSMISS_001", "x/Y")]
                ),
                jar,
            )
            row = report["candidates"][0]

            self.assertEqual(
                row["relation"],
                "candidate_class_is_package_prefix",
            )
            self.assertEqual(
                row["descendant_class_count"],
                1,
            )
            self.assertTrue(
                row["direct_collision_node"],
            )

    def test_candidate_can_have_ancestor_and_descendant_collision(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a",
                    "a/b/C",
                    "a/b/C/d/E",
                ],
            )
            report = build_namespace_collision_graph(
                self._plan(
                    [("JCLASSMISS_001", "a/b/C")]
                ),
                jar,
            )
            row = report["candidates"][0]

            self.assertEqual(
                row["relation"],
                "ancestor_and_descendant_collision",
            )
            self.assertEqual(
                row["ancestor_collision_count"],
                1,
            )
            self.assertEqual(
                row["descendant_class_count"],
                1,
            )

    def test_no_collision_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a/b/C",
                    "x/y/Z",
                ],
            )
            report = build_namespace_collision_graph(
                self._plan(
                    [("JCLASSMISS_001", "a/b/C")]
                ),
                jar,
            )
            self.assertEqual(
                report["candidates"][0]["relation"],
                "no_namespace_collision",
            )
            self.assertEqual(
                report["summary"][
                    "candidate_collision_count"
                ],
                0,
            )

    def test_public_private_graph_id_is_stable_and_public_redacts_names(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a",
                    "a/b/C",
                ],
            )
            plan = self._plan(
                [("JCLASSMISS_001", "a/b/C")]
            )

            public = build_namespace_collision_graph(
                plan,
                jar,
            )
            private = build_namespace_collision_graph(
                plan,
                jar,
                include_identifiers=True,
            )

            self.assertEqual(
                public["graph_id"],
                private["graph_id"],
            )
            self.assertNotIn("a/b/C", json.dumps(public))
            self.assertIn("a/b/C", json.dumps(private))

    def test_candidate_missing_from_readable_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(root, ["a/b/C"])
            with self.assertRaises(NamespaceCollisionError):
                build_namespace_collision_graph(
                    self._plan(
                        [("JCLASSMISS_001", "x/y/Z")]
                    ),
                    jar,
                )


if __name__ == "__main__":
    unittest.main()
