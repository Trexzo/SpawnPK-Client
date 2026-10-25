"""R131: fail-closed read-only, symbol-attributed Java client call edges.

Never guesses call owners from lexical text, imports or source filenames.
The trusted JDK AST helper performs symbol attribution with an EXPLICITLY EMPTY
external classpath/sourcepath; Java source is not executed or class-generated.
Compilation diagnostics and unresolved invocation owners are retained as
visible coverage blockers, never silently treated as negative call evidence.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from .private_client_source_ast_census_r126 import source_members, sha_file


class PrivateSourceInvokeR131Error(ValueError):
    pass


def need(value, code):
    if not value:
        raise PrivateSourceInvokeR131Error(code)


def decode(value):
    try:
        return base64.b64decode(
            value + "=" * (-len(value) % 4),
            altchars=b"-_", validate=True).decode("utf-8")
    except Exception as exc:
        raise PrivateSourceInvokeR131Error(
            "SOURCE_ATTRIBUTED_EDGE_PROTOCOL_BASE64_INVALID") from exc


def _run_trusted_helper(entries):
    javac, java = shutil.which("javac"), shutil.which("java")
    need(javac is not None and java is not None,
         "JDK_REQUIRED_FOR_SYMBOL_ATTRIBUTION")
    helper = (Path(__file__).resolve().parent / "java" /
              "ClientAttributedCallEdgesR131.java")
    need(helper.is_file(), "TRUSTED_ATTRIBUTION_HELPER_MISSING")
    with tempfile.TemporaryDirectory(prefix="spk-r131-private-") as td:
        root = Path(td)
        staged = root / "sources"
        classes = root / "compiled-trusted-helper"
        empty = root / "empty-dependencies"
        staged.mkdir()
        classes.mkdir()
        empty.mkdir()
        for rel, data in entries:
            source_file = staged / rel
            source_file.parent.mkdir(parents=True, exist_ok=True)
            source_file.write_bytes(data)
        commands = (
            [javac, "-encoding", "UTF-8", "-d",
             str(classes), str(helper)],
            [java, "-Xmx1536m", "-cp", str(classes),
             "ClientAttributedCallEdgesR131", str(staged), str(empty)],
        )
        payload = b""
        for index, argv in enumerate(commands):
            try:
                proc = subprocess.run(
                    argv, cwd=root, stdin=subprocess.DEVNULL,
                    capture_output=True, timeout=60 if index == 0 else 240)
            except (subprocess.TimeoutExpired, OSError) as exc:
                raise PrivateSourceInvokeR131Error(
                    "JAVA_SOURCE_ATTRIBUTION_NOT_COMPLETED") from exc
            need(proc.returncode == 0,
                 "JAVA_SOURCE_ATTRIBUTION_OR_HELPER_FAILED")
            payload = proc.stdout
        need(len(payload) <= 32_000_000, "ATTRIBUTED_GRAPH_OUTPUT_TOO_LARGE")
    return parse_attributed_stdout(payload)


def parse_attributed_stdout(payload):
    """Validate exact helper protocol independently of compiler toolchain."""
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise PrivateSourceInvokeR131Error(
            "ATTRIBUTED_GRAPH_OUTPUT_NOT_UTF8") from exc
    need(bool(lines), "ATTRIBUTED_GRAPH_MISSING_SUMMARY")
    summary = lines[0].split("\t")
    need(len(summary) == 6 and summary[0] == "SUMMARY",
         "ATTRIBUTED_GRAPH_SUMMARY_PROTOCOL_INVALID")
    try:
        fields = [int(x) for x in summary[1:]]
    except ValueError as exc:
        raise PrivateSourceInvokeR131Error(
            "ATTRIBUTED_GRAPH_SUMMARY_VALUES_INVALID") from exc
    need(all(0 <= x <= 10_000_000 for x in fields) and fields[0] >= 1,
         "ATTRIBUTED_GRAPH_SUMMARY_VALUES_OUT_OF_RANGE")
    names = ("parsed_java_source_files",
             "java_symbol_attribution_errors",
             "source_invocations_inside_resolved_rs_classes",
             "unresolved_source_method_invocations",
             "resolved_calls_to_non_rs_class_owners")
    aggregate = dict(zip(names, fields))
    rows = []
    seen = set()
    for line in lines[1:]:
        columns = line.split("\t")
        need(len(columns) == 4 and columns[0] == "EDGE",
             "ATTRIBUTED_GRAPH_EDGE_PROTOCOL_INVALID")
        a, b = decode(columns[1]), decode(columns[2])
        try:
            count = int(columns[3])
        except ValueError as exc:
            raise PrivateSourceInvokeR131Error(
                "ATTRIBUTED_GRAPH_EDGE_COUNT_INVALID") from exc
        need(a.startswith("rs/") and b.startswith("rs/")
             and a and b and 0 < count <= 1_000_000,
             "ATTRIBUTED_GRAPH_EDGE_INVALID")
        need((a, b) not in seen,
             "ATTRIBUTED_GRAPH_DUPLICATE_SOURCE_EDGE")
        seen.add((a, b))
        rows.append({"caller": a, "callee": b, "count": count})
    rows.sort(key=lambda r: (r["caller"], r["callee"]))
    need(sum(r["count"] for r in rows)
         + fields[3] + fields[4] <= fields[2],
         "ATTRIBUTED_GRAPH_INVOCATION_COUNT_INCONSISTENT")
    return aggregate, rows


def extract_client_source_call_edges(source_zip, *,
                                     source_sha256,
                                     include_identifiers=False):
    entries = source_members(source_zip, source_sha256)
    stats, edges = _run_trusted_helper(entries)
    need(stats["parsed_java_source_files"] == len(entries),
         "SOURCE_FILE_INVENTORY_CHANGED_DURING_AST_ANALYSIS")
    manifest = hashlib.sha256(json.dumps(
        edges, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    result = {
        "schema_version": 1,
        "kind": "private_v309_source_ast_attributed_call_edges_r131",
        "source_archive_sha256": source_sha256,
        **stats,
        "direct_rs_to_rs_attributed_call_sites":
            sum(r["count"] for r in edges),
        "distinct_rs_to_rs_source_owner_edges": len(edges),
        "private_edge_manifest_sha256": manifest,
        "java_source_executed": False,
        "java_source_classfiles_generated": False,
        "original_rs_jar_used_for_symbol_resolution": False,
        "source_callgraph_complete": False,
        "independent_jvm_edge_parity_proven": False,
        "class_lineage_accepted": False,
        "private_identifiers_included": bool(include_identifiers),
    }
    # Source analysis (even when error-free) does not lower source lambdas
    # into JVM synthetic methods and does not include implicit bytecode calls.
    # Therefore NEVER equate AST call counts with whole original JVM graph.
    if include_identifiers:
        result["private_source_call_edges"] = edges
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_client_source_zip")
    p.add_argument("fresh_private_report")
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--private-identifiers", action="store_true")
    a = p.parse_args(argv)
    target = Path(a.fresh_private_report)
    try:
        need(not target.exists() and not target.is_symlink()
             and target.parent.is_dir() and not target.parent.is_symlink(),
             "FRESH_PRIVATE_REPORT_REQUIRED")
        report = extract_client_source_call_edges(
            a.private_client_source_zip,
            source_sha256=a.source_sha256,
            include_identifiers=a.private_identifiers)
        target.write_text(json.dumps(
            report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
        print(json.dumps({key: value for key, value in report.items()
                          if key != "private_source_call_edges"},
                         sort_keys=True))
    except Exception:
        p.error("PRIVATE_SOURCE_ATTRIBUTED_CALL_GRAPH_R131_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
