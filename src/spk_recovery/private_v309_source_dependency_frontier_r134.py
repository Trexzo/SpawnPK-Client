"""R134: compare candidate Java imports against exact original-v309 class inventory.

Source *import spelling* does not prove original bytecode class/member lineage.
In particular a candidate-only dependency must not be called an "original"
requirement merely because a decompiler workspace imports it. Read-only.
"""
from __future__ import annotations

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import re

from .private_client_namespace_legalizer_r125 import (
    CANONICAL_V309, original_class_inventory,
)
from .private_client_source_ast_census_r126 import source_members, sha_file

_IMPORT = re.compile(
    r"^[ \t]*import[ \t]+(static[ \t]+)?"
    r"([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*|\.\*)+)"
    r"[ \t]*;[ \t]*(?://[^\n]*)?$", re.M
)


class PrivateSourceDependencyR134Error(ValueError):
    pass


def need(value, reason):
    if not value:
        raise PrivateSourceDependencyR134Error(reason)


def _manifest_sha(rows):
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _import_inventory(entries):
    rows = []
    for relative, content in entries:
        text = content.decode("utf-8", errors="strict")
        for match in _IMPORT.finditer(text):
            expression = match.group(2)
            need(len(expression) <= 512, "IMPORT_NAME_TOO_LONG")
            rows.append({
                "source_path": relative,
                "java_import": expression,
                "static": match.group(1) is not None,
                "wildcard": expression.endswith(".*"),
            })
    return sorted(rows, key=lambda r: (
        r["source_path"], r["java_import"], r["static"]))


def _candidate_paths(entries):
    return {name[:-5] for name, _ in entries if name.endswith(".java")}


def source_dependency_provenance(entries, original_classes,
                                 *, include_private_names=False):
    """Pure preflight; results are dependency uncertainty, not provenance proof."""
    need(type(original_classes) is set
         and all(type(x) is str for x in original_classes),
         "ORIGINAL_CLASS_INDEX_REQUIRED")
    imports = _import_inventory(entries)
    source_paths = _candidate_paths(entries)
    totals = Counter()
    unresolved_packages = Counter()
    private_rows = []
    for imp in imports:
        spelling = imp["java_import"]
        if imp["wildcard"] or imp["static"]:
            classification = "wildcard_or_static_not_resolved"
        else:
            internal = spelling.replace(".", "/")
            candidate_outer = internal.rpartition("/")[0]
            if internal in original_classes:
                classification = "exact_original_class_path_present"
            elif internal in source_paths:
                classification = "source_file_path_present_original_unverified"
            elif candidate_outer in original_classes:
                classification = "possible_original_nested_class_unverified"
            elif candidate_outer in source_paths:
                classification = "possible_candidate_nested_class_unverified"
            elif spelling.startswith(("java.", "javax.", "jdk.", "sun.")):
                classification = "jdk_namespace_or_external_api_unverified"
            else:
                # This does not assert that the import *should* exist in the
                # original binary. It may be introduced or supplied externally.
                classification = "not_found_by_exact_original_or_source_path"
                unresolved_packages[".".join(
                    spelling.split(".")[:3])] += 1
        totals[classification] += 1
        private_rows.append({
            **imp,
            "source_import_evidence": classification,
            "is_original_dependency_certified": False,
            "is_user_added_code_certified": False,
        })
    summary = {
        "schema_version": 1,
        "kind": "private_v309_candidate_import_original_dependency_frontier_r134",
        "candidate_java_files": len(entries),
        "original_class_paths": len(original_classes),
        "java_import_declarations": len(imports),
        "classifications": dict(sorted(totals.items())),
        "unlocated_top_package_families": dict(sorted(
            unresolved_packages.items())),
        "private_row_manifest_sha256": _manifest_sha(private_rows),
        "original_dependency_ownership_certified": False,
        "missing_import_proves_nonoriginal_source": False,
        "decompiled_candidate_is_equivalent_to_original": False,
        "full_source_compiles_without_original_project_binaries": False,
        "raw_original_client_executed": False,
        "private_import_names_included": bool(include_private_names),
    }
    if include_private_names:
        summary["private_import_evidence"] = private_rows
    return summary


def audit_private_source_original_dependency(source_zip, original_jar, *,
                                             source_sha256,
                                             original_sha256=CANONICAL_V309,
                                             include_private_names=False):
    entries = source_members(source_zip, source_sha256)
    originals = original_class_inventory(original_jar, original_sha256)
    report = source_dependency_provenance(
        entries, originals, include_private_names=include_private_names)
    report["source_archive_sha256"] = source_sha256
    report["original_client_jar_sha256"] = original_sha256
    need(sha_file(source_zip) == source_sha256,
         "SOURCE_ARCHIVE_CHANGED_DURING_DEPENDENCY_SCAN")
    need(sha_file(original_jar) == original_sha256,
         "ORIGINAL_JAR_CHANGED_DURING_DEPENDENCY_SCAN")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_source_candidate_zip")
    p.add_argument("private_original_v309_jar")
    p.add_argument("fresh_private_report")
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--original-sha256", default=CANONICAL_V309)
    p.add_argument("--private-imports", action="store_true")
    a = p.parse_args(argv)
    out = Path(a.fresh_private_report)
    try:
        need(not out.exists() and not out.is_symlink()
             and out.parent.is_dir() and not out.parent.is_symlink(),
             "FRESH_PRIVATE_OUTPUT_REQUIRED")
        report = audit_private_source_original_dependency(
            a.private_source_candidate_zip, a.private_original_v309_jar,
            source_sha256=a.source_sha256,
            original_sha256=a.original_sha256,
            include_private_names=a.private_imports)
        out.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        print(json.dumps({
            k: v for k, v in report.items()
            if k != "private_import_evidence"
        }, sort_keys=True))
    except Exception:
        p.error("PRIVATE_R134_SOURCE_DEPENDENCY_FRONTIER_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
