from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from spk_recovery.source_authority_artifact import (
    SourceAuthorityArtifactError,
    build_source_authority_artifact,
    verify_source_authority_artifact as _verify_source_authority_artifact,
)
from spk_recovery.source_digest import source_tree_digest
from spk_recovery.source_milestone import V308_SOURCE_AUTHORITY_SHA256


def verify_source_authority_artifact(artifact_dir, **kwargs):
    kwargs.setdefault("expected_authority_commit", "f" * 40)
    if "expected_milestone_id" not in kwargs:
        manifest = json.loads(
            (
                Path(artifact_dir)
                / "SOURCE-AUTHORITY-ARTIFACT.json"
            ).read_text(encoding="utf-8")
        )
        kwargs["expected_milestone_id"] = manifest[
            "preflight_milestone_id"
        ]
    return _verify_source_authority_artifact(
        artifact_dir,
        **kwargs,
    )


def _document_digest(value) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()




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
    names = [
        "release_manifest_exact_reproduction",
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
    ]
    checks = []
    for name in names:
        if name == "release_manifest_exact_reproduction":
            expected = release
            actual = release
        else:
            expected = True
            actual = True
        checks.append(
            {
                "name": name,
                "required": True,
                "passed": True,
                "expected": expected,
                "actual": actual,
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


def _fixture(source_root: Path) -> dict:
    source_root.mkdir(parents=True)
    rs = source_root / "rs"
    rs.mkdir()
    (rs / "A.java").write_bytes(
        b"package rs; public class A {}\r\n"
    )

    tree_sha, _files, _bytes = source_tree_digest(
        source_root
    )

    authority_sha = V308_SOURCE_AUTHORITY_SHA256
    namespace_id = "SEMNS_" + "B" * 20
    class_digest = "c" * 64
    member_digest = "d" * 64

    fixture = {
        "class_lineage": {
            "classes": [
                {
                    "semantic_status": "ACCEPTED",
                    "semantic_provenance": [
                        {"review_id": "SEMREVIEW_CLASS"}
                    ],
                }
            ],
        },
        "member_lineage": {
            "members": [
                {
                    "semantic_status": "ACCEPTED",
                    "semantic_provenance": [
                        {"review_id": "SEMREVIEW_MEMBER"}
                    ],
                }
            ],
        },
        "readable_manifest": {
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
        },
        "recovered_source_manifest": {
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
        },
        "clean_rebuild_report": {
            "schema_version": 1,
            "kind": "clean_project_rebuild_report",
            "rebuild_id": "CLEANBUILD_TEST",
            "status": "complete",
            "build_id": "v308",
            "namespace_id": namespace_id,
            "source_authority_sha256": authority_sha,
            "source_tree_sha256": tree_sha,
            "readable_jar_sha256": "b" * 64,
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
        },
        "release_manifest": {
            "schema_version": 1,
            "kind": "recovery_release_manifest",
            "release_id": "RECOVERY_TEST",
            "build_id": "v308",
            "authority_sha256": authority_sha,
            "namespace_id": namespace_id,
            "final_source_tree_sha256": tree_sha,
            "ready_for_release": True,
        },
        "release_verification": {
            "schema_version": 1,
            "kind": "recovery_release_verification",
            "verification_id": "REPRO_TEST",
            "release_id": "RECOVERY_TEST",
            "verified": True,
        },
    }
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
    _refresh_release_verification(fixture)
    return fixture


class SourceAuthorityArtifactTests(unittest.TestCase):
    def _build(
        self,
        source: Path,
        out: Path,
        fixture: dict,
        **build_kwargs,
    ) -> dict:
        return build_source_authority_artifact(
            authority_commit="f" * 40,
            source_root=source,
            out_dir=out,
            **fixture,
            **build_kwargs,
        )

    def test_verifier_requires_external_milestone_id(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            out = root / "artifact"

            self._build(source, out, fixture)
            report = _verify_source_authority_artifact(
                out,
                expected_authority_commit="f" * 40,
            )

            self.assertFalse(report["verified"])
            self.assertFalse(
                report["checks"]["expected_milestone_id"]
            )
            self.assertTrue(
                all(
                    value
                    for key, value in report["checks"].items()
                    if key != "expected_milestone_id"
                )
            )

    def test_verifier_rejects_wrong_external_milestone_id(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            out = root / "artifact"

            self._build(source, out, fixture)
            report = verify_source_authority_artifact(
                out,
                expected_milestone_id=(
                    "SRCMILESTONE_" + "0" * 20
                ),
            )

            self.assertFalse(report["verified"])
            self.assertFalse(
                report["checks"]["expected_milestone_id"]
            )
            self.assertTrue(
                all(
                    value
                    for key, value in report["checks"].items()
                    if key != "expected_milestone_id"
                )
            )

    def test_verifier_requires_external_authority_commit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            out = root / "artifact"

            self._build(source, out, fixture)
            manifest = json.loads(
                (
                    out / "SOURCE-AUTHORITY-ARTIFACT.json"
                ).read_text(encoding="utf-8")
            )
            report = _verify_source_authority_artifact(
                out,
                expected_milestone_id=manifest[
                    "preflight_milestone_id"
                ],
            )

            self.assertFalse(report["verified"])
            self.assertFalse(
                report["checks"]["expected_authority_commit"]
            )
            self.assertTrue(
                all(
                    value
                    for key, value in report["checks"].items()
                    if key != "expected_authority_commit"
                )
            )

    def test_verifier_rejects_wrong_external_authority_commit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            out = root / "artifact"

            self._build(source, out, fixture)
            report = verify_source_authority_artifact(
                out,
                expected_authority_commit="e" * 40,
            )

            self.assertFalse(report["verified"])
            self.assertFalse(
                report["checks"]["expected_authority_commit"]
            )
            self.assertTrue(
                all(
                    value
                    for key, value in report["checks"].items()
                    if key != "expected_authority_commit"
                )
            )

    def test_exact_artifact_is_deterministic_and_verifies(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)

            first_dir = root / "first"
            second_dir = root / "second"

            first = self._build(
                source,
                first_dir,
                fixture,
            )
            second = self._build(
                source,
                second_dir,
                fixture,
            )

            self.assertEqual(first, second)
            self.assertTrue(
                first["artifact_id"].startswith("SRCAUTHART_")
            )

            exported = (
                first_dir / "src" / "rs" / "A.java"
            ).read_bytes()
            self.assertEqual(
                exported,
                b"package rs; public class A {}\n",
            )

            report = verify_source_authority_artifact(
                first_dir,
                expected_authority_commit="f" * 40,
            )
            repeat = verify_source_authority_artifact(
                first_dir,
                expected_authority_commit="f" * 40,
            )

            self.assertTrue(report["verified"])
            self.assertEqual(report, repeat)
            self.assertTrue(
                report["verification_id"].startswith(
                    "SRCAUTHVERIFY_"
                )
            )
            self.assertTrue(
                all(report["checks"].values())
            )

    def test_verifier_rejects_noncanonical_authority_repository(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            out = root / "artifact"

            self._build(
                source,
                out,
                fixture,
                authority_repository="Trexzo/Forged-Authority",
            )
            report = verify_source_authority_artifact(
                out,
                expected_authority_commit="f" * 40,
            )

            self.assertFalse(report["verified"])
            self.assertFalse(
                report["checks"]["expected_authority_repository"]
            )
            self.assertTrue(
                all(
                    value
                    for key, value in report["checks"].items()
                    if key != "expected_authority_repository"
                )
            )

    def test_verifier_rejects_noncanonical_publication_repository(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            out = root / "artifact"

            self._build(
                source,
                out,
                fixture,
                publication_repository="Trexzo/Forged-Publication",
            )
            report = verify_source_authority_artifact(
                out,
                expected_authority_commit="f" * 40,
            )

            self.assertFalse(report["verified"])
            self.assertFalse(
                report["checks"]["expected_publication_repository"]
            )
            self.assertTrue(
                all(
                    value
                    for key, value in report["checks"].items()
                    if key != "expected_publication_repository"
                )
            )

    def test_artifact_id_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            out = root / "artifact"

            self._build(source, out, fixture)
            manifest_path = (
                out / "SOURCE-AUTHORITY-ARTIFACT.json"
            )
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
            manifest["artifact_id"] = (
                "SRCAUTHART_" + "0" * 20
            )
            manifest_path.write_text(
                json.dumps(
                    manifest,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            report = verify_source_authority_artifact(
                out,
                expected_authority_commit="f" * 40,
            )

            self.assertFalse(report["verified"])
            self.assertFalse(
                report["checks"]["artifact_id_match"]
            )

    def test_empty_artifact_source_tree_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            out = root / "artifact"

            self._build(source, out, fixture)
            (out / "src" / "rs" / "A.java").unlink()

            report = verify_source_authority_artifact(
                out,
                expected_authority_commit="f" * 40,
            )

            self.assertFalse(report["verified"])
            self.assertFalse(
                report["checks"]["source_tree_nonempty"]
            )
            self.assertEqual(report["source_file_count"], 0)

    def test_source_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            out = root / "artifact"

            self._build(source, out, fixture)
            (out / "src" / "rs" / "A.java").write_text(
                "package rs; public class A { int drift; }\n",
                encoding="utf-8",
            )

            report = verify_source_authority_artifact(
                out,
                expected_authority_commit="f" * 40,
            )

            self.assertFalse(report["verified"])
            self.assertFalse(
                report["checks"]["payload_file_hashes_match"]
            )
            self.assertFalse(
                report["checks"]["source_tree_sha256_match"]
            )

    def test_unindexed_binary_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            out = root / "artifact"

            self._build(source, out, fixture)
            (out / "client.jar").write_bytes(b"binary")

            report = verify_source_authority_artifact(
                out,
                expected_authority_commit="f" * 40,
            )

            self.assertFalse(report["verified"])
            self.assertFalse(
                report["checks"]["source_only_layout"]
            )
            self.assertFalse(
                report["checks"]["payload_file_set_match"]
            )

    def test_blocked_source_milestone_cannot_be_packaged(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            fixture["clean_rebuild_report"][
                "project_classes"
            ]["binary_fallback_count"] = 1

            with self.assertRaisesRegex(
                SourceAuthorityArtifactError,
                "not publishable",
            ):
                self._build(
                    source,
                    root / "artifact",
                    fixture,
                )


if __name__ == "__main__":
    unittest.main()
