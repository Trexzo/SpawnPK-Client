from __future__ import annotations

import binascii
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any
import zipfile

from .dependency_reverse_transport_apply import (
    DependencyReverseTransportApplyError,
    apply_dependency_reverse_transport,
)
from .source_digest import source_tree_digest


class DependencyOfficialDerivedCompileError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path, *, kind: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyOfficialDerivedCompileError(
            f"invalid JSON authority: {path}"
        ) from exc
    if value.get("kind") != kind:
        raise DependencyOfficialDerivedCompileError(
            f"{path}: expected kind {kind!r}"
        )
    return value


def _require(command: str) -> str:
    candidate = Path(command)
    if candidate.is_absolute():
        if not candidate.is_file():
            raise DependencyOfficialDerivedCompileError(
                f"required executable missing: {candidate}"
            )
        return str(candidate)
    found = shutil.which(command)
    if found is None:
        raise DependencyOfficialDerivedCompileError(
            f"required executable not found: {command}"
        )
    return found


def _normalize_prefixes(
    prefixes: tuple[str, ...],
) -> tuple[str, ...]:
    values: list[str] = []
    for prefix in prefixes:
        value = prefix.replace("\\", "/").lstrip("/")
        if not value:
            raise DependencyOfficialDerivedCompileError(
                "project prefix must not be empty"
            )
        if not value.endswith("/"):
            value += "/"
        values.append(value)
    if not values:
        raise DependencyOfficialDerivedCompileError(
            "project prefixes must not be empty"
        )
    return tuple(sorted(set(values)))


def _arg(value: str) -> str:
    return '"' + value.replace("\\", "/").replace('"', '\\"') + '"'


def _write_project_jar(
    classes_root: Path,
    out: Path,
    prefixes: tuple[str, ...],
) -> tuple[int, int]:
    rows: list[tuple[str, bytes]] = []
    total = 0
    for path in sorted(
        classes_root.rglob("*.class"),
        key=lambda p: p.relative_to(classes_root).as_posix(),
    ):
        rel = path.relative_to(classes_root).as_posix()
        if not any(rel.startswith(prefix) for prefix in prefixes):
            raise DependencyOfficialDerivedCompileError(
                "javac generated a class outside the project namespace: "
                + rel
            )
        data = path.read_bytes()
        rows.append((rel, data))
        total += len(data)

    if not rows:
        raise DependencyOfficialDerivedCompileError(
            "javac generated no project classes"
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        out,
        "w",
        compression=zipfile.ZIP_STORED,
    ) as archive:
        for name, data in rows:
            info = zipfile.ZipInfo(
                name,
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_STORED
            info.file_size = len(data)
            info.CRC = binascii.crc32(data) & 0xFFFFFFFF
            archive.writestr(info, data)
    return len(rows), total


def _artifact_shas(paths: list[Path]) -> list[str]:
    return sorted(_sha256_file(path) for path in paths)


def compile_official_overlay_and_restore(
    overlay_manifest_path: Path,
    overlay_source_root: Path,
    canonical_source_root: Path,
    private_replacement_plan_path: Path,
    private_reverse_plan_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    out_dir: Path,
    *,
    project_prefixes: tuple[str, ...] = ("rs/", "tools/"),
    java_command: str = "java",
    javac_command: str = "javac",
) -> dict[str, Any]:
    overlay_manifest_path = overlay_manifest_path.resolve()
    overlay_source_root = overlay_source_root.resolve()
    canonical_source_root = canonical_source_root.resolve()
    private_replacement_plan_path = (
        private_replacement_plan_path.resolve()
    )
    private_reverse_plan_path = private_reverse_plan_path.resolve()
    bundled_jar = bundled_jar.resolve()
    out_dir = out_dir.resolve()
    artifacts = [path.resolve() for path in official_artifacts]

    if not overlay_source_root.is_dir():
        raise DependencyOfficialDerivedCompileError(
            "overlay source root does not exist"
        )
    if not canonical_source_root.is_dir():
        raise DependencyOfficialDerivedCompileError(
            "canonical source root does not exist"
        )
    if not bundled_jar.is_file():
        raise DependencyOfficialDerivedCompileError(
            "bundled JAR does not exist"
        )
    if not artifacts or any(not path.is_file() for path in artifacts):
        raise DependencyOfficialDerivedCompileError(
            "official artifact set is incomplete"
        )
    if out_dir.exists() and any(out_dir.iterdir()):
        raise DependencyOfficialDerivedCompileError(
            "derived compile output directory must be empty"
        )

    overlay = _load_json(
        overlay_manifest_path,
        kind="dependency_source_overlay_manifest",
    )
    replacement = _load_json(
        private_replacement_plan_path,
        kind="dependency_replacement_boundary_plan",
    )
    reverse = _load_json(
        private_reverse_plan_path,
        kind="dependency_reverse_compile_transport_plan",
    )

    if replacement.get("identifiers_included") is not True:
        raise DependencyOfficialDerivedCompileError(
            "requires private DEPREPLACE plan"
        )
    if reverse.get("identifiers_included") is not True:
        raise DependencyOfficialDerivedCompileError(
            "requires private DEPREVERSE plan"
        )
    if reverse.get("summary", {}).get(
        "ready_for_bytecode_restore"
    ) is not True:
        raise DependencyOfficialDerivedCompileError(
            "DEPREVERSE is not ready for bytecode restore"
        )

    replacement_id = replacement.get("replacement_plan_id")
    if overlay.get("replacement_plan_id") != replacement_id:
        raise DependencyOfficialDerivedCompileError(
            "overlay is bound to a different DEPREPLACE"
        )
    if reverse.get("replacement_plan_id") != replacement_id:
        raise DependencyOfficialDerivedCompileError(
            "DEPREVERSE is bound to a different DEPREPLACE"
        )

    remap_id = replacement.get("dependency_remap_proof_id")
    if overlay.get("dependency_remap_proof_id") != remap_id:
        raise DependencyOfficialDerivedCompileError(
            "overlay remap authority differs"
        )
    if reverse.get("dependency_remap_proof_id") != remap_id:
        raise DependencyOfficialDerivedCompileError(
            "DEPREVERSE remap authority differs"
        )

    bundled_sha = _sha256_file(bundled_jar)
    for label, value in (
        ("overlay", overlay.get("bundled_jar_sha256")),
        ("DEPREPLACE", replacement.get("bundled_jar_sha256")),
        ("DEPREVERSE", reverse.get("bundled_jar_sha256")),
    ):
        if value != bundled_sha:
            raise DependencyOfficialDerivedCompileError(
                f"{label} bundled JAR authority differs"
            )

    release = replacement.get("java_release")
    if (
        not isinstance(release, int)
        or isinstance(release, bool)
        or release < 1
        or overlay.get("java_release") != release
    ):
        raise DependencyOfficialDerivedCompileError(
            "Java release authority differs"
        )

    official_shas = _artifact_shas(artifacts)
    if sorted(overlay.get("official_artifact_sha256", [])) != official_shas:
        raise DependencyOfficialDerivedCompileError(
            "overlay official artifact authority differs"
        )
    replacement_shas = sorted(
        str(row.get("sha256"))
        for row in replacement.get("official_artifacts", [])
        if row.get("sha256") is not None
    )
    if replacement_shas and replacement_shas != official_shas:
        raise DependencyOfficialDerivedCompileError(
            "DEPREPLACE official artifact authority differs"
        )

    canonical_before, canonical_files, canonical_bytes = (
        source_tree_digest(canonical_source_root)
    )
    if overlay.get("input_source_tree_sha256") != canonical_before:
        raise DependencyOfficialDerivedCompileError(
            "canonical source does not match overlay input authority"
        )
    overlay_sha, overlay_files, overlay_bytes = source_tree_digest(
        overlay_source_root
    )
    if overlay.get("output_source_tree_sha256") != overlay_sha:
        raise DependencyOfficialDerivedCompileError(
            "overlay source tree does not match manifest"
        )
    if int(overlay.get("java_file_count", -1)) != len(overlay_files):
        raise DependencyOfficialDerivedCompileError(
            "overlay Java file count differs"
        )

    prefixes = _normalize_prefixes(project_prefixes)
    java = _require(java_command)
    javac = _require(javac_command)

    out_dir.mkdir(parents=True, exist_ok=True)
    generated = out_dir / "generated-official"
    generated.mkdir()
    generated_jar = out_dir / "generated-official-project.jar"
    restored_jar = out_dir / "restored-bundled-project.jar"
    argfile = out_dir / "javac.args"

    sources = sorted(
        overlay_source_root.rglob("*.java"),
        key=lambda path: path.relative_to(
            overlay_source_root
        ).as_posix(),
    )
    if not sources:
        raise DependencyOfficialDerivedCompileError(
            "overlay contains no Java sources"
        )

    classpath = [*artifacts, bundled_jar]
    args = [
        "-proc:none",
        "-encoding",
        "UTF-8",
        "-Xlint:none",
        "--release",
        str(release),
        "-classpath",
        os.pathsep.join(str(path) for path in classpath),
        "-d",
        str(generated),
        *[str(path) for path in sources],
    ]
    argfile.write_text(
        "\n".join(_arg(value) for value in args) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    proc = subprocess.run(
        [javac, "@" + str(argfile)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise DependencyOfficialDerivedCompileError(
            "official-first overlay javac failed:\n"
            + proc.stdout
            + proc.stderr
        )

    generated_count, generated_bytes = _write_project_jar(
        generated,
        generated_jar,
        prefixes,
    )

    try:
        restored = apply_dependency_reverse_transport(
            private_reverse_plan_path,
            generated_jar,
            restored_jar,
            project_prefixes=prefixes,
            java_command=java,
            javac_command=javac,
        )
    except DependencyReverseTransportApplyError as exc:
        raise DependencyOfficialDerivedCompileError(str(exc)) from exc

    canonical_after, after_files, after_bytes = source_tree_digest(
        canonical_source_root
    )
    if (
        canonical_after != canonical_before
        or len(after_files) != len(canonical_files)
        or after_bytes != canonical_bytes
    ):
        raise DependencyOfficialDerivedCompileError(
            "canonical source changed during derived compile"
        )
    if _sha256_file(bundled_jar) != bundled_sha:
        raise DependencyOfficialDerivedCompileError(
            "bundled runtime dependency was modified"
        )
    if _artifact_shas(artifacts) != official_shas:
        raise DependencyOfficialDerivedCompileError(
            "official compile artifacts were modified"
        )

    material = {
        "overlay_id": overlay["overlay_id"],
        "replacement_plan_id": replacement_id,
        "reverse_plan_id": reverse["reverse_plan_id"],
        "reverse_application_id": restored["application_id"],
        "canonical_source_tree_sha256": canonical_before,
        "overlay_source_tree_sha256": overlay_sha,
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": official_shas,
        "generated_project_jar_sha256": _sha256_file(
            generated_jar
        ),
        "restored_project_jar_sha256": _sha256_file(
            restored_jar
        ),
        "release": release,
    }
    return {
        "schema_version": 1,
        "kind": "dependency_official_first_derived_compile",
        "compile_id": (
            "DEPOFFICIALCOMPILE_"
            + _stable_digest(material)[:20].upper()
        ),
        "status": "complete",
        **material,
        "summary": {
            "source_count": len(sources),
            "generated_project_class_count": generated_count,
            "generated_project_class_bytes": generated_bytes,
            "reverse_reference_surface_match": restored[
                "summary"
            ]["reference_surface_match"],
            "project_class_identity_changed_count": restored[
                "summary"
            ]["project_class_identity_changed_count"],
            "canonical_source_modified": False,
            "bundled_runtime_dependency_modified": False,
            "official_compile_artifacts_modified": False,
            "official_dependencies_runtime_allowed": False,
            "restored_project_bytecode_ready_for_runtime_assembly": True,
        },
    }


def write_dependency_official_derived_compile(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
