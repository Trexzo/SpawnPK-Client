from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_runtime_resource import (
    DependencyRuntimeResourceError,
    build_dependency_runtime_resource_equivalence,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DependencyRuntimeResourceTests(unittest.TestCase):
    def _fixture(self, root: Path) -> dict:
        bundled = root / "bundled.jar"
        with zipfile.ZipFile(
            bundled,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            archive.writestr(
                "config/exact.txt",
                b"exact",
            )
            archive.writestr(
                "META-INF/services/example.Service",
                b"impl.Provider",
            )
            archive.writestr(
                "config/mismatch.txt",
                b"bundled",
            )
            archive.writestr(
                "natives/example.dll",
                b"native",
            )

        first = root / "first.jar"
        with zipfile.ZipFile(
            first,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            archive.writestr(
                "config/exact.txt",
                b"exact",
            )
            archive.writestr(
                "META-INF/services/example.Service",
                b"impl.Provider\n",
            )
            archive.writestr(
                "config/mismatch.txt",
                b"official",
            )
            archive.writestr(
                "config/missing.txt",
                b"only-official",
            )
            archive.writestr(
                "natives/example.dll",
                b"native",
            )
            archive.writestr(
                "shared/duplicate.txt",
                b"first",
            )

        second = root / "second.jar"
        with zipfile.ZipFile(
            second,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            archive.writestr(
                "shared/duplicate.txt",
                b"second",
            )

        closure = {
            "schema_version": 1,
            "kind": "dependency_runtime_closure",
            "runtime_closure_id": (
                "DEPRUNTIMECLOSURE_" + "1" * 20
            ),
            "bundled_jar_sha256": _sha(bundled),
            "official_artifact_sha256": sorted(
                [_sha(first), _sha(second)]
            ),
            "summary": {
                "reflection_dynamic_loading_unproven": True,
            },
            "resources": {
                "artifacts": [
                    {
                        "artifact_id": "DEPCLOSUREARTIFACT_0001",
                        "artifact": "first.jar",
                        "resource_entry_count": 6,
                        "resource_bytes": 1,
                        "service_entry_count": 1,
                        "native_entry_count": 1,
                    },
                    {
                        "artifact_id": "DEPCLOSUREARTIFACT_0002",
                        "artifact": "second.jar",
                        "resource_entry_count": 1,
                        "resource_bytes": 1,
                        "service_entry_count": 0,
                        "native_entry_count": 0,
                    },
                ]
            },
            "identifiers_included": True,
        }
        closure_path = root / "closure.json"
        closure_path.write_text(
            json.dumps(closure, indent=2) + "\n",
            encoding="utf-8",
        )
        return {
            "bundled": bundled,
            "first": first,
            "second": second,
            "closure": closure_path,
            "closure_report": closure,
        }

    def test_classifies_exact_service_missing_mismatch_and_ambiguous(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = build_dependency_runtime_resource_equivalence(
                fx["closure"],
                fx["bundled"],
                [fx["first"], fx["second"]],
                include_identifiers=True,
            )

            counts = report["summary"]["status_counts"]
            self.assertEqual(counts["exact_byte_match"], 2)
            self.assertEqual(
                counts[
                    "service_trailing_newline_equivalent"
                ],
                1,
            )
            self.assertEqual(
                counts["missing_from_bundled"],
                1,
            )
            self.assertEqual(
                counts["byte_mismatch"],
                1,
            )
            self.assertEqual(
                counts["ambiguous_official_path"],
                1,
            )
            self.assertEqual(
                report["summary"]["resource_blocker_count"],
                3,
            )
            self.assertEqual(
                report["summary"]["native_entry_count"],
                1,
            )
            self.assertTrue(
                report["summary"][
                    "native_runtime_safety_unproven"
                ]
            )
            self.assertTrue(
                report["summary"][
                    "reflection_dynamic_loading_unproven"
                ]
            )
            self.assertFalse(
                report["summary"][
                    "runtime_capsule_mutation_ready"
                ]
            )

    def test_public_report_redacts_paths_and_preserves_id(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            public = build_dependency_runtime_resource_equivalence(
                fx["closure"],
                fx["bundled"],
                [fx["first"], fx["second"]],
            )
            private = build_dependency_runtime_resource_equivalence(
                fx["closure"],
                fx["bundled"],
                [fx["first"], fx["second"]],
                include_identifiers=True,
            )

            self.assertEqual(
                public["runtime_resource_id"],
                private["runtime_resource_id"],
            )
            self.assertFalse(public["identifiers_included"])
            rendered = json.dumps(public)
            self.assertNotIn("config/exact.txt", rendered)
            self.assertNotIn("first.jar", rendered)

    def test_public_closure_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            closure = fx["closure_report"]
            closure["identifiers_included"] = False
            for row in closure["resources"]["artifacts"]:
                row.pop("artifact", None)
            fx["closure"].write_text(
                json.dumps(closure) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                DependencyRuntimeResourceError,
                "identifier-bearing closure",
            ):
                build_dependency_runtime_resource_equivalence(
                    fx["closure"],
                    fx["bundled"],
                    [fx["first"], fx["second"]],
                )

    def test_official_artifact_sha_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            fx["second"].write_bytes(b"drift")

            with self.assertRaisesRegex(
                DependencyRuntimeResourceError,
                "SHA set differs",
            ):
                build_dependency_runtime_resource_equivalence(
                    fx["closure"],
                    fx["bundled"],
                    [fx["first"], fx["second"]],
                )

    def test_non_service_newline_difference_is_not_normalized(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = root / "bundled.jar"
            official = root / "official.jar"
            with zipfile.ZipFile(
                bundled,
                "w",
                zipfile.ZIP_STORED,
            ) as archive:
                archive.writestr("plain.txt", b"value")
            with zipfile.ZipFile(
                official,
                "w",
                zipfile.ZIP_STORED,
            ) as archive:
                archive.writestr("plain.txt", b"value\n")

            closure = {
                "kind": "dependency_runtime_closure",
                "runtime_closure_id": (
                    "DEPRUNTIMECLOSURE_" + "2" * 20
                ),
                "bundled_jar_sha256": _sha(bundled),
                "official_artifact_sha256": [_sha(official)],
                "summary": {
                    "reflection_dynamic_loading_unproven": True,
                },
                "resources": {
                    "artifacts": [
                        {
                            "artifact_id": (
                                "DEPCLOSUREARTIFACT_0001"
                            ),
                            "artifact": "official.jar",
                        }
                    ]
                },
                "identifiers_included": True,
            }
            closure_path = root / "closure.json"
            closure_path.write_text(
                json.dumps(closure) + "\n",
                encoding="utf-8",
            )

            report = build_dependency_runtime_resource_equivalence(
                closure_path,
                bundled,
                [official],
            )
            self.assertEqual(
                report["summary"]["status_counts"][
                    "byte_mismatch"
                ],
                1,
            )


if __name__ == "__main__":
    unittest.main()
