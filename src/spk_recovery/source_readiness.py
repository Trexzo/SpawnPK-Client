from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any


class SourceReadinessError(ValueError):
    pass


_PACKAGE_RE = re.compile(r"(?m)^\s*package\s+([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*;")
_IMPORT_RE = re.compile(
    r"(?m)^\s*import\s+(?:static\s+)?([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*(?:\.\*)?)\s*;"
)
_PUBLIC_TYPE_RE = re.compile(
    r"(?m)^\s*public\s+(?:(?:abstract|final|sealed|non-sealed|strictfp)\s+)*"
    r"(?:class|interface|enum|record|@interface)\s+([A-Za-z_$][\w$]*)\b"
)
_TOP_TYPE_RE = re.compile(
    r"(?m)^\s*(?:(?:public|protected|private|abstract|final|sealed|non-sealed|strictfp|static)\s+)*"
    r"(?:class|interface|enum|record|@interface)\s+([A-Za-z_$][\w$]*)\b"
)

_DECOMPILER_FAILURE_MARKERS = (
    "could not decompile",
    "couldn't be decompiled",
    "decompilation failed",
    "failed to decompile",
    "this method could not be decompiled",
)

_JDK_ROOTS = {
    "java",
    "javax",
    "jdk",
    "sun",
    "com.sun",
}


def _stable_tree_digest(root: Path) -> tuple[str, list[Path], int]:
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
    return h.hexdigest(), files, total_bytes


def _import_root(name: str) -> str:
    clean = name[:-2] if name.endswith(".*") else name
    parts = clean.split(".")
    if len(parts) >= 2 and ".".join(parts[:2]) in _JDK_ROOTS:
        return ".".join(parts[:2])
    return parts[0]


def audit_source_workspace(
    recovered_manifest: dict[str, Any],
    source_root: Path,
) -> dict[str, Any]:
    if (
        recovered_manifest.get("schema_version") != 1
        or recovered_manifest.get("kind")
        != "recovered_source_workspace_manifest"
    ):
        raise SourceReadinessError(
            "unsupported recovered-source workspace manifest"
        )

    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise SourceReadinessError(
            f"source root does not exist: {source_root}"
        )

    tree_sha, files, total_bytes = _stable_tree_digest(source_root)
    expected_tree_sha = str(
        recovered_manifest.get("source_tree_sha256", "")
    ).lower()
    if tree_sha.lower() != expected_tree_sha:
        raise SourceReadinessError(
            "source tree SHA-256 does not match recovered-source manifest: "
            f"{tree_sha} != {expected_tree_sha}"
        )

    expected_count = recovered_manifest.get("java_file_count")
    if expected_count != len(files):
        raise SourceReadinessError(
            "Java file count does not match recovered-source manifest: "
            f"{len(files)} != {expected_count}"
        )

    package_counts: Counter[str] = Counter()
    import_counts: Counter[str] = Counter()
    external_roots: Counter[str] = Counter()
    project_roots: set[str] = set()
    rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    # Pass 1 establishes project package roots.
    file_text: dict[Path, str] = {}
    file_packages: dict[Path, str | None] = {}
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        file_text[path] = text
        match = _PACKAGE_RE.search(text)
        package = match.group(1) if match else None
        file_packages[path] = package
        if package:
            package_counts[package] += 1
            project_roots.add(package.split(".")[0])

    for path in files:
        text = file_text[path]
        rel = path.relative_to(source_root).as_posix()
        package = file_packages[path]
        imports = sorted(set(_IMPORT_RE.findall(text)))
        public_types = _PUBLIC_TYPE_RE.findall(text)
        top_types = _TOP_TYPE_RE.findall(text)

        for imp in imports:
            import_counts[imp] += 1
            root = _import_root(imp)
            if root not in _JDK_ROOTS and root not in project_roots:
                external_roots[root] += 1

        marker_hits = sorted(
            marker
            for marker in _DECOMPILER_FAILURE_MARKERS
            if marker in text.lower()
        )
        if marker_hits:
            issues.append(
                {
                    "severity": "high",
                    "code": "decompiler_failure_marker",
                    "path": rel,
                    "markers": marker_hits,
                }
            )

        if len(public_types) > 1:
            issues.append(
                {
                    "severity": "high",
                    "code": "multiple_public_top_level_types",
                    "path": rel,
                    "public_types": public_types,
                }
            )
        elif len(public_types) == 1:
            expected_filename = public_types[0] + ".java"
            if path.name != expected_filename:
                issues.append(
                    {
                        "severity": "high",
                        "code": "public_type_filename_mismatch",
                        "path": rel,
                        "public_type": public_types[0],
                        "expected_filename": expected_filename,
                    }
                )

        expected_rel_dir = (
            package.replace(".", "/")
            if package
            else ""
        )
        actual_rel_dir = path.parent.relative_to(source_root).as_posix()
        if actual_rel_dir == ".":
            actual_rel_dir = ""
        if package and actual_rel_dir != expected_rel_dir:
            issues.append(
                {
                    "severity": "medium",
                    "code": "package_path_mismatch",
                    "path": rel,
                    "package": package,
                    "expected_directory": expected_rel_dir,
                    "actual_directory": actual_rel_dir,
                }
            )

        rows.append(
            {
                "path": rel,
                "package": package,
                "public_types": public_types,
                "top_level_types": top_types,
                "import_count": len(imports),
                "imports": imports,
                "size_bytes": len(text.encode("utf-8")),
            }
        )

    issue_counts = Counter(row["code"] for row in issues)
    severity_counts = Counter(row["severity"] for row in issues)

    material = {
        "workspace_id": recovered_manifest.get("workspace_id"),
        "source_tree_sha256": tree_sha,
        "java_file_count": len(files),
        "external_import_roots": dict(sorted(external_roots.items())),
        "issue_counts": dict(sorted(issue_counts.items())),
    }
    audit_id = (
        "SRCREADY_"
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
        "kind": "source_readiness_report",
        "audit_id": audit_id,
        "workspace_id": recovered_manifest.get("workspace_id"),
        "build_id": recovered_manifest.get("build_id"),
        "source_authority_sha256": recovered_manifest.get(
            "source_authority_sha256"
        ),
        "readable_jar_sha256": recovered_manifest.get(
            "readable_jar_sha256"
        ),
        "namespace_id": recovered_manifest.get("namespace_id"),
        "source_tree_sha256": tree_sha,
        "summary": {
            "java_file_count": len(files),
            "source_bytes": total_bytes,
            "package_count": len(package_counts),
            "unique_import_count": len(import_counts),
            "external_import_root_count": len(external_roots),
            "issue_count": len(issues),
            "high_issue_count": severity_counts.get("high", 0),
            "medium_issue_count": severity_counts.get("medium", 0),
            "static_readiness_pass": severity_counts.get("high", 0) == 0,
        },
        "packages": dict(sorted(package_counts.items())),
        "external_import_roots": dict(sorted(external_roots.items())),
        "external_imports": sorted(
            imp
            for imp in import_counts
            if _import_root(imp) in external_roots
        ),
        "issue_counts": dict(sorted(issue_counts.items())),
        "issues": sorted(
            issues,
            key=lambda row: (
                row["severity"] != "high",
                row["code"],
                row["path"],
            ),
        ),
        "files": rows,
    }


def write_source_readiness_report(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
