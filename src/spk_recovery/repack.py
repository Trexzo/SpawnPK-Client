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


def _member_exists(
    index: dict[str, Any],
    *,
    owner: str,
    kind: str,
    name: str,
    descriptor: str,
) -> bool:
    cls = index.get("classes", {}).get(owner + ".class")
    if not isinstance(cls, dict):
        return False
    collection = "fields" if kind == "field" else "methods"
    return any(
        member.get("name") == name
        and member.get("descriptor") == descriptor
        for member in cls.get(collection, [])
    )


def _validate_inputs(
    source_jar: Path,
    index: dict[str, Any],
    class_plan: dict[str, Any] | None,
    member_plan: dict[str, Any] | None,
) -> str:
    if not source_jar.is_file():
        raise RepackError(f"source JAR does not exist: {source_jar}")
    if class_plan is None and member_plan is None:
        raise RepackError("at least one class/member remap plan is required")

    expected: set[str] = set()

    if class_plan is not None:
        if (
            class_plan.get("schema_version") != 1
            or class_plan.get("kind") != "remap_plan"
        ):
            raise RepackError("unsupported class remap plan schema/kind")
        expected.add(str(class_plan.get("source_sha256", "")).lower())
        entry_paths = set(index.get("entries", {}))
        for row in class_plan.get("classes", []):
            source = row.get("source_entry_path")
            target = row.get("target_entry_path")
            if source not in entry_paths:
                raise RepackError(
                    f"source class missing from exact index: {source!r}"
                )
            if not isinstance(target, str) or not target.endswith(".class"):
                raise RepackError(
                    f"invalid target class entry path: {target!r}"
                )

    if member_plan is not None:
        if (
            member_plan.get("schema_version") != 1
            or member_plan.get("kind") != "member_remap_plan"
        ):
            raise RepackError("unsupported member remap plan schema/kind")
        expected.add(str(member_plan.get("source_sha256", "")).lower())
        for row in member_plan.get("members", []):
            kind = row.get("kind")
            if kind not in {"field", "method"}:
                raise RepackError(f"invalid member kind: {kind!r}")
            if not _member_exists(
                index,
                owner=str(row.get("owner_internal_name", "")),
                kind=kind,
                name=str(row.get("source_name", "")),
                descriptor=str(row.get("descriptor", "")),
            ):
                raise RepackError(
                    "member remap source coordinate absent from exact index: "
                    f"{row.get('owner_internal_name')}."
                    f"{row.get('source_name')}{row.get('descriptor')}"
                )

    if len(expected) != 1:
        raise RepackError(
            "class/member remap plans do not agree on one exact source SHA"
        )
    expected_sha = next(iter(expected))
    actual_sha = _sha256_file(source_jar)
    if actual_sha.lower() != expected_sha:
        raise RepackError(
            f"source JAR SHA-256 {actual_sha} does not match plan {expected_sha}"
        )
    if str(index.get("sha256", "")).lower() != expected_sha:
        raise RepackError("source index SHA-256 does not match remap plan")
    return expected_sha


def _write_mapping(
    class_plan: dict[str, Any] | None,
    member_plan: dict[str, Any] | None,
    path: Path,
) -> None:
    rows: list[str] = []

    if class_plan is not None:
        for row in sorted(
            class_plan.get("classes", []),
            key=lambda r: r["source_internal_name"],
        ):
            rows.append(
                "C\t"
                + row["source_internal_name"]
                + "\t"
                + row["target_internal_name"]
            )

    if member_plan is not None:
        for row in sorted(
            member_plan.get("members", []),
            key=lambda r: (
                r["owner_internal_name"],
                r["kind"],
                r["source_name"],
                r["descriptor"],
            ),
        ):
            prefix = "F" if row["kind"] == "field" else "M"
            rows.append(
                prefix
                + "\t"
                + row["owner_internal_name"]
                + "\t"
                + row["source_name"]
                + "\t"
                + row["descriptor"]
                + "\t"
                + row["target_name"]
            )

    if not rows:
        raise RepackError("remap plans contain no mappings")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _compile_helper(classes_dir: Path, *, javac: str) -> None:
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
    class_plan: dict[str, Any] | None,
    output_jar: Path,
    *,
    member_plan: dict[str, Any] | None = None,
    allow_package_resource_risk: bool = False,
    rewrite_class_name_strings: bool = False,
    allow_member_reflection_risk: bool = False,
    java_command: str = "java",
    javac_command: str = "javac",
) -> dict[str, Any]:
    """Apply verified class/member remap plans to one exact client JAR."""
    source_jar = source_jar.resolve()
    output_jar = output_jar.resolve()
    source_sha = _validate_inputs(
        source_jar,
        index,
        class_plan,
        member_plan,
    )

    if class_plan is not None:
        risk = remap_risk_scan(index, class_plan)
    else:
        risk = {
            "summary": {
                "literal_class_name_hit_count": 0,
                "package_resource_hit_count": 0,
                "service_descriptor_count": 0,
                "manifest_requires_review": False,
            }
        }

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

    member_count = (
        int(member_plan.get("member_count", 0))
        if member_plan is not None
        else 0
    )
    if member_count and not allow_member_reflection_risk:
        raise RepackError(
            "member remap reflection/name-sensitivity is not yet proven safe; "
            "use explicit allow_member_reflection_risk acknowledgement"
        )

    java = _require_executable(java_command)
    javac = _require_executable(javac_command)
    output_jar.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="spk-remap-") as td:
        temp = Path(td)
        mapping = temp / "mapping.tsv"
        classes_dir = temp / "classes"
        _write_mapping(class_plan, member_plan, mapping)
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

    mapped_classes = 0
    if class_plan is not None:
        for row in class_plan["classes"]:
            source_path = row["source_entry_path"]
            target_path = row["target_entry_path"]
            if (
                source_path != target_path
                and source_path in output_index["entries"]
            ):
                raise RepackError(
                    f"old class path remains after remap: {source_path}"
                )
            if target_path not in output_index["classes"]:
                raise RepackError(
                    f"target class path missing after remap: {target_path}"
                )
            actual_name = output_index["classes"][target_path]["internal_name"]
            if actual_name != row["target_internal_name"]:
                raise RepackError(
                    f"target class internal name mismatch for {target_path}: "
                    f"{actual_name!r}"
                )
        mapped_classes = int(class_plan["class_count"])

    # Verify transformed member declarations using the post-class-remap owner path.
    if member_plan is not None:
        class_names = {
            row["source_internal_name"]: row["target_internal_name"]
            for row in (class_plan or {}).get("classes", [])
        }
        for row in member_plan.get("members", []):
            owner = class_names.get(
                row["owner_internal_name"],
                row["owner_internal_name"],
            )
            cls = output_index["classes"].get(owner + ".class")
            if not isinstance(cls, dict):
                raise RepackError(
                    f"transformed member owner class missing: {owner}"
                )
            collection = (
                "fields" if row["kind"] == "field" else "methods"
            )
            if not any(
                m.get("name") == row["target_name"]
                and m.get("descriptor") == row["descriptor"]
                for m in cls.get(collection, [])
            ):
                raise RepackError(
                    f"transformed {row['kind']} missing: "
                    f"{owner}.{row['target_name']}{row['descriptor']}"
                )

    return {
        "schema_version": 1,
        "kind": "jar_remap_result",
        "source_sha256": source_sha,
        "output_sha256": output_index["sha256"],
        "mapped_classes": mapped_classes,
        "mapped_members": member_count,
        "mapped_fields": (
            int(member_plan.get("field_count", 0))
            if member_plan is not None
            else 0
        ),
        "mapped_methods": (
            int(member_plan.get("method_count", 0))
            if member_plan is not None
            else 0
        ),
        "output_entries": output_index["summary"]["entry_count"],
        "output_classes": output_index["summary"]["class_count"],
        "class_parse_errors": output_index["summary"]["class_parse_error_count"],
        "rewrite_class_name_strings": rewrite_class_name_strings,
        "package_resource_risk_acknowledged": allow_package_resource_risk,
        "member_reflection_risk_acknowledged": allow_member_reflection_risk,
        "helper_stdout": helper_stdout.strip().splitlines(),
        "risk_summary": risk["summary"],
    }


def write_result(result: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
