from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_runtime_frontier import (
    DependencyRuntimeFrontierError,
    build_dependency_runtime_frontier,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DependencyRuntimeFrontierTests(unittest.TestCase):
    def _fixture(self, root: Path) -> dict:
        bundled = root / "bundled.jar"
        with zipfile.ZipFile(
            bundled,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            archive.writestr("old/A.class", b"A" * 11)
            archive.writestr("old/B.class", b"B" * 13)
            archive.writestr("old/C.class", b"C" * 17)
            archive.writestr("unused/D.class", b"D" * 19)
            archive.writestr("META-INF/service", b"service")

        official = root / "official.jar"
        with zipfile.ZipFile(
            official,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            archive.writestr("official/A.class", b"official-A")
            archive.writestr("official/Extra.class", b"extra")

        replacement = {
            "schema_version": 1,
            "kind": "dependency_replacement_boundary_plan",
            "replacement_plan_id": "DEPREPLACE_" + "1" * 20,
            "bundled_jar_sha256": _sha(bundled),
            "java_release": 9,
            "project_prefixes": ["rs/"],
            "official_artifact_set_sha256": "f" * 64,
            "official_artifacts": [
                {
                    "artifact": "official.jar",
                    "sha256": _sha(official),
                    "multi_release_class_count": 0,
                    "java_release": 9,
                }
            ],
            "artifact_ids": {
                "official.jar": "DEPARTIFACT_0001",
            },
            "owners": [
                {
                    "owner_id": "DEPOWNER_00001",
                    "classification": "official_replaceable",
                    "old_owner": "old/A",
                    "new_owner": "official/A",
                    "artifact": "official.jar",
                },
                {
                    "owner_id": "DEPOWNER_00002",
                    "classification": "residual_bundled",
                    "old_owner": "old/B",
                    "new_owner": None,
                    "artifact": None,
                },
                {
                    "owner_id": "DEPOWNER_00003",
                    "classification": "project_retained",
                    "old_owner": "old/C",
                    "new_owner": None,
                    "artifact": None,
                },
                {
                    "owner_id": "DEPOWNER_00004",
                    "classification": "platform_runtime",
                    "old_owner": "java/util/List",
                    "new_owner": None,
                    "artifact": None,
                },
            ],
            "identifiers_included": True,
        }
        plan = root / "replacement.json"
        plan.write_text(
            json.dumps(replacement, indent=2) + "\n",
            encoding="utf-8",
        )
        return {
            "bundled": bundled,
            "official": official,
            "plan": plan,
            "replacement": replacement,
        }

    def test_quantifies_direct_runtime_frontier_without_authorizing_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = build_dependency_runtime_frontier(
                fx["plan"],
                fx["bundled"],
                [fx["official"]],
            )

            self.assertEqual(
                report["kind"],
                "dependency_runtime_frontier",
            )
            self.assertFalse(
                report["summary"]["runtime_capsule_mutation_ready"]
            )
            self.assertTrue(
                report["summary"][
                    "requires_dependency_closure_proof"
                ]
            )
            self.assertEqual(
                report["summary"][
                    "official_replaceable_bundled_class_entry_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "official_replaceable_bundled_class_bytes"
                ],
                11,
            )
            self.assertEqual(
                report["summary"][
                    "protected_bundled_class_entry_count"
                ],
                2,
            )
            self.assertEqual(
                report["summary"]["protected_bundled_class_bytes"],
                30,
            )
            self.assertFalse(report["identifiers_included"])
            self.assertNotIn(
                "old_owner",
                json.dumps(report["owners"]),
            )

    def test_private_mode_preserves_exact_owner_binding(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = build_dependency_runtime_frontier(
                fx["plan"],
                fx["bundled"],
                [fx["official"]],
                include_identifiers=True,
            )
            row = report["owners"][0]
            self.assertEqual(row["old_owner"], "old/A")
            self.assertEqual(row["new_owner"], "official/A")
            self.assertEqual(row["artifact"], "official.jar")

    def test_official_artifact_byte_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            fx["official"].write_bytes(b"drift")
            with self.assertRaisesRegex(
                DependencyRuntimeFrontierError,
                "artifact SHA drifted",
            ):
                build_dependency_runtime_frontier(
                    fx["plan"],
                    fx["bundled"],
                    [fx["official"]],
                )

    def test_missing_official_target_class_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            replacement = fx["replacement"]
            replacement["owners"][0]["new_owner"] = "official/Missing"

            with zipfile.ZipFile(
                fx["official"],
                "w",
                zipfile.ZIP_STORED,
            ) as archive:
                archive.writestr("official/Other.class", b"other")

            replacement["official_artifacts"][0]["sha256"] = _sha(
                fx["official"]
            )
            fx["plan"].write_text(
                json.dumps(replacement) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                DependencyRuntimeFrontierError,
                "target class missing",
            ):
                build_dependency_runtime_frontier(
                    fx["plan"],
                    fx["bundled"],
                    [fx["official"]],
                )

    def test_project_owned_runtime_owner_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            replacement = fx["replacement"]
            replacement["owners"][1]["old_owner"] = "rs/NotExternal"
            fx["plan"].write_text(
                json.dumps(replacement) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                DependencyRuntimeFrontierError,
                "overlaps project prefixes",
            ):
                build_dependency_runtime_frontier(
                    fx["plan"],
                    fx["bundled"],
                    [fx["official"]],
                )


if __name__ == "__main__":
    unittest.main()
