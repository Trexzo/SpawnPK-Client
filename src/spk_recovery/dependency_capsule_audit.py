from __future__ import annotations

from collections import Counter
import hashlib
import json
import re
from pathlib import Path
import subprocess
import tempfile
from typing import Any
import zipfile

from .classfile import ClassFormatError, parse_class


class DependencyCapsuleAuditError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _jar_entries(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as z:
        return {
            info.filename: z.read(info)
            for info in z.infolist()
            if not info.is_dir()
        }


def _probe_source(
    internal_name: str,
    index: int,
) -> tuple[str, str]:
    dotted = internal_name.replace("/", ".")
    simple = dotted.rsplit(".", 1)[-1]
    probe = f"SpkDependencyProbe{index:03d}"
    source = (
        f"import {dotted};\n"
        f"public class {probe} {{\n"
        f"    public {simple} value;\n"
        f"}}\n"
    )
    return probe, source


_JAVAC_LINE_RE = re.compile(
    r"^[^:\n]+:(\\d+):(?:\\d+:)?\\s+error:",
    re.MULTILINE,
)


def _class_major(data: bytes | None) -> int | None:
    if data is None:
        return None
    try:
        return int(parse_class(data).major)
    except (ClassFormatError, ValueError):
        return None


def _classify_javac_probe(
    proc: subprocess.CompletedProcess[str],
    generated: Path,
) -> tuple[str, str, list[int]]:
    diagnostic = (
        proc.stdout + proc.stderr
    ).replace("\r\n", "\n").replace("\r", "\n")
    lines = sorted(
        {
            int(match.group(1))
            for match in _JAVAC_LINE_RE.finditer(diagnostic)
        }
    )

    if proc.returncode == 0 and generated.is_file():
        classification = "javac_resolves_exact_class"
    elif "bad class file" in diagnostic.lower():
        classification = "javac_bad_class_file"
    elif "cannot access" in diagnostic.lower():
        classification = "javac_cannot_access_class"
    elif "does not exist" in diagnostic.lower():
        classification = "javac_package_or_class_missing"
    elif "cannot find symbol" in diagnostic.lower():
        classification = "javac_cannot_find_symbol"
    else:
        classification = "javac_other_failure"

    return classification, diagnostic, lines


def _run_javac_probe(
    *,
    javac_command: str,
    classpath: Path,
    internal: str,
    index: int,
    root: Path,
    release: int | None,
    label: str,
) -> dict[str, Any]:
    probe_name, source_text = _probe_source(
        internal,
        index,
    )
    probe_dir = root / f"{index:03d}-{label}"
    probe_dir.mkdir()
    source = probe_dir / (probe_name + ".java")
    out = probe_dir / "classes"
    out.mkdir()
    source.write_text(source_text, encoding="utf-8")

    command = [
        javac_command,
        "-proc:none",
        "-encoding",
        "UTF-8",
        "-Xlint:none",
        "-classpath",
        str(classpath),
        "-d",
        str(out),
    ]
    if release is not None:
        command.extend(["--release", str(release)])
    command.append(str(source))

    proc = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    generated = out / (probe_name + ".class")
    classification, diagnostic, lines = _classify_javac_probe(
        proc,
        generated,
    )
    return {
        "classification": classification,
        "exit_code": proc.returncode,
        "diagnostic_sha256": _sha256(
            diagnostic.encode("utf-8")
        ),
        "error_lines": lines,
    }


def _run_javap_probe(
    *,
    javac_command: str,
    classpath: Path,
    internal: str,
) -> dict[str, Any]:
    javac_path = Path(javac_command)
    name = "javap.exe" if javac_path.suffix.lower() == ".exe" else "javap"
    javap = javac_path.with_name(name)
    if not javap.is_file():
        return {
            "classification": "javap_unavailable",
            "exit_code": None,
            "diagnostic_sha256": None,
        }

    dotted = internal.replace("/", ".")
    proc = subprocess.run(
        [
            str(javap),
            "-classpath",
            str(classpath),
            dotted,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    diagnostic = (
        proc.stdout + proc.stderr
    ).replace("\r\n", "\n").replace("\r", "\n")
    if proc.returncode == 0:
        classification = "javap_resolves_exact_class"
    elif "class not found" in diagnostic.lower():
        classification = "javap_class_not_found"
    else:
        classification = "javap_other_failure"

    return {
        "classification": classification,
        "exit_code": proc.returncode,
        "diagnostic_sha256": _sha256(
            diagnostic.encode("utf-8")
        ),
    }


def audit_dependency_capsule(
    private_plan: dict[str, Any],
    readable_jar: Path,
    dependency_capsule: Path,
    *,
    javac_command: str,
    release: int | None,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    if (
        private_plan.get("schema_version") != 1
        or private_plan.get("kind")
        != "javac_missing_class_recovery_plan"
        or private_plan.get("identifiers_included") is not True
    ):
        raise DependencyCapsuleAuditError(
            "requires private identifier-bearing class recovery plan"
        )

    readable_jar = readable_jar.resolve()
    dependency_capsule = dependency_capsule.resolve()
    if not readable_jar.is_file():
        raise DependencyCapsuleAuditError(
            "readable JAR does not exist"
        )
    if not dependency_capsule.is_file():
        raise DependencyCapsuleAuditError(
            "dependency capsule does not exist"
        )

    readable = _jar_entries(readable_jar)
    capsule = _jar_entries(dependency_capsule)

    rows: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(
        prefix="spk-dependency-audit-"
    ) as td:
        root = Path(td)

        for index, candidate in enumerate(
            private_plan.get("candidates", []),
            start=1,
        ):
            internal = candidate.get("candidate_internal_name")
            if not isinstance(internal, str) or not internal:
                raise DependencyCapsuleAuditError(
                    "private plan candidate lacks internal name"
                )

            entry = internal + ".class"
            readable_bytes = readable.get(entry)
            capsule_bytes = capsule.get(entry)

            readable_present = readable_bytes is not None
            capsule_present = capsule_bytes is not None
            byte_identical = (
                readable_bytes is not None
                and capsule_bytes is not None
                and readable_bytes == capsule_bytes
            )

            class_major = _class_major(capsule_bytes)

            capsule_release_probe = {
                "classification": "not_run",
                "exit_code": None,
                "diagnostic_sha256": None,
                "error_lines": [],
            }
            capsule_default_probe = {
                "classification": "not_run",
                "exit_code": None,
                "diagnostic_sha256": None,
                "error_lines": [],
            }
            readable_release_probe = {
                "classification": "not_run",
                "exit_code": None,
                "diagnostic_sha256": None,
                "error_lines": [],
            }
            javap_probe = {
                "classification": "not_run",
                "exit_code": None,
                "diagnostic_sha256": None,
            }

            if capsule_present:
                capsule_release_probe = _run_javac_probe(
                    javac_command=javac_command,
                    classpath=dependency_capsule,
                    internal=internal,
                    index=index,
                    root=root,
                    release=release,
                    label="capsule-release",
                )
                capsule_default_probe = _run_javac_probe(
                    javac_command=javac_command,
                    classpath=dependency_capsule,
                    internal=internal,
                    index=index,
                    root=root,
                    release=None,
                    label="capsule-default",
                )
                readable_release_probe = _run_javac_probe(
                    javac_command=javac_command,
                    classpath=readable_jar,
                    internal=internal,
                    index=index,
                    root=root,
                    release=release,
                    label="readable-release",
                )
                javap_probe = _run_javap_probe(
                    javac_command=javac_command,
                    classpath=dependency_capsule,
                    internal=internal,
                )

            row = {
                "candidate_id": candidate.get("candidate_id"),
                "readable_present": readable_present,
                "capsule_present": capsule_present,
                "byte_identical": byte_identical,
                "class_major": class_major,
                "capsule_release_probe": capsule_release_probe,
                "capsule_default_probe": capsule_default_probe,
                "readable_release_probe": readable_release_probe,
                "javap_probe": javap_probe,
            }
            if include_identifiers:
                row.update(
                    {
                        "candidate_internal_name": internal,
                        "class_entry": entry,
                    }
                )
            rows.append(row)

    capsule_release_classifications = Counter(
        row["capsule_release_probe"]["classification"]
        for row in rows
    )
    capsule_default_classifications = Counter(
        row["capsule_default_probe"]["classification"]
        for row in rows
    )
    readable_release_classifications = Counter(
        row["readable_release_probe"]["classification"]
        for row in rows
    )
    javap_classifications = Counter(
        row["javap_probe"]["classification"]
        for row in rows
    )
    major_versions = Counter(
        str(row["class_major"])
        for row in rows
    )

    public_rows = [
        {
            key: row[key]
            for key in (
                "candidate_id",
                "readable_present",
                "capsule_present",
                "byte_identical",
                "class_major",
                "capsule_release_probe",
                "capsule_default_probe",
                "readable_release_probe",
                "javap_probe",
            )
        }
        for row in rows
    ]

    material = {
        "class_recovery_plan_id": private_plan.get("plan_id"),
        "readable_jar_sha256": _sha256(readable_jar.read_bytes()),
        "dependency_capsule_sha256": _sha256(
            dependency_capsule.read_bytes()
        ),
        "release": release,
        "rows": public_rows,
    }
    report = {
        "schema_version": 1,
        "kind": "dependency_capsule_resolution_audit",
        "audit_id": (
            "DEPCAPAUDIT_"
            + _stable_digest(material)[:20].upper()
        ),
        "class_recovery_plan_id": private_plan.get("plan_id"),
        "readable_jar_sha256": material[
            "readable_jar_sha256"
        ],
        "dependency_capsule_sha256": material[
            "dependency_capsule_sha256"
        ],
        "target_release": release,
        "summary": {
            "candidate_count": len(rows),
            "readable_present_count": sum(
                bool(row["readable_present"]) for row in rows
            ),
            "capsule_present_count": sum(
                bool(row["capsule_present"]) for row in rows
            ),
            "byte_identical_count": sum(
                bool(row["byte_identical"]) for row in rows
            ),
            "class_major_versions": dict(
                sorted(major_versions.items())
            ),
            "capsule_release_classifications": dict(
                sorted(capsule_release_classifications.items())
            ),
            "capsule_default_classifications": dict(
                sorted(capsule_default_classifications.items())
            ),
            "readable_release_classifications": dict(
                sorted(readable_release_classifications.items())
            ),
            "javap_classifications": dict(
                sorted(javap_classifications.items())
            ),
            "capsule_release_resolved_count": (
                capsule_release_classifications.get(
                    "javac_resolves_exact_class",
                    0,
                )
            ),
            "capsule_default_resolved_count": (
                capsule_default_classifications.get(
                    "javac_resolves_exact_class",
                    0,
                )
            ),
            "readable_release_resolved_count": (
                readable_release_classifications.get(
                    "javac_resolves_exact_class",
                    0,
                )
            ),
            "javap_resolved_count": javap_classifications.get(
                "javap_resolves_exact_class",
                0,
            ),
        },
        "candidates": rows,
        "identifiers_included": include_identifiers,
    }
    return report


def write_dependency_capsule_audit(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
