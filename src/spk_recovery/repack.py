from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from .indexer import index_jar
from .remap_plan import RemapPlanError, remap_risk_scan


class RepackError(RemapPlanError):
    pass


_ASM_EXPORTS = (
    "java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED",
    "java.base/jdk.internal.org.objectweb.asm.commons=ALL-UNNAMED",
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _helper_source() -> Path:
    path = Path(__file__).resolve().parent / "java" / "SpkJarRemapper.java"
    if not path.is_file():
        raise RepackError(f"missing packaged Java remapper helper: {path}")
    return path


def _require_executable(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise RepackError(f"required executable not found on PATH: {name}")
    return found


def _validate_inputs(
    source_jar: Path,
    index: dict[str, Any],
    plan: dict[str, Any],
) -> None:
    if not source_jar.is_file():
        raise RepackError(f"source JAR does not exist: {source_jar}")
    if (
        plan.get("schema_version") != 1
        or plan.get("kind") != "remap_plan"
    ):
        raise RepackError("unsupported remap plan schema/kind")

    actual_sha = _sha256_file(source_jar)
    expected_sha = str(plan.get("source_sha256", "")).lower()
    if actual_sha.lower() != expected_sha:
        raise RepackError(
            f"source JAR SHA-256 {actual_sha} does not match plan {expected_sha}"
        )
    if str(index.get("sha256", "")).lower() != expected_sha:
        raise RepackError("source index SHA-256 does not match remap plan")

    entry_paths = set(index.get("entries", {}))
    for row in plan.get("classes", []):
        source = row.get("source_entry_path")
        target = row.get("target_entry_path")
        if source not in entry_paths:
            raise RepackError(f"source class missing from exact index: {source!r}")
        if not isinstance(target, str) or not target.endswith(".class"):
            raise RepackError(f"invalid target class entry path: {target!r}")


def _write_mapping(plan: dict[str, Any], path: Path) -> None:
    rows = []
    for row in sorted(
        plan.get("classes", []),
        key=lambda r: r["source_internal_name"],
    ):
        rows.append(
            row["source_internal_name"]
            + "\t"
            + row["target_internal_name"]
        )
    if not rows:
        raise RepackError("remap plan contains no classes")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _compile_helper(
    classes_dir: Path,
    *,
    javac: str,
) -> None:
    classes_dir.mkdir(parents=True, exist_ok=True)
    cmd = [javac]
    for export in _ASM_EXPORTS:
        cmd.extend(["--add-exports", export])
    cmd.extend(["-d", str(classes_dir), str(_helper_source())])
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise RepackError(
            "Java remapper helper compilation failed:\n"
            + proc.stdout
            + proc.stderr
        )


def _run_helper(
    mapping: Path,
    source_jar: Path,
    output_jar: Path,
    classes_dir: Path,
    *,
    java: str,
    rewrite_class_name_strings: bool,
) -> str:
    cmd = [java]
    for export in _ASM_EXPORTS:
        cmd.extend(["--add-exports", export])
    cmd.extend(
        [
            "-cp",
            str(classes_dir),
            "SpkJarRemapper",
            str(mapping),
            str(source_jar),
            str(output_jar),
        ]
    )
    if rewrite_class_name_strings:
        cmd.append("--rewrite-class-name-strings")

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise RepackError(
            "Java whole-JAR remapper failed:\n"
            + proc.stdout
            + proc.stderr
        )
    return proc.stdout


def remap_jar(
    source_jar: Path,
    index: dict[str, Any],
    plan: dict[str, Any],
    output_jar: Path,
    *,
    allow_package_resource_risk: bool = False,
    rewrite_class_name_strings: bool = False,
    java_command: str = "java",
    javac_command: str = "javac",
) -> dict[str, Any]:
    """Apply a verified class-only remap plan to one exact client JAR.

    All JVM type references are rewritten through ASM. Manifest Main-Class and
    META-INF/services class names are rewritten deterministically. Arbitrary
    package resources are never moved implicitly. Exact class-name string
    literals are rewritten only with explicit opt-in.
    """
    source_jar = source_jar.resolve()
    output_jar = output_jar.resolve()
    _validate_inputs(source_jar, index, plan)

    risk = remap_risk_scan(index, plan)
    literal_hits = risk["summary"]["literal_class_name_hit_count"]
    package_hits = risk["summary"]["package_resource_hit_count"]

    if literal_hits and not rewrite_class_name_strings:
        raise RepackError(
            f"remap has {literal_hits} exact class-name string literal risk(s); "
            "use explicit rewrite_class_name_strings opt-in"
        )
    if package_hits and not allow_package_resource_risk:
        raise RepackError(
            f"remap has {package_hits} package-resource risk(s); "
            "review and explicitly allow before repackaging"
        )

    java = _require_executable(java_command)
    javac = _require_executable(javac_command)
    output_jar.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="spk-remap-") as td:
        temp = Path(td)
        mapping = temp / "mapping.tsv"
        classes_dir = temp / "classes"
        _write_mapping(plan, mapping)
        _compile_helper(classes_dir, javac=javac)
        helper_stdout = _run_helper(
            mapping,
            source_jar,
            output_jar,
            classes_dir,
            java=java,
            rewrite_class_name_strings=rewrite_class_name_strings,
        )

    if not output_jar.is_file():
        raise RepackError("remapper did not produce an output JAR")

    output_index = index_jar(output_jar)
    source_entry_count = index.get("summary", {}).get("entry_count")
    if output_index["summary"]["entry_count"] != source_entry_count:
        raise RepackError(
            "output entry count changed unexpectedly: "
            f"{output_index['summary']['entry_count']} != {source_entry_count}"
        )
    if output_index["summary"]["class_parse_error_count"] != 0:
        raise RepackError(
            "transformed JAR contains JVM class parse errors: "
            f"{output_index['summary']['class_parse_error_count']}"
        )

    for row in plan["classes"]:
        source_path = row["source_entry_path"]
        target_path = row["target_entry_path"]
        if source_path != target_path and source_path in output_index["entries"]:
            raise RepackError(f"old class path remains after remap: {source_path}")
        if target_path not in output_index["classes"]:
            raise RepackError(f"target class path missing after remap: {target_path}")
        actual_name = output_index["classes"][target_path]["internal_name"]
        if actual_name != row["target_internal_name"]:
            raise RepackError(
                f"target class internal name mismatch for {target_path}: "
                f"{actual_name!r}"
            )

    return {
        "schema_version": 1,
        "kind": "class_remap_result",
        "source_sha256": plan["source_sha256"],
        "output_sha256": output_index["sha256"],
        "mapped_classes": plan["class_count"],
        "output_entries": output_index["summary"]["entry_count"],
        "output_classes": output_index["summary"]["class_count"],
        "class_parse_errors": output_index["summary"]["class_parse_error_count"],
        "rewrite_class_name_strings": rewrite_class_name_strings,
        "package_resource_risk_acknowledged": allow_package_resource_risk,
        "helper_stdout": helper_stdout.strip().splitlines(),
        "risk_summary": risk["summary"],
    }


def write_result(result: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
