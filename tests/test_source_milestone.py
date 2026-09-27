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

    return {
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
