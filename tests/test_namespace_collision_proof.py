from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.namespace_collision_proof import (
    prove_namespace_collisions,
)


class NamespaceCollisionProofTests(unittest.TestCase):
    def _plan(self, names: list[str]):
        return {
            "schema_version": 1,
            "kind": "javac_missing_class_recovery_plan",
            "plan_id": "JCLASSPLAN_" + "5" * 20,
            "identifiers_included": True,
            "candidates": [
                {
                    "candidate_id": f"JCLASSMISS_{index:03d}",
                    "candidate_internal_name": name,
                }
                for index, name in enumerate(names, start=1)
            ],
        }

    def _jar(self, root: Path, names: list[str]) -> Path:
        jar = root / "readable.jar"
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
            for name in names:
                z.writestr(name + ".class", b"placeholder")
        return jar

    def test_proves_class_package_collision_chain(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a/b",
                    "a/b/c",
                    "a/b/c/Target",
                    "safe/Other",
                ],
            )
            report = prove_namespace_collisions(
                self._plan(["a/b/c/Target"]),
                jar,
            )

            self.assertEqual(
                report["summary"]["candidate_count"],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "collision_proven_candidate_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "candidate_collision_node_count"
                ],
                2,
            )
            self.assertEqual(
                report["summary"][
                    "planned_colliding_class_rename_count"
                ],
                2,
            )
            self.assertEqual(
                report["candidates"][0]["collision_depths"],
                [2, 3],
            )

    def test_unrelated_candidate_is_not_falsely_proven(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a/b",
                    "a/b/c/Target",
                    "safe/Other",
                ],
            )
            report = prove_namespace_collisions(
                self._plan(["safe/Other"]),
                jar,
            )

            self.assertEqual(
                report["summary"][
                    "collision_proven_candidate_count"
                ],
                0,
            )
            self.assertEqual(
                report["summary"][
                    "collision_unproven_candidate_count"
                ],
                1,
            )
            self.assertEqual(
                report["collision_plan"],
                [],
            )

    def test_public_and_private_share_same_proof_id(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a/b",
                    "a/b/c/Target",
                ],
            )
            plan = self._plan(["a/b/c/Target"])

            public = prove_namespace_collisions(
                plan,
                jar,
            )
            private = prove_namespace_collisions(
                plan,
                jar,
                include_identifiers=True,
            )

            self.assertEqual(
                public["proof_id"],
                private["proof_id"],
            )
            self.assertNotIn("a/b", str(public))
            self.assertIn("a/b", str(private))


if __name__ == "__main__":
    unittest.main()
