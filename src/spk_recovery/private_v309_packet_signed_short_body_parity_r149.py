"""R149: original-v309 signed-short reader B()I independent SOURCE body parity.

Never place original rs/ game classfiles on javac's classpath. Instead parse
exactly two identical candidate Java methods with a trusted Java AST, rewrite
only AST-verified this.caret / this.payload field-access spans into the two
JVM field identities directly proven by the original B method instructions,
and independently compile each method in an isolated minimal Java9 owner.
Compare decoded JVM Code instructions, resolved CP operands, stack/frame
metadata and exception handlers to ORIGINAL B. This is a method-body parity
witness under explicit field aliases, not whole Packet-class recovery or
a unique mapping between two semantically identical source methods.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .bytecode_profile import profile_class_field_accesses
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import source_members, sha_file
from .private_v309_packet_member_seeds_r147 import private_packet_member_seeds


class PrivateSignedShortBodyParityR149Error(ValueError):
    pass


def ensure(ok, reason):
    if not ok:
        raise PrivateSignedShortBodyParityR149Error(reason)


def _cmd(args, work, *, seconds=65):
    env = os.environ.copy()
    for key in ("CLASSPATH", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS",
                "_JAVA_OPTIONS"):
        env.pop(key, None)
    try:
        result = subprocess.run(
            args, cwd=work, env=env, stdin=subprocess.DEVNULL,
            capture_output=True, timeout=seconds, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PrivateSignedShortBodyParityR149Error(
            "R149_TRUSTED_JAVA_PROCESS_NOT_COMPLETED") from exc
    return result


def _candidate_method_spans(source, *, scratch):
    java, javac = shutil.which("java"), shutil.which("javac")
    ensure(java and javac, "R149_JDK_REQUIRED")
    ensure(type(source) is bytes and len(source) <= 2_000_000
           and all(ch < 128 for ch in source)
           and b"\r" not in source,
           "R149_SOURCE_NOT_ASCII_OR_IS_UNBOUNDED")
    source_file = scratch / "PrivatePacket.java"
    source_file.write_bytes(source)
    trusted = scratch / "trusted"
    empty = scratch / "empty"
    trusted.mkdir()
    empty.mkdir()
    helper = (Path(__file__).resolve().parent / "java" /
              "PrivateSignedShortSourceSpansR149.java")
    ensure(helper.is_file() and not helper.is_symlink(),
           "R149_TRUSTED_AST_HELPER_ABSENT")
    compile_helper = _cmd(
        [javac, "--release", "11", "-proc:none", "-encoding", "UTF-8",
         "-classpath", str(empty), "-sourcepath", str(empty),
         "-d", str(trusted), str(helper)], scratch)
    ensure(compile_helper.returncode == 0,
           "R149_TRUSTED_JAVAC_AST_HELPER_COMPILE_FAILED")
    result = _cmd(
        [java, "-cp", str(trusted), "PrivateSignedShortSourceSpansR149",
         str(source_file), str(empty)], scratch)
    ensure(result.returncode == 0 and len(result.stdout) < 4096,
           "R149_AST_CANDIDATE_SPANS_REJECTED")
    rows = result.stdout.decode("utf-8", errors="strict").splitlines()
    methods = []
    current = None
    for line in rows:
        parts = line.split("\t")
        if parts[0] == "METHOD":
            ensure(current is None and len(parts) == 4
                   and parts[1].isidentifier(),
                   "R149_METHOD_SPAN_PROTOCOL")
            start, end = int(parts[2]), int(parts[3])
            ensure(0 <= start < end <= len(source),
                   "R149_METHOD_OFFSET_OUT_OF_SOURCE")
            current = {"name": parts[1], "start": start,
                       "end": end, "fields": []}
        elif parts[0] == "FIELD":
            ensure(current is not None and len(parts) == 4
                   and parts[1] in ("this.caret", "this.payload"),
                   "R149_FIELD_SPAN_PROTOCOL")
            start, end = int(parts[2]), int(parts[3])
            ensure(current["start"] <= start < end <= current["end"]
                   and source[start:end].decode("ascii") == parts[1],
                   "R149_AST_FIELD_SOURCE_OFFSET_MISMATCH")
            current["fields"].append((start, end, parts[1]))
        elif parts == ["END"]:
            ensure(current is not None and len(current["fields"]) == 5,
                   "R149_METHOD_FIELDS_NOT_COMPLETE")
            methods.append(current)
            current = None
        else:
            raise PrivateSignedShortBodyParityR149Error(
                "R149_UNRECOGNIZED_AST_PROTOCOL_ROW")
    ensure(current is None and len(methods) == 2
           and len({m["name"] for m in methods}) == 2,
           "R149_EXACT_TWO_METHODS_NOT_PROVEN")
    return methods


def _original_B_member(raw, owner, name):
    profile = profile_class_field_accesses(raw)
    ensure(profile["internal_name"] == owner,
           "R149_ORIGINAL_CLASSFILE_INTERNAL_OWNER_MISMATCH")
    methods = [m for m in profile["methods"]
               if m["name"] == name and m["descriptor"] == "()I"]
    ensure(len(methods) == 1 and methods[0]["access"] & 0x0001
           and not methods[0]["access"] & 0x0008,
           "R149_ORIGINAL_SIGNED_SHORT_METHOD_NOT_UNIQUE_PUBLIC_INSTANCE")
    method = methods[0]
    ensure(method["code_length"] == 59 and
           method["method_invocations"] == [] and
           method["exception_handlers"] == [],
           "R149_ORIGINAL_B_NOT_EXPECTED_59_BYTE_LEAF")
    accesses = method["field_accesses"]
    ints = {a["name"] for a in accesses
            if a["owner"] == owner and a["descriptor"] == "I"}
    payloads = {a["name"] for a in accesses
                if a["owner"] == owner and a["descriptor"] == "[B"}
    ensure(len(ints) == len(payloads) == 1
           and len(accesses) == 6
           and all(a["owner"] == owner and a["descriptor"] in ("I", "[B")
                   for a in accesses)
           and [a["operation"] for a in accesses].count("putfield") == 1
           and [a["operation"] for a in accesses].count("getfield") == 5,
           "R149_ORIGINAL_CURSOR_PAYLOAD_FIELD_ROLES_UNPROVEN")
    ensure(all(a["name"] == next(iter(ints))
               for a in accesses if a["descriptor"] == "I")
           and all(a["name"] == next(iter(payloads))
                   for a in accesses if a["descriptor"] == "[B"),
           "R149_ORIGINAL_ROLE_ALIASES_INCONSISTENT")
    return method, next(iter(ints)), next(iter(payloads))


def _isolated_java(source, method, owner, original_name,
                   cursor, payload):
    parts = owner.split("/")
    ensure(all(re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", p)
               for p in parts), "R149_ORIGINAL_OWNER_NOT_JAVA_IDENTIFIER")
    begin, end = method["start"], method["end"]
    original = source[begin:end].decode("ascii")
    edits = []
    for a, b, role in method["fields"]:
        edits.append((a - begin, b - begin,
                      "this." + (cursor if role == "this.caret" else payload)))
    ordered = sorted(edits)
    ensure(all(ordered[i][1] <= ordered[i+1][0]
               for i in range(len(ordered)-1)),
           "R149_OVERLAPPING_SOURCE_AST_FIELDS")
    updated = original
    for a, b, replacement in reversed(ordered):
        updated = updated[:a] + replacement + updated[b:]
    head = re.compile(r"\bpublic\s+int\s+" +
                      re.escape(method["name"]) + r"\s*\(\s*\)")
    updated, count = head.subn("public int " + original_name + "()", updated)
    ensure(count == 1 and
           "this.caret" not in updated and "this.payload" not in updated,
           "R149_ISOLATED_SOURCE_ALIAS_REWRITE_NOT_COMPLETE")
    prefix = ("package " + ".".join(parts[:-1]) + ";\n"
              if len(parts) > 1 else "")
    return (prefix + "public class " + parts[-1] +
            " {\n public int " + cursor + ";\n public byte[] " +
            payload + ";\n" + updated + "\n}\n")


def _normal_instructions(method):
    # CP pool indices differ in isolated compilation; retain all resolved
    # members, raw constant bits, operands, branches, offsets and opcodes.
    result = []
    for raw in method["instructions"]:
        item = dict(raw)
        item.pop("constant_pool_index", None)
        result.append(item)
    return result


def _one_isolated_compile(source, original_method, *, owner, name, scratch):
    javac = shutil.which("javac")
    ensure(javac, "R149_TRUSTED_JDK_NOT_FOUND")
    target = scratch / "src" / (owner + ".java")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="ascii")
    compiled = scratch / "classes"
    compiled.mkdir()
    empty = scratch / "empty"
    empty.mkdir()
    proc = _cmd(
        [javac, "--release", "9", "-proc:none", "-implicit:none",
         "-g:none", "-classpath", str(empty), "-sourcepath", str(empty),
         "-d", str(compiled), str(target)], scratch)
    ensure(proc.returncode == 0,
           "R149_ISOLATED_REAL_JAVA_METHOD_JAVAC_FAILED")
    cls = compiled / (owner + ".class")
    ensure(cls.is_file(), "R149_ISOLATED_SOURCE_CLASS_NOT_EMITTED")
    profile = profile_class_field_accesses(cls.read_bytes())
    ensure(profile["internal_name"] == owner and
           len([m for m in profile["methods"]
                if m["name"] == name and m["descriptor"] == "()I"]) == 1,
           "R149_ISOLATED_REBUILT_MEMBER_NOT_UNIQUE")
    built = next(m for m in profile["methods"]
                 if m["name"] == name and m["descriptor"] == "()I")
    tests = {
        "exact_code_length": built["code_length"] == original_method["code_length"],
        "exact_max_stack": built["max_stack"] == original_method["max_stack"],
        "exact_max_locals": built["max_locals"] == original_method["max_locals"],
        "exact_decoded_jvm_instructions_and_resolved_cp":
            _normal_instructions(built) == _normal_instructions(original_method),
        "exact_exception_handlers":
            built["exception_handlers"] == original_method["exception_handlers"],
        "exact_stackmap_presence_and_resolved_frames":
            built["stackmap_table_present"] == original_method["stackmap_table_present"]
            and built["stackmap_frames"] == original_method["stackmap_frames"],
        "exact_member_access":
            built["access"] == original_method["access"],
    }
    return tests


def prove_private_signed_short_body_rebuild(original_jar, source_zip, *,
                                            source_sha256,
                                            original_sha256=CANONICAL_V309,
                                            original_owner="rs/x/e",
                                            source_file="rs/io/Packet.java",
                                            original_method="B",
                                            original_dependent="com/a/b/a/b"):
    ensure(sha_file(original_jar) == original_sha256
           and sha_file(source_zip) == source_sha256,
           "R149_INPUT_SHA256_MISMATCH")
    parent = private_packet_member_seeds(
        original_jar, source_zip,
        source_sha256=source_sha256, original_sha256=original_sha256,
        original_buffer=original_owner, source_file=source_file,
        original_dependent=original_dependent)
    ensure(parent["all_members_partitioned_without_guessing"],
           "R149_R146_R147_UPSTREAM_OWNER_NOT_CORROBORATED")
    source_files = dict(source_members(source_zip, source_sha256))
    ensure(source_file in source_files,
           "R149_ORIGINAL_CANDIDATE_PACKET_SOURCE_MISSING")
    with ZipFile(original_jar) as jar:
        cls = jar.read(original_owner + ".class")
    orig, cursor, payload = _original_B_member(
        cls, original_owner, original_method)
    with tempfile.TemporaryDirectory(prefix="spk-r149-private-") as tmp:
        root = Path(tmp)
        spans = _candidate_method_spans(source_files[source_file], scratch=root)
        attempts = []
        for number, m in enumerate(spans):
            preview = _isolated_java(
                source_files[source_file], m, original_owner,
                original_method, cursor, payload)
            folder = root / ("candidate_" + str(number))
            folder.mkdir()
            checks = _one_isolated_compile(
                preview, orig, owner=original_owner,
                name=original_method, scratch=folder)
            attempts.append({
                "private_source_method_name": m["name"],
                "all_checked_bytecode_parity_properties_equal": all(checks.values()),
                "checks": checks,
            })

    ensure(all(a["all_checked_bytecode_parity_properties_equal"]
               for a in attempts),
           "R149_SIGNED_SHORT_SOURCE_BODY_BYTECODE_PARITY_NOT_ESTABLISHED")
    # Same method name is deliberately used for both isolated recompiles;
    # neither tells us which original source method was called historically.
    name_digest = hashlib.sha256(
        json.dumps(attempts, sort_keys=True).encode("utf-8")).hexdigest()
    result = {
        "schema_version": 1,
        "kind": "private_v309_packet_two_signed_short_isolated_method_parity_r149",
        "original_client_sha256": original_sha256,
        "candidate_source_zip_sha256": source_sha256,
        "original_signed_short_classfile_sha256":
            hashlib.sha256(cls).hexdigest(),
        "private_candidate_method_parity_manifest_sha256": name_digest,
        "original_public_signed_short_leaf_59_byte_method_confirmed": True,
        "jdk_java9_compilation_used_no_original_game_binary_classpath": True,
        "trusted_jdk_ast_verified_source_method_spans": True,
        "original_cursor_and_payload_field_aliases_from_jvm_code": True,
        "distinct_identical_java_source_bodies_found": len(attempts),
        "isolated_method_compilations_performed": len(attempts),
        "each_isolated_method_all_checked_parity_properties_equal":
            all(a["all_checked_bytecode_parity_properties_equal"] for a in attempts),
        "per_method_exact_code_length": all(a["checks"]["exact_code_length"]
                                           for a in attempts),
        "per_method_exact_decoded_instructions_resolved_cp":
            all(a["checks"]["exact_decoded_jvm_instructions_and_resolved_cp"]
                for a in attempts),
        "per_method_exact_stackmaps":
            all(a["checks"]["exact_stackmap_presence_and_resolved_frames"]
                for a in attempts),
        "original_to_source_member_identity_uniquely_determined": False,
        "bytecode_parity_applies_to_full_original_packet_owner": False,
        "full_packet_method_mapping_accepted": False,
        "matrix_java_source_recovered": False,
        "original_client_recompiled": False,
        "real_full_v309_compiler_error_count_reduced": False,
        "original_derived_source_publication_authorized": False,
    }
    ensure(sha_file(original_jar) == original_sha256
           and sha_file(source_zip) == source_sha256,
           "R149_PRIVATE_ORIGINAL_INPUT_CHANGED_DURING_ANALYSIS")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_original_v309_jar")
    parser.add_argument("private_candidate_source_zip")
    parser.add_argument("fresh_private_sanitized_report_json")
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--original-sha256", default=CANONICAL_V309)
    parser.add_argument("--original-owner", default="rs/x/e")
    parser.add_argument("--source-file", default="rs/io/Packet.java")
    parser.add_argument("--original-method", default="B")
    parser.add_argument("--original-dependent", default="com/a/b/a/b")
    opts = parser.parse_args(argv)
    output = Path(opts.fresh_private_sanitized_report_json)
    try:
        ensure(not output.exists() and not output.is_symlink()
               and output.parent.is_dir() and not output.parent.is_symlink(),
               "R149_REPORT_OUTPUT_MUST_BE_FRESH")
        report = prove_private_signed_short_body_rebuild(
            opts.private_original_v309_jar, opts.private_candidate_source_zip,
            source_sha256=opts.source_sha256,
            original_sha256=opts.original_sha256,
            original_owner=opts.original_owner,
            source_file=opts.source_file,
            original_method=opts.original_method,
            original_dependent=opts.original_dependent)
        output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                          encoding="utf-8")
        print("R149_PRIVATE_SIGNED_SHORT_JAVA9_METHOD_BODY_PARITY_WITNESS")
        print("sanitized_report_sha256=" + sha_file(output))
    except Exception:
        parser.error("R149_SIGNED_SHORT_SOURCE_BODY_PARITY_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
