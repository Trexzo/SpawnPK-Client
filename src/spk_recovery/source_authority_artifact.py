from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .source_digest import (
    canonical_source_bytes,
    source_tree_digest,
)
from .source_milestone import (
    SourceMilestoneError,
    build_source_milestone_manifest,
)


class SourceAuthorityArtifactError(ValueError):
    pass


_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_MILESTONE_ID_RE = re.compile(r"^SRCMILESTONE_[0-9A-F]{20}$")
_DEFAULT_AUTHORITY_REPOSITORY = "Trexzo/SpawnPK-Client"
_DEFAULT_PUBLICATION_REPOSITORY = "Trexzo/SpawnPK-Client-Source"

_DOCUMENT_NAMES = {
    "class-lineage.json": "class_lineage",
    "member-lineage.json": "member_lineage",
    "readable-client-manifest.json": "readable_manifest",
    "recovered-source-manifest.json": "recovered_source_manifest",
    "clean-rebuild.json": "clean_rebuild_report",
    "recovery-release.json": "release_manifest",
    "release-verification.json": "release_verification",
}


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _exact_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise SourceAuthorityArtifactError(
                f"duplicate JSON key: {key!r}"
            )
        out[key] = value
    return out


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_exact_object,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceAuthorityArtifactError(
            f"invalid JSON document: {path}"
        ) from exc
    if not isinstance(value, dict):
        raise SourceAuthorityArtifactError(
            f"JSON document must be an object: {path}"
        )
    return value


def _build_milestone(
    *,
    authority_commit: str,
    documents: dict[str, dict[str, Any]],
    source_root: Path,
    authority_repository: str,
    publication_repository: str,
) -> dict[str, Any]:
    try:
        return build_source_milestone_manifest(
            authority_commit=authority_commit,
            class_lineage=documents["class_lineage"],
            member_lineage=documents["member_lineage"],
            readable_manifest=documents["readable_manifest"],
            recovered_source_manifest=documents[
                "recovered_source_manifest"
            ],
            clean_rebuild_report=documents[
                "clean_rebuild_report"
            ],
            release_manifest=documents["release_manifest"],
            release_verification=documents[
                "release_verification"
            ],
            source_root=source_root,
            authority_repository=authority_repository,
            publication_repository=publication_repository,
        )
    except SourceMilestoneError as exc:
        raise SourceAuthorityArtifactError(str(exc)) from exc


def build_source_authority_artifact(
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
    out_dir: Path,
    authority_repository: str = _DEFAULT_AUTHORITY_REPOSITORY,
    publication_repository: str = _DEFAULT_PUBLICATION_REPOSITORY,
) -> dict[str, Any]:
    authority_commit = authority_commit.strip().lower()
    if not _COMMIT_RE.fullmatch(authority_commit):
        raise SourceAuthorityArtifactError(
            "authority commit must be exact lowercase 40-hex"
        )

    source_root = source_root.resolve()
    out_dir = out_dir.resolve()

    if not source_root.is_dir():
        raise SourceAuthorityArtifactError(
            "source root does not exist"
        )
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SourceAuthorityArtifactError(
            "authority artifact output directory must be empty"
        )

    documents = {
        "class_lineage": class_lineage,
        "member_lineage": member_lineage,
        "readable_manifest": readable_manifest,
        "recovered_source_manifest": recovered_source_manifest,
        "clean_rebuild_report": clean_rebuild_report,
        "release_manifest": release_manifest,
        "release_verification": release_verification,
    }

    milestone = _build_milestone(
        authority_commit=authority_commit,
        documents=documents,
        source_root=source_root,
        authority_repository=authority_repository,
        publication_repository=publication_repository,
    )
    if milestone.get("publishable") is not True:
        reasons = sorted(
            str(row.get("reason"))
            for row in milestone.get("blockers", [])
            if isinstance(row, dict)
        )
        raise SourceAuthorityArtifactError(
            "source milestone preflight is not publishable: "
            + ", ".join(reasons)
        )

    tree_sha, source_files, source_bytes = source_tree_digest(
        source_root
    )
    if not source_files:
        raise SourceAuthorityArtifactError(
            "source root contains no Java files"
        )

    out_dir.mkdir(parents=True, exist_ok=True)

    document_sha256: dict[str, str] = {}
    for filename, key in _DOCUMENT_NAMES.items():
        raw = _json_bytes(documents[key])
        target = out_dir / filename
        target.write_bytes(raw)
        document_sha256[filename] = _sha256(raw)

    source_out = out_dir / "src"
    source_file_sha256: dict[str, str] = {}
    for path in source_files:
        rel = path.relative_to(source_root)
        target = source_out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = canonical_source_bytes(path.read_bytes())
        target.write_bytes(raw)
        source_file_sha256[
            "src/" + rel.as_posix()
        ] = _sha256(raw)

    exported_tree, exported_files, exported_bytes = (
        source_tree_digest(source_out)
    )
    if (
        exported_tree != tree_sha
        or len(exported_files) != len(source_files)
        or exported_bytes != source_bytes
    ):
        raise SourceAuthorityArtifactError(
            "canonical source export drifted"
        )

    payload_file_sha256 = {
        **document_sha256,
        **source_file_sha256,
    }

    material = {
        "authority_repository": authority_repository,
        "authority_commit": authority_commit,
        "publication_repository": publication_repository,
        "preflight_milestone_id": milestone["milestone_id"],
        "build_id": milestone["provenance"]["build_id"],
        "client_sha256": milestone["provenance"][
            "authority_client_sha256"
        ],
        "source_tree_sha256": tree_sha,
        "source_file_count": len(source_files),
        "source_bytes": source_bytes,
        "document_sha256": document_sha256,
        "payload_file_sha256": payload_file_sha256,
    }
    artifact_id = (
        "SRCAUTHART_"
        + _stable_digest(material)[:20].upper()
    )

    report = {
        "schema_version": 1,
        "kind": "source_m1_authority_artifact",
        "artifact_id": artifact_id,
        "authority_repository": authority_repository,
        "authority_commit": authority_commit,
        "publication_repository": publication_repository,
        "preflight_milestone_id": milestone["milestone_id"],
        "preflight_publishable": True,
        "build_id": milestone["provenance"]["build_id"],
        "client_sha256": milestone["provenance"][
            "authority_client_sha256"
        ],
        "source_tree_sha256": tree_sha,
        "source_file_count": len(source_files),
        "source_bytes": source_bytes,
        "document_sha256": document_sha256,
        "payload_file_sha256": payload_file_sha256,
        "contains_binary_artifacts": False,
    }
    (out_dir / "SOURCE-AUTHORITY-ARTIFACT.json").write_bytes(
        _json_bytes(report)
    )
    return report


def verify_source_authority_artifact(
    artifact_dir: Path,
    *,
    expected_authority_commit: str | None = None,
    expected_milestone_id: str | None = None,
    expected_authority_repository: str = (
        _DEFAULT_AUTHORITY_REPOSITORY
    ),
    expected_publication_repository: str = (
        _DEFAULT_PUBLICATION_REPOSITORY
    ),
) -> dict[str, Any]:
    artifact_dir = artifact_dir.resolve()
    manifest_path = (
        artifact_dir / "SOURCE-AUTHORITY-ARTIFACT.json"
    )
    source_root = artifact_dir / "src"

    if not artifact_dir.is_dir():
        raise SourceAuthorityArtifactError(
            "authority artifact directory does not exist"
        )
    if not manifest_path.is_file():
        raise SourceAuthorityArtifactError(
            "authority artifact manifest is missing"
        )
    if not source_root.is_dir():
        raise SourceAuthorityArtifactError(
            "authority artifact source root is missing"
        )

    manifest = _read_json(manifest_path)
    if (
        manifest.get("schema_version") != 1
        or manifest.get("kind")
        != "source_m1_authority_artifact"
    ):
        raise SourceAuthorityArtifactError(
            "unsupported authority artifact manifest"
        )

    authority_commit = str(
        manifest.get("authority_commit") or ""
    )
    if not _COMMIT_RE.fullmatch(authority_commit):
        raise SourceAuthorityArtifactError(
            "artifact authority commit is invalid"
        )

    authority_repository = str(
        manifest.get("authority_repository") or ""
    )
    publication_repository = str(
        manifest.get("publication_repository") or ""
    )

    checks: dict[str, bool] = {}
    checks["expected_authority_commit"] = (
        isinstance(expected_authority_commit, str)
        and _COMMIT_RE.fullmatch(expected_authority_commit)
        is not None
        and expected_authority_commit == authority_commit
    )
    checks["expected_authority_repository"] = (
        authority_repository == expected_authority_repository
    )
    checks["expected_publication_repository"] = (
        publication_repository == expected_publication_repository
    )
    checks["preflight_publishable"] = (
        manifest.get("preflight_publishable") is True
    )
    checks["contains_binary_artifacts_false"] = (
        manifest.get("contains_binary_artifacts") is False
    )

    artifact_material = {
        "authority_repository": authority_repository,
        "authority_commit": authority_commit,
        "publication_repository": publication_repository,
        "preflight_milestone_id": manifest.get(
            "preflight_milestone_id"
        ),
        "build_id": manifest.get("build_id"),
        "client_sha256": manifest.get("client_sha256"),
        "source_tree_sha256": manifest.get(
            "source_tree_sha256"
        ),
        "source_file_count": manifest.get(
            "source_file_count"
        ),
        "source_bytes": manifest.get("source_bytes"),
        "document_sha256": manifest.get("document_sha256"),
        "payload_file_sha256": manifest.get(
            "payload_file_sha256"
        ),
    }
    expected_artifact_id = (
        "SRCAUTHART_"
        + _stable_digest(artifact_material)[:20].upper()
    )
    checks["artifact_id_match"] = (
        manifest.get("artifact_id") == expected_artifact_id
    )

    expected_payload = manifest.get("payload_file_sha256")
    if not isinstance(expected_payload, dict):
        expected_payload = {}

    actual_payload: dict[str, str] = {}
    source_only = True
    for path in sorted(
        artifact_dir.rglob("*"),
        key=lambda item: item.relative_to(artifact_dir).as_posix(),
    ):
        if not path.is_file():
            continue
        rel = path.relative_to(artifact_dir).as_posix()
        if rel == "SOURCE-AUTHORITY-ARTIFACT.json":
            continue

        if rel in _DOCUMENT_NAMES:
            pass
        elif rel.startswith("src/") and rel.endswith(".java"):
            pass
        else:
            source_only = False

        actual_payload[rel] = _sha256(path.read_bytes())

    checks["source_only_layout"] = source_only
    checks["payload_file_set_match"] = (
        set(actual_payload) == set(expected_payload)
    )
    checks["payload_file_hashes_match"] = (
        actual_payload == expected_payload
    )

    expected_document_hashes = manifest.get(
        "document_sha256"
    )
    if not isinstance(expected_document_hashes, dict):
        expected_document_hashes = {}
    actual_document_hashes = {
        name: actual_payload.get(name)
        for name in _DOCUMENT_NAMES
        if name in actual_payload
    }
    checks["document_hashes_match"] = (
        actual_document_hashes == expected_document_hashes
    )

    tree_sha, source_files, source_bytes = source_tree_digest(
        source_root
    )
    checks["source_tree_nonempty"] = bool(source_files)
    checks["source_tree_sha256_match"] = (
        tree_sha == manifest.get("source_tree_sha256")
    )
    checks["source_file_count_match"] = (
        len(source_files)
        == manifest.get("source_file_count")
    )
    checks["source_bytes_match"] = (
        source_bytes == manifest.get("source_bytes")
    )

    docs_by_key: dict[str, dict[str, Any]] = {}
    for filename, key in _DOCUMENT_NAMES.items():
        path = artifact_dir / filename
        if not path.is_file():
            docs_by_key[key] = {}
            continue
        docs_by_key[key] = _read_json(path)

    milestone: dict[str, Any] | None = None
    milestone_error: str | None = None
    try:
        milestone = _build_milestone(
            authority_commit=authority_commit,
            documents=docs_by_key,
            source_root=source_root,
            authority_repository=authority_repository,
            publication_repository=publication_repository,
        )
    except SourceAuthorityArtifactError as exc:
        milestone_error = str(exc)

    checks["milestone_rebuild_succeeded"] = (
        milestone is not None
    )
    checks["milestone_publishable"] = (
        milestone is not None
        and milestone.get("publishable") is True
    )
    checks["milestone_id_match"] = (
        milestone is not None
        and milestone.get("milestone_id")
        == manifest.get("preflight_milestone_id")
    )
    checks["expected_preflight_milestone_id"] = (
        isinstance(expected_milestone_id, str)
        and _MILESTONE_ID_RE.fullmatch(expected_milestone_id)
        is not None
        and manifest.get("preflight_milestone_id")
        == expected_milestone_id
        and milestone is not None
        and milestone.get("milestone_id")
        == expected_milestone_id
    )
    checks["build_id_match"] = (
        milestone is not None
        and milestone.get("provenance", {}).get("build_id")
        == manifest.get("build_id")
    )
    checks["client_sha256_match"] = (
        milestone is not None
        and milestone.get("provenance", {}).get(
            "authority_client_sha256"
        )
        == manifest.get("client_sha256")
    )

    material = {
        "artifact_id": manifest.get("artifact_id"),
        "authority_commit": authority_commit,
        "checks": checks,
        "source_tree_sha256": tree_sha,
        "payload_file_sha256": actual_payload,
        "recomputed_milestone_id": (
            milestone.get("milestone_id")
            if milestone is not None
            else None
        ),
    }
    verification_id = (
        "SRCAUTHVERIFY_"
        + _stable_digest(material)[:20].upper()
    )

    verified = all(checks.values())
    return {
        "schema_version": 1,
        "kind": "source_m1_authority_artifact_verification",
        "verification_id": verification_id,
        "artifact_id": manifest.get("artifact_id"),
        "verified": verified,
        "authority_commit": authority_commit,
        "source_tree_sha256": tree_sha,
        "source_file_count": len(source_files),
        "source_bytes": source_bytes,
        "payload_file_count": len(actual_payload),
        "recomputed_milestone_id": (
            milestone.get("milestone_id")
            if milestone is not None
            else None
        ),
        "milestone_error": milestone_error,
        "checks": checks,
    }


def load_authority_artifact_inputs(
    *,
    class_lineage: Path,
    member_lineage: Path,
    readable_manifest: Path,
    recovered_manifest: Path,
    clean_rebuild: Path,
    release_manifest: Path,
    release_verification: Path,
) -> dict[str, dict[str, Any]]:
    return {
        "class_lineage": _read_json(class_lineage),
        "member_lineage": _read_json(member_lineage),
        "readable_manifest": _read_json(readable_manifest),
        "recovered_source_manifest": _read_json(
            recovered_manifest
        ),
        "clean_rebuild_report": _read_json(clean_rebuild),
        "release_manifest": _read_json(release_manifest),
        "release_verification": _read_json(
            release_verification
        ),
    }
