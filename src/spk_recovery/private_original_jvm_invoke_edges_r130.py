"""R130: exact original-v309 JVM invoke edges, from a SHA-pinned JAR.

Uses the existing classfile bytecode decoder, NOT raw constant-pool references:
only actually encountered invokevirtual/invokespecial/invokestatic/
invokeinterface instructions become class-to-class edges. invokedynamic is
tracked separately, because bootstrap targets need separate provenance.
The original JAR is read-only and never loaded by a JVM or launched.

This is one half of R129's two-parser evidence contract. It does NOT validate
source-to-original mapping or source callgraph equivalence.
"""
from __future__ import annotations

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

from .bytecode_profile import (
    BytecodeProfileError, profile_class_field_accesses,
)
from .private_client_namespace_legalizer_r125 import CANONICAL_V309


class PrivateOriginalInvokeR130Error(ValueError):
    pass


def require(value, code):
    if not value:
        raise PrivateOriginalInvokeR130Error(code)


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")).hexdigest()


_INVOKES = frozenset((
    "invokevirtual", "invokespecial", "invokestatic", "invokeinterface"
))


# Independent original-v309 Code walker checkpoint for the exact pinned
# binary. This is an aggregate cross-parser invariant, not source parity.
_CANONICAL_INVOKE_SHAPE = {
    "game_rs_classfiles_parsed": 1159,
    "declared_game_methods_scanned": 8389,
    "direct_jvm_invoke_sites_total": 49438,
    "direct_rs_to_rs_invoke_sites": 31241,
    "distinct_rs_to_rs_owner_edges": 3939,
    "distinct_rs_to_rs_method_target_sites": 10970,
    "invokedynamic_sites_excluded_for_independent_bootstrap_proof": 2069,
    "rs_target_edges_without_corresponding_original_classfile": 0,
}


def require_independent_canonical_invoke_checkpoint(report, original_sha):
    if original_sha != CANONICAL_V309:
        return
    require(all(report.get(k) == v for k, v
                in _CANONICAL_INVOKE_SHAPE.items()),
            "CANONICAL_V309_INDEPENDENT_INVOKE_CHECKPOINT_MISMATCH")


def collect_jvm_invoke_edges(original_jar, *,
                             expected_sha=CANONICAL_V309,
                             include_identifiers=False):
    original_jar = Path(original_jar)
    require(original_jar.is_file() and not original_jar.is_symlink(),
            "EXACT_PRIVATE_ORIGINAL_JAR_REQUIRED")
    require(type(expected_sha) is str and
            re.fullmatch(r"[a-f0-9]{64}", expected_sha) is not None,
            "ORIGINAL_JAR_PIN_INVALID")
    require(_sha256(original_jar) == expected_sha,
            "ORIGINAL_JAR_SHA256_MISMATCH")

    calls = Counter()
    full_calls = Counter()
    source_methods = 0
    decoded_calls = 0
    ignored_dynamic = 0
    classes = 0
    absent_game_targets = Counter()
    with zipfile.ZipFile(original_jar) as jar:
        infos = jar.infolist()
        require(1 <= len(infos) <= 20000,
                "ORIGINAL_ARCHIVE_SIZE_INVALID")
        names = [info.filename for info in infos]
        require(len(names) == len(set(names)),
                "ORIGINAL_ARCHIVE_DUPLICATE_PATH")
        for info in infos:
            name = info.filename
            require(not name.startswith("/") and "\\" not in name
                    and all(seg not in ("", ".", "..")
                            for seg in name.rstrip("/").split("/")),
                    "ORIGINAL_ARCHIVE_UNSAFE_PATH")
            require(((info.external_attr >> 16) & 0o170000) != 0o120000,
                    "ORIGINAL_ARCHIVE_SYMLINK_MEMBER")
        game_names = {
            name[:-6] for name in names
            if name.startswith("rs/") and name.endswith(".class")
        }
        require(bool(game_names), "ORIGINAL_RS_GAME_CLASSES_MISSING")

        for original in sorted(game_names):
            info = jar.getinfo(original + ".class")
            require(0 < info.file_size <= 16_000_000,
                    "ORIGINAL_CLASS_SIZE_INVALID")
            try:
                profile = profile_class_field_accesses(
                    jar.read(original + ".class"))
            except (BytecodeProfileError, IndexError, KeyError,
                    ValueError) as exc:
                raise PrivateOriginalInvokeR130Error(
                    "ORIGINAL_RS_BYTECODE_DECODE_FAILED") from exc
            require(profile.get("internal_name") == original,
                    "ORIGINAL_CLASS_HEADER_PATH_MISMATCH")
            classes += 1
            for method in profile["methods"]:
                invocations = method.get("method_invocations")
                require(isinstance(invocations, list),
                        "DECODED_METHOD_INVOKES_MISSING")
                source_methods += 1
                for call in invocations:
                    opname = call.get("operation")
                    if opname == "invokedynamic":
                        ignored_dynamic += 1
                        continue
                    require(opname in _INVOKES,
                            "UNSUPPORTED_JVM_CALL_OPCODE")
                    owner, name, desc = (call.get("owner"),
                                         call.get("name"),
                                         call.get("descriptor"))
                    require(type(owner) is str and bool(owner) and
                            type(name) is str and bool(name) and
                            type(desc) is str and bool(desc),
                            "JVM_INVOKE_TARGET_MISSING")
                    decoded_calls += 1
                    if owner.startswith("rs/"):
                        calls[(original, owner)] += 1
                        full_calls[(original, owner, opname, name, desc)] += 1
                        if owner not in game_names:
                            absent_game_targets[(original, owner)] += 1

    require(_sha256(original_jar) == expected_sha,
            "ORIGINAL_JAR_CHANGED_DURING_READ")
    edges = [
        {"caller": caller, "callee": callee, "count": count}
        for (caller, callee), count in sorted(calls.items())
    ]
    method_witness = [
        {"caller": caller, "callee": callee,
         "opcode": opcode, "method_name": name,
         "method_descriptor": descriptor, "count": count}
        for (caller, callee, opcode, name, descriptor), count
        in sorted(full_calls.items())
    ]
    # Default public output contains no raw obfuscated names.
    report = {
        "schema_version": 1,
        "kind": "private_original_v309_jvm_invoke_edges_r130",
        "original_client_sha256": expected_sha,
        "game_rs_classfiles_parsed": classes,
        "declared_game_methods_scanned": source_methods,
        "direct_jvm_invoke_sites_total": decoded_calls,
        "direct_rs_to_rs_invoke_sites": sum(calls.values()),
        "distinct_rs_to_rs_owner_edges": len(calls),
        "distinct_rs_to_rs_method_target_sites": len(full_calls),
        "invokedynamic_sites_excluded_for_independent_bootstrap_proof":
            ignored_dynamic,
        "rs_target_edges_without_corresponding_original_classfile":
            len(absent_game_targets),
        "edge_manifest_sha256": _digest(edges),
        "method_target_manifest_sha256": _digest(method_witness),
        "original_jar_executed": False,
        "source_to_original_callgraph_comparison_performed": False,
        "source_class_identity_accepted": False,
        "full_client_deobfuscated": False,
        "private_identifiers_included": bool(include_identifiers),
    }
    require_independent_canonical_invoke_checkpoint(report, expected_sha)
    if include_identifiers:
        # These are solely the original-side inputs to R129.
        report["private_original_call_edges"] = edges
        report["private_original_method_targets"] = method_witness
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_original_v309_jar")
    parser.add_argument("fresh_private_report")
    parser.add_argument("--original-sha256", default=CANONICAL_V309)
    parser.add_argument("--private-identifiers", action="store_true")
    args = parser.parse_args(argv)
    target = Path(args.fresh_private_report)
    try:
        require(not target.exists() and not target.is_symlink()
                and target.parent.is_dir() and not target.parent.is_symlink(),
                "FRESH_PRIVATE_REPORT_REQUIRED")
        report = collect_jvm_invoke_edges(
            args.private_original_v309_jar,
            expected_sha=args.original_sha256,
            include_identifiers=args.private_identifiers)
        target.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                          encoding="utf-8")
        print(json.dumps({
            key: value for key, value in report.items()
            if not key.startswith("private_original_")
        }, sort_keys=True))
    except Exception:
        parser.error("ORIGINAL_V309_INVOKE_R130_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
