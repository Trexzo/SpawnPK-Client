from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any
import zipfile


class BuildAuthorityError(ValueError):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_properties(raw: bytes) -> dict[str, str]:
    text = raw.decode("utf-8", errors="replace")
    out: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "!")):
            continue
        if "=" in stripped:
            key, value = stripped.split("=", 1)
        elif ":" in stripped:
            key, value = stripped.split(":", 1)
        else:
            continue
        out[key.strip()] = value.strip()
    return out


def _java_release_from_major(major: int) -> int | None:
    # JVM major 45 = Java 1.1, 46 = 1.2 ... 52 = Java 8, 53 = Java 9.
    if 45 <= major <= 200:
        return major - 44
    return None


def _embedded_maven_metadata(
    jar: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with zipfile.ZipFile(jar) as z:
        names = set(z.namelist())
        props = sorted(
            name
            for name in names
            if name.startswith("META-INF/maven/")
            and name.endswith("/pom.properties")
        )
        for path in props:
            raw = z.read(path)
            values = _parse_properties(raw)
            prefix = path[: -len("pom.properties")]
            pom_path = prefix + "pom.xml"
            pom_sha = (
                _sha256_bytes(z.read(pom_path))
                if pom_path in names
                else None
            )
            rows.append(
                {
                    "group_id": values.get("groupId"),
                    "artifact_id": values.get("artifactId"),
                    "version": values.get("version"),
                    "properties_entry": path,
                    "properties_sha256": _sha256_bytes(raw),
                    "pom_entry": pom_path if pom_path in names else None,
                    "pom_sha256": pom_sha,
                    "evidence": "EXACT_EMBEDDED_MAVEN_METADATA",
                }
            )
    rows.sort(
        key=lambda row: (
            str(row.get("group_id")),
            str(row.get("artifact_id")),
            str(row.get("version")),
            row["properties_entry"],
        )
    )
    return rows


def _root_build_metadata(jar: Path) -> list[dict[str, Any]]:
    candidates = {
        "pom.xml",
        "build.xml",
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "settings.gradle.kts",
        "gradle.properties",
    }
    out: list[dict[str, Any]] = []
    with zipfile.ZipFile(jar) as z:
        for info in z.infolist():
            name = info.filename
            if "/" not in name and (
                name in candidates
                or name.endswith(".iml")
            ):
                raw = z.read(name)
                out.append(
                    {
                        "entry": name,
                        "sha256": _sha256_bytes(raw),
                        "size": len(raw),
                        "evidence": "EXACT_ROOT_ARCHIVE_METADATA",
                    }
                )
    return sorted(out, key=lambda row: row["entry"])


def _probe_executable(
    name: str,
    args: list[str],
) -> dict[str, Any]:
    found = shutil.which(name)
    if found is None:
        raise BuildAuthorityError(
            f"required Java toolchain executable not found on PATH: {name}"
        )
    path = Path(found).resolve()
    proc = subprocess.run(
        [str(path), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise BuildAuthorityError(
            f"{name} probe failed with exit code {proc.returncode}: "
            f"{proc.stdout}{proc.stderr}"
        )
    combined = (proc.stdout + proc.stderr).strip()
    binary_sha = _sha256_file(path) if path.is_file() else None
    return {
        "requested_command": name,
        "resolved_path": str(path),
        "binary_sha256": binary_sha,
        "version_output": combined,
    }


def build_build_authority(
    source_jar: Path,
    source_index: dict[str, Any],
    *,
    source_readiness: dict[str, Any] | None = None,
    class_prefix: str = "rs/",
    java_command: str = "java",
    javac_command: str = "javac",
) -> dict[str, Any]:
    source_jar = source_jar.resolve()
    if not source_jar.is_file():
        raise BuildAuthorityError(
            f"source authority JAR does not exist: {source_jar}"
        )

    actual_sha = _sha256_file(source_jar)
    index_sha = str(source_index.get("sha256", "")).lower()
    if actual_sha.lower() != index_sha:
        raise BuildAuthorityError(
            "source JAR SHA-256 does not match exact index: "
            f"{actual_sha} != {index_sha}"
        )

    if source_readiness is not None:
        if (
            source_readiness.get("schema_version") != 1
            or source_readiness.get("kind")
            != "source_readiness_report"
        ):
            raise BuildAuthorityError(
                "unsupported source-readiness report"
            )
        if (
            str(
                source_readiness.get(
                    "source_authority_sha256",
                    "",
                )
            ).lower()
            != actual_sha.lower()
        ):
            raise BuildAuthorityError(
                "source-readiness authority SHA does not match source JAR"
            )

    class_rows = [
        row
        for path, row in source_index.get("classes", {}).items()
        if not class_prefix or path.startswith(class_prefix)
    ]
    if not class_rows:
        raise BuildAuthorityError(
            f"exact index has no classes in prefix {class_prefix!r}"
        )

    major_counts: Counter[int] = Counter(
        int(row["major"])
        for row in class_rows
        if isinstance(row.get("major"), int)
    )
    if not major_counts:
        raise BuildAuthorityError(
            "exact index contains no class major versions"
        )

    releases = {
        str(major): _java_release_from_major(major)
        for major in sorted(major_counts)
    }
    dominant_major, dominant_count = max(
        major_counts.items(),
        key=lambda item: (item[1], item[0]),
    )

    maven = _embedded_maven_metadata(source_jar)
    root_meta = _root_build_metadata(source_jar)
    java_probe = _probe_executable(
        java_command,
        ["-version"],
    )
    javac_probe = _probe_executable(
        javac_command,
        ["-version"],
    )

    external_roots = (
        dict(
            source_readiness.get(
                "external_import_roots",
                {},
            )
        )
        if source_readiness is not None
        else {}
    )

    material = {
        "source_sha256": actual_sha,
        "class_prefix": class_prefix,
        "class_major_versions": dict(
            sorted(major_counts.items())
        ),
        "embedded_maven": [
            {
                "group_id": row["group_id"],
                "artifact_id": row["artifact_id"],
                "version": row["version"],
                "properties_sha256": row[
                    "properties_sha256"
                ],
                "pom_sha256": row["pom_sha256"],
            }
            for row in maven
        ],
        "java_version": java_probe["version_output"],
        "javac_version": javac_probe["version_output"],
    }
    authority_id = (
        "BUILDAUTH_"
        + hashlib.sha256(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "build_authority_manifest",
        "authority_id": authority_id,
        "source_sha256": actual_sha,
        "class_prefix": class_prefix,
        "bytecode": {
            "class_count": len(class_rows),
            "major_versions": {
                str(k): v
                for k, v in sorted(major_counts.items())
            },
            "java_release_by_major": releases,
            "dominant_major": dominant_major,
            "dominant_major_count": dominant_count,
            "dominant_java_release": _java_release_from_major(
                dominant_major
            ),
            "evidence": "EXACT_CLASSFILE_HEADER",
        },
        "compiler_runtime": {
            "java": java_probe,
            "javac": javac_probe,
            "evidence": "LOCAL_PINNED_TOOLCHAIN_PROBE",
            "note": (
                "Compiler runtime is the rebuild toolchain, not proof of the "
                "original developer JDK."
            ),
        },
        "embedded_maven_metadata": maven,
        "root_build_metadata": root_meta,
        "source_dependency_surface": {
            "external_import_roots": external_roots,
            "evidence": (
                "RECOVERED_SOURCE_IMPORT_SURFACE"
                if source_readiness is not None
                else "NOT_SUPPLIED"
            ),
            "note": (
                "Import roots are discovery evidence only and are not mapped "
                "to Maven coordinates automatically."
            ),
        },
        "interpretation": {
            "embedded_maven_metadata_is_original_build_file": False,
            "embedded_maven_metadata_proves_archive_metadata_strings": True,
            "compiler_runtime_is_original_jdk": False,
        },
    }


def write_build_authority(
    manifest: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
