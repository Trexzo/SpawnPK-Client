from __future__ import annotations

"""Pinned research-only compile capsule; never canonical dependency authority."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from .v309_external_source_corpus_intake import digest as file_sha256

EXACT_V309_SHA256 = "ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
SOURCE_ARCHIVE_SHA256 = "3a3b84a03f9cc6588a714b03f8b36ae3a7008ce4976de2609841fdf9db9e80ad"
DEOB_TOOL_SHA256 = "a4a5db25ee916885462a8b5efc946b9541154d2f0106df0b33b8ff58e27d17c7"
LITERAL_NAMESPACE_PREFIXES = ("com/", "org/", "gnu/", "javax/", "net/")
EXCLUDED_CLASS_ROOTS = ("rs/", "tools/", "a/")
MAX_ENTRY_BYTES = 100_000_000


class V309CompileCapsuleError(ValueError):
    pass


def _safe_names(z: ZipFile) -> list[str]:
    names = []
    for info in z.infolist():
        name = info.filename
        bits = (info.external_attr >> 16) & 0o170000
        parts = name.split("/")
        if (name.startswith("/") or "\\" in name or info.flag_bits & 1
            or (not name.endswith("/") and parts[-1] in ("", ".", ".."))
            or any(p in ("", ".", "..") for p in parts[:-1])
            or bits == 0o120000 or info.file_size > MAX_ENTRY_BYTES):
            raise V309CompileCapsuleError("unsafe ZIP entry")
        names.append(name)
    if not names or len(names) != len(set(names)):
        raise V309CompileCapsuleError("duplicate or empty ZIP inventory")
    return names


def _zip_write_stable(output: ZipFile, name: str, data: bytes) -> None:
    info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    output.writestr(info, data, compress_type=ZIP_DEFLATED, compresslevel=6)


def build_external_compile_capsule(
    *, original_jar: Path, source_archive: Path, deob_tool_archive: Path,
    out_dir: Path, expected_client_sha256: str, expected_source_sha256: str,
    expected_deob_sha256: str, expected_external_classes: int | None = None,
) -> dict:
    pins = {
        "original": (original_jar, expected_client_sha256),
        "source": (source_archive, expected_source_sha256),
        "deob": (deob_tool_archive, expected_deob_sha256),
    }
    if any(not re.fullmatch("[0-9a-f]{64}", sha) for _, sha in pins.values()):
        raise V309CompileCapsuleError("invalid required private SHA256")
    if out_dir.exists() or out_dir.is_symlink():
        raise V309CompileCapsuleError("output directory already exists")
    if any(out_dir.resolve() == path.resolve() for path, _ in pins.values()):
        raise V309CompileCapsuleError("output overlaps protected private input")
    for path, sha in pins.values():
        if file_sha256(path) != sha:
            raise V309CompileCapsuleError("original SHA256 preflight mismatch")

    with ZipFile(original_jar) as original, ZipFile(source_archive) as source, \
         ZipFile(deob_tool_archive) as deob:
        original_names = _safe_names(original)
        source_names = _safe_names(source)
        deob_names = _safe_names(deob)
        roots = {name.split("/")[0] for name in source_names if "/" in name}
        if len(roots) != 1:
            raise V309CompileCapsuleError("candidate ZIP root ambiguity")
        src_prefix = next(iter(roots)) + "/src/main/java/"
        java_sources = [
            name[len(src_prefix):] for name in source_names
            if name.startswith(src_prefix) and name.endswith(".java")
        ]
        if not java_sources:
            raise V309CompileCapsuleError("missing Java source corpus")
        source_defined = {name[:-5] + ".class" for name in java_sources}
        # Native project owners and explicitly source-defined package roots
        # are NEVER provided as fallback binaries. The candidate archive is
        # unaccepted source and this is not a dependency-authority certificate.
        include = sorted(
            name for name in original_names
            if name.endswith(".class") and name.startswith(LITERAL_NAMESPACE_PREFIXES)
            and not name.startswith(EXCLUDED_CLASS_ROOTS)
            and not name.startswith("com/apple/eawt/")
            and name not in source_defined
        )
        if (not include or len(set(include)) != len(include)
            or any(name.startswith("rs/") for name in include)
            or any(name in source_defined for name in include)
            or (expected_external_classes is not None
                and len(include) != expected_external_classes)):
            raise V309CompileCapsuleError("unsafe external candidate class partition")

        lombok = [
            name for name in deob_names if name.endswith("/lib/lombok-1.18.32.jar")
        ]
        if len(lombok) != 1:
            raise V309CompileCapsuleError("Lombok compiler dependency missing/ambiguous")
        lombok_bytes = deob.read(lombok[0])
        with ZipFile(__import__("io").BytesIO(lombok_bytes)) as lombok_archive:
            _safe_names(lombok_archive)
            if "lombok/SneakyThrows.class" not in lombok_archive.namelist():
                raise V309CompileCapsuleError("invalid compiler annotation processor")

        out_dir.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".v309-compile-capsule-", dir=out_dir.parent))
        try:
            external = stage / "external-namespace-compile-candidate.jar"
            with ZipFile(external, "w") as capsule:
                for name in include:
                    _zip_write_stable(capsule, name, original.read(name))
            lombok_path = stage / "lombok-1.18.32.jar"
            lombok_path.write_bytes(lombok_bytes)
            body = {
                "schema_version": 1,
                "kind": "v309_external_namespace_compile_capsule_research",
                "canonical": False,
                "state": "PROVISIONAL_COMPILE_ONLY_NO_DEPENDENCY_OR_SOURCE_ACCEPTANCE",
                "original_client_sha256": expected_client_sha256,
                "external_source_archive_sha256": expected_source_sha256,
                "deob_pipeline_archive_sha256": expected_deob_sha256,
                "summary": {
                    "source_java_files": len(java_sources),
                    "external_namespace_candidate_classes": len(include),
                    "source_owned_classfile_fallbacks": 0,
                    "spawnpk_rs_classfile_fallbacks": 0,
                    "exact_compile_capsule_sha256": file_sha256(external),
                    "lombok_compiler_sha256": file_sha256(lombok_path),
                    "complete_dependency_authority_verified": False,
                    "clean_whole_project_build_verified": False,
                    "new_accepted_source_or_member_identities": 0,
                },
                "limits": "Not a third-party-provenance certificate: non-rs obfuscated classes could include first-party code. Excludes rs, tools, a, and source-owned com/apple/eawt classes. Never copy the derived JAR to Git; use only for local compile diagnostics.",
            }
            raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
            result = {"report_id": "SPKDEPCAPSULE_" + hashlib.sha256(raw).hexdigest()[:20].upper(), **body}
            (stage / "COMPILE-CAPSULE-RESEARCH.json").write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            for path, sha in pins.values():
                if file_sha256(path) != sha:
                    raise V309CompileCapsuleError("private input mutated during scan")
            if out_dir.exists() or out_dir.is_symlink():
                raise V309CompileCapsuleError("output appeared during research")
            stage.rename(out_dir)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="spk-v309-external-compile-capsule")
    parser.add_argument("--original-v309", required=True, type=Path)
    parser.add_argument("--source-zip", required=True, type=Path)
    parser.add_argument("--deob-tool-zip", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--original-sha256", default=EXACT_V309_SHA256)
    parser.add_argument("--source-sha256", default=SOURCE_ARCHIVE_SHA256)
    parser.add_argument("--deob-sha256", default=DEOB_TOOL_SHA256)
    parser.add_argument("--expected-external-classes", default=9333, type=int)
    a = parser.parse_args(argv)
    try:
        result = build_external_compile_capsule(
            original_jar=a.original_v309, source_archive=a.source_zip,
            deob_tool_archive=a.deob_tool_zip, out_dir=a.out_dir,
            expected_client_sha256=a.original_sha256,
            expected_source_sha256=a.source_sha256,
            expected_deob_sha256=a.deob_sha256,
            expected_external_classes=a.expected_external_classes)
    except Exception as exc:
        # No raw paths, external class/member names, CP contents or tracebacks.
        print("SPK_V309_EXTERNAL_COMPILE_CAPSULE_FAIL_CLOSED")
        print("category=" + type(exc).__name__)
        return 1
    print("SPK_V309_EXTERNAL_COMPILE_CAPSULE_PASS_RESEARCH_ONLY")
    print("report_id=" + result["report_id"])
    print("canonical_changes=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
