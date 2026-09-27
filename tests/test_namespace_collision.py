from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.namespace_collision import (
    analyze_namespace_collisions,
)


class NamespaceCollisionTests(unittest.TestCase):
    def _jar(self, root: Path, entries: list[str]) -> Path:
        jar = root / "readable.jar"
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
            for entry in entries:
                z.writestr(entry + ".class", b"fixture")
        return jar

    def test_class_occupying_package_prefix_blocks_downstream_classes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a/b",
                    "a/b/c/One",
                    "a/b/c/Two",
                    "x/y/Z",
                ],
            )

            report = analyze_namespace_collisions(jar)
            summary = report["summary"]

            self.assertEqual(summary["class_count"], 4)
            self.assertEqual(summary["affected_class_count"], 2)
            self.assertEqual(summary["blocking_class_count"], 1)
            self.assertEqual(summary["collision_component_count"], 1)
            self.assertEqual(summary["collision_edge_count"], 2)
            self.assertEqual(
                summary["blocking_depth_counts"],
                {"2": 2},
            )
            self.assertEqual(
                summary["max_blocking_prefixes_per_target"],
                1,
            )

            self.assertEqual(len(report["targets"]), 2)
            self.assertEqual(len(report["blockers"]), 1)
            self.assertTrue(
                all(
                    row["source_addressability"]
                    == "blocked_by_class_package_prefix"
                    for row in report["targets"]
                )
            )

    def test_nested_prefix_collisions_group_into_one_component(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a",
                    "a/b",
                    "a/b/c/Target",
                ],
            )

            report = analyze_namespace_collisions(jar)
            summary = report["summary"]

            self.assertEqual(summary["affected_class_count"], 2)
            self.assertEqual(summary["blocking_class_count"], 2)
            self.assertEqual(summary["collision_component_count"], 1)
            self.assertEqual(summary["collision_edge_count"], 3)
            self.assertEqual(
                summary["max_blocking_prefixes_per_target"],
                2,
            )

            target = next(
                row
                for row in report["targets"]
                if row["blocking_prefix_count"] == 2
            )
            self.assertEqual(target["shallowest_blocking_depth"], 1)
            self.assertEqual(target["deepest_blocking_depth"], 2)

    def test_public_and_private_reports_share_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a/b",
                    "a/b/c/One",
                ],
            )

            public = analyze_namespace_collisions(jar)
            private = analyze_namespace_collisions(
                jar,
                include_identifiers=True,
            )

            self.assertEqual(
                public["report_id"],
                private["report_id"],
            )
            self.assertFalse(public["identifiers_included"])
            self.assertTrue(private["identifiers_included"])
            self.assertNotIn("a/b/c/One", str(public))
            self.assertIn("a/b/c/One", str(private))
            self.assertIn("a/b", str(private))

    def test_no_collision_is_explicit_zero_surface(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a/b/C",
                    "x/y/Z",
                ],
            )

            report = analyze_namespace_collisions(jar)

            self.assertEqual(
                report["summary"]["affected_class_count"],
                0,
            )
            self.assertEqual(
                report["summary"]["blocking_class_count"],
                0,
            )
            self.assertEqual(report["targets"], [])
            self.assertEqual(report["blockers"], [])


if __name__ == "__main__":
    unittest.main()
