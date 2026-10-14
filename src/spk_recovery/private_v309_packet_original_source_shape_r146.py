"""R146: corroborate v309 original buffer owner against decompiled Packet Java.

Only bytecode parsing and JDK parse-only source AST. No original binaries
are added to javac, no original/client code executed, and no source names or
RSA literals appear in the sanitized report. Matching an erased type-shape
multiset and literal sentinels DOES NOT prove method bytecode equivalence.
"""
from __future__ import annotations

from collections import Counter
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

from .classfile import parse_class, ClassFormatError
from .bytecode_profile import profile_class_constant_pool_references
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import source_members, sha_file


class PrivatePacketStructuralR146Error(ValueError):
    pass


_ACCESS_MASK = (0x0001 | 0x0002 | 0x0004 | 0x0008 | 0x0010
                | 0x0020 | 0x0100 | 0x0400)
_RSA_MODULUS = re.compile(r"[0-9]{200,512}\Z")


def need(ok, code):
    if not ok:
        raise PrivatePacketStructuralR146Error(code)


def _shape(descriptor):
    # The original and the preliminary deobfuscated Java use different
    # reference-class *names*. Preserve JVM primitive type, array rank,
    # method arity and access, but intentionally erase L<binaryname>;.
    need(type(descriptor) is str and descriptor, "R146_JVM_DESCRIPTOR_MISSING")
    return re.sub(r"L[^;]+;", "L;", descriptor)


def _hash(value):
    return hashlib.sha256(value).hexdigest()


def _member_shapes(parsed):
    fields = Counter(
        ("F", field["access"] & _ACCESS_MASK,
         _shape(field["descriptor"])) for field in parsed.fields)
    methods = Counter(
        ("M", method["access"] & _ACCESS_MASK,
         _shape(method["descriptor"]))
        for method in parsed.methods
        if method["name"] != "<clinit>")
    return fields, methods


def _source_structural_ast(source, *, helper):
    raw = source.decode("utf-8", errors="strict")
    need("\r" not in raw and all(ord(ch) <= 0xffff for ch in raw),
         "R146_UTF16_OR_NEWLINE_AST_OFFSETS_UNSUPPORTED")
    need(len(raw) <= 2_000_000, "R146_SOURCE_UNBOUNDED")
    javac, java = shutil.which("javac"), shutil.which("java")
    need(javac and java and helper.is_file() and not helper.is_symlink(),
         "R146_TRUSTED_JDK_HELPER_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r146-private-") as tmp:
        root = Path(tmp)
        input_file = root / "PrivateSource.java"
        input_file.write_bytes(source)
        classes = root / "trusted-helper"
        empty = root / "empty-classpath"
        classes.mkdir()
        empty.mkdir()
        environment = os.environ.copy()
        for key in ("CLASSPATH", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS",
                    "_JAVA_OPTIONS"):
            environment.pop(key, None)
        try:
            compile_tool = subprocess.run(
                [javac, "--release", "11", "-encoding", "UTF-8",
                 "-proc:none", "-classpath", str(empty),
                 "-sourcepath", str(empty),
                 "-d", str(classes), str(helper)],
                cwd=root, env=environment, stdin=subprocess.DEVNULL,
                capture_output=True, timeout=60, check=False)
            need(compile_tool.returncode == 0,
                 "R146_TRUSTED_JDK_AST_HELPER_DID_NOT_COMPILE")
            parsed = subprocess.run(
                [java, "-cp", str(classes),
                 "PrivatePacketStructuralSourceR146",
                 str(input_file), str(empty)],
                cwd=root, env=environment, stdin=subprocess.DEVNULL,
                capture_output=True, timeout=60, check=False)
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise PrivatePacketStructuralR146Error(
                "R146_SOURCE_AST_RUN_NOT_COMPLETED") from exc
        need(parsed.returncode == 0 and len(parsed.stdout) <= 200_000,
             "R146_PRIVATE_SOURCE_AST_REJECTED")
        try:
            rows = [row.split("\t") for row in
                    parsed.stdout.decode("utf-8", errors="strict").splitlines()]
        except UnicodeError as exc:
            raise PrivatePacketStructuralR146Error(
                "R146_PRIVATE_SOURCE_AST_NOT_UTF8") from exc
    need(all(len(row) in (2, 3) and row[0] in
             ("OWNER", "F", "M", "RSA") for row in rows),
         "R146_PRIVATE_SOURCE_AST_PROTOCOL_INVALID")
    owner = [x[1] for x in rows if x[0] == "OWNER"]
    fields, methods = Counter(), Counter()
    literals = []
    for row in rows:
        if row[0] in ("F", "M"):
            need(len(row) == 3 and row[1].isdigit()
                 and 0 <= int(row[1]) <= 2048,
                 "R146_JDK_SOURCE_MEMBER_FLAGS_INVALID")
            entry = (row[0], int(row[1]), row[2])
            if row[0] == "F":
                fields[entry] += 1
            else:
                methods[entry] += 1
        elif row[0] == "RSA":
            need(len(row) == 2 and re.fullmatch(r"[0-9]{1,512}", row[1]),
                 "R146_SOURCE_RSA_LITERAL_MALFORMED")
            literals.append(row[1])
    need(len(owner) == 1, "R146_JAVA_HAS_NOT_EXACT_ONE_OWNER")
    return owner[0], fields, methods, literals


def _rsa_literals(literals):
    return sorted(s for s in literals
                  if s == "65537" or _RSA_MODULUS.fullmatch(s))


def corroborate_private_packet_source(original_jar, source_zip, *,
                                     original_sha256=CANONICAL_V309,
                                     source_sha256,
                                     original_buffer="rs/x/e",
                                     source_file="rs/io/Packet.java",
                                     original_dependent="com/a/b/a/b"):
    """Output sanitized evidence, never an original↔source acceptance."""
    need(sha_file(original_jar) == original_sha256 and
         sha_file(source_zip) == source_sha256,
         "R146_PINNED_ORIGINAL_OR_SOURCE_ZIP_SHA_MISMATCH")
    candidates = dict(source_members(source_zip, source_sha256))
    need(source_file in candidates and source_file.endswith(".java"),
         "R146_CANDIDATE_JAVA_SOURCE_NOT_PRESENT")
    for identity in (original_buffer, original_dependent):
        need(identity and len(identity) <= 256 and
             not identity.startswith("/") and "\\" not in identity and
             all(s not in ("", ".", "..") for s in identity.split("/")),
             "R146_ORIGINAL_CLASS_OWNER_IDENTITY_UNSAFE")
    with ZipFile(original_jar) as archive:
        path_buffer = original_buffer + ".class"
        path_dependent = original_dependent + ".class"
        names = archive.namelist()
        need(path_buffer in names and path_dependent in names
             and len(names) == len(set(names)),
             "R146_ORIGINAL_CLASSES_MISSING_OR_DUPLICATE")
        raw_buffer, raw_dependent = (archive.read(path_buffer),
                                     archive.read(path_dependent))
    try:
        binary = parse_class(raw_buffer)
        dependent = parse_class(raw_dependent)
        calls = profile_class_constant_pool_references(raw_dependent)
    except (ClassFormatError, ValueError, KeyError) as exc:
        raise PrivatePacketStructuralR146Error(
            "R146_ORIGINAL_JVM_CLASSFILE_NOT_PARSEABLE") from exc
    need(binary.name == original_buffer and
         dependent.name == original_dependent and
         calls["internal_name"] == original_dependent,
         "R146_ORIGINAL_BINARY_CLASSFILE_IDENTITY_MISMATCH")
    linked = original_buffer in calls["class_references"]
    original_fields, original_methods = _member_shapes(binary)
    helper = (Path(__file__).resolve().parent / "java" /
              "PrivatePacketStructuralSourceR146.java")
    source_owner, source_fields, source_methods, rsa_java = (
        _source_structural_ast(candidates[source_file], helper=helper))
    source_owner_declared = source_file[:-5]
    need(source_owner == source_owner_declared,
         "R146_SOURCE_CLASS_PACKAGE_AND_FILENAME_DONT_MATCH")
    rsa_binary = _rsa_literals(binary.literal_strings)
    rsa_source = _rsa_literals(rsa_java)
    rsa_shape = (len(rsa_binary) == len(rsa_source) == 2 and
                 rsa_binary == rsa_source and
                 "65537" in rsa_binary and
                 len([x for x in rsa_binary if _RSA_MODULUS.fullmatch(x)]) == 1)
    matched_fields = sum((original_fields & source_fields).values())
    matched_methods = sum((original_methods & source_methods).values())
    full_member_shape = (
        matched_fields == sum(original_fields.values()) ==
        sum(source_fields.values()) and
        matched_methods == sum(original_methods.values()) ==
        sum(source_methods.values()))
    supported = bool(linked and rsa_shape and full_member_shape)
    result = {
        "schema_version": 1,
        "kind": "private_v309_original_buffer_candidate_source_shape_r146",
        "original_client_sha256": original_sha256,
        "candidate_client_source_zip_sha256": source_sha256,
        "private_original_buffer_class_sha256": _hash(raw_buffer),
        "private_original_dependent_class_sha256": _hash(raw_dependent),
        "candidate_java_file_sha256": _hash(candidates[source_file]),
        "original_class_major": binary.major,
        "original_field_count": sum(original_fields.values()),
        "candidate_field_count": sum(source_fields.values()),
        "field_access_and_erased_descriptor_shapes_common": matched_fields,
        "original_declared_method_and_constructor_count":
            sum(original_methods.values()),
        "candidate_declared_method_and_constructor_count":
            sum(source_methods.values()),
        "method_access_arity_and_erased_descriptor_shapes_common":
            matched_methods,
        "original_explicit_static_initializer_present":
            any(m["name"] == "<clinit>" for m in binary.methods),
        "full_erased_member_shape_multiset_match": full_member_shape,
        "original_exact_rsa_bigint_literal_pair_present":
            len(rsa_binary) == 2 and "65537" in rsa_binary,
        "candidate_exact_rsa_bigint_literal_pair_present":
            len(rsa_source) == 2 and "65537" in rsa_source,
        "original_and_source_rsa_bigint_literals_exactly_equal": rsa_shape,
        "rsa_literal_pair_sha256":
            _hash(("\n".join(rsa_binary)).encode("ascii"))
            if rsa_shape else None,
        "original_dependent_class_references_buffer": linked,
        "provisional_source_identity_structurally_corroborated":
            supported,
        "source_member_names_equivalent_to_original_verified": False,
        "original_bytecode_body_parity_verified": False,
        "source_and_original_runtime_behavior_equivalent": False,
        "source_to_original_inheritance_and_references_fully_mapped": False,
        "candidate_import_aliases_accepted": False,
        "game_linked_original_binary_classpath_fallback_allowed": False,
        "whole_client_compilation_accepted": False,
        "original_derived_code_release_authorized": False,
    }
    need(sha_file(original_jar) == original_sha256 and
         sha_file(source_zip) == source_sha256,
         "R146_PRIVATE_INPUT_CHANGED_DURING_SOURCE_CORROBORATION")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exact_private_original_v309_jar")
    parser.add_argument("private_decompiled_java_source_zip")
    parser.add_argument("fresh_private_sanitized_report")
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--original-sha256", default=CANONICAL_V309)
    parser.add_argument("--original-buffer", default="rs/x/e")
    parser.add_argument("--source-file", default="rs/io/Packet.java")
    parser.add_argument("--original-dependent", default="com/a/b/a/b")
    args = parser.parse_args(argv)
    out = Path(args.fresh_private_sanitized_report)
    try:
        need(not out.exists() and not out.is_symlink()
             and out.parent.is_dir() and not out.parent.is_symlink(),
             "R146_REPORT_MUST_BE_NEW")
        result = corroborate_private_packet_source(
            args.exact_private_original_v309_jar,
            args.private_decompiled_java_source_zip,
            source_sha256=args.source_sha256,
            original_sha256=args.original_sha256,
            original_buffer=args.original_buffer,
            source_file=args.source_file,
            original_dependent=args.original_dependent)
        out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                       encoding="utf-8")
        print("R146_PACKET_ORIGINAL_SOURCE_SHAPE_REPORT_PRIVATE_ONLY")
        print("private_report_sha256=" + sha_file(out))
    except Exception:
        parser.error("R146_PACKET_SOURCE_ORIGINAL_LINKAGE_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
