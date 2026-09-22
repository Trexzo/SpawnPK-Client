from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .decompiler import DecompilerError, run_decompiler, sha256_file


class SourceWorkspaceError(ValueError):
    pass


def _write_json(doc: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _source_tree_digest(root: Path) -> tuple[str, int, int]:
    files = sorted(root.rglob("*.java"))
    h = hashlib.sha256()
    total_bytes = 0
    for path in files:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
        total_bytes += len(data)
    return h.hexdigest(), len(files), total_bytes


def build_source_workspace(
    readable_manifest: dict[str, Any],
    readable_jar: Path,
    decompiler_jar: Path,
    *,
    expected_decompiler_sha256: str,
    engine: str,
    out_dir: Path,
) -> dict[str, Any]:
    if (
        readable_manifest.get("schema_version") != 1
        or readable_manifest.get("kind")
        != "readable_client_build_manifest"
    ):
        raise SourceWorkspaceError("unsupported readable-client manifest")

    if readable_manifest.get("status") != "complete":
        raise SourceWorkspaceError(
            "source workspace requires a complete readable-client build"
        )
    if readable_manifest.get("verification_pass") is not True:
        raise SourceWorkspaceError(
            "readable-client manifest is not independently verified"
        )

    readable_jar = readable_jar.resolve()
    if not readable_jar.is_file():
        raise SourceWorkspaceError(
            f"readable client JAR does not exist: {readable_jar}"
        )

    expected_input_sha = str(
        readable_manifest.get("output_sha256", "")
    ).lower()
    actual_input_sha = sha256_file(readable_jar)
    if actual_input_sha.lower() != expected_input_sha:
        raise SourceWorkspaceError(
            "readable client SHA-256 does not match build manifest: "
            f"{actual_input_sha} != {expected_input_sha}"
        )

    namespace_id = readable_manifest.get("namespace_id")
    class_plan_digest = readable_manifest.get("class_plan_digest")
    member_plan_digest = readable_manifest.get("member_plan_digest")
    if not all(
        isinstance(value, str) and value
        for value in (
            namespace_id,
            class_plan_digest,
            member_plan_digest,
        )
    ):
        raise SourceWorkspaceError(
            "readable-client manifest lacks namespace/plan digest pins"
        )

    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SourceWorkspaceError(
            "source workspace output directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    source_dir = out_dir / "src"

    try:
        result = run_decompiler(
            readable_jar,
            decompiler_jar,
            expected_decompiler_sha256=expected_decompiler_sha256,
            engine=engine,
            out_dir=source_dir,
            clean_out=False,
        )
    except DecompilerError as exc:
        raise SourceWorkspaceError(str(exc)) from exc

    tree_sha, java_count, source_bytes = _source_tree_digest(source_dir)
    if java_count != int(result.get("java_file_count", -1)):
        raise SourceWorkspaceError(
            "decompiler result java_file_count disagrees with source tree"
        )

    material = {
        "source_sha256": readable_manifest["source_sha256"],
        "readable_jar_sha256": actual_input_sha,
        "namespace_id": namespace_id,
        "class_plan_digest": class_plan_digest,
        "member_plan_digest": member_plan_digest,
        "engine": result["engine"],
        "decompiler_sha256": result["decompiler_sha256"],
        "source_tree_sha256": tree_sha,
    }
    raw = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    workspace_id = (
        "SRCWS_" + hashlib.sha256(raw).hexdigest()[:20].upper()
    )

    manifest = {
        "schema_version": 1,
        "kind": "recovered_source_workspace_manifest",
        "workspace_id": workspace_id,
        "build_id": readable_manifest["build_id"],
        "source_authority_sha256": readable_manifest["source_sha256"],
        "readable_jar_sha256": actual_input_sha,
        "namespace_id": namespace_id,
        "class_plan_digest": class_plan_digest,
        "member_plan_digest": member_plan_digest,
        "engine": result["engine"],
        "decompiler_sha256": result["decompiler_sha256"],
        "source_tree_sha256": tree_sha,
        "java_file_count": java_count,
        "source_bytes": source_bytes,
        "source_directory": "src",
    }
    _write_json(result, out_dir / "decompiler-result.json")
    _write_json(
        manifest,
        out_dir / "recovered-source-manifest.json",
    )
    return manifest
