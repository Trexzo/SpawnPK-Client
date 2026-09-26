from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.namespace_remap_bundle import (
    NamespaceRemapBundleError,
    build_namespace_remap_bundle_plan,
    mapping_tsv,
)


class NamespaceRemapBundleTests(unittest.TestCase):
    def _jar(
        self,
        root: Path,
        *,
        occupy_target: bool = False,
    ) -> Path:
        jar = root / "readable.jar"
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
            z.writestr("a/b.class", b"owner")
            z.writestr("a/b$Inner.class", b"inner")
            z.writestr("a/b/c/Target.class", b"target")
            if occupy_target:
                z.writestr(
                    "a/b__spk_type_deadbeef.class",
                    b"occupied",
                )
        return jar

    def _proof(
        self,
        *,
        target: str = "a/b__spk_type_deadbeef",
    ):
        return {
            "schema_version": 1,
            "kind": "dependency_namespace_collision_proof",
            "proof_id": "NSCOLLISION_" + "A" * 20,
            "identifiers_included": True,
            "summary": {
                "remap_plan_topology_safe": True,
            },
            "collision_plan": [
                {
                    "collision_id": "JCOLLISION_001",
                    "rename_family": [
                        {"from": "a/b", "to": target},
                        {
                            "from": "a/b$Inner",
                            "to": target + "$Inner",
                        },
                    ],
                }
            ],
        }

    def _impact(
        self,
        jar: Path,
        *,
        reflective_risk: int = 0,
    ):
        return {
            "schema_version": 1,
            "kind": "dependency_namespace_remap_impact_plan",
            "impact_plan_id": "NSREMAPIMPACT_" + "B" * 20,
            "collision_proof_id": "NSCOLLISION_" + "A" * 20,
            "readable_jar_sha256": hashlib.sha256(
                jar.read_bytes()
            ).hexdigest(),
            "summary": {
                "planned_binary_class_rename_count": 2,
                "unclassified_utf8_risk_count": 0,
                "reflective_literal_risk_count": reflective_risk,
                "automatic_bytecode_rewrite_safe": (
                    reflective_risk == 0
                ),
            },
        }

    def test_builds_public_private_bundle_with_stable_id(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = "a/b__spk_type_cafef00d"
            jar = self._jar(root)
            proof = self._proof(target=target)
            impact = self._impact(jar)

            public = build_namespace_remap_bundle_plan(
                proof,
                impact,
                jar,
            )
            private = build_namespace_remap_bundle_plan(
                proof,
                impact,
                jar,
                include_identifiers=True,
            )

            self.assertEqual(
                public["bundle_plan_id"],
                private["bundle_plan_id"],
            )
            self.assertEqual(public["class_mapping_count"], 2)
            self.assertFalse(public["rewrite_class_name_strings"])
            self.assertNotIn("a/b", str(public))
            self.assertIn("a/b", str(private))
            self.assertEqual(
                mapping_tsv(private),
                (
                    "C\ta/b\t"
                    + target
                    + "\n"
                    + "C\ta/b$Inner\t"
                    + target
                    + "$Inner\n"
                ),
            )

    def test_refuses_occupied_target_entry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(root, occupy_target=True)
            proof = self._proof()
            impact = self._impact(jar)

            with self.assertRaisesRegex(
                NamespaceRemapBundleError,
                "target entry already exists",
            ):
                build_namespace_remap_bundle_plan(
                    proof,
                    impact,
                    jar,
                )

    def test_refuses_reflective_literal_risk(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(root)
            proof = self._proof(
                target="a/b__spk_type_cafef00d"
            )
            impact = self._impact(
                jar,
                reflective_risk=1,
            )

            with self.assertRaisesRegex(
                NamespaceRemapBundleError,
                "reflective literal risk",
            ):
                build_namespace_remap_bundle_plan(
                    proof,
                    impact,
                    jar,
                )

    def test_refuses_impact_binding_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(root)
            proof = self._proof(
                target="a/b__spk_type_cafef00d"
            )
            impact = self._impact(jar)
            impact["collision_proof_id"] = (
                "NSCOLLISION_" + "C" * 20
            )

            with self.assertRaisesRegex(
                NamespaceRemapBundleError,
                "binding mismatch",
            ):
                build_namespace_remap_bundle_plan(
                    proof,
                    impact,
                    jar,
                )


if __name__ == "__main__":
    unittest.main()
