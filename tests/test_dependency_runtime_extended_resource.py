from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_runtime_extended_resource import (
    build_dependency_runtime_extended_resource,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DependencyRuntimeExtendedResourceTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        *,
        collide: bool = False,
    ) -> dict[str, Path]:
        bundled = root / "bundled.jar"
        with zipfile.ZipFile(
            bundled,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            archive.writestr("common.txt", b"same")
            archive.writestr("new.txt", b"new")
            archive.writestr(
                "META-INF/services/example.Service",
                b"impl.New\r\n",
            )
            archive.writestr("natives/example.dll", b"native")

        old = root / "old.jar"
        with zipfile.ZipFile(
            old,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            archive.writestr("common.txt", b"same")

        new = root / "new.jar"
        with zipfile.ZipFile(
            new,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            archive.writestr("new.txt", b"new")
            archive.writestr(
                "META-INF/services/example.Service",
                b"impl.New\n",
            )
            archive.writestr("natives/example.dll", b"native")
            if collide:
                archive.writestr("common.txt", b"other-provider")

        bundled_sha = _sha(bundled)
        old_sha = _sha(old)
        new_sha = _sha(new)
        closure_id = "DEPRUNTIMECLOSURE_" + "1" * 20

        original = {
            "schema_version": 1,
            "kind": "dependency_runtime_resource_equivalence",
            "runtime_resource_id": (
                "DEPRUNTIMERESOURCE_" + "2" * 20
            ),
            "runtime_closure_id": closure_id,
            "bundled_jar_sha256": bundled_sha,
            "official_artifact_sha256": sorted(
                [old_sha, new_sha]
            ),
            "summary": {
                "used_official_artifact_count": 1,
                "resource_entry_count": 1,
            },
            "artifacts": [
                {
                    "artifact_id": "DEPRUNTIMEARTIFACT_0001",
                    "artifact": "old.jar",
                    "sha256": old_sha,
                }
            ],
            "resources": [
                {
                    "resource_id": "DEPRUNTIME_RESOURCE_00001",
                    "status": "exact_byte_match",
                    "provider_count": 1,
                    "provider_artifact_ids": [
                        "DEPRUNTIMEARTIFACT_0001"
                    ],
                    "official_bytes": 4,
                    "bundled_present": True,
                    "bundled_bytes": 4,
                    "service_entry": False,
                    "native_entry": False,
                    "entry": "common.txt",
                    "providers": [
                        {
                            "artifact": "old.jar",
                            "sha256": hashlib.sha256(
                                b"same"
                            ).hexdigest(),
                            "bytes": 4,
                        }
                    ],
                    "bundled_sha256": hashlib.sha256(
                        b"same"
                    ).hexdigest(),
                }
            ],
            "identifiers_included": True,
        }
        original_path = root / "original-resource.json"
        original_path.write_text(
            json.dumps(original, indent=2) + "\n",
            encoding="utf-8",
        )

        extended = {
            "schema_version": 1,
            "kind": "dependency_runtime_extended_closure",
            "runtime_extended_closure_id": (
                "DEPRUNTIMEEXTCLOSURE_" + "3" * 20
            ),
            "replacement_plan_id": "DEPREPLACE_" + "4" * 20,
            "replacement_extension_id": (
                "DEPREPLACEEXT_" + "5" * 20
            ),
            "runtime_closure_id": closure_id,
            "runtime_dynamic_target_id": (
                "DEPRUNTIMEDYNAMICTARGET_" + "6" * 20
            ),
            "bundled_jar_sha256": bundled_sha,
            "official_artifact_sha256": sorted(
                [old_sha, new_sha]
            ),
            "summary": {
                "runtime_capsule_mutation_ready": False,
            },
            "dynamic_roots": [
                {
                    "extended_root_id": "ROOT_1",
                    "status": "authorized_dynamic_root",
                    "authority_source": "replacement_extension",
                    "owner": "old/Dynamic",
                    "new_owner": "official/Dynamic",
                    "artifact": "new.jar",
                }
            ],
            "new_owners": [],
            "new_edges": [],
            "identifiers_included": True,
        }
        extended_path = root / "extended-closure.json"
        extended_path.write_text(
            json.dumps(extended, indent=2) + "\n",
            encoding="utf-8",
        )

        return {
            "bundled": bundled,
            "old": old,
            "new": new,
            "original": original_path,
            "extended": extended_path,
        }

    def test_preserves_old_rows_and_audits_new_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = build_dependency_runtime_extended_resource(
                fx["extended"],
                fx["original"],
                fx["bundled"],
                [fx["old"], fx["new"]],
                include_identifiers=True,
            )

            summary = report["summary"]
            self.assertEqual(
                summary["original_audited_artifact_count"],
                1,
            )
            self.assertEqual(
                summary["extended_used_artifact_count"],
                2,
            )
            self.assertEqual(
                summary["newly_audited_artifact_count"],
                1,
            )
            self.assertTrue(
                summary["resource_equivalence_complete"]
            )
            self.assertEqual(summary["native_entry_count"], 1)
            self.assertTrue(
                summary["native_runtime_safety_unproven"]
            )
            self.assertEqual(
                summary["service_equivalent_count"],
                1,
            )

            by_entry = {
                row["entry"]: row
                for row in report["resources"]
            }
            self.assertEqual(
                by_entry["common.txt"]["audit_source"],
                "preserved_r8dep26",
            )
            self.assertEqual(
                by_entry["new.txt"]["audit_source"],
                "new_or_extended_artifact",
            )
            self.assertEqual(
                by_entry[
                    "META-INF/services/example.Service"
                ]["status"],
                "service_trailing_newline_equivalent",
            )

    def test_new_artifact_collision_becomes_new_blocker(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td), collide=True)
            report = build_dependency_runtime_extended_resource(
                fx["extended"],
                fx["original"],
                fx["bundled"],
                [fx["old"], fx["new"]],
                include_identifiers=True,
            )

            summary = report["summary"]
            self.assertFalse(
                summary["resource_equivalence_complete"]
            )
            self.assertGreaterEqual(
                summary["newly_introduced_blocker_count"],
                1,
            )
            by_entry = {
                row["entry"]: row
                for row in report["resources"]
            }
            self.assertEqual(
                by_entry["common.txt"]["status"],
                "ambiguous_official_path",
            )
            self.assertEqual(
                by_entry["common.txt"]["provider_count"],
                2,
            )

    def test_public_and_private_reports_share_id(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            public = build_dependency_runtime_extended_resource(
                fx["extended"],
                fx["original"],
                fx["bundled"],
                [fx["old"], fx["new"]],
            )
            private = build_dependency_runtime_extended_resource(
                fx["extended"],
                fx["original"],
                fx["bundled"],
                [fx["old"], fx["new"]],
                include_identifiers=True,
            )
            self.assertEqual(
                public["runtime_extended_resource_id"],
                private["runtime_extended_resource_id"],
            )
            rendered = json.dumps(public)
            self.assertNotIn("old.jar", rendered)
            self.assertNotIn("new.jar", rendered)


if __name__ == "__main__":
    unittest.main()
