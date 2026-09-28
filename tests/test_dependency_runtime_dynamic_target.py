from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_runtime_dynamic_target import (
    DependencyRuntimeDynamicTargetError,
    build_dependency_runtime_dynamic_target_classification,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DependencyRuntimeDynamicTargetTests(unittest.TestCase):
    def _fixture(self, root: Path) -> dict:
        bundled = root / "bundled.jar"
        with zipfile.ZipFile(
            bundled,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            archive.writestr("dep/Replaceable.class", b"x")
            archive.writestr("dep/Residual.class", b"y")
            archive.writestr("dep/Unclassified.class", b"z")
            archive.writestr("rs/Client.class", b"p")
            archive.writestr("rs/pkg/Caller.class", b"q")
            archive.writestr(
                "META-INF/versions/9/dep/VersionOnly.class",
                b"v",
            )
            archive.writestr("rs/pkg/rel.txt", b"rel")
            archive.writestr("config/exact.txt", b"exact")

        bundled_sha = _sha(bundled)

        replacement = {
            "schema_version": 1,
            "kind": "dependency_replacement_boundary_plan",
            "replacement_plan_id": "DEPREPLACE_" + "1" * 20,
            "bundled_jar_sha256": bundled_sha,
            "project_prefixes": ["rs/"],
            "owners": [
                {
                    "owner_id": "DEPOWNER_00001",
                    "classification": "official_replaceable",
                    "old_owner": "dep/Replaceable",
                    "new_owner": "official/Replaceable",
                    "artifact": "official.jar",
                },
                {
                    "owner_id": "DEPOWNER_00002",
                    "classification": "residual_bundled",
                    "old_owner": "dep/Residual",
                    "new_owner": None,
                    "artifact": None,
                },
            ],
            "identifiers_included": True,
        }
        replacement_path = root / "replacement.json"
        replacement_path.write_text(
            json.dumps(replacement, indent=2) + "\n",
            encoding="utf-8",
        )

        resource_id = "DEPRUNTIMERESOURCE_" + "2" * 20
        resource = {
            "schema_version": 1,
            "kind": "dependency_runtime_resource_equivalence",
            "runtime_resource_id": resource_id,
            "bundled_jar_sha256": bundled_sha,
            "resources": [
                {
                    "resource_id": "DEPRUNTIME_RESOURCE_00001",
                    "entry": "config/exact.txt",
                    "status": "exact_byte_match",
                },
                {
                    "resource_id": "DEPRUNTIME_RESOURCE_00002",
                    "entry": "config/bad.txt",
                    "status": "byte_mismatch",
                },
            ],
            "identifiers_included": True,
        }
        resource_path = root / "resource.json"
        resource_path.write_text(
            json.dumps(resource, indent=2) + "\n",
            encoding="utf-8",
        )

        rows = [
            {
                "callsite_id": "DEPRUNTIME_DYNAMIC_00001",
                "category": "class_loading",
                "classification": "literal_target_proven",
                "literal_target_proven": True,
                "literal_target": "dep.Replaceable",
                "caller": "rs/Client",
                "caller_method": "a",
                "invoked_owner": "java/lang/Class",
                "invoked_name": "forName",
                "invoked_descriptor": (
                    "(Ljava/lang/String;)Ljava/lang/Class;"
                ),
            },
            {
                "callsite_id": "DEPRUNTIME_DYNAMIC_00002",
                "category": "class_loading",
                "classification": "literal_target_proven",
                "literal_target_proven": True,
                "literal_target": "dep.Residual",
                "caller": "rs/Client",
                "caller_method": "b",
                "invoked_owner": "java/lang/ClassLoader",
                "invoked_name": "loadClass",
                "invoked_descriptor": (
                    "(Ljava/lang/String;)Ljava/lang/Class;"
                ),
            },
            {
                "callsite_id": "DEPRUNTIME_DYNAMIC_00003",
                "category": "class_loading",
                "classification": "literal_target_proven",
                "literal_target_proven": True,
                "literal_target": "dep.Unclassified",
                "caller": "rs/Client",
                "caller_method": "c",
                "invoked_owner": "java/lang/Class",
                "invoked_name": "forName",
                "invoked_descriptor": "",
            },
            {
                "callsite_id": "DEPRUNTIME_DYNAMIC_00004",
                "category": "class_loading",
                "classification": "literal_target_proven",
                "literal_target_proven": True,
                "literal_target": "rs.Client",
                "caller": "rs/Client",
                "caller_method": "d",
                "invoked_owner": "java/lang/Class",
                "invoked_name": "forName",
                "invoked_descriptor": "",
            },
            {
                "callsite_id": "DEPRUNTIME_DYNAMIC_00005",
                "category": "class_loading",
                "classification": "literal_target_proven",
                "literal_target_proven": True,
                "literal_target": "java.lang.String",
                "caller": "rs/Client",
                "caller_method": "e",
                "invoked_owner": "java/lang/Class",
                "invoked_name": "forName",
                "invoked_descriptor": "",
            },
            {
                "callsite_id": "DEPRUNTIME_DYNAMIC_00006",
                "category": "class_loading",
                "classification": "literal_target_proven",
                "literal_target_proven": True,
                "literal_target": "dep.VersionOnly",
                "caller": "rs/Client",
                "caller_method": "f",
                "invoked_owner": "java/lang/Class",
                "invoked_name": "forName",
                "invoked_descriptor": "",
            },
            {
                "callsite_id": "DEPRUNTIME_DYNAMIC_00007",
                "category": "class_loading",
                "classification": "literal_target_proven",
                "literal_target_proven": True,
                "literal_target": "bad/name",
                "caller": "rs/Client",
                "caller_method": "g",
                "invoked_owner": "java/lang/Class",
                "invoked_name": "forName",
                "invoked_descriptor": "",
            },
            {
                "callsite_id": "DEPRUNTIME_DYNAMIC_00008",
                "category": "service_loading",
                "classification": "service_loader_class_token",
                "literal_target_proven": True,
                "literal_target": "dep/Residual",
                "caller": "rs/Client",
                "caller_method": "h",
                "invoked_owner": "java/util/ServiceLoader",
                "invoked_name": "load",
                "invoked_descriptor": "",
            },
            {
                "callsite_id": "DEPRUNTIME_DYNAMIC_00009",
                "category": "resource_loading",
                "classification": "literal_target_proven",
                "literal_target_proven": True,
                "literal_target": "/config/exact.txt",
                "caller": "rs/Client",
                "caller_method": "i",
                "invoked_owner": "java/lang/Class",
                "invoked_name": "getResource",
                "invoked_descriptor": "",
            },
            {
                "callsite_id": "DEPRUNTIME_DYNAMIC_00010",
                "category": "resource_loading",
                "classification": "literal_target_proven",
                "literal_target_proven": True,
                "literal_target": "rel.txt",
                "caller": "rs/pkg/Caller",
                "caller_method": "j",
                "invoked_owner": "java/lang/Class",
                "invoked_name": "getResourceAsStream",
                "invoked_descriptor": "",
            },
            {
                "callsite_id": "DEPRUNTIME_DYNAMIC_00011",
                "category": "resource_loading",
                "classification": "literal_target_proven",
                "literal_target_proven": True,
                "literal_target": "/leading.txt",
                "caller": "rs/Client",
                "caller_method": "k",
                "invoked_owner": "java/lang/ClassLoader",
                "invoked_name": "getResource",
                "invoked_descriptor": "",
            },
            {
                "callsite_id": "DEPRUNTIME_DYNAMIC_00012",
                "category": "native_loading",
                "classification": "native_load_literal",
                "literal_target_proven": True,
                "literal_target": "lwjgl",
                "caller": "rs/Client",
                "caller_method": "l",
                "invoked_owner": "java/lang/System",
                "invoked_name": "loadLibrary",
                "invoked_descriptor": "",
            },
            {
                "callsite_id": "DEPRUNTIME_DYNAMIC_00013",
                "category": "class_loading",
                "classification": "dynamic_target_unresolved",
                "literal_target_proven": False,
                "literal_target": None,
                "caller": "rs/Client",
                "caller_method": "m",
                "invoked_owner": "java/lang/Class",
                "invoked_name": "forName",
                "invoked_descriptor": "",
            },
        ]

        dynamic = {
            "schema_version": 1,
            "kind": "dependency_runtime_dynamic_inventory",
            "runtime_dynamic_id": "DEPRUNTIMEDYNAMIC_" + "3" * 20,
            "runtime_resource_id": resource_id,
            "bundled_jar_sha256": bundled_sha,
            "callsites": rows,
            "identifiers_included": True,
        }
        dynamic_path = root / "dynamic.json"
        dynamic_path.write_text(
            json.dumps(dynamic, indent=2) + "\n",
            encoding="utf-8",
        )

        return {
            "bundled": bundled,
            "replacement": replacement_path,
            "resource": resource_path,
            "resource_report": resource,
            "dynamic": dynamic_path,
            "dynamic_report": dynamic,
        }

    def _build(self, fx: dict, *, private: bool = False):
        return build_dependency_runtime_dynamic_target_classification(
            fx["dynamic"],
            fx["replacement"],
            fx["resource"],
            fx["bundled"],
            include_identifiers=private,
        )

    def test_classifies_proven_class_targets(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = self._build(fx)
            counts = report["summary"]["classification_counts"]

            self.assertEqual(
                counts["dependency_official_replaceable"],
                1,
            )
            self.assertEqual(
                counts["dependency_residual_bundled"],
                1,
            )
            self.assertEqual(
                counts["bundled_unclassified"],
                1,
            )
            self.assertEqual(counts["project_class"], 1)
            self.assertEqual(counts["platform_runtime"], 1)
            self.assertEqual(
                counts["bundled_multi_release_unresolved"],
                1,
            )
            self.assertEqual(
                counts["class_target_malformed"],
                1,
            )

    def test_classifies_service_resource_native_and_unresolved(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = self._build(fx)
            counts = report["summary"]["classification_counts"]

            self.assertEqual(
                counts["service_dependency_residual_bundled"],
                1,
            )
            self.assertEqual(
                counts["resource_official_equivalent"],
                1,
            )
            self.assertEqual(
                counts["resource_bundled_only"],
                1,
            )
            self.assertEqual(
                counts["resource_semantics_unresolved"],
                1,
            )
            self.assertEqual(
                counts["native_runtime_requirement"],
                1,
            )
            self.assertEqual(
                counts["dynamic_target_unresolved"],
                1,
            )
            self.assertTrue(
                report["summary"][
                    "service_provider_discovery_unproven"
                ]
            )
            self.assertTrue(
                report["summary"][
                    "native_artifact_equivalence_unproven"
                ]
            )
            self.assertFalse(
                report["summary"][
                    "runtime_capsule_mutation_ready"
                ]
            )
            self.assertEqual(
                report["summary"]["unresolved_or_blocked_count"],
                9,
            )

    def test_private_rows_preserve_exact_normalization(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = self._build(fx, private=True)
            by_call = {
                row["source_callsite_id"]: row
                for row in report["targets"]
            }
            self.assertEqual(
                by_call["DEPRUNTIME_DYNAMIC_00001"][
                    "normalized_class_target"
                ],
                "dep/Replaceable",
            )
            self.assertEqual(
                by_call["DEPRUNTIME_DYNAMIC_00009"][
                    "resource_entry"
                ],
                "config/exact.txt",
            )
            self.assertEqual(
                by_call["DEPRUNTIME_DYNAMIC_00010"][
                    "resource_entry"
                ],
                "rs/pkg/rel.txt",
            )

    def test_public_and_private_reports_share_id_and_redact_targets(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            public = self._build(fx)
            private = self._build(fx, private=True)
            self.assertEqual(
                public["runtime_dynamic_target_id"],
                private["runtime_dynamic_target_id"],
            )
            rendered = json.dumps(public)
            self.assertNotIn("dep.Replaceable", rendered)
            self.assertNotIn("config/exact.txt", rendered)
            self.assertNotIn("lwjgl", rendered)

    def test_authority_linkage_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            dynamic = fx["dynamic_report"]
            dynamic["runtime_resource_id"] = (
                "DEPRUNTIMERESOURCE_" + "9" * 20
            )
            fx["dynamic"].write_text(
                json.dumps(dynamic) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                DependencyRuntimeDynamicTargetError,
                "different runtime resource authority",
            ):
                self._build(fx)


if __name__ == "__main__":
    unittest.main()
