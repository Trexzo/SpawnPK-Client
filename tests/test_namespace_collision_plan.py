from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.namespace_collision_plan import (
    build_namespace_collision_plan,
)


class NamespaceCollisionPlanTests(unittest.TestCase):
    def _jar(self, root: Path, entries: list[str]) -> Path:
        jar = root / "readable.jar"
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
            for entry in entries:
                z.writestr(entry + ".class", b"fixture")
        return jar

    def test_single_blocker_plan_eliminates_all_collisions(self):
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

            report = build_namespace_collision_plan(jar)
            summary = report["summary"]

            self.assertEqual(summary["blocker_remap_count"], 1)
            self.assertEqual(summary["affected_target_count"], 2)
            self.assertEqual(summary["pre_collision_edge_count"], 2)
            self.assertEqual(summary["post_collision_edge_count"], 0)
            self.assertTrue(
                summary["plan_eliminates_all_collisions"]
            )
            self.assertEqual(
                summary["parent_package_preserved_count"],
                1,
            )

    def test_nested_collision_chain_remaps_every_blocker(self):
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

            report = build_namespace_collision_plan(
                jar,
                include_identifiers=True,
            )

            self.assertEqual(
                report["summary"]["blocker_remap_count"],
                2,
            )
            self.assertEqual(
                report["summary"]["pre_collision_edge_count"],
                3,
            )
            self.assertEqual(
                report["summary"]["post_collision_edge_count"],
                0,
            )
            self.assertEqual(
                len(report["remaps"]),
                2,
            )

            old_names = {
                row["old_internal_name"]
                for row in report["remaps"]
            }
            new_names = {
                row["new_internal_name"]
                for row in report["remaps"]
            }

            self.assertEqual(old_names, {"a", "a/b"})
            self.assertEqual(len(new_names), 2)
            self.assertTrue(old_names.isdisjoint(new_names))

    def test_replacement_avoids_existing_class_and_package_prefix(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a/b",
                    "a/b/c/Target",
                    "a/Recovered_JNSBLOCKER_0001",
                    "a/Recovered_JNSBLOCKER_0001/x/Existing",
                ],
            )

            report = build_namespace_collision_plan(
                jar,
                include_identifiers=True,
            )

            blocker = next(
                row
                for row in report["remaps"]
                if row["old_internal_name"] == "a/b"
            )

            self.assertNotEqual(
                blocker["new_internal_name"],
                "a/Recovered_JNSBLOCKER_0001",
            )
            self.assertNotEqual(
                blocker["new_internal_name"],
                "a/Recovered_JNSBLOCKER_0001_1",
            )

    def test_public_and_private_plans_share_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a/b",
                    "a/b/c/Target",
                ],
            )

            public = build_namespace_collision_plan(jar)
            private = build_namespace_collision_plan(
                jar,
                include_identifiers=True,
            )

            self.assertEqual(
                public["plan_id"],
                private["plan_id"],
            )
            self.assertEqual(
                public["collision_report_id"],
                private["collision_report_id"],
            )
            self.assertFalse(public["identifiers_included"])
            self.assertTrue(private["identifiers_included"])
            self.assertNotIn("a/b", str(public))
            self.assertIn("a/b", str(private))

    def test_zero_collision_plan_is_explicit_noop(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a/b/C",
                    "x/y/Z",
                ],
            )

            report = build_namespace_collision_plan(jar)

            self.assertEqual(
                report["summary"]["blocker_remap_count"],
                0,
            )
            self.assertEqual(
                report["summary"]["post_collision_edge_count"],
                0,
            )
            self.assertEqual(report["remaps"], [])


if __name__ == "__main__":
    unittest.main()
