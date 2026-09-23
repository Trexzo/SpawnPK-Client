from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery.readable_build import (
    _manifest,
    build_readable_client,
)


NAMESPACE = {
    "schema_version": 1,
    "kind": "semantic_namespace_manifest",
    "namespace_id": "SEMNS_1234567890ABCDEF1234",
    "build_id": "v308",
    "source_sha256": "a" * 64,
    "target_package": "recovered/spawnpk/client",
    "class_plan_digest": "c" * 64,
    "member_plan_digest": "d" * 64,
    "summary": {
        "classes_total": 1,
        "classes_accepted": 1,
        "classes_remapped": 1,
        "fields_total": 1,
        "fields_accepted": 0,
        "fields_remapped": 0,
        "methods_total": 1,
        "methods_accepted": 0,
        "methods_remapped": 0,
        "members_total": 2,
        "members_accepted": 0,
        "members_remapped": 0,
    },
}

CLASS_PLAN = {
    "schema_version": 1,
    "kind": "remap_plan",
    "source_sha256": "a" * 64,
    "class_count": 1,
    "classes": [],
}

MEMBER_PLAN_EMPTY = {
    "schema_version": 1,
    "kind": "member_remap_plan",
    "source_sha256": "a" * 64,
    "member_count": 0,
    "field_count": 0,
    "method_count": 0,
    "members": [],
}


class ReadableBuildTests(unittest.TestCase):
    def test_manifest_publishes_source_safe_project_prefixes(self):
        namespace = dict(NAMESPACE)
        namespace["summary"] = dict(NAMESPACE["summary"])
        namespace["summary"]["source_safety_fallbacks"] = 1
        namespace["source_safe_fallback"] = True
        namespace["fallback_name_prefix"] = "Recovered_"

        manifest = _manifest(
            namespace=namespace,
            status="complete",
            output_sha256="b" * 64,
            verification_pass=True,
            blocker=None,
        )

        self.assertTrue(manifest["source_safe_fallback"])
        self.assertEqual(
            manifest["fallback_name_prefix"],
            "Recovered_",
        )
        self.assertEqual(
            manifest["project_source_prefixes"],
            [
                "recovered/spawnpk/client/",
                "rs/",
            ],
        )


    def test_manifest_publishes_member_source_safety_metadata(self):
        namespace = dict(NAMESPACE)
        namespace["summary"] = dict(NAMESPACE["summary"])
        namespace["summary"]["source_safety_member_remaps"] = 3
        namespace["source_safe_member_fallback"] = True
        namespace["member_fallback_name_prefix"] = "Recovered_"

        manifest = _manifest(
            namespace=namespace,
            status="complete",
            output_sha256="b" * 64,
            verification_pass=True,
            blocker=None,
        )

        self.assertTrue(manifest["source_safe_member_fallback"])
        self.assertEqual(
            manifest["member_fallback_name_prefix"],
            "Recovered_",
        )
        self.assertEqual(
            manifest["semantic_summary"]["source_safety_member_remaps"],
            3,
        )

    def _source(self, root: Path) -> Path:
        path = root / "client.jar"
        path.write_bytes(b"jar")
        return path

    @patch("spk_recovery.readable_build.verify_transformed_jar")
    @patch("spk_recovery.readable_build.remap_jar")
    @patch("spk_recovery.readable_build.remap_risk_scan")
    @patch("spk_recovery.readable_build.build_semantic_namespace")
    def test_complete_build_writes_verified_manifest(
        self,
        semantic,
        risk,
        remap,
        verify,
    ):
        semantic.return_value = (NAMESPACE, CLASS_PLAN, MEMBER_PLAN_EMPTY)
        risk.return_value = {
            "summary": {
                "package_resource_hit_count": 0,
                "literal_class_name_hit_count": 0,
            }
        }
        remap.return_value = {
            "output_sha256": "b" * 64,
        }
        verify.return_value = {
            "pass": True,
            "issues": [],
        }

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "out"
            manifest = build_readable_client(
                self._source(root),
                {},
                {},
                {},
                build_id="v308",
                out_dir=out,
            )
            self.assertEqual(manifest["status"], "complete")
            self.assertTrue(manifest["verification_pass"])
            self.assertEqual(manifest["output_sha256"], "b" * 64)
            self.assertTrue((out / "readable-client-manifest.json").is_file())
            self.assertTrue((out / "semantic-namespace.json").is_file())
            self.assertTrue((out / "verification.json").is_file())

    @patch("spk_recovery.readable_build.build_member_safety_report")
    @patch("spk_recovery.readable_build.remap_risk_scan")
    @patch("spk_recovery.readable_build.build_semantic_namespace")
    def test_member_rewrite_blocks_without_safety_acceptance(
        self,
        semantic,
        risk,
        safety,
    ):
        member_plan = dict(MEMBER_PLAN_EMPTY)
        member_plan.update({
            "member_count": 1,
            "method_count": 1,
            "members": [{"member_id": "CLIENT_METHOD_000001"}],
        })
        namespace = dict(NAMESPACE)
        namespace["summary"] = dict(NAMESPACE["summary"])
        namespace["summary"]["methods_accepted"] = 1
        namespace["summary"]["methods_remapped"] = 1
        namespace["summary"]["members_accepted"] = 1
        namespace["summary"]["members_remapped"] = 1
        semantic.return_value = (namespace, CLASS_PLAN, member_plan)
        risk.return_value = {
            "summary": {
                "package_resource_hit_count": 0,
                "literal_class_name_hit_count": 0,
            }
        }
        safety.return_value = {
            "report_id": "MEMRISKREVIEW_1234567890ABCDEF1234",
            "member_count": 1,
        }

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "out"
            manifest = build_readable_client(
                self._source(root),
                {},
                {},
                {},
                build_id="v308",
                out_dir=out,
            )
            self.assertEqual(manifest["status"], "blocked")
            self.assertEqual(
                manifest["blocker"]["code"],
                "member_safety_acceptance_required",
            )
            self.assertFalse((out / "readable-client.jar").exists())
            self.assertTrue((out / "member-safety-report.json").is_file())

    @patch("spk_recovery.readable_build.remap_risk_scan")
    @patch("spk_recovery.readable_build.build_semantic_namespace")
    def test_class_resource_risk_blocks_before_rewrite(self, semantic, risk):
        semantic.return_value = (NAMESPACE, CLASS_PLAN, MEMBER_PLAN_EMPTY)
        risk.return_value = {
            "summary": {
                "package_resource_hit_count": 2,
                "literal_class_name_hit_count": 0,
            }
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = build_readable_client(
                self._source(root),
                {},
                {},
                {},
                build_id="v308",
                out_dir=root / "out",
            )
            self.assertEqual(manifest["status"], "blocked")
            self.assertEqual(
                manifest["blocker"]["code"],
                "class_package_resource_review_required",
            )


if __name__ == "__main__":
    unittest.main()
