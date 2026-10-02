import copy
from pathlib import Path
import tempfile
import unittest

from spk_recovery.release_manifest import (
    RecoveryReleaseError,
    build_recovery_release_manifest,
)
from spk_recovery.release_manifest_cli import _load as _manifest_cli_load


AUTH = "a" * 64
READABLE = "b" * 64
TREE = "c" * 64
REBUILT = "d" * 64


def _class_lineage():
    return {
        "schema_version": 1,
        "namespace": "spawnpk-client",
        "id_format": "CLIENT_CLASS_%06d",
        "baseline_build_id": "v308",
        "builds": [
            {
                "build_id": "v308",
                "build_number": 308,
                "sha256": AUTH,
                "source_name": "client.jar",
                "authority": "EXACT_CURRENT_CLIENT",
            }
        ],
        "classes": [
            {
                "logical_id": "CLIENT_CLASS_000001",
                "semantic_name": "Example",
                "semantic_status": "ACCEPTED",
                "semantic_confidence": 0.95,
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": "rs/A",
                        "entry_path": "rs/A.class",
                        "entry_sha256": "1" * 64,
                        "structural_sha256": "2" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [],
            }
        ],
        "unresolved": [],
    }


def _member_lineage():
    return {
        "schema_version": 1,
        "kind": "member_lineage",
        "class_namespace": "spawnpk-client",
        "baseline_build_id": "v308",
        "source_sha256": AUTH,
        "members": [
            {
                "member_id": "CLIENT_METHOD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "method",
                "semantic_name": "work",
                "semantic_status": "ACCEPTED",
                "semantic_confidence": 0.9,
                "lineage": [
                    {
                        "build_id": "v308",
                        "owner_internal_name": "rs/A",
                        "name": "a",
                        "descriptor": "()V",
                        "access": 1,
                        "code_length": 4,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [],
            }
        ],
        "unresolved": [],
    }


def _docs():
    authority = {"sha256": AUTH}
    readable = {
        "schema_version": 1,
        "kind": "readable_client_build_manifest",
        "build_id": "v308",
        "namespace_id": "SEMNS_0123456789ABCDEF0123",
        "source_sha256": AUTH,
        "target_package": "recovered/spawnpk/client",
        "class_plan_digest": "3" * 64,
        "member_plan_digest": "4" * 64,
        "status": "complete",
        "output_sha256": READABLE,
        "verification_pass": True,
        "semantic_summary": {},
        "blocker": None,
        "artifact_names": {},
        "manifest_id": "READABLE_0123456789ABCDEF0123",
    }
    source = {
        "schema_version": 1,
        "kind": "recovered_source_workspace_manifest",
        "workspace_id": "SRCWS_0123456789ABCDEF0123",
        "build_id": "v308",
        "source_authority_sha256": AUTH,
        "readable_jar_sha256": READABLE,
        "namespace_id": "SEMNS_0123456789ABCDEF0123",
        "class_plan_digest": "3" * 64,
        "member_plan_digest": "4" * 64,
        "engine": "cfr",
        "decompiler_sha256": "5" * 64,
        "source_tree_sha256": TREE,
        "java_file_count": 1,
        "source_bytes": 100,
        "source_directory": "src",
    }
    clean = {
        "schema_version": 1,
        "kind": "clean_project_rebuild_report",
        "rebuild_id": "CLEANBUILD_0123456789ABCDEF0123",
        "status": "complete",
        "workspace_id": "SRCWS_0123456789ABCDEF0123",
        "build_id": "v308",
        "source_authority_sha256": AUTH,
        "readable_jar_sha256": READABLE,
        "namespace_id": "SEMNS_0123456789ABCDEF0123",
        "source_tree_sha256": TREE,
        "build_authority_id": "BUILDAUTH_TEST",
        "source_scope": {},
        "compiler": {},
        "dependency_capsule": {},
        "project_classes": {},
        "diagnostic": "",
        "rebuilt_client": {"sha256": REBUILT},
        "clean_project_build": True,
        "all_dependencies_rebuilt_from_source": False,
        "note": "",
    }
    roundtrip = {
        "schema_version": 1,
        "kind": "round_trip_verification_report",
        "verification_id": "ROUNDTRIP_0123456789ABCDEF0123",
        "rebuild_id": "CLEANBUILD_0123456789ABCDEF0123",
        "build_id": "v308",
        "workspace_id": "SRCWS_0123456789ABCDEF0123",
        "namespace_id": "SEMNS_0123456789ABCDEF0123",
        "source_authority_sha256": AUTH,
        "readable_jar_sha256": READABLE,
        "rebuilt_jar_sha256": REBUILT,
        "comparison": {},
        "rebuild_authority_candidate": {
            "ready": True,
            "project_binary_fallback_count": 0,
            "semantic_surface_blockers": 0,
            "byte_identical_class_count": 1,
            "structural_equivalent_class_count": 0,
            "codegen_variance_only_class_count": 0,
            "note": "",
        },
    }
    return authority, readable, source, clean, roundtrip


def _official_transport() -> dict:
    return {
        "mode": "official_first_restored",
        "opt_in": True,
        "status": "complete",
        "official_compile_id": "DEPOFFICIALCOMPILE_" + "1" * 20,
        "overlay_id": "DEPSRCOVERLAY_" + "2" * 20,
        "replacement_plan_id": "DEPREPLACE_" + "3" * 20,
        "reverse_plan_id": "DEPREVERSE_" + "4" * 20,
        "reverse_application_id": "DEPREVERSEAPPLY_" + "5" * 20,
        "official_artifact_sha256": ["a" * 64, "b" * 64],
        "compile_dependency_capsule_sha256": "c" * 64,
        "compile_dependency_capsule_class_count": 17,
        "generated_project_jar_sha256": "d" * 64,
        "restored_project_jar_sha256": "e" * 64,
        "project_binary_fallback_count": 0,
        "runtime_official_dependencies_allowed": False,
        "runtime_dependency_source": (
            "original_verified_readable_non_project_bytes"
        ),
        "canonical_source_modified": False,
        "bundled_runtime_dependency_modified": False,
        "restored_project_bytecode_ready_for_runtime_assembly": True,
    }


class RecoveryReleaseManifestTests(unittest.TestCase):
    def test_manifest_cli_loader_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "duplicate.json"
            path.write_text(
                '{"kind":"a","kind":"b"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                RecoveryReleaseError,
                "duplicate JSON key: 'kind'",
            ):
                _manifest_cli_load(path)

    def test_ready_manifest_is_deterministic(self):
        authority, readable, source, clean, roundtrip = _docs()
        args = (
            authority,
            _class_lineage(),
            _member_lineage(),
            readable,
            source,
            clean,
            roundtrip,
        )
        a = build_recovery_release_manifest(*args)
        b = build_recovery_release_manifest(*copy.deepcopy(args))
        self.assertEqual(a, b)
        self.assertTrue(a["ready_for_release"])
        self.assertEqual(a["blockers"], [])
        self.assertEqual(a["source_state"], "recovered")
        self.assertTrue(a["release_id"].startswith("RECOVERY_"))

    def test_official_first_release_authority_is_bound(self):
        authority, readable, source, clean, roundtrip = _docs()
        clean["compile_transport"] = _official_transport()

        manifest = build_recovery_release_manifest(
            authority,
            _class_lineage(),
            _member_lineage(),
            readable,
            source,
            clean,
            roundtrip,
        )

        self.assertTrue(manifest["ready_for_release"])
        self.assertEqual(manifest["blockers"], [])
        self.assertEqual(
            manifest["stage_ids"]["official_compile_id"],
            clean["compile_transport"]["official_compile_id"],
        )
        self.assertEqual(
            manifest["stage_ids"][
                "dependency_reverse_application_id"
            ],
            clean["compile_transport"]["reverse_application_id"],
        )

    def test_official_first_missing_authority_blocks_release(self):
        authority, readable, source, clean, roundtrip = _docs()
        clean["compile_transport"] = _official_transport()
        clean["compile_transport"]["reverse_plan_id"] = None

        manifest = build_recovery_release_manifest(
            authority,
            _class_lineage(),
            _member_lineage(),
            readable,
            source,
            clean,
            roundtrip,
        )

        self.assertFalse(manifest["ready_for_release"])
        self.assertIn(
            {
                "stage": "clean_rebuild",
                "reason": "official_first_transport_authority_incomplete",
            },
            manifest["blockers"],
        )

    def test_official_first_runtime_boundary_blocks_release(self):
        authority, readable, source, clean, roundtrip = _docs()
        clean["compile_transport"] = _official_transport()
        clean["compile_transport"][
            "runtime_official_dependencies_allowed"
        ] = True

        manifest = build_recovery_release_manifest(
            authority,
            _class_lineage(),
            _member_lineage(),
            readable,
            source,
            clean,
            roundtrip,
        )

        self.assertFalse(manifest["ready_for_release"])
        self.assertIn(
            {
                "stage": "clean_rebuild",
                "reason": "official_first_runtime_boundary_invalid",
            },
            manifest["blockers"],
        )

    def test_consistent_blocked_chain_returns_blocker(self):
        authority, readable, source, clean, roundtrip = _docs()
        clean["status"] = "compile_failed"
        clean["clean_project_build"] = False
        manifest = build_recovery_release_manifest(
            authority,
            _class_lineage(),
            _member_lineage(),
            readable,
            source,
            clean,
            roundtrip,
        )
        self.assertFalse(manifest["ready_for_release"])
        reasons = {row["reason"] for row in manifest["blockers"]}
        self.assertIn("clean_rebuild_not_complete", reasons)
        self.assertIn("project_binary_fallback_or_unclean_build", reasons)

    def test_mixed_authority_is_rejected(self):
        authority, readable, source, clean, roundtrip = _docs()
        source["source_authority_sha256"] = "f" * 64
        with self.assertRaises(RecoveryReleaseError):
            build_recovery_release_manifest(
                authority,
                _class_lineage(),
                _member_lineage(),
                readable,
                source,
                clean,
                roundtrip,
            )


if __name__ == "__main__":
    unittest.main()
