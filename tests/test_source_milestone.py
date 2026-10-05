from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from spk_recovery.source_digest import source_tree_digest
from spk_recovery.source_milestone import (
    SourceMilestoneError,
    build_source_milestone_manifest,
    build_source_provenance_document,
    build_source_publication_bundle,
    verify_source_milestone_manifest,
    verify_source_publication_bundle,
)


def _document_digest(value) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _refresh_release_pins(fixture: dict) -> None:
    fixture["release_manifest"]["authority_pins"] = {
        "class_lineage_sha256": _document_digest(
            fixture["class_lineage"]
        ),
        "member_lineage_sha256": _document_digest(
            fixture["member_lineage"]
        ),
        "readable_manifest_sha256": _document_digest(
            fixture["readable_manifest"]
        ),
        "recovered_source_manifest_sha256": _document_digest(
            fixture["recovered_source_manifest"]
        ),
        "clean_rebuild_report_sha256": _document_digest(
            fixture["clean_rebuild_report"]
        ),
    }




def _release_verification_required_names(
    fixture: dict,
) -> set[str]:
    names = {"release_manifest_exact_reproduction"}
    transport = fixture["clean_rebuild_report"].get(
        "compile_transport"
    )
    mode = (
        transport.get("mode")
        if isinstance(transport, dict)
        else None
    )
    if mode == "collision_derived_remap":
        names.update(
            {
                "collision_private_plan_supplied",
                "collision_plan_id_authority",
                "collision_report_id_authority",
                "collision_transform_id_authority",
                "collision_base_readable_authority",
                "collision_private_plan_kind",
                "collision_private_plan_id",
                "collision_private_plan_report_id",
                "collision_private_plan_readable_sha256",
                "collision_private_plan_sha256",
                "collision_private_mapping_sha256",
            }
        )
        if transport.get("compile_only_platform_bridges"):
            names.update(
                {
                    "collision_platform_bridge_count",
                    "collision_platform_bridge_id",
                    "collision_platform_bridge_release",
                    "collision_platform_bridge_runtime_forbidden",
                    "collision_platform_bridge_transport_runtime_forbidden",
                    "collision_platform_bridge_v308_authority",
                    "collision_platform_bridge_source_authority",
                }
            )
    elif mode == "official_first_restored":
        names.update(
            {
                "official_overlay_manifest_supplied",
                "official_overlay_source_root_supplied",
                "official_private_replacement_plan_supplied",
                "official_private_reverse_plan_supplied",
                "official_artifacts_supplied",
                "official_overlay_id",
                "official_overlay_replacement_plan_id",
                "official_overlay_canonical_source_tree_sha256",
                "official_overlay_bundled_readable_sha256",
                "official_overlay_artifact_sha256",
                "official_overlay_source_tree_sha256",
                "official_private_replacement_identifiers",
                "official_private_replacement_plan_id",
                "official_private_replacement_bundled_readable_sha256",
                "official_private_replacement_artifact_sha256",
                "official_private_reverse_identifiers",
                "official_private_reverse_plan_id",
                "official_private_reverse_replacement_plan_id",
                "official_private_reverse_bundled_readable_sha256",
                "official_private_reverse_bytecode_restore_ready",
                "official_artifact_file_sha256",
            }
        )
    return names


def _release_verification_id(report: dict) -> str:
    material = {
        "release_id": report["release_id"],
        "checks": [
            (
                row["name"],
                row["required"],
                row["passed"],
                row.get("expected"),
                row.get("actual"),
            )
            for row in report["checks"]
        ],
    }
    raw = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "REPRO_" + hashlib.sha256(raw).hexdigest()[:20].upper()


def _refresh_release_verification(fixture: dict) -> None:
    release = fixture["release_manifest"]
    checks = [
        {
            "name": "release_manifest_exact_reproduction",
            "required": True,
            "passed": True,
            "expected": release,
            "actual": release,
        }
    ]
    for name in sorted(
        _release_verification_required_names(fixture)
        - {"release_manifest_exact_reproduction"}
    ):
        checks.append(
            {
                "name": name,
                "required": True,
                "passed": True,
                "expected": True,
                "actual": True,
            }
        )
    report = {
        "schema_version": 1,
        "kind": "recovery_release_verification",
        "verification_id": "",
        "release_id": release["release_id"],
        "release_ready": True,
        "verified": True,
        "required_check_count": len(checks),
        "failed_required_check_count": 0,
        "checks": checks,
        "toolchain_probe": None,
    }
    report["verification_id"] = _release_verification_id(
        report
    )
    fixture["release_verification"] = report


def _fixtures(source_root: Path):
    source_root.mkdir(parents=True)
    (source_root / "rs").mkdir()
    (source_root / "rs" / "A.java").write_text(
        "package rs; public class A {}\n",
        encoding="utf-8",
    )
    tree_sha, files, source_bytes = source_tree_digest(
        source_root
    )

    authority_sha = "a" * 64
    namespace_id = "SEMNS_" + "B" * 20
    class_digest = "c" * 64
    member_digest = "d" * 64

    classes = {
        "classes": [
            {
                "semantic_status": "ACCEPTED",
                "semantic_provenance": [
                    {"review_id": "SEMREVIEW_CLASS"}
                ],
            },
            {
                "semantic_status": "UNREVIEWED",
                "semantic_provenance": [],
            },
        ],
    }
    members = {
        "members": [
            {
                "semantic_status": "ACCEPTED",
                "semantic_provenance": [
                    {"review_id": "SEMREVIEW_MEMBER"},
                    {"review_id": "SEMREVIEW_CLASS"},
                ],
            }
        ],
    }

    readable = {
        "schema_version": 1,
        "kind": "readable_client_build_manifest",
        "build_id": "v308",
        "manifest_id": "READABLE_TEST",
        "namespace_id": namespace_id,
        "source_sha256": authority_sha,
        "class_plan_digest": class_digest,
        "member_plan_digest": member_digest,
        "source_safe_fallback": True,
        "fallback_name_prefix": "Recovered_",
    }
    recovered = {
        "schema_version": 1,
        "kind": "recovered_source_workspace_manifest",
        "workspace_id": "SRCWS_TEST",
        "build_id": "v308",
        "namespace_id": namespace_id,
        "source_authority_sha256": authority_sha,
        "class_plan_digest": class_digest,
        "member_plan_digest": member_digest,
        "source_tree_sha256": tree_sha,
        "collision_transform_id": "COLLTRANS_TEST",
        "collision_plan_id": "JNSPLAN_TEST",
        "collision_report_id": "JNSCOLLISION_TEST",
        "collision_mapping_sha256": "f" * 64,
        "base_readable_jar_sha256": "b" * 64,
    }
    clean = {
        "schema_version": 1,
        "kind": "clean_project_rebuild_report",
        "rebuild_id": "CLEANBUILD_TEST",
        "status": "complete",
        "build_id": "v308",
        "namespace_id": namespace_id,
        "source_authority_sha256": authority_sha,
        "build_authority_id": "BUILDAUTH_TEST",
        "clean_project_build": True,
        "project_classes": {
            "expected_count": 1,
            "generated_count": 1,
            "missing": [],
            "unexpected": [],
            "binary_fallback_count": 0,
        },
        "compile_transport": {
            "mode": "collision_derived_remap",
            "collision_compile_id": "COLLCOMPILE_TEST",
            "collision_transform_id": "COLLTRANS_TEST",
            "collision_plan_id": "JNSPLAN_TEST",
            "collision_plan_sha256": "e" * 64,
            "collision_report_id": "JNSCOLLISION_TEST",
        },
    }
    release = {
        "schema_version": 1,
        "kind": "recovery_release_manifest",
        "release_id": "RECOVERY_TEST",
        "build_id": "v308",
        "authority_sha256": authority_sha,
        "namespace_id": namespace_id,
        "final_source_tree_sha256": tree_sha,
        "ready_for_release": True,
    }
    verification = {
        "schema_version": 1,
        "kind": "recovery_release_verification",
        "verification_id": "REPRO_TEST",
        "release_id": "RECOVERY_TEST",
        "verified": True,
    }

    fixture = {
        "class_lineage": classes,
        "member_lineage": members,
        "readable_manifest": readable,
        "recovered_source_manifest": recovered,
        "clean_rebuild_report": clean,
        "release_manifest": release,
        "release_verification": verification,
        "source_tree_sha256": tree_sha,
        "source_files": files,
        "source_bytes": source_bytes,
    }
    _refresh_release_pins(fixture)
    _refresh_release_verification(fixture)
    return fixture


class SourceMilestoneTests(unittest.TestCase):
    def _build(self, root: Path, fixture: dict):
        return build_source_milestone_manifest(
            authority_commit="f" * 40,
            class_lineage=fixture["class_lineage"],
            member_lineage=fixture["member_lineage"],
            readable_manifest=fixture["readable_manifest"],
            recovered_source_manifest=fixture[
                "recovered_source_manifest"
            ],
            clean_rebuild_report=fixture[
                "clean_rebuild_report"
            ],
            release_manifest=fixture["release_manifest"],
            release_verification=fixture[
                "release_verification"
            ],
            source_root=root,
        )

    def _official_transport(self) -> dict:
        return {
            "mode": "official_first_restored",
            "opt_in": True,
            "status": "complete",
            "official_compile_id": (
                "DEPOFFICIALCOMPILE_" + "1" * 20
            ),
            "overlay_id": "DEPSRCOVERLAY_" + "2" * 20,
            "replacement_plan_id": "DEPREPLACE_" + "3" * 20,
            "reverse_plan_id": "DEPREVERSE_" + "4" * 20,
            "reverse_application_id": (
                "DEPREVERSEAPPLY_" + "5" * 20
            ),
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

    def test_publishable_manifest_binds_all_hard_gates(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)

            manifest = self._build(source, fixture)

            self.assertTrue(manifest["publishable"])
            self.assertEqual(manifest["blockers"], [])
            self.assertEqual(
                manifest["source_tree"]["sha256"],
                fixture["source_tree_sha256"],
            )
            self.assertEqual(
                manifest["class_set"],
                {
                    "expected_count": 1,
                    "generated_count": 1,
                    "missing_count": 0,
                    "unexpected_count": 0,
                    "binary_fallback_count": 0,
                    "exact_match": True,
                },
            )
            self.assertEqual(
                manifest["provenance"]["semantic_review_ids"],
                [
                    "SEMREVIEW_CLASS",
                    "SEMREVIEW_MEMBER",
                ],
            )
            self.assertEqual(
                manifest["provenance"]["authority_commit"],
                "f" * 40,
            )
            self.assertEqual(
                manifest["publication"]["target_repository"],
                "Trexzo/SpawnPK-Client-Source",
            )
            evidence = manifest["provenance"][
                "release_verification_evidence"
            ]
            self.assertTrue(
                evidence["exact_release_manifest_reproduction"]
            )
            self.assertEqual(
                evidence["failed_required_check_count"],
                0,
            )
            provenance = build_source_provenance_document(
                manifest
            )
            self.assertEqual(
                provenance["recovery_authority"][
                    "release_verification_evidence"
                ],
                evidence,
            )

    def test_empty_java_source_tree_blocks_publication(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            (source / "rs" / "A.java").unlink()

            tree_sha, files, source_bytes = source_tree_digest(
                source
            )
            self.assertEqual(files, [])
            self.assertEqual(source_bytes, 0)

            fixture["recovered_source_manifest"][
                "source_tree_sha256"
            ] = tree_sha
            fixture["release_manifest"][
                "final_source_tree_sha256"
            ] = tree_sha
            fixture["clean_rebuild_report"][
                "project_classes"
            ]["expected_count"] = 0
            fixture["clean_rebuild_report"][
                "project_classes"
            ]["generated_count"] = 0
            _refresh_release_pins(fixture)
            _refresh_release_verification(fixture)

            manifest = self._build(source, fixture)

            self.assertFalse(manifest["publishable"])
            self.assertEqual(
                manifest["source_tree"]["java_file_count"],
                0,
            )
            self.assertTrue(manifest["class_set"]["exact_match"])
            self.assertIn(
                {
                    "gate": "source_tree",
                    "reason": "source_tree_contains_no_java_files",
                },
                manifest["blockers"],
            )

    def test_release_authority_pins_bind_supplied_documents(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)

            manifest = self._build(source, fixture)

            self.assertTrue(manifest["publishable"])
            linked = manifest["provenance"]["release_authority_pins"]
            expected = fixture["release_manifest"]["authority_pins"]
            for key in (
                "class_lineage_sha256",
                "member_lineage_sha256",
                "readable_manifest_sha256",
                "recovered_source_manifest_sha256",
                "clean_rebuild_report_sha256",
            ):
                self.assertEqual(linked[key], expected[key])

    def test_class_lineage_pin_drift_blocks_publication(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            fixture["class_lineage"]["pin_drift"] = True

            manifest = self._build(source, fixture)

            self.assertFalse(manifest["publishable"])
            self.assertIn(
                {
                    "gate": "release_authority_pins",
                    "reason": "release_authority_pin_mismatch",
                },
                manifest["blockers"],
            )

    def test_readable_manifest_pin_drift_blocks_publication(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            fixture["readable_manifest"]["pin_drift"] = True

            manifest = self._build(source, fixture)

            self.assertFalse(manifest["publishable"])
            self.assertIn(
                {
                    "gate": "release_authority_pins",
                    "reason": "release_authority_pin_mismatch",
                },
                manifest["blockers"],
            )

    def test_clean_rebuild_pin_drift_blocks_publication(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            fixture["clean_rebuild_report"]["pin_drift"] = True

            manifest = self._build(source, fixture)

            self.assertFalse(manifest["publishable"])
            self.assertIn(
                {
                    "gate": "release_authority_pins",
                    "reason": "release_authority_pin_mismatch",
                },
                manifest["blockers"],
            )

    def test_missing_release_authority_pins_blocks_publication(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            fixture["release_manifest"].pop("authority_pins")

            manifest = self._build(source, fixture)

            self.assertFalse(manifest["publishable"])
            self.assertIn(
                {
                    "gate": "release_authority_pins",
                    "reason": "release_authority_pins_missing",
                },
                manifest["blockers"],
            )

    def test_minimal_release_verification_blocks_publication(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            fixture["release_verification"] = {
                "schema_version": 1,
                "kind": "recovery_release_verification",
                "verification_id": "REPRO_MINIMAL",
                "release_id": "RECOVERY_TEST",
                "verified": True,
            }

            manifest = self._build(source, fixture)

            self.assertFalse(manifest["publishable"])
            self.assertIn(
                {
                    "gate": "release_authority",
                    "reason": "release_verification_structure_invalid",
                },
                manifest["blockers"],
            )

    def test_release_verification_passed_flag_must_match_values(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            report = fixture["release_verification"]
            report["checks"][1]["actual"] = "drift"
            report["checks"][1]["passed"] = True
            report["verification_id"] = _release_verification_id(
                report
            )

            manifest = self._build(source, fixture)

            self.assertFalse(manifest["publishable"])
            self.assertIn(
                {
                    "gate": "release_authority",
                    "reason": "release_verification_structure_invalid",
                },
                manifest["blockers"],
            )

    def test_failed_required_release_check_blocks_publication(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            report = fixture["release_verification"]
            report["checks"][1]["actual"] = "drift"
            report["checks"][1]["passed"] = False
            report["failed_required_check_count"] = 1
            report["verified"] = False
            report["verification_id"] = _release_verification_id(
                report
            )

            manifest = self._build(source, fixture)

            self.assertFalse(manifest["publishable"])
            self.assertIn(
                {
                    "gate": "release_authority",
                    "reason": "release_verification_required_checks_failed",
                },
                manifest["blockers"],
            )

    def test_release_manifest_reproduction_drift_blocks_publication(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            report = fixture["release_verification"]
            report["checks"][0]["actual"] = {
                "kind": "drifted_release_manifest"
            }
            report["checks"][0]["passed"] = False
            report["failed_required_check_count"] = 1
            report["verified"] = False
            report["verification_id"] = _release_verification_id(
                report
            )

            manifest = self._build(source, fixture)

            self.assertFalse(manifest["publishable"])
            self.assertIn(
                {
                    "gate": "release_authority",
                    "reason": (
                        "release_verification_manifest_reproduction_invalid"
                    ),
                },
                manifest["blockers"],
            )

    def test_missing_collision_verification_evidence_blocks_publication(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            report = fixture["release_verification"]
            report["checks"] = [
                row
                for row in report["checks"]
                if row["name"] != "collision_private_mapping_sha256"
            ]
            report["required_check_count"] = len(
                report["checks"]
            )
            report["verification_id"] = _release_verification_id(
                report
            )

            manifest = self._build(source, fixture)

            self.assertFalse(manifest["publishable"])
            self.assertIn(
                {
                    "gate": "release_authority",
                    "reason": (
                        "release_verification_mode_evidence_incomplete"
                    ),
                },
                manifest["blockers"],
            )

    def test_release_verification_id_drift_blocks_publication(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            fixture["release_verification"][
                "verification_id"
            ] = "REPRO_" + "0" * 20

            manifest = self._build(source, fixture)

            self.assertFalse(manifest["publishable"])
            self.assertIn(
                {
                    "gate": "release_authority",
                    "reason": "release_verification_id_mismatch",
                },
                manifest["blockers"],
            )

    def test_collision_provenance_binds_recovered_source_authority(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)

            manifest = self._build(source, fixture)

            self.assertTrue(manifest["publishable"])
            collision = manifest["provenance"]["collision_provenance"]
            self.assertEqual(
                collision["collision_transform_id"],
                fixture["recovered_source_manifest"][
                    "collision_transform_id"
                ],
            )
            self.assertEqual(
                collision["collision_plan_id"],
                fixture["recovered_source_manifest"]["collision_plan_id"],
            )
            self.assertEqual(
                collision["collision_report_id"],
                fixture["recovered_source_manifest"][
                    "collision_report_id"
                ],
            )
            self.assertEqual(
                collision["collision_mapping_sha256"],
                fixture["recovered_source_manifest"][
                    "collision_mapping_sha256"
                ],
            )
            self.assertEqual(
                collision["base_readable_jar_sha256"],
                fixture["recovered_source_manifest"][
                    "base_readable_jar_sha256"
                ],
            )

    def test_collision_authority_mismatch_blocks_publication(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            fixture["recovered_source_manifest"][
                "collision_report_id"
            ] = "JNSCOLLISION_OTHER"

            manifest = self._build(source, fixture)

            self.assertFalse(manifest["publishable"])
            self.assertIn(
                {
                    "gate": "collision_compile_transport",
                    "reason": "collision_stage_authority_mismatch",
                },
                manifest["blockers"],
            )

    def test_missing_collision_mapping_commitment_blocks_publication(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            fixture["recovered_source_manifest"].pop(
                "collision_mapping_sha256"
            )

            manifest = self._build(source, fixture)

            self.assertFalse(manifest["publishable"])
            reasons = {
                row["reason"]
                for row in manifest["blockers"]
                if row["gate"] == "collision_compile_transport"
            }
            self.assertIn(
                "collision_source_authority_incomplete",
                reasons,
            )
            self.assertIn(
                "collision_mapping_commitment_invalid",
                reasons,
            )

    def test_official_first_dependency_provenance_is_bound(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            transport = self._official_transport()
            for key in (
                "collision_transform_id",
                "collision_plan_id",
                "collision_report_id",
                "collision_mapping_sha256",
                "base_readable_jar_sha256",
            ):
                fixture["recovered_source_manifest"].pop(key, None)
            fixture["clean_rebuild_report"][
                "compile_transport"
            ] = transport
            _refresh_release_pins(fixture)
            _refresh_release_verification(fixture)

            manifest = self._build(source, fixture)

            self.assertTrue(manifest["publishable"])
            self.assertEqual(manifest["blockers"], [])
            dependency = manifest["provenance"][
                "dependency_transport_provenance"
            ]
            self.assertEqual(
                dependency["official_compile_id"],
                transport["official_compile_id"],
            )
            self.assertEqual(
                dependency["reverse_application_id"],
                transport["reverse_application_id"],
            )
            self.assertEqual(
                dependency["official_artifact_sha256"],
                transport["official_artifact_sha256"],
            )
            self.assertFalse(
                dependency["runtime_official_dependencies_allowed"]
            )
            self.assertTrue(
                dependency[
                    "restored_project_bytecode_ready_for_runtime_assembly"
                ]
            )

            provenance = build_source_provenance_document(
                manifest
            )
            self.assertEqual(
                provenance["recovery_authority"][
                    "dependency_transport_provenance"
                ],
                dependency,
            )

    def test_official_first_missing_authority_blocks_publication(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            transport = self._official_transport()
            transport["reverse_plan_id"] = None
            for key in (
                "collision_transform_id",
                "collision_plan_id",
                "collision_report_id",
                "collision_mapping_sha256",
                "base_readable_jar_sha256",
            ):
                fixture["recovered_source_manifest"].pop(key, None)
            fixture["clean_rebuild_report"][
                "compile_transport"
            ] = transport
            _refresh_release_pins(fixture)
            _refresh_release_verification(fixture)

            manifest = self._build(source, fixture)

            self.assertFalse(manifest["publishable"])
            self.assertIn(
                {
                    "gate": "dependency_compile_transport",
                    "reason": (
                        "official_first_transport_authority_incomplete"
                    ),
                },
                manifest["blockers"],
            )

    def test_official_first_runtime_boundary_blocks_publication(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            transport = self._official_transport()
            transport["runtime_official_dependencies_allowed"] = True
            for key in (
                "collision_transform_id",
                "collision_plan_id",
                "collision_report_id",
                "collision_mapping_sha256",
                "base_readable_jar_sha256",
            ):
                fixture["recovered_source_manifest"].pop(key, None)
            fixture["clean_rebuild_report"][
                "compile_transport"
            ] = transport
            _refresh_release_pins(fixture)
            _refresh_release_verification(fixture)

            manifest = self._build(source, fixture)

            self.assertFalse(manifest["publishable"])
            self.assertIn(
                {
                    "gate": "dependency_compile_transport",
                    "reason": "official_first_runtime_boundary_invalid",
                },
                manifest["blockers"],
            )

    def test_exact_verifier_rejects_source_drift(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            manifest = self._build(source, fixture)

            exact = verify_source_milestone_manifest(
                manifest,
                authority_commit="f" * 40,
                class_lineage=fixture["class_lineage"],
                member_lineage=fixture["member_lineage"],
                readable_manifest=fixture["readable_manifest"],
                recovered_source_manifest=fixture[
                    "recovered_source_manifest"
                ],
                clean_rebuild_report=fixture[
                    "clean_rebuild_report"
                ],
                release_manifest=fixture["release_manifest"],
                release_verification=fixture[
                    "release_verification"
                ],
                source_root=source,
            )
            self.assertTrue(exact["verified"])
            self.assertTrue(exact["publishable"])

            (source / "rs" / "A.java").write_text(
                "package rs; public class A { int x; }\n",
                encoding="utf-8",
            )
            drift = verify_source_milestone_manifest(
                manifest,
                authority_commit="f" * 40,
                class_lineage=fixture["class_lineage"],
                member_lineage=fixture["member_lineage"],
                readable_manifest=fixture["readable_manifest"],
                recovered_source_manifest=fixture[
                    "recovered_source_manifest"
                ],
                clean_rebuild_report=fixture[
                    "clean_rebuild_report"
                ],
                release_manifest=fixture["release_manifest"],
                release_verification=fixture[
                    "release_verification"
                ],
                source_root=source,
            )
            self.assertFalse(drift["verified"])
            self.assertFalse(drift["publishable"])

    def test_blocked_manifest_refuses_publication_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            fixture["clean_rebuild_report"][
                "project_classes"
            ]["binary_fallback_count"] = 1

            manifest = self._build(source, fixture)
            self.assertFalse(manifest["publishable"])
            reasons = {
                row["reason"] for row in manifest["blockers"]
            }
            self.assertIn(
                "project_binary_fallback_present",
                reasons,
            )

            with self.assertRaisesRegex(
                SourceMilestoneError,
                "not publishable",
            ):
                build_source_publication_bundle(
                    manifest,
                    source,
                    Path(td) / "bundle",
                    provenance_documents={},
                )

    def test_flipped_publishable_blocked_manifest_refuses_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            fixture["clean_rebuild_report"][
                "project_classes"
            ]["binary_fallback_count"] = 1
            manifest = self._build(source, fixture)
            self.assertFalse(manifest["publishable"])
            self.assertTrue(manifest["blockers"])

            manifest["publishable"] = True

            with self.assertRaisesRegex(
                SourceMilestoneError,
                "publication state is inconsistent",
            ):
                build_source_publication_bundle(
                    manifest,
                    source,
                    Path(td) / "bundle",
                    provenance_documents={},
                )

    def test_publication_allowed_must_match_publishable_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            manifest = self._build(source, fixture)
            self.assertTrue(manifest["publishable"])

            manifest["publication"]["allowed"] = False

            with self.assertRaisesRegex(
                SourceMilestoneError,
                "publication state is inconsistent",
            ):
                build_source_publication_bundle(
                    manifest,
                    source,
                    Path(td) / "bundle",
                    provenance_documents={},
                )

    def test_publication_bundle_rejects_milestone_identity_drift(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            manifest = self._build(source, fixture)
            self.assertTrue(manifest["publishable"])

            manifest["milestone_id"] = (
                "SRCMILESTONE_" + "0" * 20
            )

            with self.assertRaisesRegex(
                SourceMilestoneError,
                "source milestone identity mismatch",
            ):
                build_source_publication_bundle(
                    manifest,
                    source,
                    Path(td) / "bundle",
                    provenance_documents={},
                )

    def test_provenance_document_is_deterministic_and_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            manifest = self._build(source, fixture)

            first = build_source_provenance_document(
                manifest
            )
            second = build_source_provenance_document(
                manifest
            )

            self.assertEqual(first, second)
            self.assertTrue(
                first["provenance_id"].startswith("SRCPROV_")
            )
            self.assertEqual(
                first["authority"]["commit"],
                "f" * 40,
            )
            self.assertEqual(
                first["semantic_authority"]["review_ids"],
                [
                    "SEMREVIEW_CLASS",
                    "SEMREVIEW_MEMBER",
                ],
            )
            self.assertEqual(
                first["source_authority"]["tree_sha256"],
                fixture["source_tree_sha256"],
            )
            self.assertIn(
                "does not claim",
                first["semantic_name_statement"],
            )

    def test_bundle_refuses_provenance_override(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            manifest = self._build(source, fixture)

            with self.assertRaisesRegex(
                SourceMilestoneError,
                "cannot be overridden",
            ):
                build_source_publication_bundle(
                    manifest,
                    source,
                    Path(td) / "bundle",
                    provenance_documents={
                        "SOURCE-PROVENANCE.json": {},
                    },
                )

    def test_source_only_bundle_is_deterministic_and_excludes_binary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixtures(source)
            (source / "ignored.class").write_bytes(b"binary")
            (source / "README.txt").write_text(
                "not source\n",
                encoding="utf-8",
            )

            manifest = self._build(source, fixture)
            bundle = build_source_publication_bundle(
                manifest,
                source,
                root / "bundle",
                provenance_documents={
                    "recovery-release.json": fixture[
                        "release_manifest"
                    ],
                    "release-verification.json": fixture[
                        "release_verification"
                    ],
                },
            )

            self.assertFalse(bundle["contains_binary_artifacts"])
            self.assertEqual(bundle["source_file_count"], 1)
            self.assertTrue(
                (root / "bundle" / "src" / "rs" / "A.java").is_file()
            )
            self.assertFalse(
                (root / "bundle" / "src" / "ignored.class").exists()
            )
            self.assertFalse(
                (root / "bundle" / "src" / "README.txt").exists()
            )
            self.assertTrue(
                (
                    root
                    / "bundle"
                    / "provenance"
                    / "recovery-release.json"
                ).is_file()
            )
            provenance_path = (
                root
                / "bundle"
                / "provenance"
                / "SOURCE-PROVENANCE.json"
            )
            self.assertTrue(provenance_path.is_file())
            provenance = json.loads(
                provenance_path.read_text(encoding="utf-8")
            )
            self.assertEqual(
                provenance["milestone_id"],
                manifest["milestone_id"],
            )
            self.assertIn(
                "SOURCE-PROVENANCE.json",
                bundle["provenance_documents"],
            )

    def test_publication_bundle_verifier_accepts_exact_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixtures(source)
            manifest = self._build(source, fixture)
            bundle_root = root / "bundle"

            build_source_publication_bundle(
                manifest,
                source,
                bundle_root,
                provenance_documents={
                    "recovery-release.json": fixture[
                        "release_manifest"
                    ],
                    "release-verification.json": fixture[
                        "release_verification"
                    ],
                },
            )

            report = verify_source_publication_bundle(
                bundle_root,
                expected_manifest=manifest,
            )
            second = verify_source_publication_bundle(
                bundle_root,
                expected_manifest=manifest,
            )

            self.assertTrue(report["verified"])
            self.assertEqual(report, second)
            self.assertTrue(
                report["verification_id"].startswith(
                    "SRCBUNDLEVERIFY_"
                )
            )
            self.assertTrue(
                all(report["checks"].values())
            )

    def test_publication_bundle_verifier_rejects_source_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixtures(source)
            manifest = self._build(source, fixture)
            bundle_root = root / "bundle"

            build_source_publication_bundle(
                manifest,
                source,
                bundle_root,
                provenance_documents={},
            )

            target = bundle_root / "src" / "rs" / "A.java"
            target.write_text(
                "package rs; public class A { int drift; }\n",
                encoding="utf-8",
            )

            report = verify_source_publication_bundle(
                bundle_root,
                expected_manifest=manifest,
            )

            self.assertFalse(report["verified"])
            self.assertFalse(
                report["checks"]["source_tree_sha256_match"]
            )
            self.assertFalse(
                report["checks"]["indexed_file_hashes_match"]
            )

    def test_publication_bundle_verifier_rejects_unindexed_binary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixtures(source)
            manifest = self._build(source, fixture)
            bundle_root = root / "bundle"

            build_source_publication_bundle(
                manifest,
                source,
                bundle_root,
                provenance_documents={},
            )

            (bundle_root / "payload.jar").write_bytes(b"binary")

            report = verify_source_publication_bundle(
                bundle_root,
                expected_manifest=manifest,
            )

            self.assertFalse(report["verified"])
            self.assertFalse(
                report["checks"]["source_only_layout"]
            )
            self.assertFalse(
                report["checks"]["indexed_file_set_match"]
            )

    def test_wrong_build_is_never_publishable(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)
            fixture["release_manifest"]["build_id"] = "v309"

            manifest = self._build(source, fixture)

            self.assertFalse(manifest["publishable"])
            self.assertIn(
                {
                    "gate": "exact_authority",
                    "reason": "source_milestone_requires_exact_v308",
                },
                manifest["blockers"],
            )

    def test_authority_commit_must_be_exact_git_sha(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            fixture = _fixtures(source)

            with self.assertRaisesRegex(
                SourceMilestoneError,
                "40-hex",
            ):
                build_source_milestone_manifest(
                    authority_commit="main",
                    class_lineage=fixture["class_lineage"],
                    member_lineage=fixture["member_lineage"],
                    readable_manifest=fixture[
                        "readable_manifest"
                    ],
                    recovered_source_manifest=fixture[
                        "recovered_source_manifest"
                    ],
                    clean_rebuild_report=fixture[
                        "clean_rebuild_report"
                    ],
                    release_manifest=fixture[
                        "release_manifest"
                    ],
                    release_verification=fixture[
                        "release_verification"
                    ],
                    source_root=source,
                )


if __name__ == "__main__":
    unittest.main()
