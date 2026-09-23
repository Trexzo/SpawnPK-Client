from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any
import zipfile

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



def _project_prefixes(readable_manifest: dict[str, Any]) -> list[str]:
    values = readable_manifest.get("project_source_prefixes")
    if not isinstance(values, list) or not values:
        raise SourceWorkspaceError(
            "project-only source workspace requires non-empty "
            "readable manifest project_source_prefixes"
        )
    out: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value:
            raise SourceWorkspaceError(
                "readable manifest project_source_prefixes must contain "
                "non-empty strings"
            )
        normalized = value.replace("\\", "/").lstrip("/")
        if not normalized:
            raise SourceWorkspaceError(
                "readable manifest project_source_prefixes must not normalize "
                "to the archive root"
            )
        parts = [part for part in normalized.rstrip("/").split("/") if part]
        if (
            not parts
            or any(part in {".", ".."} for part in parts)
            or normalized.startswith("META-INF/")
        ):
            raise SourceWorkspaceError(
                "readable manifest project_source_prefixes contains an unsafe "
                f"or unsupported prefix: {value!r}"
            )
        normalized = "/".join(parts) + "/"
        out.append(normalized)
    return sorted(set(out))


def _is_project_class(entry: str, prefixes: list[str]) -> bool:
    if not entry.endswith(".class"):
        return False
    if entry.startswith("META-INF/versions/"):
        parts = entry.split("/", 3)
        if len(parts) == 4:
            return any(parts[3].startswith(prefix) for prefix in prefixes)
    return any(entry.startswith(prefix) for prefix in prefixes)


def _is_project_source_target(entry: str, prefixes: list[str]) -> bool:
    """Select Java source units, not nested/inner classfiles.

    Procyon reconstructs $-named inner classes from the outer class when they
    remain available as resolver context. Targeting them independently produces
    invalid duplicate source units such as Outer$Inner.java declaring public
    class Inner.
    """
    if not _is_project_class(entry, prefixes):
        return False
    return "$" not in Path(entry).name


def _selection_digest(entries: list[str]) -> str:
    h = hashlib.sha256()
    for entry in entries:
        raw = entry.encode("utf-8")
        h.update(len(raw).to_bytes(4, "big"))
        h.update(raw)
    return h.hexdigest()


def _extract_class_context(
    readable_jar: Path,
    root: Path,
    prefixes: list[str],
) -> tuple[list[Path], list[str]]:
    selected: list[str] = []
    with zipfile.ZipFile(readable_jar) as z:
        infos = sorted(z.infolist(), key=lambda info: info.filename)
        for info in infos:
            name = info.filename
            if info.is_dir() or not name.endswith(".class"):
                continue
            path = Path(name)
            if path.is_absolute() or ".." in path.parts:
                raise SourceWorkspaceError(
                    f"unsafe class entry in readable JAR: {name!r}"
                )
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(info))
            if _is_project_source_target(name, prefixes):
                if name.startswith("META-INF/versions/"):
                    raise SourceWorkspaceError(
                        "project-only source workspace does not support "
                        f"multi-release project class {name!r}"
                    )
                selected.append(name)
    if not selected:
        raise SourceWorkspaceError(
            "project-only source workspace selected no project classes"
        )
    return [root / Path(name) for name in selected], selected


def _resume_checkpoint_material(
    *,
    readable_manifest: dict[str, Any],
    readable_jar_sha256: str,
    decompiler_sha256: str,
    engine: str,
    project_prefixes: list[str],
    selected_entries: list[str],
    batch_size: int,
) -> dict[str, Any]:
    if not isinstance(batch_size, int) or batch_size < 1:
        raise SourceWorkspaceError("project batch size must be an integer >= 1")
    return {
        "source_sha256": readable_manifest["source_sha256"],
        "readable_jar_sha256": readable_jar_sha256,
        "namespace_id": readable_manifest["namespace_id"],
        "class_plan_digest": readable_manifest["class_plan_digest"],
        "member_plan_digest": readable_manifest["member_plan_digest"],
        "engine": engine.lower(),
        "decompiler_sha256": decompiler_sha256.lower(),
        "project_source_prefixes": project_prefixes,
        "selected_class_count": len(selected_entries),
        "selected_class_digest": _selection_digest(selected_entries),
        "batch_size": batch_size,
        "batch_count": (len(selected_entries) + batch_size - 1) // batch_size,
    }


def _checkpoint_id(material: dict[str, Any]) -> str:
    raw = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "R4CCHK_" + hashlib.sha256(raw).hexdigest()[:20].upper()


def _merge_java_tree(source: Path, target: Path) -> int:
    merged = 0
    for src in sorted(source.rglob("*.java")):
        rel = src.relative_to(source)
        dst = target / rel
        data = src.read_bytes()
        if dst.exists():
            if dst.read_bytes() != data:
                raise SourceWorkspaceError(
                    "resumable source merge found conflicting Java output: "
                    + rel.as_posix()
                )
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        merged += 1
    return merged


def _load_resume_checkpoint(
    path: Path,
    *,
    material: dict[str, Any],
    source_dir: Path,
) -> dict[str, Any]:
    expected_id = _checkpoint_id(material)
    if not path.exists():
        if source_dir.exists() and any(source_dir.rglob("*.java")):
            raise SourceWorkspaceError(
                "resumable source directory is non-empty without a checkpoint"
            )
        return {
            "schema_version": 1,
            "kind": "project_source_resume_checkpoint",
            "checkpoint_id": expected_id,
            "status": "incomplete",
            "material": material,
            "completed_batches": [],
            "source_tree_sha256": None,
            "java_file_count": 0,
            "source_bytes": 0,
        }
    try:
        checkpoint = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceWorkspaceError(f"invalid resume checkpoint: {exc}") from exc
    if (
        checkpoint.get("schema_version") != 1
        or checkpoint.get("kind") != "project_source_resume_checkpoint"
        or checkpoint.get("checkpoint_id") != expected_id
        or checkpoint.get("material") != material
    ):
        raise SourceWorkspaceError(
            "resume checkpoint authority or batch policy does not match current inputs"
        )
    completed = checkpoint.get("completed_batches")
    if not isinstance(completed, list):
        raise SourceWorkspaceError("resume checkpoint completed_batches is invalid")
    seen: set[int] = set()
    for row in completed:
        if not isinstance(row, dict) or not isinstance(row.get("batch_index"), int):
            raise SourceWorkspaceError("resume checkpoint contains an invalid batch record")
        idx = row["batch_index"]
        if idx in seen or idx < 0 or idx >= material["batch_count"]:
            raise SourceWorkspaceError("resume checkpoint contains invalid batch indices")
        seen.add(idx)
    tree_sha, java_count, source_bytes = _source_tree_digest(source_dir)
    expected_tree = checkpoint.get("source_tree_sha256")
    if expected_tree is None:
        if java_count != 0:
            raise SourceWorkspaceError("resume checkpoint source tree is unexpectedly non-empty")
    elif (
        tree_sha != expected_tree
        or java_count != checkpoint.get("java_file_count")
        or source_bytes != checkpoint.get("source_bytes")
    ):
        raise SourceWorkspaceError("resume checkpoint source tree has drifted")
    return checkpoint


def _write_resume_checkpoint(
    checkpoint: dict[str, Any],
    path: Path,
    source_dir: Path,
) -> None:
    tree_sha, java_count, source_bytes = _source_tree_digest(source_dir)
    checkpoint["source_tree_sha256"] = tree_sha if java_count else None
    checkpoint["java_file_count"] = java_count
    checkpoint["source_bytes"] = source_bytes
    _write_json(checkpoint, path)

def build_source_workspace(
    readable_manifest: dict[str, Any],
    readable_jar: Path,
    decompiler_jar: Path,
    *,
    expected_decompiler_sha256: str,
    engine: str,
    out_dir: Path,
    project_only: bool = False,
    resume_project_only: bool = False,
    project_batch_size: int = 5,
    max_batches_per_run: int | None = None,
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
    if resume_project_only and not project_only:
        raise SourceWorkspaceError(
            "resume mode requires project-only source recovery"
        )
    if max_batches_per_run is not None and (
        not isinstance(max_batches_per_run, int) or max_batches_per_run < 1
    ):
        raise SourceWorkspaceError(
            "max_batches_per_run must be an integer >= 1"
        )

    readable_jar = readable_jar.resolve()
    decompiler_jar = decompiler_jar.resolve()
    if not readable_jar.is_file():
        raise SourceWorkspaceError(
            f"readable client JAR does not exist: {readable_jar}"
        )
    if not decompiler_jar.is_file():
        raise SourceWorkspaceError(
            f"decompiler JAR does not exist: {decompiler_jar}"
        )

    expected_input_sha = str(readable_manifest.get("output_sha256", "")).lower()
    actual_input_sha = sha256_file(readable_jar)
    if actual_input_sha.lower() != expected_input_sha:
        raise SourceWorkspaceError(
            "readable client SHA-256 does not match build manifest: "
            f"{actual_input_sha} != {expected_input_sha}"
        )
    actual_decompiler_sha: str | None = None
    if resume_project_only:
        actual_decompiler_sha = sha256_file(decompiler_jar)
        if actual_decompiler_sha.lower() != expected_decompiler_sha256.lower():
            raise SourceWorkspaceError(
                "decompiler SHA-256 mismatch: "
                f"{actual_decompiler_sha} != {expected_decompiler_sha256.lower()}"
            )

    namespace_id = readable_manifest.get("namespace_id")
    class_plan_digest = readable_manifest.get("class_plan_digest")
    member_plan_digest = readable_manifest.get("member_plan_digest")
    if not all(
        isinstance(value, str) and value
        for value in (namespace_id, class_plan_digest, member_plan_digest)
    ):
        raise SourceWorkspaceError(
            "readable-client manifest lacks namespace/plan digest pins"
        )

    out_dir = out_dir.resolve()
    if not resume_project_only and out_dir.exists() and any(out_dir.iterdir()):
        raise SourceWorkspaceError(
            "source workspace output directory must be empty"
        )
    if resume_project_only and (out_dir / "recovered-source-manifest.json").exists():
        raise SourceWorkspaceError(
            "resumable source workspace is already complete"
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    source_dir = out_dir / "src"

    project_prefixes: list[str] = []
    selected_entries: list[str] = []
    selection_sha: str | None = None
    result: dict[str, Any]
    try:
        if project_only:
            if engine.lower() != "procyon":
                raise SourceWorkspaceError(
                    "project-only source workspace is currently supported only with Procyon"
                )
            project_prefixes = _project_prefixes(readable_manifest)
            with tempfile.TemporaryDirectory(prefix="spk-project-decompile-") as td:
                class_files, selected_entries = _extract_class_context(
                    readable_jar, Path(td), project_prefixes
                )
                selection_sha = _selection_digest(selected_entries)
                if resume_project_only:
                    material = _resume_checkpoint_material(
                        readable_manifest=readable_manifest,
                        readable_jar_sha256=actual_input_sha,
                        decompiler_sha256=str(actual_decompiler_sha),
                        engine=engine,
                        project_prefixes=project_prefixes,
                        selected_entries=selected_entries,
                        batch_size=project_batch_size,
                    )
                    checkpoint_path = out_dir / "project-decompile-checkpoint.json"
                    checkpoint = _load_resume_checkpoint(
                        checkpoint_path, material=material, source_dir=source_dir
                    )
                    completed = {
                        row["batch_index"] for row in checkpoint["completed_batches"]
                    }
                    pending = [
                        i for i in range(material["batch_count"]) if i not in completed
                    ]
                    if max_batches_per_run is not None:
                        pending = pending[:max_batches_per_run]
                    source_dir.mkdir(parents=True, exist_ok=True)
                    for batch_index in pending:
                        lo = batch_index * project_batch_size
                        hi = min(lo + project_batch_size, len(class_files))
                        batch_files = class_files[lo:hi]
                        batch_entries = selected_entries[lo:hi]
                        with tempfile.TemporaryDirectory(
                            prefix=f"spk-project-batch-{batch_index:04d}-"
                        ) as batch_td:
                            batch_out = Path(batch_td) / "src"
                            run_decompiler(
                                readable_jar,
                                decompiler_jar,
                                expected_decompiler_sha256=expected_decompiler_sha256,
                                engine=engine,
                                out_dir=batch_out,
                                clean_out=False,
                                input_class_files=batch_files,
                            )
                            batch_tree_sha, batch_java_count, _ = _source_tree_digest(batch_out)
                            _merge_java_tree(batch_out, source_dir)
                        checkpoint["completed_batches"].append({
                            "batch_index": batch_index,
                            "selected_class_count": len(batch_entries),
                            "selected_class_digest": _selection_digest(batch_entries),
                            "java_file_count": batch_java_count,
                            "source_tree_sha256": batch_tree_sha,
                        })
                        checkpoint["completed_batches"] = sorted(
                            checkpoint["completed_batches"],
                            key=lambda row: row["batch_index"],
                        )
                        _write_resume_checkpoint(
                            checkpoint, checkpoint_path, source_dir
                        )
                    completed_count = len(checkpoint["completed_batches"])
                    if completed_count < material["batch_count"]:
                        checkpoint["status"] = "incomplete"
                        _write_resume_checkpoint(
                            checkpoint, checkpoint_path, source_dir
                        )
                        return checkpoint
                    checkpoint["status"] = "complete"
                    _write_resume_checkpoint(
                        checkpoint, checkpoint_path, source_dir
                    )
                    tree_sha, java_count, source_bytes = _source_tree_digest(source_dir)
                    result = {
                        "schema_version": 1,
                        "kind": "decompiler_result",
                        "engine": "procyon",
                        "input_sha256": actual_input_sha,
                        "decompiler_sha256": str(actual_decompiler_sha),
                        "java_file_count": java_count,
                        "output_directory": str(source_dir),
                        "input_mode": "class_files_resumable",
                        "selected_class_file_count": len(selected_entries),
                        "batch_count": material["batch_count"],
                        "stdout": "",
                        "stderr": "",
                    }
                else:
                    result = run_decompiler(
                        readable_jar,
                        decompiler_jar,
                        expected_decompiler_sha256=expected_decompiler_sha256,
                        engine=engine,
                        out_dir=source_dir,
                        clean_out=False,
                        input_class_files=class_files,
                    )
        else:
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
    if not resume_project_only and java_count != int(result.get("java_file_count", -1)):
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
        "source_scope": "project_classes" if project_only else "whole_archive",
        "project_source_prefixes": project_prefixes,
        "selected_class_count": len(selected_entries) if project_only else None,
        "selected_class_digest": selection_sha,
    }
    raw = json.dumps(
        material, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    workspace_id = "SRCWS_" + hashlib.sha256(raw).hexdigest()[:20].upper()
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
        "source_scope": "project_classes" if project_only else "whole_archive",
        "project_source_prefixes": project_prefixes,
        "selected_class_count": len(selected_entries) if project_only else None,
        "selected_class_digest": selection_sha,
    }
    _write_json(result, out_dir / "decompiler-result.json")
    _write_json(manifest, out_dir / "recovered-source-manifest.json")
    return manifest
