"""R131: independently resolved Java-source owner call edges for R129.

Uses trusted javac Trees/Elements symbol analysis on SHA-pinned private
candidate .java sources. No source classfiles are generated or executed; no
original game binary or ambient CLASSPATH is allowed as a dependency.
An unresolved source symbol rejects the WHOLE result: no guessed edges.
"""
from __future__ import annotations

from collections import Counter
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from .private_client_source_ast_census_r126 import source_members, sha_file


class PrivateSourceCallEdgesR131Error(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise PrivateSourceCallEdgesR131Error(code)


def _decode(value):
    return base64.urlsafe_b64decode(
        value + "=" * (-len(value) % 4)).decode("utf-8")


def _edge_digest(rows):
    return hashlib.sha256(json.dumps(
        rows, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def extract_private_source_call_edges(source_zip, *, source_sha256,
                                      include_private_edges=False):
    selected = source_members(source_zip, source_sha256)
    javac = shutil.which("javac")
    java = shutil.which("java")
    need(javac is not None and java is not None,
         "JDK_COMPILER_AND_RUNTIME_REQUIRED")
    helper = (Path(__file__).resolve().parent /
              "java" / "ClientResolvedCallEdgesR131.java")
    need(helper.is_file() and not helper.is_symlink(),
         "PACKAGED_TRUSTED_JAVA_HELPER_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="v309-r131-private-source-") as td:
        root = Path(td)
        sources = root / "sources"
        helper_classes = root / "trusted-helper-classes"
        empty_classpath = root / "empty-dependencies"
        sources.mkdir()
        helper_classes.mkdir()
        empty_classpath.mkdir()
        for rel, content in selected:
            target = sources / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        commands = [
            [javac, "-encoding", "UTF-8", "-classpath",
             str(empty_classpath), "-sourcepath", str(empty_classpath),
             "-d", str(helper_classes), str(helper)],
            [java, "-cp", str(helper_classes),
             "ClientResolvedCallEdgesR131", str(sources),
             str(empty_classpath)],
        ]
        raw = b""
        stderr = b""
        for command in commands:
            try:
                proc = subprocess.run(
                    command, cwd=root, stdin=subprocess.DEVNULL,
                    capture_output=True, timeout=240, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise PrivateSourceCallEdgesR131Error(
                    "R131_AST_SYMBOL_SCAN_NOT_COMPLETED") from exc
            need(proc.returncode == 0,
                 "R131_AST_SYMBOL_RESOLUTION_FAILED_NO_EDGES_ACCEPTED")
            raw = proc.stdout
            stderr = proc.stderr
    need(len(raw) <= 12_000_000,
         "R131_AST_CALL_EDGE_OUTPUT_TOO_LARGE")
    decoded_stderr = stderr.decode("utf-8", errors="strict").strip()
    match = re.fullmatch(
        r"R131_EXCLUDED_SOURCE_METHOD_REFERENCES=(\d+)",
        decoded_stderr)
    need(match is not None,
         "R131_SOURCE_HELPER_EVIDENCE_FOOTER_INVALID")
    omitted_method_references = int(match.group(1))
    edges = {}
    for line in raw.decode("utf-8", errors="strict").splitlines():
        parts = line.split("\t")
        need(len(parts) == 3, "R131_EDGE_PROTOCOL_INVALID")
        caller, callee = _decode(parts[0]), _decode(parts[1])
        try:
            count = int(parts[2])
        except ValueError as exc:
            raise PrivateSourceCallEdgesR131Error(
                "R131_EDGE_COUNT_INVALID") from exc
        need(caller.startswith("rs/") and callee.startswith("rs/")
             and type(count) is int and 0 < count <= 1_000_000
             and (caller, callee) not in edges,
             "R131_EDGE_IDENTITY_OR_COUNT_INVALID")
        edges[caller, callee] = count
    rows = [
        {"caller": caller, "callee": callee, "count": count}
        for (caller, callee), count in sorted(edges.items())
    ]
    need(sha_file(source_zip) == source_sha256,
         "SOURCE_ZIP_CHANGED_DURING_AST_SCAN")
    report = {
        "schema_version": 1,
        "kind": "private_source_ast_symbol_resolved_calls_r131",
        "source_archive_sha256": source_sha256,
        "source_java_file_count": len(selected),
        "source_direct_rs_call_edge_count": len(rows),
        "source_direct_rs_callsite_count": sum(edges.values()),
        "source_method_reference_sites_excluded": omitted_method_references,
        "private_source_call_edge_manifest_sha256": _edge_digest(rows),
        "source_call_owners_symbol_resolved": True,
        "source_symbols_missing_or_ambiguous": False,
        "ambient_project_classpath_disabled": True,
        "source_game_classes_generated": False,
        "original_game_binary_used_as_fallback": False,
        "source_game_code_executed": False,
        "method_opcode_dispatch_equivalence_proven": False,
        "complete_v309_client_source_compiles": False,
        "private_edges_included": bool(include_private_edges),
    }
    if include_private_edges:
        report["private_source_call_edges"] = rows
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_decompiled_source_zip")
    parser.add_argument("fresh_private_report")
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--private-edges", action="store_true")
    args = parser.parse_args(argv)
    out = Path(args.fresh_private_report)
    try:
        need(not out.exists() and not out.is_symlink()
             and out.parent.is_dir() and not out.parent.is_symlink(),
             "FRESH_PRIVATE_REPORT_REQUIRED")
        report = extract_private_source_call_edges(
            args.private_decompiled_source_zip,
            source_sha256=args.source_sha256,
            include_private_edges=args.private_edges)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")
        print(json.dumps({
            k: v for k, v in report.items()
            if k != "private_source_call_edges"
        }, sort_keys=True))
    except Exception:
        parser.error("PRIVATE_R131_SOURCE_CALL_GRAPH_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
