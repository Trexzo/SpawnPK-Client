"""R147: unique-shape v309 JVM ↔ decompiled Java member mapping SEEDS.

Only when R146 corroborates the complete source OWNER, compare every original
JVM classfile field/constructor/method against Java AST declarations. A member
is a candidate only when its access+erased JVM descriptor occurs exactly ONCE
on both sides, with no neighboring duplicate of that shape. Names and full
candidate map remain PRIVATE. No bytecode, semantic parity, source publication
or actual recovered client recompilation is asserted.
"""
from __future__ import annotations

from collections import defaultdict
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .classfile import parse_class
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import source_members, sha_file
from .private_v309_packet_original_source_shape_r146 import (
    _ACCESS_MASK, _shape, corroborate_private_packet_source,
)


class PrivatePacketMemberSeedsR147Error(ValueError):
    pass


def check(ok, reason):
    if not ok:
        raise PrivatePacketMemberSeedsR147Error(reason)


def _named_ast(source):
    helper = (Path(__file__).resolve().parent / "java" /
              "PrivatePacketNamedSourceR147.java")
    check(helper.is_file() and not helper.is_symlink(),
          "R147_TRUSTED_AST_SOURCE_REQUIRED")
    javac, java = shutil.which("javac"), shutil.which("java")
    check(javac and java, "R147_JDK_REQUIRED")
    check(b"\r" not in source and len(source) <= 2_000_000,
          "R147_AMBIGUOUS_NEWLINE_OR_SOURCE_SIZE")
    try:
        decoded = source.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PrivatePacketMemberSeedsR147Error(
            "R147_SOURCE_MUST_BE_UTF8") from exc
    check(all(ord(x) <= 0xffff for x in decoded),
          "R147_UTF16_SOURCE_UNSUPPORTED")
    with tempfile.TemporaryDirectory(prefix="spk-r147-private-") as td:
        root = Path(td)
        classes = root / "trusted"
        empty = root / "empty"
        classes.mkdir()
        empty.mkdir()
        source_path = root / "Candidate.java"
        source_path.write_bytes(source)
        env = os.environ.copy()
        for key in ("JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS",
                    "_JAVA_OPTIONS", "CLASSPATH"):
            env.pop(key, None)
        try:
            compiled = subprocess.run([
                javac, "--release", "11", "-proc:none", "-encoding", "UTF-8",
                "-classpath", str(empty), "-sourcepath", str(empty),
                "-d", str(classes), str(helper)
            ], cwd=root, env=env, stdin=subprocess.DEVNULL,
                capture_output=True, timeout=60, check=False)
            check(compiled.returncode == 0,
                  "R147_TRUSTED_JAVA_HELPER_COMPILATION_FAILED")
            run = subprocess.run([
                java, "-cp", str(classes),
                "PrivatePacketNamedSourceR147", str(source_path), str(empty)
            ], cwd=root, env=env, stdin=subprocess.DEVNULL,
                capture_output=True, timeout=60, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PrivatePacketMemberSeedsR147Error(
                "R147_JAVA_AST_RUN_NOT_COMPLETED") from exc
        check(run.returncode == 0 and len(run.stdout) <= 300_000,
              "R147_TRUSTED_JAVA_AST_PARSE_REJECTED")
        text = run.stdout.decode("utf-8", errors="strict")
    names = []
    owner = []
    for line in text.splitlines():
        parts = line.split("\t")
        check(parts and parts[0] in ("OWNER", "F", "M", "RSA"),
              "R147_AST_PROTOCOL_UNKNOWN_LINE")
        if parts[0] == "OWNER":
            check(len(parts) == 2, "R147_JAVA_OWNER_PROTOCOL_BAD")
            owner.append(parts[1])
        elif parts[0] in ("F", "M"):
            check(len(parts) == 4 and parts[1].isdigit()
                  and parts[3] and "\n" not in parts[3],
                  "R147_JAVA_NAMED_MEMBER_PROTOCOL_BAD")
            kind = ("F" if parts[0] == "F"
                    else "C" if parts[3] == "<init>" else "M")
            names.append((kind, int(parts[1]), parts[2], parts[3]))
        else:
            check(len(parts) == 2, "R147_RSA_PROTOCOL_BAD")
    check(len(owner) == 1, "R147_JAVA_OWNER_COUNT_INVALID")
    return owner[0], names


def _original_named_members(parsed):
    results = []
    for row in parsed.fields:
        results.append(("F", row["access"] & _ACCESS_MASK,
                        _shape(row["descriptor"]), row["name"]))
    for row in parsed.methods:
        if row["name"] == "<clinit>":
            continue
        kind = "C" if row["name"] == "<init>" else "M"
        results.append((kind, row["access"] & _ACCESS_MASK,
                        _shape(row["descriptor"]), row["name"]))
    return results


def _group(names):
    result = defaultdict(list)
    for kind, flags, shape, name in names:
        check(kind in ("F", "C", "M") and type(flags) is int
              and isinstance(shape, str) and isinstance(name, str),
              "R147_UNEXPECTED_MEMBER_FORMAT")
        result[(kind, flags, shape)].append(name)
    return result


def private_packet_member_seeds(original_jar, source_zip, *,
                               source_sha256,
                               original_sha256=CANONICAL_V309,
                               original_buffer="rs/x/e",
                               source_file="rs/io/Packet.java",
                               original_dependent="com/a/b/a/b",
                               include_private_identifiers=False):
    check(sha_file(original_jar) == original_sha256 and
          sha_file(source_zip) == source_sha256,
          "R147_INPUT_SHA256_MISMATCH")
    evidence = corroborate_private_packet_source(
        original_jar, source_zip, source_sha256=source_sha256,
        original_sha256=original_sha256, original_buffer=original_buffer,
        source_file=source_file, original_dependent=original_dependent)
    check(evidence["provisional_source_identity_structurally_corroborated"],
          "R147_SOURCE_OWNER_NOT_CORROBORATED_BY_R146")
    sources = dict(source_members(source_zip, source_sha256))
    with ZipFile(original_jar) as original:
        raw = original.read(original_buffer + ".class")
    parsed = parse_class(raw)
    check(parsed.name == original_buffer,
          "R147_JVM_BUFFER_CLASSFILE_NAME_MISMATCH")
    original = _original_named_members(parsed)
    source_owner, candidate = _named_ast(sources[source_file])
    check(source_owner == source_file[:-5],
          "R147_CANDIDATE_JAVA_OWNER_MISMATCH")
    old_groups, new_groups = _group(original), _group(candidate)
    check(set(old_groups) == set(new_groups)
          and all(len(old_groups[k]) == len(new_groups[k])
                  for k in old_groups),
          "R147_R146_STRUCTURAL_MULTIPLICITIES_DRIFTED")

    unique = []
    ambiguous_classes = 0
    ambiguous_members = 0
    for key in sorted(old_groups):
        from_names = old_groups[key]
        to_names = new_groups[key]
        if len(from_names) != 1 or len(to_names) != 1:
            ambiguous_classes += 1
            ambiguous_members += len(from_names)
            continue
        kind, flags, normalized_descriptor = key
        unique.append({
            "member_kind": {"F":"field", "M":"method", "C":"constructor"}[kind],
            "original_jvm_member_name": from_names[0],
            "source_candidate_member_name": to_names[0],
            "member_access_mask": flags,
            "erased_jvm_descriptor": normalized_descriptor,
            "mapping_status": "unique_shape_candidate_not_semantically_accepted",
        })

    check(len(unique) + ambiguous_members == len(original) == len(candidate),
          "R147_MEMBER_PARTITION_INCOMPLETE")
    unique_material = json.dumps(
        unique, sort_keys=True, separators=(",", ":")).encode("utf-8")
    private_digest = hashlib.sha256(unique_material).hexdigest()
    report = {
        "schema_version": 1,
        "kind": "private_v309_packet_unique_member_shape_candidates_r147",
        "original_client_sha256": original_sha256,
        "client_candidate_source_zip_sha256": source_sha256,
        "private_original_buffer_class_sha256":
            evidence["private_original_buffer_class_sha256"],
        "private_source_member_candidates_sha256": private_digest,
        "original_total_structurally_corroborated_members": len(original),
        "source_total_structurally_corroborated_members": len(candidate),
        "unique_member_shape_candidates_total": len(unique),
        "unique_field_shape_candidates": sum(
            p["member_kind"] == "field" for p in unique),
        "unique_constructor_shape_candidates": sum(
            p["member_kind"] == "constructor" for p in unique),
        "unique_method_shape_candidates": sum(
            p["member_kind"] == "method" for p in unique),
        "ambiguous_erased_shape_groups": ambiguous_classes,
        "ambiguous_member_count_not_assigned": ambiguous_members,
        "all_members_partitioned_without_guessing": True,
        "original_owner_candidate_java_source_r146_correspondence_required": True,
        "original_member_names_compared_only_in_private_memory": True,
        "original_method_bytecode_parity_verified": False,
        "unique_signature_proves_exact_original_method_mapping": False,
        "ambiguous_method_or_field_names_guessing_allowed": False,
        "original_class_methods_recompiled": False,
        "whole_client_compilation_accepted": False,
        "recovered_private_source_publication_authorized": False,
    }
    if include_private_identifiers:
        report["private_member_seed_candidates"] = unique
    check(sha_file(original_jar) == original_sha256
          and sha_file(source_zip) == source_sha256,
          "R147_INPUTS_CHANGED_DURING_ANALYSIS")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_original_v309_jar")
    parser.add_argument("private_source_candidate_zip")
    parser.add_argument("fresh_private_aggregate_report_json")
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--original-sha256", default=CANONICAL_V309)
    parser.add_argument("--original-buffer", default="rs/x/e")
    parser.add_argument("--source-file", default="rs/io/Packet.java")
    parser.add_argument("--original-dependent", default="com/a/b/a/b")
    parser.add_argument("--fresh-private-identifier-map")
    args = parser.parse_args(argv)
    output = Path(args.fresh_private_aggregate_report_json)
    identity = (Path(args.fresh_private_identifier_map)
                if args.fresh_private_identifier_map else None)
    try:
        paths = [p for p in (output, identity) if p is not None]
        check(len(paths) == len(set(paths)) and
              all(not path.exists() and not path.is_symlink()
                  and path.parent.is_dir() and not path.parent.is_symlink()
                  for path in paths), "R147_PRIVATE_REPORT_PATH_NOT_FRESH")
        record = private_packet_member_seeds(
            args.private_original_v309_jar,
            args.private_source_candidate_zip,
            original_sha256=args.original_sha256,
            source_sha256=args.source_sha256,
            original_buffer=args.original_buffer,
            source_file=args.source_file,
            original_dependent=args.original_dependent,
            include_private_identifiers=bool(identity))
        if identity:
            exact_names = record.pop("private_member_seed_candidates")
            identity.write_text(
                json.dumps(exact_names, indent=2, sort_keys=True) + "\n",
                encoding="utf-8")
        output.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        print("R147_PRIVATE_PACKET_MEMBER_SEEDS_RECORDED_NO_SEMANTIC_ACCEPTANCE")
        print("sanitized_report_sha256=" + sha_file(output))
    except Exception:
        parser.error("R147_PRIVATE_PACKET_MEMBER_CORRESPONDENCE_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
