from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from .source_digest import source_tree_digest


class SourceRepositoryExportError(ValueError):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def export_source_repository(
    milestone_manifest: dict[str, Any],
    source_root: Path,
    out_dir: Path,
) -> dict[str, Any]:
    if (
        milestone_manifest.get("schema_version") != 1
        or milestone_manifest.get("kind")
        != "spawnpk_source_milestone_manifest"
    ):
        raise SourceRepositoryExportError(
            "unsupported source milestone manifest"
        )
    if milestone_manifest.get("publishable") is not True:
        raise SourceRepositoryExportError(
            "source milestone is not publishable"
        )

    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise SourceRepositoryExportError(
            "source root does not exist"
        )

    expected_tree = (
        milestone_manifest.get("source", {})
        .get("source_tree_sha256")
    )
    actual_tree, source_files, source_bytes = source_tree_digest(
        source_root
    )
    java_count = len(source_files)
    if actual_tree != expected_tree:
        raise SourceRepositoryExportError(
            "source root SHA-256 disagrees with milestone authority"
        )

    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SourceRepositoryExportError(
            "source repository export directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    export_source = out_dir / "src"
    shutil.copytree(source_root, export_source)

    exported_tree, exported_files, exported_bytes = (
        source_tree_digest(export_source)
    )
    exported_count = len(exported_files)
    if exported_tree != expected_tree:
        raise SourceRepositoryExportError(
            "exported source tree SHA-256 drifted"
        )
    if exported_count != java_count or exported_bytes != source_bytes:
        raise SourceRepositoryExportError(
            "exported source tree count/size drifted"
        )

    _write_json(
        milestone_manifest,
        out_dir / "SOURCE-MILESTONE.json",
    )

    provenance = {
        "schema_version": 1,
        "kind": "spawnpk_source_repository_provenance",
        "milestone_id": milestone_manifest["milestone_id"],
        "publish_target": milestone_manifest["publish_target"],
        "build_id": milestone_manifest["build_id"],
        "source_tree_sha256": expected_tree,
        "java_file_count": java_count,
        "source_bytes": source_bytes,
        "naming_policy": milestone_manifest["naming_policy"],
        "semantic_authority": milestone_manifest[
            "semantic_authority"
        ],
        "project_class_set": milestone_manifest[
            "project_class_set"
        ],
        "provenance": milestone_manifest["provenance"],
        "authority_pins": milestone_manifest["authority_pins"],
    }
    _write_json(
        provenance,
        out_dir / "SOURCE-PROVENANCE.json",
    )

    readme = (
        "# SpawnPK Client Source\n\n"
        "This repository is a deterministic recovered Java-source "
        "publication for the exact SpawnPK v308 client authority.\n\n"
        "## Naming policy\n\n"
        "Semantic names appear only where accepted recovery authority "
        "exists. Unresolved symbols retain deterministic source-safe "
        "fallback names. No unresolved semantic meaning is invented.\n\n"
        "## Authority\n\n"
        "See SOURCE-MILESTONE.json and SOURCE-PROVENANCE.json for the "
        "exact SpawnPK-Client authority commit, client SHA-256, semantic "
        "namespace/plan digests, source-tree SHA-256, clean-rebuild "
        "authority, and project class-set equality gate.\n\n"
        "The source tree is under src/.\n"
    )
    (out_dir / "README.md").write_text(
        readme,
        encoding="utf-8",
    )

    files = [
        path
        for path in out_dir.rglob("*")
        if path.is_file()
    ]
    publication_files = {
        path.relative_to(out_dir).as_posix(): _sha256_file(path)
        for path in sorted(files)
    }

    report_material = {
        "milestone_id": milestone_manifest["milestone_id"],
        "authority_commit": milestone_manifest["provenance"][
            "spawnpk_client_authority_commit"
        ],
        "source_tree_sha256": expected_tree,
        "java_file_count": java_count,
        "source_bytes": source_bytes,
        "publication_files": publication_files,
    }
    export_id = (
        "SOURCE_EXPORT_"
        + hashlib.sha256(
            json.dumps(
                report_material,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )

    report = {
        "schema_version": 1,
        "kind": "spawnpk_source_repository_export",
        "export_id": export_id,
        "milestone_id": milestone_manifest["milestone_id"],
        "publish_target": milestone_manifest["publish_target"],
        "publishable": True,
        "source_directory": "src",
        "source_tree_sha256": expected_tree,
        "java_file_count": java_count,
        "source_bytes": source_bytes,
        "authority_commit": milestone_manifest["provenance"][
            "spawnpk_client_authority_commit"
        ],
        "publication_files": publication_files,
    }
    _write_json(report, out_dir / "SOURCE-EXPORT.json")
    return report
