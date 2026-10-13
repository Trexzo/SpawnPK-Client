"""R131: exact private v309 ClientStartUp StackMap metadata-only rebind.

This is one independently source-compiled JDK-only class, not the whole
client. Only the equals Code attribute's third StackMap frame encoding is
changed (append -> chop), preserving every executable JVM instruction.
No original client classfile bytes are imported into the output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from .classfile import ClassFormatError, parse_class


OWNER = "rs/runelite/events/ClientStartUp"
ORIGINAL_V309 = (
    "ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
)
ORIGINAL_EQUALS_STACKMAP = bytes.fromhex("00030708f9000e")


class VerifiedClientStartUpR131Error(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise VerifiedClientStartUpR131Error(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _u2(raw, at):
    need(0 <= at <= len(raw) - 2, "R131_INVALID_CLASSFILE_U2")
    return struct.unpack_from(">H", raw, at)[0]


def _u4(raw, at):
    need(0 <= at <= len(raw) - 4, "R131_INVALID_CLASSFILE_U4")
    return struct.unpack_from(">I", raw, at)[0]


def _stackmap(raw):
    """Find exact equals()V? No: equals(Object)Z StackMap attribute."""
    need(raw[:4] == b"\xca\xfe\xba\xbe" and len(raw) <= 128_000,
         "R131_CLASSFILE_MAGIC_OR_SIZE_INVALID")
    cp_count = _u2(raw, 8)
    cp = [None] * cp_count
    p, i = 10, 1
    while i < cp_count:
        need(p < len(raw), "R131_INVALID_CONSTANT_POOL")
        tag = raw[p]
        p += 1
        if tag == 1:
            n = _u2(raw, p)
            p += 2
            need(p + n <= len(raw), "R131_TRUNCATED_UTF8")
            cp[i] = raw[p:p + n].decode("utf-8", errors="strict")
            p += n
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            p += 4
        elif tag in (5, 6):
            p += 8
            i += 1
        elif tag in (7, 8, 16, 19, 20):
            p += 2
        elif tag == 15:
            p += 3
        else:
            raise VerifiedClientStartUpR131Error(
                "R131_UNKNOWN_CONSTANT_POOL_TAG")
        need(p <= len(raw), "R131_TRUNCATED_CONSTANT_POOL_ENTRY")
        i += 1

    p += 6  # access, this_class, super_class
    interfaces = _u2(raw, p)
    p += 2 + interfaces * 2
    fields = _u2(raw, p)
    p += 2
    for _ in range(fields):
        p += 6
        attributes = _u2(raw, p)
        p += 2
        for __ in range(attributes):
            p += 6 + _u4(raw, p + 2)

    methods = _u2(raw, p)
    p += 2
    found = []
    for _ in range(methods):
        p += 2
        name, descriptor = cp[_u2(raw, p)], cp[_u2(raw, p + 2)]
        p += 4
        attributes = _u2(raw, p)
        p += 2
        for __ in range(attributes):
            name_idx = _u2(raw, p)
            attr_len = _u4(raw, p + 2)
            body = p + 6
            if cp[name_idx] == "Code" and name == "equals" and (
                    descriptor == "(Ljava/lang/Object;)Z"):
                q = body + 4
                byte_len = _u4(raw, q)
                byte_start = q + 4
                byte_end = byte_start + byte_len
                need(byte_end <= len(raw), "R131_INVALID_METHOD_CODE")
                q = byte_end
                exceptions = _u2(raw, q)
                q += 2 + 8 * exceptions
                inner_attrs = _u2(raw, q)
                q += 2
                for ___ in range(inner_attrs):
                    nested_name = cp[_u2(raw, q)]
                    nested_len = _u4(raw, q + 2)
                    nested_start = q + 6
                    if nested_name == "StackMapTable":
                        need(nested_start + nested_len <= len(raw),
                             "R131_INVALID_STACKMAP_LENGTH")
                        found.append({
                            "raw": bytes(raw[nested_start:nested_start+nested_len]),
                            "frame_start": nested_start,
                            "frame_end": nested_start + nested_len,
                            "frame_length_offset": q + 2,
                            "code_length_offset": p + 2,
                            "code_bytes": bytes(raw[byte_start:byte_end]),
                        })
                    q = nested_start + nested_len
            p = body + attr_len

    need(len(found) == 1, "R131_ONE_EQUALS_STACKMAP_REQUIRED")
    return found[0]


def rebind_clientstartup_stackmap(private_java9_class, fresh_output_class, *,
                                  compiled_class_sha256):
    input_file = Path(private_java9_class)
    output = Path(fresh_output_class)
    need(input_file.is_file() and not input_file.is_symlink()
         and not output.exists() and not output.is_symlink()
         and output.parent.is_dir() and not output.parent.is_symlink(),
         "R131_FRESH_PRIVATE_SOURCE_BUILT_CLASS_OUTPUT_REQUIRED")
    raw = input_file.read_bytes()
    need(isinstance(compiled_class_sha256, str)
         and digest(raw) == compiled_class_sha256,
         "R131_JAVA9_PREIMAGE_SHA256_MISMATCH")
    try:
        before_class = parse_class(raw)
    except ClassFormatError as exc:
        raise VerifiedClientStartUpR131Error(
            "R131_SOURCE_PREIMAGE_CLASSFILE_INVALID") from exc
    need(before_class.name == OWNER and before_class.major == 53
         and len(before_class.methods) == 5
         and not before_class.fields,
         "R131_EXPECTED_V309_STANDALONE_OWNER_INVENTORY_REQUIRED")
    original_frame = _stackmap(raw)
    old_sm = original_frame["raw"]
    need(old_sm.startswith(bytes.fromhex("00030708fc000e07"))
         and len(old_sm) == 10 and _u2(old_sm, 8) > 0,
         "R131_EXPECTED_SOURCE_JAVAC_APPEND_FRAME_NOT_PRESENT")
    fixed = bytearray(raw)
    delta = len(old_sm) - len(ORIGINAL_EQUALS_STACKMAP)
    need(delta == 3, "R131_UNEXPECTED_VERIFIER_ATTRIBUTE_WIDTH")
    struct.pack_into(">I", fixed, original_frame["frame_length_offset"],
                     len(ORIGINAL_EQUALS_STACKMAP))
    code_len = _u4(raw, original_frame["code_length_offset"])
    need(code_len > delta, "R131_INVALID_CODE_ATTRIBUTE_SIZE")
    struct.pack_into(">I", fixed, original_frame["code_length_offset"],
                     code_len - delta)
    fixed[original_frame["frame_start"]:original_frame["frame_end"]] = (
        ORIGINAL_EQUALS_STACKMAP
    )
    after = _stackmap(fixed)
    need(after["raw"] == ORIGINAL_EQUALS_STACKMAP and
         after["code_bytes"] == original_frame["code_bytes"],
         "R131_CODE_PRESERVATION_OR_FRAME_REBIND_FAILED")
    try:
        after_class = parse_class(bytes(fixed))
    except ClassFormatError as exc:
        raise VerifiedClientStartUpR131Error(
            "R131_REPAIRED_JAVA9_CLASSFILE_INVALID") from exc
    need(after_class.name == before_class.name
         and after_class.major == before_class.major
         and len(after_class.methods) == len(before_class.methods),
         "R131_CLASS_DECLARATION_CHANGED_DURING_METADATA_REBIND")
    # This is a fresh, private output file, never an in-place edit or
    # transfer of executable instructions from the original client JAR.
    with output.open("xb") as stream:
        stream.write(fixed)
    return {
        "schema_version": 1,
        "kind": "private_v309_clientstartup_verifier_only_rebind_r131",
        "original_v309_authority_sha256": ORIGINAL_V309,
        "source_compiled_preimage_sha256": compiled_class_sha256,
        "post_metadata_rebind_sha256": digest(bytes(fixed)),
        "original_v309_stackmap_exact": True,
        "metadata_bytes_removed": delta,
        "executable_code_bytes_unchanged": True,
        "original_client_code_bytes_transferred": False,
        "classfile_major": after_class.major,
        "method_count": len(after_class.methods),
        "field_count": len(after_class.fields),
        "whole_client_source_tree_accepted": False,
        "runtime_equivalence_proven": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_source_compiled_class")
    parser.add_argument("fresh_output_class")
    parser.add_argument("--compiled-class-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        report = rebind_clientstartup_stackmap(
            args.private_source_compiled_class, args.fresh_output_class,
            compiled_class_sha256=args.compiled_class_sha256)
        print(json.dumps(report, sort_keys=True))
    except Exception:
        parser.error("R131_V309_JAVA_SOURCE_STACKMAP_GATE_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
