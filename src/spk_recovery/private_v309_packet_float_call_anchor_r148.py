"""R148: provenance-anchored cross-name Packet float→int call-edge mapping.

The original-v309 JVM rs/x/e public float ()F code is required to be exactly
  aload_0; invokevirtual same-owner int()I; invokestatic
  java/lang/Float.intBitsToFloat (I)F; freturn.
The independently decompiled candidate Java source must contain exactly one
  float f() { return Float.intBitsToFloat(this.g()); }
where g() is a uniquely declared int-zero-argument method. First require
R146's whole-source/RSA match and R147's unique-shape mapping of float f().

This permits a *new, context-anchored candidate* for the original int()I
callee among its otherwise ambiguous 37-shape group; it does NOT prove the
reader body is correct, bytecode-equivalent, original name accepted, or that
the recovered client compiles. Original identifiers stay private.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import source_members, sha_file
from .private_v309_packet_member_seeds_r147 import (
    private_packet_member_seeds, _original_named_members, _group,
)
from .bytecode_profile import profile_class_field_accesses, BytecodeProfileError
from .classfile import parse_class


class PrivatePacketCallAnchorR148Error(ValueError):
    pass


def need(value, reason):
    if not value:
        raise PrivatePacketCallAnchorR148Error(reason)


def _source_float_to_int_calls(source):
    helper = (Path(__file__).resolve().parent / "java" /
              "PrivatePacketFloatCallAnchorR148.java")
    java = shutil.which("java")
    javac = shutil.which("javac")
    need(java and javac and helper.is_file() and not helper.is_symlink(),
         "R148_TRUSTED_AST_JDK_REQUIRED")
    need(type(source) is bytes and len(source) <= 2_000_000
         and b"\r" not in source,
         "R148_SOURCE_SIZE_OR_LINE_ENDING_AMBIGUITY")
    decoded = source.decode("utf-8", errors="strict")
    need(all(ord(x) <= 0xffff for x in decoded),
         "R148_UNSUPPORTED_UTF16_SOURCE_SPAN")
    with tempfile.TemporaryDirectory(prefix="spk-r148-private-") as tmp:
        root = Path(tmp)
        candidate = root / "PrivateSource.java"
        classes = root / "trusted-ast"
        empty = root / "empty"
        classes.mkdir()
        empty.mkdir()
        candidate.write_bytes(source)
        env = os.environ.copy()
        for key in ("CLASSPATH", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS",
                    "_JAVA_OPTIONS"):
            env.pop(key, None)
        try:
            compile_result = subprocess.run(
                [javac, "--release", "11", "-proc:none",
                 "-classpath", str(empty), "-sourcepath", str(empty),
                 "-d", str(classes), str(helper)],
                cwd=root, env=env, stdin=subprocess.DEVNULL,
                capture_output=True, timeout=60, check=False)
            need(compile_result.returncode == 0,
                 "R148_AST_HELPER_JAVAC_FAILED")
            checked = subprocess.run(
                [java, "-cp", str(classes),
                 "PrivatePacketFloatCallAnchorR148",
                 str(candidate), str(empty)],
                cwd=root, env=env, stdin=subprocess.DEVNULL,
                capture_output=True, timeout=60, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PrivatePacketCallAnchorR148Error(
                "R148_JAVA_AST_NOT_COMPLETED") from exc
        need(checked.returncode == 0 and len(checked.stdout) <= 2048,
             "R148_FLOAT_READER_SOURCE_AST_NOT_PROVEN")
        line = checked.stdout.decode("utf-8", errors="strict").strip()
    values = line.split("\t")
    need(len(values) == 2
         and all(value.isidentifier() for value in values),
         "R148_FLOAT_READER_AST_PROTOCOL_INVALID")
    return values[0], values[1]


def _only_float_jvm_reader(original_raw, owner):
    try:
        profile = profile_class_field_accesses(original_raw)
    except (BytecodeProfileError, ValueError) as exc:
        raise PrivatePacketCallAnchorR148Error(
            "R148_ORIGINAL_BYTECODE_NOT_DECODED") from exc
    need(profile["internal_name"] == owner,
         "R148_ORIGINAL_BINARY_OWNER_MISMATCH")
    anchors = [m for m in profile["methods"]
               if m["descriptor"] == "()F"]
    need(len(anchors) == 1, "R148_JVM_FLOAT_METHOD_NOT_UNIQUE")
    method = anchors[0]
    instructions = method["instructions"]
    need([op.get("opcode") for op in instructions] ==
         ["0x2a", "0xb6", "0xb8", "0xae"]
         and method["code_length"] == 8
         and method["exception_handlers"] == []
         and method["field_accesses"] == [],
         "R148_JVM_FLOAT_METHOD_NOT_SIMPLE_BITCAST_FORWARDER")
    calls = method["method_invocations"]
    need(len(calls) == 2
         and calls[0]["operation"] == "invokevirtual"
         and calls[0]["owner"] == owner
         and calls[0]["descriptor"] == "()I"
         and calls[1]["operation"] == "invokestatic"
         and calls[1]["owner"] == "java/lang/Float"
         and calls[1]["name"] == "intBitsToFloat"
         and calls[1]["descriptor"] == "(I)F",
         "R148_JVM_FLOAT_BITCAST_CALLEE_NOT_PROVEN")
    members = [m for m in profile["methods"]
               if (m["name"], m["descriptor"]) ==
               (calls[0]["name"], "()I")]
    need(len(members) == 1
         and (members[0]["access"] & 0x0008) == 0,
         "R148_ORIGINAL_INT_READER_DECLARATION_NOT_UNIQUE")
    return method, members[0]


def private_packet_float_callee_anchor(original_jar, source_zip, *,
                                       original_sha256=CANONICAL_V309,
                                       source_sha256,
                                       original_buffer="rs/x/e",
                                       source_file="rs/io/Packet.java",
                                       original_dependent="com/a/b/a/b",
                                       include_private_identifiers=False):
    need(sha_file(original_jar) == original_sha256 and
         sha_file(source_zip) == source_sha256,
         "R148_INPUT_SHA256_MISMATCH")
    r147 = private_packet_member_seeds(
        original_jar, source_zip, original_sha256=original_sha256,
        source_sha256=source_sha256, original_buffer=original_buffer,
        source_file=source_file, original_dependent=original_dependent,
        include_private_identifiers=True)
    sources = dict(source_members(source_zip, source_sha256))
    java_float_name, java_int_name = _source_float_to_int_calls(
        sources[source_file])
    with ZipFile(original_jar) as jar:
        raw = jar.read(original_buffer + ".class")
    original_float, original_int = _only_float_jvm_reader(
        raw, original_buffer)
    anchors = [item for item in r147["private_member_seed_candidates"]
               if item["member_kind"] == "method"
               and item["erased_jvm_descriptor"] == "()F"
               and item["original_jvm_member_name"] == original_float["name"]
               and item["source_candidate_member_name"] == java_float_name]
    need(len(anchors) == 1,
         "R148_FLOAT_ANCHOR_NOT_UNIQUE_IN_R147_SEEDS")
    # The int()I callee is deliberately not auto-mapped via R147, as it
    # belongs to a multiple-member signature group.
    group = _group(_original_named_members(parse_class(raw)))
    int_shape = ("M", original_int["access"] &
                 (0x0001 | 0x0002 | 0x0004 | 0x0008 | 0x0010
                  | 0x0020 | 0x0100 | 0x0400), "()I")
    ambiguity = len(group.get(int_shape, []))
    need(ambiguity > 1,
         "R148_INT_READER_NOT_IN_AN_AMBIGUOUS_ORIGINAL_SHAPE_GROUP")
    pair = {
        "original_caller": original_float["name"],
        "source_caller": java_float_name,
        "original_ambiguous_int_callee": original_int["name"],
        "source_candidate_int_callee": java_int_name,
        "source_callsite_pattern": "Float.intBitsToFloat(this.intReader())",
        "original_jvm_caller_opcode_pattern":
            "aload_0 invokevirtual invokestatic freturn",
        "mapping_status": "call_edge_correlated_candidate_not_method_parity",
    }
    material = json.dumps(pair, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")
    output = {
        "schema_version": 1,
        "kind": "v309_private_packet_jvm_float_source_call_anchor_r148",
        "original_client_sha256": original_sha256,
        "candidate_source_zip_sha256": source_sha256,
        "original_buffer_class_sha256": hashlib.sha256(raw).hexdigest(),
        "r147_private_unique_member_candidates_sha256":
            r147["private_source_member_candidates_sha256"],
        "source_float_method_uniquely_structurally_anchored": True,
        "original_float_bytecode_exact_four_instruction_shape": True,
        "original_float_direct_self_int_invoke_then_float_bitcast": True,
        "candidate_java_exact_float_int_call_ast_pattern": True,
        "original_int_reader_erased_shape_group_size": ambiguity,
        "additional_ambiguity_narrowed_callee_candidates": 1,
        "private_candidate_call_edge_digest_sha256":
            hashlib.sha256(material).hexdigest(),
        "original_jvm_member_names_published": False,
        "original_int_reader_method_body_parity_verified": False,
        "candidate_source_int_reader_method_body_parity_verified": False,
        "caller_exact_compiled_source_instruction_parity_verified": False,
        "java_type_and_member_alias_mapping_accepted": False,
        "original_client_recompiled": False,
        "real_full_v309_javac_error_count_changed": False,
        "redistributable_original_source_accepted": False,
    }
    if include_private_identifiers:
        output["private_original_to_source_callee_candidate"] = pair
    need(sha_file(original_jar) == original_sha256 and
         sha_file(source_zip) == source_sha256,
         "R148_INPUTS_CHANGED_DURING_EVIDENCE_SCAN")
    return output


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_original_v309_client_jar")
    p.add_argument("private_candidate_source_zip")
    p.add_argument("fresh_private_aggregate_json")
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--original-sha256", default=CANONICAL_V309)
    p.add_argument("--original-buffer", default="rs/x/e")
    p.add_argument("--source-file", default="rs/io/Packet.java")
    p.add_argument("--original-dependent", default="com/a/b/a/b")
    p.add_argument("--fresh-private-identifier-map")
    args = p.parse_args(argv)
    dest = Path(args.fresh_private_aggregate_json)
    private = (Path(args.fresh_private_identifier_map)
               if args.fresh_private_identifier_map else None)
    paths = [v for v in (dest, private) if v is not None]
    try:
        need(len(paths) == len(set(paths)) and
             all(not f.exists() and not f.is_symlink()
                 and f.parent.is_dir() and not f.parent.is_symlink()
                 for f in paths), "R148_FRESH_PRIVATE_OUTPUTS_REQUIRED")
        result = private_packet_float_callee_anchor(
            args.private_original_v309_client_jar,
            args.private_candidate_source_zip,
            original_sha256=args.original_sha256,
            source_sha256=args.source_sha256,
            original_buffer=args.original_buffer,
            source_file=args.source_file,
            original_dependent=args.original_dependent,
            include_private_identifiers=bool(private))
        if private:
            sensitive = result.pop("private_original_to_source_callee_candidate")
            private.write_text(json.dumps(sensitive, sort_keys=True, indent=2)
                               + "\n", encoding="utf-8")
        dest.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
        print("R148_PACKET_FLOAT_CALL_EDGE_SEED_ONLY_NO_PARITY")
        print("private_report_sha256=" + sha_file(dest))
    except Exception:
        p.error("R148_ORIGINAL_FLOAT_CALL_EDGE_EVIDENCE_REJECTED")


if __name__ == "__main__":
    main()
