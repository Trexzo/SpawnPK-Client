"""R130: exact-hash original-v309 JVM invoke edge extraction, read-only.

Parses pinned classfile Code/constant pools without executing the client.
Returns private class-owner edges only; invokedynamic is NEVER attributed to
a guessed callee. Edges are not source identity, parity, or callsite proofs.
"""
from __future__ import annotations

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, BadZipFile

from .bytecode_profile import BytecodeProfileError, profile_class_field_accesses

EXACT_V309_SHA256 = "ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
DIRECT_CALL_OPERATIONS = frozenset({
    "invokevirtual", "invokespecial", "invokestatic", "invokeinterface",
})


class PrivateJvmCallEdgesR130Error(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise PrivateJvmCallEdgesR130Error(code)


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _private_edges_sha256(rows):
    canonical = json.dumps(rows, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def extract_jvm_call_edges(original_jar, *,
                           original_sha256=EXACT_V309_SHA256,
                           include_private_edges=False):
    """Return a pinned, sanitized report; not a runnable/rebuilt client."""
    path = Path(original_jar)
    need(path.is_file() and not path.is_symlink(), "ORIGINAL_JAR_FILE_REQUIRED")
    need(type(original_sha256) is str
         and re.fullmatch(r"[a-f0-9]{64}", original_sha256) is not None,
         "ORIGINAL_JAR_SHA256_PIN_INVALID")
    need(sha256_file(path) == original_sha256,
         "ORIGINAL_JAR_SHA256_MISMATCH")
    edges = Counter()
    dispatch = Counter()
    excluded_dynamic = 0
    classes = 0
    methods = 0
    try:
        with ZipFile(path) as jar:
            infos = jar.infolist()
            need(1 <= len(infos) <= 18000, "JAR_ENTRY_COUNT_UNSAFE")
            names = [info.filename for info in infos]
            need(len(names) == len(set(names)),
                 "DUPLICATE_JAR_ENTRY")
            for info in infos:
                name = info.filename
                need(not name.startswith("/") and "\\" not in name
                     and all(part not in ("", ".", "..")
                             for part in name.rstrip("/").split("/")),
                     "UNSAFE_JAR_PATH")
                need(((info.external_attr >> 16) & 0o170000) != 0o120000,
                     "JAR_SYMLINK_REJECTED")
            targets = sorted(
                (info for info in infos
                 if info.filename.startswith("rs/")
                 and info.filename.endswith(".class")
                 and not info.is_dir()),
                key=lambda item: item.filename)
            need(bool(targets) and len(targets) <= 10000,
                 "ORIGINAL_RS_CLASS_COUNT_INVALID")
            for info in targets:
                need(info.file_size <= 20_000_000, "ORIGINAL_CLASS_TOO_LARGE")
                try:
                    parsed = profile_class_field_accesses(
                        jar.read(info))
                except (BytecodeProfileError, IndexError, KeyError,
                        ValueError, UnicodeError) as exc:
                    raise PrivateJvmCallEdgesR130Error(
                        "ORIGINAL_RS_CLASSFILE_PARSE_FAILED") from exc
                owner = info.filename[:-6]
                need(parsed.get("internal_name") == owner,
                     "ORIGINAL_RS_CLASSFILE_OWNER_MISMATCH")
                classes += 1
                for method in parsed["methods"]:
                    methods += 1
                    calls = method.get("method_invocations")
                    need(type(calls) is list, "ORIGINAL_METHOD_CALLS_MISSING")
                    for call in calls:
                        op = call.get("operation")
                        if op == "invokedynamic":
                            excluded_dynamic += 1
                            continue
                        need(op in DIRECT_CALL_OPERATIONS,
                             "UNSUPPORTED_JVM_CALL_OPERATION")
                        callee = call.get("owner")
                        need(type(callee) is str and callee,
                             "UNRESOLVED_ORIGINAL_INVOKE_OWNER")
                        if callee.startswith("rs/"):
                            need("/" not in callee[:1] and "\\" not in callee,
                                 "UNSAFE_INVOKED_CLIENT_OWNER")
                            edges[owner, callee] += 1
                            dispatch[op] += 1
    except (OSError, BadZipFile) as exc:
        raise PrivateJvmCallEdgesR130Error(
            "PRIVATE_ORIGINAL_JAR_UNREADABLE") from exc
    need(sha256_file(path) == original_sha256,
         "ORIGINAL_JAR_CHANGED_DURING_SCAN")
    private = [
        {"caller": caller, "callee": callee, "count": count}
        for (caller, callee), count in sorted(edges.items())
    ]
    need(all(r["count"] <= 1_000_000 for r in private),
         "JVM_EDGE_FREQUENCY_TOO_LARGE")
    report = {
        "schema_version": 1,
        "kind": "private_original_v309_jvm_invoke_edges_r130",
        "original_client_sha256": original_sha256,
        "parsed_rs_class_count": classes,
        "parsed_rs_method_count": methods,
        "direct_rs_owner_edge_count": len(private),
        "direct_rs_callsite_count": sum(edges.values()),
        "direct_dispatch_counts": dict(sorted(dispatch.items())),
        "unattributed_invokedynamic_site_count": excluded_dynamic,
        "private_edge_manifest_sha256": _private_edges_sha256(private),
        "private_class_names_included": bool(include_private_edges),
        "original_client_executed": False,
        "invokedynamic_callees_guessed": False,
        "original_source_identity_accepted": False,
        "whole_client_recompiled": False,
        "callgraph_equivalence_certified": False,
    }
    if include_private_edges:
        report["private_original_call_edges"] = private
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_original_client_jar")
    parser.add_argument("fresh_private_report")
    parser.add_argument("--original-sha256", default=EXACT_V309_SHA256)
    parser.add_argument("--private-edges", action="store_true")
    args = parser.parse_args(argv)
    output = Path(args.fresh_private_report)
    try:
        need(not output.exists() and not output.is_symlink()
             and output.parent.is_dir() and not output.parent.is_symlink(),
             "FRESH_PRIVATE_REPORT_REQUIRED")
        report = extract_jvm_call_edges(
            args.private_original_client_jar,
            original_sha256=args.original_sha256,
            include_private_edges=args.private_edges)
        output.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
        print(json.dumps({
            k: v for k, v in report.items()
            if k != "private_original_call_edges"
        }, sort_keys=True))
    except Exception:
        parser.error("PRIVATE_R130_JVM_CALL_EDGES_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
