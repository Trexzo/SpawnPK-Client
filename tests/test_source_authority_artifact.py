from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from spk_recovery.source_authority_artifact import (
    SourceAuthorityArtifactError,
    build_source_authority_artifact,
    verify_source_authority_artifact as _verify_source_authority_artifact,
)
from spk_recovery.source_digest import source_tree_digest
from spk_recovery.v308_authority import V308_SOURCE_AUTHORITY_SHA256


def _hex(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _semantic_provenance(proposal: dict, review_id: str) -> dict:
    return {
        "proposal_id": proposal["proposal_id"],
        "review_id": review_id,
        "source_build": proposal["source_build"],
        "source_sha256": proposal["source_sha256"],
        "source_coordinate": copy.deepcopy(
            proposal["source_coordinate"]
        ),
        "evidence": copy.deepcopy(proposal["evidence"]),
        "note": proposal.get("note"),
    }


def _real_r2_lineage(review: dict, acceptance: dict):
    accepted = set(acceptance["accept"])
    proposals = [
        row
        for row in review["proposals"]
        if row["proposal_id"] in accepted
    ]
    class_proposals = {
        row["stable_id"]: row
        for row in proposals
        if row["target_kind"] == "class"
    }
    member_proposals = [
        row
        for row in proposals
        if row["target_kind"] != "class"
    ]

    owner_names = {
        stable_id: row["source_coordinate"]["owner"]
        for stable_id, row in class_proposals.items()
    }
    for row in member_proposals:
        owner_id = row["owner_logical_id"]
        owner = row["source_coordinate"]["owner"]
        prior = owner_names.get(owner_id)
        if prior is not None:
            assert prior == owner
        owner_names[owner_id] = owner

    review_id = str(review["review_id"])
    classes = []
    for logical_id in sorted(
        owner_names,
        key=lambda value: (
            value not in class_proposals,
            value,
        ),
    ):
        owner = owner_names[logical_id]
        proposal = class_proposals.get(logical_id)
        accepted_class = proposal is not None
        classes.append(
            {
                "logical_id": logical_id,
                "semantic_name": (
                    proposal["proposed_name"]
                    if accepted_class
                    else None
                ),
                "semantic_status": (
                    "ACCEPTED" if accepted_class else "UNKNOWN"
                ),
                "semantic_confidence": (
                    proposal["confidence"] if accepted_class else 0.0
                ),
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": owner,
                        "entry_path": owner + ".class",
                        "entry_sha256": _hex("entry:" + owner),
                        "structural_sha256": _hex(
                            "structural:" + owner
                        ),
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": (
                    [_semantic_provenance(proposal, review_id)]
                    if accepted_class
                    else []
                ),
            }
        )

    members = []
    for proposal in sorted(
        member_proposals,
        key=lambda row: row["stable_id"],
    ):
        coordinate = proposal["source_coordinate"]
        members.append(
            {
                "member_id": proposal["stable_id"],
                "owner_logical_id": proposal["owner_logical_id"],
                "kind": proposal["target_kind"],
                "semantic_name": proposal["proposed_name"],
                "semantic_status": "ACCEPTED",
                "semantic_confidence": proposal["confidence"],
                "lineage": [
                    {
                        "build_id": "v308",
                        "owner_internal_name": coordinate["owner"],
                        "name": coordinate["name"],
                        "descriptor": coordinate["descriptor"],
                        "access": 1,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [
                    _semantic_provenance(proposal, review_id)
                ],
            }
        )

    return (
        {
            "schema_version": 1,
            "namespace": "spawnpk-client",
            "id_format": "CLIENT_CLASS_%06d",
            "baseline_build_id": "v308",
            "builds": [
                {
                    "build_id": "v308",
                    "build_number": 308,
                    "sha256": V308_SOURCE_AUTHORITY_SHA256,
                    "source_name": "client.jar",
                    "authority": "EXACT_CURRENT_CLIENT",
                }
            ],
            "classes": classes,
            "unresolved": [],
        },
        {
            "schema_version": 1,
            "kind": "member_lineage",
            "class_namespace": "spawnpk-client",
            "baseline_build_id": "v308",
            "source_sha256": V308_SOURCE_AUTHORITY_SHA256,
            "members": members,
            "unresolved": [],
        },
    )


def _artifact_milestone_id(artifact_dir: Path) -> str:
    manifest = json.loads(
        (
            Path(artifact_dir)
            / "SOURCE-AUTHORITY-ARTIFACT.json"
        ).read_text(encoding="utf-8")
    )
    return str(manifest["preflight_milestone_id"])


def verify_source_authority_artifact(artifact_dir, **kwargs):
    kwargs.setdefault("expected_authority_commit", "f" * 40)
    kwargs.setdefault(
        "expected_milestone_id",
        _artifact_milestone_id(Path(artifact_dir)),
    )
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

    repo_root = Path(__file__).resolve().parents[1]
    semantic_review = json.loads(
        (
            repo_root
            / "mappings"
            / "candidates"
            / "v308.semantic-review.chat2.r2.json"
        ).read_text(encoding="utf-8")
    )
    semantic_acceptance = json.loads(
        (
            repo_root
            / "mappings"
            / "v308.semantic.acceptance.json"
        ).read_text(encoding="utf-8")
    )
    classes, members = _real_r2_lineage(
        semantic_review,
        semantic_acceptance,
    )

    fixture = {
        "class_lineage": classes,
        "member_lineage": members,
        "semantic_review": semantic_review,
        "semantic_acceptance": semantic_acceptance,
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

    def test_verifier_requires_external_authority_commit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            out = root / "artifact"

            self._build(source, out, fixture)
            report = _verify_source_authority_artifact(
                out,
                expected_milestone_id=_artifact_milestone_id(out),
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
            report = _verify_source_authority_artifact(
                out,
                expected_authority_commit="e" * 40,
                expected_milestone_id=_artifact_milestone_id(out),
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
                report["checks"]["expected_preflight_milestone_id"]
            )
            self.assertTrue(
                all(
                    value
                    for key, value in report["checks"].items()
                    if key != "expected_preflight_milestone_id"
                )
            )

    def test_verifier_rejects_wrong_external_milestone_id(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            out = root / "artifact"

            self._build(source, out, fixture)
            report = _verify_source_authority_artifact(
                out,
                expected_authority_commit="f" * 40,
                expected_milestone_id=(
                    "SRCMILESTONE_" + "0" * 20
                ),
            )

            self.assertFalse(report["verified"])
            self.assertFalse(
                report["checks"]["expected_preflight_milestone_id"]
            )
            self.assertTrue(
                all(
                    value
                    for key, value in report["checks"].items()
                    if key != "expected_preflight_milestone_id"
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
            self.assertTrue(
                first["semantic_authority_verification_id"].startswith(
                    "SOURCESEMAUTH_"
                )
            )
            self.assertTrue(
                (first_dir / "semantic-review.json").is_file()
            )
            self.assertTrue(
                (first_dir / "semantic-acceptance.json").is_file()
            )
            self.assertIn(
                "semantic-review.json",
                first["document_sha256"],
            )
            self.assertIn(
                "semantic-acceptance.json",
                first["document_sha256"],
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

    def test_verifier_rejects_semantic_authority_payload_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            out = root / "artifact"

            self._build(source, out, fixture)
            review_path = out / "semantic-review.json"
            review = json.loads(
                review_path.read_text(encoding="utf-8")
            )
            review["proposal_count"] = 0
            review_path.write_text(
                json.dumps(
                    review,
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
                report["checks"]["payload_file_hashes_match"]
            )
            self.assertFalse(
                report["checks"]["milestone_publishable"]
            )

    def test_verifier_rejects_noncanonical_same_repository(self):
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
                publication_repository="Trexzo/Forged-Authority",
            )
            report = verify_source_authority_artifact(
                out,
                expected_authority_commit="f" * 40,
            )

            self.assertFalse(report["verified"])
            self.assertFalse(
                report["checks"]["expected_authority_repository"]
            )
            self.assertFalse(
                report["checks"]["expected_publication_repository"]
            )
            self.assertTrue(
                all(
                    value
                    for key, value in report["checks"].items()
                    if key
                    not in {
                        "expected_authority_repository",
                        "expected_publication_repository",
                    }
                )
            )

    def test_builder_rejects_split_publication_repository(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            out = root / "artifact"

            with self.assertRaisesRegex(
                SourceAuthorityArtifactError,
                "publication_repository_must_equal_authority_repository",
            ):
                self._build(
                    source,
                    out,
                    fixture,
                    publication_repository="Trexzo/Forged-Publication",
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

    def test_builder_rejects_symbolic_link_source_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            link = root / "source-link"
            try:
                link.symlink_to(source, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(
                    f"symbolic links unavailable on this runner: {exc}"
                )

            with self.assertRaisesRegex(
                SourceAuthorityArtifactError,
                "symbolic link",
            ):
                self._build(
                    link,
                    root / "artifact",
                    fixture,
                )

    def test_builder_output_must_be_outside_source_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            before = source_tree_digest(source)[0]
            nested = source / "artifact"
            nested.mkdir()

            with self.assertRaisesRegex(
                SourceAuthorityArtifactError,
                "outside source root",
            ):
                self._build(source, nested, fixture)

            self.assertEqual(source_tree_digest(source)[0], before)
            self.assertEqual(list(nested.iterdir()), [])

    def test_verifier_rejects_byte_identical_symlink_payload(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            out = root / "artifact"

            self._build(source, out, fixture)
            milestone_id = _artifact_milestone_id(out)
            stored = out / "class-lineage.json"
            outside = root / "outside-class-lineage.json"
            outside.write_bytes(stored.read_bytes())
            stored.unlink()
            try:
                stored.symlink_to(outside)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(
                    f"symbolic links unavailable on this runner: {exc}"
                )

            with self.assertRaisesRegex(
                SourceAuthorityArtifactError,
                "symbolic link",
            ):
                _verify_source_authority_artifact(
                    out,
                    expected_authority_commit="f" * 40,
                    expected_milestone_id=milestone_id,
                )

    def test_verifier_rejects_extra_fifo_entry(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("FIFO creation is unavailable on this platform")

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            fixture = _fixture(source)
            out = root / "artifact"

            self._build(source, out, fixture)
            milestone_id = _artifact_milestone_id(out)
            fifo = out / "ignored.fifo"
            try:
                os.mkfifo(fifo)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(
                    f"FIFO creation unavailable on this runner: {exc}"
                )

            with self.assertRaisesRegex(
                SourceAuthorityArtifactError,
                "non-regular file",
            ):
                _verify_source_authority_artifact(
                    out,
                    expected_authority_commit="f" * 40,
                    expected_milestone_id=milestone_id,
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
