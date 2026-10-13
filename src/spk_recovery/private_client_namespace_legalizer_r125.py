"""R125: deterministic JVM-to-Java/Windows-safe class-name proposal.

Read-only planning against an exact SHA-pinned original client JAR. Only
identifier-bearing reports are private; default JSON has aggregate counts.
No source is changed, compiled, imported, executed, or certified by this tool.
Cross-build *semantic* class names must come from separately accepted lineage.
"""
from __future__ import annotations

from collections import defaultdict
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

CANONICAL_V309 = "ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
_IDENT = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
_JAVA_RESERVED = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch",
    "char", "class", "const", "continue", "default", "do", "double",
    "else", "enum", "extends", "final", "finally", "float", "for",
    "goto", "if", "implements", "import", "instanceof", "int",
    "interface", "long", "native", "new", "package", "private",
    "protected", "public", "return", "short", "static", "strictfp",
    "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while", "_", "true",
    "false", "null", "var", "record", "sealed", "permits", "yield",
    "module", "open", "requires", "transitive", "exports", "opens",
    "to", "uses", "provides", "with",
}


class ClientNamespaceLegalizationError(ValueError):
    pass


def require(value, reason):
    if not value:
        raise ClientNamespaceLegalizationError(reason)


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def file_sha(path):
    sha = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def original_class_inventory(original_jar, expected_sha=CANONICAL_V309):
    source = Path(original_jar)
    require(source.is_file() and not source.is_symlink(),
            "PRIVATE_ORIGINAL_JAR_FILE_REQUIRED")
    require(type(expected_sha) is str and
            re.fullmatch(r"[a-f0-9]{64}", expected_sha) is not None
            and file_sha(source) == expected_sha,
            "ORIGINAL_CLIENT_JAR_SHA256_MISMATCH")
    with zipfile.ZipFile(source) as archive:
        infos = archive.infolist()
        require(1 <= len(infos) <= 18000, "JAR_ENTRY_COUNT_INVALID")
        require(len({x.filename for x in infos}) == len(infos),
                "JAR_DUPLICATE_ARCHIVE_MEMBER")
        names = set()
        for item in infos:
            raw = item.filename
            require(not raw.startswith("/") and "\\" not in raw
                    and all(part not in ("", ".", "..")
                            for part in raw.rstrip("/").split("/")),
                    "UNSAFE_ARCHIVE_MEMBER_PATH")
            require(((item.external_attr >> 16) & 0o170000) != 0o120000,
                    "ORIGINAL_JAR_SYMLINK_REJECTED")
            if raw.endswith(".class") and not item.is_dir():
                names.add(raw[:-6])
    require(len(names) > 0, "JAR_HAS_NO_CLASSES")
    return names


def package_prefixes(classes):
    paths = set()
    for name in classes:
        parts = name.split("/")
        for index in range(1, len(parts)):
            paths.add("/".join(parts[:index]))
    return paths


def case_groups(names):
    grouped = defaultdict(list)
    for name in names:
        grouped[name.casefold()].append(name)
    return [sorted(group) for group in grouped.values()
            if len(group) > 1]


def _invalid_java_identifiers(classes):
    failures = set()
    for name in classes:
        for segment in name.split("/"):
            # '$' can appear in JVM nested binary names. The actual source
            # declaration arrangement is separately verified at javac time.
            if not _IDENT.fullmatch(segment) or segment in _JAVA_RESERVED:
                failures.add(name)
    return failures


def _fresh(current, old, suffix, *, cls_name):
    # Keep the parent package for class renames; keep the parent of the
    # conflicting package segment for package renames.
    parent, sep, simple = old.rpartition("/")
    base = simple + "__" + suffix + "_" + digest(old)[:12]
    candidate = (parent + "/" if sep else "") + base
    live = set(current.values())
    prefixes = package_prefixes(live)
    occupied = {x.casefold() for x in live | prefixes}
    attempt = 0
    while candidate.casefold() in occupied:
        attempt += 1
        require(attempt < 128, "NO_UNOCCUPIED_LEGAL_NAMESPACE_ALIAS")
        candidate = ((parent + "/" if sep else "") + base +
                     "_" + str(attempt))
    return candidate


def _replace_family(current, old, new, *, is_package, reasons, reason):
    if is_package:
        changed = [key for key, value in current.items()
                   if value.startswith(old + "/")]
    else:
        changed = [key for key, value in current.items()
                   if value == old or value.startswith(old + "$")]
    require(bool(changed), "NAMESPACE_REMAP_TARGET_HAS_NO_CLASSES")
    for key in changed:
        prev = current[key]
        current[key] = new + prev[len(old):]
        reasons[key].add(reason)


def _validate_final(current, original):
    require(set(current) == original, "MAPPING_ORIGINAL_CLASS_SET_CHANGED")
    targets = list(current.values())
    require(len(targets) == len(set(targets)),
            "MAPPING_MUST_BE_BIJECTIVE")
    require(not case_groups(targets),
            "WINDOWS_CLASS_FILE_PATH_COLLISION_REMAINS")
    prefixes = package_prefixes(targets)
    require(not case_groups(prefixes),
            "WINDOWS_PACKAGE_DIRECTORY_COLLISION_REMAINS")
    casefold_packages = {p.casefold() for p in prefixes}
    require(not any(p.casefold() in casefold_packages for p in targets),
            "JAVAC_CLASS_PACKAGE_SHADOW_REMAINS")
    require(not _invalid_java_identifiers(targets),
            "FINAL_JAVA_IDENTIFIER_INVALID")


def plan_client_namespaces(original, *, include_identifiers=False,
                           original_jar_sha256=None):
    """Pure solver: original is a set of original internal class names."""
    require(type(original) is set and 0 < len(original) <= 18000
            and all(type(x) is str and len(x) <= 512 and x
                    and "/" not in x[:1] and "\\" not in x
                    and all(p and p not in (".", "..") for p in x.split("/"))
                    for x in original),
            "UNSAFE_OR_EMPTY_ORIGINAL_CLASS_IDENTITY_SET")
    require(not _invalid_java_identifiers(original),
            "ORIGINAL_JVM_CLASS_NAME_NOT_DIRECTLY_JAVA_LEGAL")
    current = {name: name for name in sorted(original)}
    reasons = defaultdict(set)
    counts = {
        "windows_package_case_conflicts_fixed": 0,
        "java_type_package_shadow_conflicts_fixed": 0,
        "windows_class_filename_conflicts_fixed": 0,
    }
    limit = 2 * len(original) + 100

    # First legalize directory identities: a Windows source checkout may not
    # represent rs/A/... alongside rs/a/..., even if final leaf names differ.
    for _ in range(limit):
        groups = case_groups(package_prefixes(current.values()))
        if not groups:
            break
        group = sorted(groups, key=lambda g: (len(g[0].split("/")), g))[0]
        for loser in group[1:]:
            new = _fresh(current, loser, "Pkg", cls_name=False)
            _replace_family(current, loser, new, is_package=True,
                            reasons=reasons, reason="windows_package_case")
            counts["windows_package_case_conflicts_fixed"] += 1
    else:
        raise ClientNamespaceLegalizationError(
            "WINDOWS_PACKAGE_CASE_FIX_DID_NOT_CONVERGE")

    # A JVM permits both rs/a.class and rs/a/Child.class. Java source
    # cannot address that unambiguously; only rename the blocker type, not
    # its package and not unrelated classes below the rs/a/ prefix.
    for _ in range(limit):
        prefixes = {p.casefold() for p in package_prefixes(current.values())}
        blocked = sorted(c for c in current.values()
                         if c.casefold() in prefixes)
        if not blocked:
            break
        loser = blocked[0]
        new = _fresh(current, loser, "Type", cls_name=True)
        _replace_family(current, loser, new, is_package=False,
                        reasons=reasons, reason="java_class_package_shadow")
        counts["java_type_package_shadow_conflicts_fixed"] += 1
    else:
        raise ClientNamespaceLegalizationError(
            "CLASS_PACKAGE_SHADOW_FIX_DID_NOT_CONVERGE")

    # Finally resolve actual .java/.class path name casefold collisions.
    for _ in range(limit):
        groups = case_groups(current.values())
        if not groups:
            break
        group = sorted(groups)[0]
        for loser in group[1:]:
            new = _fresh(current, loser, "Case", cls_name=True)
            _replace_family(current, loser, new, is_package=False,
                            reasons=reasons, reason="windows_class_case")
            counts["windows_class_filename_conflicts_fixed"] += 1
    else:
        raise ClientNamespaceLegalizationError(
            "WINDOWS_CLASS_CASE_FIX_DID_NOT_CONVERGE")

    _validate_final(current, original)
    renamed = [(k, v) for k, v in sorted(current.items()) if k != v]
    public = {
        "schema_version": 1,
        "kind": "private_client_windows_and_java_namespace_legalization_r125",
        "original_client_sha256": original_jar_sha256,
        "original_classfile_count": len(original),
        "original_game_rs_classfile_count":
            sum(x.startswith("rs/") for x in original),
        "mapped_classfile_count": len(current),
        "renamed_classfile_count": len(renamed),
        "renamed_game_rs_classfile_count":
            sum(old.startswith("rs/") for old, _ in renamed),
        "java_package_case_conflicts_before":
            len(case_groups(package_prefixes(original))),
        "windows_class_case_conflicts_before":
            len(case_groups(original)),
        "class_package_shadows_before":
            sum(c.casefold() in {p.casefold() for p in package_prefixes(original)}
                for c in original),
        "remediation_operations": counts,
        "mapped_paths_unique_after_casefold": True,
        "mapped_package_directories_unique_after_casefold": True,
        "no_type_package_shadow_after_mapping": True,
        "source_files_rewritten": False,
        "source_compilation_accepted": False,
        "classfile_parity_proven": False,
        "runtime_equivalence_proven": False,
        "accepted_semantic_names_assigned": False,
        "identifiers_included": bool(include_identifiers),
    }
    # The digest is over deterministic private identities, but only a digest
    # and aggregate counts are visible in the default nonprivate report.
    material = [{"original": old, "mapped": new}
                for old, new in renamed]
    public["private_mapping_sha256"] = hashlib.sha256(
        json.dumps(material, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if include_identifiers:
        public["remaps"] = [
            {"old_internal_name": old, "new_internal_name": new,
             "reasons": sorted(reasons[old])} for old, new in renamed
        ]
    return public


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_original_client_jar")
    parser.add_argument("fresh_private_output_json")
    parser.add_argument("--original-sha256", default=CANONICAL_V309)
    parser.add_argument("--private-identifiers", action="store_true")
    args = parser.parse_args(argv)
    out = Path(args.fresh_private_output_json)
    try:
        require(not out.exists() and not out.is_symlink()
                and out.parent.is_dir() and not out.parent.is_symlink(),
                "NEW_PRIVATE_OUTPUT_PATH_REQUIRED")
        classes = original_class_inventory(
            args.private_original_client_jar, args.original_sha256)
        report = plan_client_namespaces(
            classes, include_identifiers=args.private_identifiers,
            original_jar_sha256=args.original_sha256)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")
        print("CLIENT_JAVA_NAMESPACE_LEGALIZATION_R125_PASS")
        print("private_report_sha256=" + file_sha(out))
    except Exception:
        parser.error("PRIVATE_CLIENT_JAVA_NAMESPACE_R125_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
