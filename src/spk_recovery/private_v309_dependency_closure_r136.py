"""R136: identify source-compile classpath contamination by original rs/ code.

Read-only audit of the exact pinned original v309 classfile dependency graph.
A class without graph linkage to rs/ is NOT necessarily third-party or safe
to redistribute: this is a necessary, not sufficient, dependency isolation
gate. Never execute or publish the original JAR or a derived binary capsule.
"""
from __future__ import annotations

from collections import defaultdict, deque
import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, BadZipFile

from .bytecode_profile import (
    BytecodeProfileError, profile_class_constant_pool_references,
)
from .classfile import ClassFormatError, parse_class
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import sha_file


class DependencyClosureR136Error(ValueError):
    pass


def need(value, reason):
    if not value:
        raise DependencyClosureR136Error(reason)


def _name_refs(descriptor):
    return set(re.findall(r"L([^;<>]+);", descriptor or ""))


def _direct_class_refs(binary):
    try:
        parsed = parse_class(binary)
        cp = profile_class_constant_pool_references(binary)
    except (ClassFormatError, BytecodeProfileError, ValueError,
            IndexError, UnicodeError) as exc:
        raise DependencyClosureR136Error(
            "ORIGINAL_JVM_CLASSFILE_NOT_PARSEABLE") from exc
    need(parsed.name == cp["internal_name"],
         "ORIGINAL_CLASS_PARSER_IDENTITY_MISMATCH")
    refs = set(cp["class_references"])
    if parsed.super_name:
        refs.add(parsed.super_name)
    refs.update(parsed.interfaces)
    for member in parsed.fields + parsed.methods:
        refs.update(_name_refs(member["descriptor"]))
    for row in cp["member_references"]:
        refs.add(row["owner"])
        refs.update(_name_refs(row["descriptor"]))
    return parsed.name, refs - {parsed.name}


def audit_external_class_graph(classes, *, include_private_names=False):
    """Strict in-memory JVM graph, including class/field/method descriptors.

    Rejects renamed/nonmatching class entries. Marks every non-rs class that
    directly or transitively uses rs/ as unsuitable for a provisional external
    binary-only compile capsule.
    """
    need(type(classes) is dict and 1 <= len(classes) <= 12000,
         "ORIGINAL_BINARY_INVENTORY_COUNT_INVALID")
    graph = {}
    for name, binary in sorted(classes.items()):
        need(type(name) is str and len(name) < 512 and
             all(p not in ("", ".", "..") for p in name.split("/"))
             and type(binary) is bytes and len(binary) <= 20_000_000,
             "ORIGINAL_JVM_CLASS_ENTRY_INVALID")
        actual, refs = _direct_class_refs(binary)
        need(actual == name, "ORIGINAL_JVM_CLASS_ENTRY_NAME_MISMATCH")
        graph[name] = refs
    game = {x for x in graph if x.startswith("rs/")}
    need(bool(game), "ORIGINAL_CLIENT_RS_CLASS_INVENTORY_EMPTY")
    non_game = set(graph) - game
    direct = {name for name in non_game if any(
        ref.startswith("rs/") for ref in graph[name])}
    users = defaultdict(set)
    for caller, deps in graph.items():
        if caller not in non_game:
            continue
        for callee in deps:
            if callee in non_game:
                users[callee].add(caller)
    contaminated = set(direct)
    queue = deque(sorted(direct))
    while queue:
        callee = queue.popleft()
        for caller in sorted(users[callee] - contaminated):
            contaminated.add(caller)
            queue.append(caller)
    provisional = sorted(non_game - contaminated)
    known_non_game_dependencies = sum(
        len(graph[x] & non_game) for x in non_game)
    private = {
        "direct_rs_dependent_non_rs": sorted(direct),
        "transitively_rs_dependent_non_rs": sorted(contaminated-direct),
        "provisional_non_rs_untainted": provisional,
    }
    manifest = hashlib.sha256(json.dumps(
        private, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    result = {
        "schema_version": 1,
        "kind": "private_v309_original_nonproject_dependency_graph_r136",
        "all_original_jvm_classes": len(graph),
        "original_rs_game_classes": len(game),
        "original_non_rs_classes": len(non_game),
        "non_rs_directly_referencing_rs": len(direct),
        "non_rs_transitively_referencing_rs": len(contaminated - direct),
        "non_rs_with_any_rs_dependency_chain": len(contaminated),
        "non_rs_without_known_rs_dependency_chain": len(provisional),
        "non_rs_to_non_rs_dependency_edges": known_non_game_dependencies,
        "private_graph_partition_manifest_sha256": manifest,
        "original_jar_executed": False,
        "isolated_non_rs_classes_certified_third_party": False,
        "provisional_non_rs_classes_certified_safe_compile_dependencies": False,
        "original_project_class_fallback_is_allowed": False,
        "zero_game_binary_fallback_source_build_proven": False,
        "original_client_recompiled": False,
        "private_identifiers_included": bool(include_private_names),
    }
    if include_private_names:
        result["private_dependency_partition"] = private
    return result


def audit_pinned_original_jar(jar_path, *, original_sha256=CANONICAL_V309,
                              include_private_names=False):
    path = Path(jar_path)
    need(path.is_file() and not path.is_symlink(),
         "PRIVATE_ORIGINAL_JAR_REQUIRED")
    need(type(original_sha256) is str and
         re.fullmatch(r"[0-9a-f]{64}", original_sha256) is not None
         and sha_file(path) == original_sha256,
         "ORIGINAL_SHA256_PIN_MISMATCH")
    try:
        with ZipFile(path) as jar:
            entries = jar.infolist()
            need(1 <= len(entries) <= 20000, "ORIGINAL_ARCHIVE_SIZE_UNSAFE")
            seen = set()
            classes = {}
            for entry in entries:
                name = entry.filename
                need(name not in seen, "DUPLICATE_ORIGINAL_ARCHIVE_MEMBER")
                seen.add(name)
                need(not name.startswith("/") and "\\" not in name
                     and all(p not in ("", ".", "..")
                             for p in name.rstrip("/").split("/")),
                     "UNSAFE_ORIGINAL_ARCHIVE_PATH")
                need(((entry.external_attr >> 16) & 0o170000) != 0o120000,
                     "SYMLINK_IN_ORIGINAL_ARCHIVE")
                if name.endswith(".class") and not entry.is_dir():
                    need(entry.file_size <= 20_000_000,
                         "OVERSIZED_ORIGINAL_JVM_CLASS")
                    classes[name[:-6]] = jar.read(entry)
    except (BadZipFile, OSError) as exc:
        raise DependencyClosureR136Error(
            "ORIGINAL_ARCHIVE_NOT_READABLE") from exc
    result = audit_external_class_graph(
        classes, include_private_names=include_private_names)
    result["original_jar_sha256"] = original_sha256
    need(sha_file(path) == original_sha256,
         "ORIGINAL_ARCHIVE_CHANGED_DURING_GRAPH_SCAN")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_original_v309_jar")
    p.add_argument("fresh_private_report")
    p.add_argument("--original-sha256", default=CANONICAL_V309)
    p.add_argument("--private-classes", action="store_true")
    args = p.parse_args(argv)
    output = Path(args.fresh_private_report)
    try:
        need(not output.exists() and not output.is_symlink()
             and output.parent.is_dir() and not output.parent.is_symlink(),
             "FRESH_PRIVATE_REPORT_REQUIRED")
        report = audit_pinned_original_jar(
            args.private_original_v309_jar,
            original_sha256=args.original_sha256,
            include_private_names=args.private_classes)
        output.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
        print(json.dumps({
            k: v for k, v in report.items()
            if k != "private_dependency_partition"
        }, sort_keys=True))
    except Exception:
        p.error("PRIVATE_R136_DEPENDENCY_GRAPH_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
