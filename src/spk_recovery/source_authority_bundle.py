from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .source_digest import (
    canonical_source_bytes,
    sorted_java_files,
    source_tree_digest,
)


class SourceAuthorityBundleError(ValueError):
    pass


def _write_json(value: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _stable_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def build_source_authority_bundle(
    authority_index: dict[str, Any],
    readable_manifest: dict[str, Any],
    recovered_manifest: dict[str, Any],
    clean_rebuild_report: dict[str, Any],
    source_root: Path,
    out_dir: Path,
    *,
    authority_commit: str,
) -> dict[str, Any]:
    commit = authority_commit.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise SourceAuthorityBundleError(
            "authority commit must be an exact 40-hex Git commit"
        )

    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise SourceAuthorityBundleError(
            "source root does not exist"
        )

    authority_sha = str(authority_index.get("sha256") or "").lower()
    if len(authority_sha) != 64:
        raise SourceAuthorityBundleError(
            "authority index lacks exact SHA-256"
        )

    exact_values = [
        authority_sha,
        str(readable_manifest.get("source_sha256") or "").lower(),
        str(recovered_manifest.get("source_authority_sha256") or "").lower(),
        str(clean_rebuild_report.get("source_authority_sha256") or "").lower(),
    ]
    if len(set(exact_values)) != 1:
        raise SourceAuthorityBundleError(
            "exact source authority SHA-256 mismatch"
        )

    build_ids = {
        str(readable_manifest.get("build_id") or ""),
        str(recovered_manifest.get("build_id") or ""),
        str(clean_rebuild_report.get("build_id") or ""),
    }
    if build_ids != {"v308"}:
        raise SourceAuthorityBundleError(
            f"source authority bundle requires exact v308: {build_ids!r}"
        )

    tree_sha, files, source_bytes = source_tree_digest(source_root)
    expected_tree = recovered_manifest.get("source_tree_sha256")
    if tree_sha != expected_tree:
        raise SourceAuthorityBundleError(
            "source tree SHA-256 disagrees with recovered manifest"
        )
    if clean_rebuild_report.get("source_tree_sha256") != tree_sha:
        raise SourceAuthorityBundleError(
            "source tree SHA-256 disagrees with clean rebuild report"
        )

    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SourceAuthorityBundleError(
            "authority bundle output directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    _write_json(authority_index, out_dir / "authority-index.json")
    _write_json(
        readable_manifest,
        out_dir / "readable-client-manifest.json",
    )
    _write_json(
        recovered_manifest,
        out_dir / "recovered-source-manifest.json",
    )
    _write_json(
        clean_rebuild_report,
        out_dir / "clean-rebuild.json",
    )
    bundle_source = out_dir / "src"
    bundle_source.mkdir(parents=True)
    for source in sorted_java_files(source_root):
        rel = source.relative_to(source_root)
        target = bundle_source / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(
            canonical_source_bytes(source.read_bytes())
        )

    copied_sha, copied_files, copied_bytes = source_tree_digest(
        bundle_source
    )
    if copied_sha != tree_sha:
        raise SourceAuthorityBundleError(
            "copied source tree SHA-256 drifted"
        )
    if len(copied_files) != len(files) or copied_bytes != source_bytes:
        raise SourceAuthorityBundleError(
            "copied source tree count/size drifted"
        )

    material = {
        "build_id": "v308",
        "authority_commit": commit,
        "authority_sha256": authority_sha,
        "readable_manifest_id": readable_manifest.get("manifest_id"),
        "workspace_id": recovered_manifest.get("workspace_id"),
        "clean_rebuild_id": clean_rebuild_report.get("rebuild_id"),
        "source_tree_sha256": tree_sha,
        "java_file_count": len(files),
        "source_bytes": source_bytes,
    }
    bundle_id = (
        "SOURCE_AUTHORITY_"
        + _stable_digest(material)[:20].upper()
    )
    report = {
        "schema_version": 1,
        "kind": "spawnpk_source_authority_bundle",
        "bundle_id": bundle_id,
        **material,
        "layout": {
            "authority_index": "authority-index.json",
            "readable_manifest": "readable-client-manifest.json",
            "recovered_manifest": "recovered-source-manifest.json",
            "clean_rebuild_report": "clean-rebuild.json",
            "source_root": "src",
        },
    }
    _write_json(report, out_dir / "SOURCE-AUTHORITY.json")
    return report
