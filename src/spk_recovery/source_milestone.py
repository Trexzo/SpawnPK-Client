from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
from typing import Any

from .source_digest import source_tree_digest


class SourceMilestoneError(ValueError):
    pass


_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _require_doc(
    doc: dict[str, Any],
    *,
    kind: str,
    label: str,
) -> None:
    if doc.get("schema_version") != 1 or doc.get("kind") != kind:
        raise SourceMilestoneError(
            f"{label}: expected schema_version=1 kind={kind!r}"
        )


def _semantic_review_ids(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
) -> list[str]:
    review_ids: set[str] = set()

    for record in class_lineage.get("classes", []):
        if record.get("semantic_status") != "ACCEPTED":
            continue
        for row in record.get("semantic_provenance", []):
            review_id = row.get("review_id")
            if isinstance(review_id, str) and review_id:
                review_ids.add(review_id)

    for record in member_lineage.get("members", []):
        if record.get("semantic_status") != "ACCEPTED":
            continue
        for row in record.get("semantic_provenance", []):
            review_id = row.get("review_id")
            if isinstance(review_id, str) and review_id:
                review_ids.add(review_id)

    return sorted(review_ids)


def _block(
    blockers: list[dict[str, str]],
    *,
    gate: str,
    reason: str,
) -> None:
    blockers.append(
        {
            "gate": gate,
            "reason": reason,
        }
    )


def build_source_milestone_manifest(
    *,
    authority_commit: str,
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    readable_manifest: dict[str, Any],
    recovered_source_manifest: dict[str, Any],
    clean_rebuild_report: dict[str, Any],
    release_manifest: dict[str, Any],
    release_verification: dict[str, Any],
    source_root: Path,
    authority_repository: str = "Trexzo/SpawnPK-Client",
    publication_repository: str = "Trexzo/SpawnPK-Client-Source",
) -> dict[str, Any]:
    authority_commit = authority_commit.strip().lower()
    if not _COMMIT_RE.fullmatch(authority_commit):
        raise SourceMilestoneError(
            "authority commit must be one exact lowercase 40-hex Git commit"
        )

    if not authority_repository:
        raise SourceMilestoneError("authority repository is required")
    if not publication_repository:
        raise SourceMilestoneError("publication repository is required")

    _require_doc(
        readable_manifest,
        kind="readable_client_build_manifest",
        label="readable_manifest",
    )
    _require_doc(
        recovered_source_manifest,
        kind="recovered_source_workspace_manifest",
        label="recovered_source_manifest",
    )
    _require_doc(
        clean_rebuild_report,
        kind="clean_project_rebuild_report",
        label="clean_rebuild_report",
    )
    _require_doc(
        release_manifest,
        kind="recovery_release_manifest",
        label="release_manifest",
    )
    _require_doc(
        release_verification,
        kind="recovery_release_verification",
        label="release_verification",
    )

    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise SourceMilestoneError(
            f"source root does not exist: {source_root}"
        )

    source_tree_sha, source_files, source_bytes = source_tree_digest(
        source_root
    )

    blockers: list[dict[str, str]] = []

    authority_sha = str(
        release_manifest.get("authority_sha256") or ""
    ).lower()
    authority_values = {
        str(readable_manifest.get("source_sha256") or "").lower(),
        str(
            recovered_source_manifest.get(
                "source_authority_sha256"
            )
            or ""
        ).lower(),
        str(
            clean_rebuild_report.get("source_authority_sha256")
            or ""
        ).lower(),
        authority_sha,
    }
    if len(authority_values) != 1 or not authority_sha:
        _block(
            blockers,
            gate="exact_authority",
            reason="authority_sha_linkage_mismatch",
        )

    namespace_id = str(
        readable_manifest.get("namespace_id") or ""
    )
    if (
        not namespace_id
        or namespace_id
        != str(
            recovered_source_manifest.get("namespace_id") or ""
        )
        or namespace_id
        != str(clean_rebuild_report.get("namespace_id") or "")
        or namespace_id
        != str(release_manifest.get("namespace_id") or "")
    ):
        _block(
            blockers,
            gate="semantic_authority",
            reason="semantic_namespace_linkage_mismatch",
        )

    class_plan_digest = str(
        readable_manifest.get("class_plan_digest") or ""
    )
    member_plan_digest = str(
        readable_manifest.get("member_plan_digest") or ""
    )
    if (
        not class_plan_digest
        or class_plan_digest
        != str(
            recovered_source_manifest.get("class_plan_digest") or ""
        )
    ):
        _block(
            blockers,
            gate="semantic_authority",
            reason="class_plan_digest_mismatch",
        )
    if (
        not member_plan_digest
        or member_plan_digest
        != str(
            recovered_source_manifest.get("member_plan_digest") or ""
        )
    ):
        _block(
            blockers,
            gate="semantic_authority",
            reason="member_plan_digest_mismatch",
        )

    source_safe_fallback = (
        readable_manifest.get("source_safe_fallback") is True
    )
    fallback_prefix = readable_manifest.get(
        "fallback_name_prefix"
    )
    if not source_safe_fallback or not isinstance(
        fallback_prefix,
        str,
    ) or not fallback_prefix:
        _block(
            blockers,
            gate="fallback_policy",
            reason="deterministic_source_safe_fallback_not_enabled",
        )

    if release_manifest.get("ready_for_release") is not True:
        _block(
            blockers,
            gate="release_authority",
            reason="recovery_release_not_ready",
        )
    if release_verification.get("verified") is not True:
        _block(
            blockers,
            gate="release_authority",
            reason="recovery_release_verification_failed",
        )
    if release_verification.get("release_id") != release_manifest.get(
        "release_id"
    ):
        _block(
            blockers,
            gate="release_authority",
            reason="release_verification_id_linkage_mismatch",
        )

    if source_tree_sha != str(
        release_manifest.get("final_source_tree_sha256") or ""
    ).lower():
        _block(
            blockers,
            gate="source_tree",
            reason="source_tree_sha256_mismatch",
        )

    if clean_rebuild_report.get("status") != "complete":
        _block(
            blockers,
            gate="clean_compile",
            reason="clean_rebuild_not_complete",
        )
    if clean_rebuild_report.get("clean_project_build") is not True:
        _block(
            blockers,
            gate="clean_compile",
            reason="project_build_not_clean",
        )

    project_classes = clean_rebuild_report.get(
        "project_classes"
    )
    if not isinstance(project_classes, dict):
        raise SourceMilestoneError(
            "clean rebuild lacks project_classes"
        )

    expected_count = int(
        project_classes.get("expected_count", -1)
    )
    generated_count = int(
        project_classes.get("generated_count", -1)
    )
    missing = list(project_classes.get("missing") or [])
    unexpected = list(project_classes.get("unexpected") or [])
    binary_fallback = int(
        project_classes.get("binary_fallback_count", -1)
    )

    class_set_equal = (
        expected_count >= 0
        and generated_count == expected_count
        and not missing
        and not unexpected
    )
    if not class_set_equal:
        _block(
            blockers,
            gate="project_class_set",
            reason="project_class_set_not_exact",
        )
    if binary_fallback != 0:
        _block(
            blockers,
            gate="project_binary_fallback",
            reason="project_binary_fallback_present",
        )

    review_ids = _semantic_review_ids(
        class_lineage,
        member_lineage,
    )

    compile_transport = clean_rebuild_report.get(
        "compile_transport"
    )
    collision_provenance = None
    if isinstance(compile_transport, dict):
        collision_provenance = {
            key: compile_transport.get(key)
            for key in (
                "mode",
                "collision_compile_id",
                "collision_transform_id",
                "collision_plan_id",
                "collision_plan_sha256",
                "collision_report_id",
            )
            if compile_transport.get(key) is not None
        }

    provenance = {
        "authority_repository": authority_repository,
        "authority_commit": authority_commit,
        "authority_client_sha256": authority_sha,
        "build_id": release_manifest.get("build_id"),
        "semantic_namespace_id": namespace_id,
        "class_plan_digest": class_plan_digest,
        "member_plan_digest": member_plan_digest,
        "semantic_review_ids": review_ids,
        "fallback_policy": {
            "source_safe_fallback": source_safe_fallback,
            "fallback_name_prefix": fallback_prefix,
        },
        "readable_manifest_id": readable_manifest.get(
            "manifest_id"
        ),
        "recovered_workspace_id": recovered_source_manifest.get(
            "workspace_id"
        ),
        "build_authority_id": clean_rebuild_report.get(
            "build_authority_id"
        ),
        "clean_rebuild_id": clean_rebuild_report.get(
            "rebuild_id"
        ),
        "release_id": release_manifest.get("release_id"),
        "release_verification_id": release_verification.get(
            "verification_id"
        ),
        "collision_provenance": collision_provenance,
    }

    source_tree = {
        "sha256": source_tree_sha,
        "java_file_count": len(source_files),
        "source_bytes": source_bytes,
        "layout": "src/",
    }

    class_set = {
        "expected_count": expected_count,
        "generated_count": generated_count,
        "missing_count": len(missing),
        "unexpected_count": len(unexpected),
        "binary_fallback_count": binary_fallback,
        "exact_match": class_set_equal,
    }

    publication = {
        "target_repository": publication_repository,
        "allowed": len(blockers) == 0,
        "layout": {
            "source": "src/",
            "provenance": "provenance/",
            "manifest": "SOURCE-MILESTONE.json",
        },
    }

    material = {
        "provenance": provenance,
        "source_tree": source_tree,
        "class_set": class_set,
        "publication": publication,
        "blockers": blockers,
    }
    milestone_id = (
        "SRCMILESTONE_"
        + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "source_milestone_manifest",
        "milestone_id": milestone_id,
        "milestone": "source-milestone-1",
        "publishable": len(blockers) == 0,
        "blockers": blockers,
        "provenance": provenance,
        "source_tree": source_tree,
        "class_set": class_set,
        "publication": publication,
        "note": (
            "publishable means the exact authority, semantic/fallback, "
            "clean-compile, zero-project-binary-fallback, exact class-set, "
            "source-tree, and release-verification gates all passed. "
            "Semantic names remain evidence-backed accepted recovery names; "
            "the manifest does not claim they are original developer names."
        ),
    }


def verify_source_milestone_manifest(
    manifest: dict[str, Any],
    **build_kwargs: Any,
) -> dict[str, Any]:
    _require_doc(
        manifest,
        kind="source_milestone_manifest",
        label="source_milestone_manifest",
    )
    recomputed = build_source_milestone_manifest(
        **build_kwargs
    )
    exact = manifest == recomputed

    material = {
        "milestone_id": manifest.get("milestone_id"),
        "exact_reproduction": exact,
        "source_tree_sha256": recomputed.get(
            "source_tree",
            {},
        ).get("sha256"),
    }
    verification_id = (
        "SRCMILEVERIFY_"
        + _stable_digest(material)[:20].upper()
    )
    return {
        "schema_version": 1,
        "kind": "source_milestone_verification",
        "verification_id": verification_id,
        "milestone_id": manifest.get("milestone_id"),
        "verified": exact,
        "publishable": bool(
            recomputed.get("publishable")
        ) and exact,
        "exact_reproduction": exact,
        "recomputed_milestone_id": recomputed.get(
            "milestone_id"
        ),
    }


def build_source_publication_bundle(
    manifest: dict[str, Any],
    source_root: Path,
    out_dir: Path,
    *,
    provenance_documents: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    _require_doc(
        manifest,
        kind="source_milestone_manifest",
        label="source_milestone_manifest",
    )
    if manifest.get("publishable") is not True:
        raise SourceMilestoneError(
            "source milestone is not publishable"
        )

    source_root = source_root.resolve()
    out_dir = out_dir.resolve()

    if not source_root.is_dir():
        raise SourceMilestoneError(
            "source root does not exist"
        )
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SourceMilestoneError(
            "publication bundle directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    tree_sha, files, source_bytes = source_tree_digest(
        source_root
    )
    expected_sha = manifest.get("source_tree", {}).get(
        "sha256"
    )
    if tree_sha != expected_sha:
        raise SourceMilestoneError(
            "source tree does not match milestone manifest"
        )

    source_out = out_dir / "src"
    for path in files:
        rel = path.relative_to(source_root)
        target = source_out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())

    provenance_out = out_dir / "provenance"
    provenance_out.mkdir(parents=True, exist_ok=True)

    (out_dir / "SOURCE-MILESTONE.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    provenance_index: dict[str, str] = {}
    for name in sorted(provenance_documents):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+\.json", name):
            raise SourceMilestoneError(
                "invalid provenance document name"
            )
        doc = provenance_documents[name]
        target = provenance_out / name
        raw = (
            json.dumps(doc, indent=2, sort_keys=True)
            + "\n"
        )
        target.write_text(raw, encoding="utf-8")
        provenance_index[name] = hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()

    file_hashes: dict[str, str] = {}
    for path in sorted(
        out_dir.rglob("*"),
        key=lambda p: p.relative_to(out_dir).as_posix(),
    ):
        if not path.is_file():
            continue
        rel = path.relative_to(out_dir).as_posix()
        file_hashes[rel] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

    bundle_material = {
        "milestone_id": manifest.get("milestone_id"),
        "source_tree_sha256": tree_sha,
        "source_file_count": len(files),
        "source_bytes": source_bytes,
        "provenance_index": provenance_index,
        "files": file_hashes,
    }
    bundle_id = (
        "SRCBUNDLE_"
        + _stable_digest(bundle_material)[:20].upper()
    )

    bundle = {
        "schema_version": 1,
        "kind": "source_publication_bundle",
        "bundle_id": bundle_id,
        "milestone_id": manifest.get("milestone_id"),
        "source_tree_sha256": tree_sha,
        "source_file_count": len(files),
        "source_bytes": source_bytes,
        "provenance_documents": provenance_index,
        "file_sha256": file_hashes,
        "contains_binary_artifacts": False,
        "publication_repository": manifest.get(
            "publication",
            {},
        ).get("target_repository"),
    }
    (out_dir / "BUNDLE.json").write_text(
        json.dumps(bundle, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return bundle


def write_json(doc: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(doc, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
