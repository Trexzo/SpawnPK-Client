"""R106: normalize one proven original-v309 enum StackMapTable encoding.

Original v309 Java9 case-insensitive enum lookup has full_frame(5, [], [])
where an opcode/operand-exact javac9 reconstruction emits chop_frame(5).
Rebuild just that candidate verification-table frame, never Code bytes.
Then require the COMPLETE R105 -> R104 -> R95 private acceptance gate.

This is not a substitute for R95, source authorship or client runtime proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from zipfile import ZipFile

from .bytecode_profile import (
    _Reader, _constant_pool, _utf8, _class_name, profile_jar_class,
)
from .private_four_nested_enum_acceptance import nested_entries
from .private_original_synthetic_accessor_rebind_r105 import (
    SyntheticAccessorMemberRebindError,
    assemble_original_accessor_and_r95_candidate,
)
from .private_original_fourth_enum_accessors import digest


class VerifiedEnumStackMapError(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise VerifiedEnumStackMapError(reason)


def u2(value):
    need(type(value) is int and 0 <= value < 65536, "CLASSFILE_U2_INVALID")
    return value.to_bytes(2, "big")


def u4(value):
    need(type(value) is int and 0 <= value < 4294967296,
         "CLASSFILE_U4_INVALID")
    return value.to_bytes(4, "big")


def _lookup_descriptor(binary):
    return "(Ljava/lang/String;)L" + binary + ";"


def _lookup_method(profile):
    binary = profile.get("internal_name")
    need(isinstance(binary, str) and "$" in binary and
         profile.get("classfile_major") == 53 and
         profile.get("super_name") == "java/lang/Enum",
         "ORIGINAL_LOOKUP_JAVA9_ENUM_CLASS_REQUIRED")
    matches = [m for m in profile.get("methods", [])
               if m.get("access") == 9
               and m.get("descriptor") == _lookup_descriptor(binary)
               and m.get("name") != "valueOf"]
    need(len(matches) == 1 and len(profile.get("methods", [])) == 6,
         "EXACT_SIX_METHOD_THREE_VALUE_LOOKUP_ENUM_NOT_UNIQUE")
    m = matches[0]
    need(len(m.get("instructions", [])) == 25,
         "LOOKUP_25_OPCODE_INSTRUCTIONS_REQUIRED")
    return m


def find_original_case_insensitive_enum(original_jar, candidate_jar, owner_entry):
    with ZipFile(original_jar) as a, ZipFile(candidate_jar) as b:
        entries = nested_entries(a.namelist(), owner_entry)
        others = [name for name in entries
                  if name in b.namelist()
                  and name != (owner_entry[:-6] + "$" +
                               owner_entry[:-6].rsplit("/", 1)[-1] + ".class")]
    matches = []
    for entry in others:
        orig = profile_jar_class(original_jar, entry)
        cand = profile_jar_class(candidate_jar, entry)
        try:
            mo, mc = _lookup_method(orig), _lookup_method(cand)
        except VerifiedEnumStackMapError:
            continue
        if mo["name"] == mc["name"] and mo["descriptor"] == mc["descriptor"]:
            matches.append((entry, orig, cand, mo, mc))
    need(len(matches) == 1,
         "UNIQUE_ORIGINAL_THREE_VALUE_CASE_INSENSITIVE_ENUM_NOT_FOUND")
    return matches[0]


def _frame_shape_only(payload, expected_final):
    """Strict original/surrogate three-frame evidence, without CP aliasing.

    Candidate: append3(9, object,self-array,int,int), same(24), chop3(5).
    Original:  append3(9, object,self-array,int,int), same(24),
               full(5, zero locals, zero stack).
    """
    r = _Reader(payload)
    need(r.u2() == 3 and r.u1() == 254 and r.u2() == 9
         and r.u1() == 7,
         "EXPECTED_FIRST_APPEND_THREE_FRAME_MISSING")
    object_cp = r.u2()
    need(object_cp > 0 and r.u1() == 1 and r.u1() == 1
         and r.u1() == 24,
         "APPEND_THREE_AND_SAME_FRAME_SHAPE_CHANGED")
    flag = r.u1()
    if expected_final == "chop":
        need(flag == 248 and r.u2() == 5,
             "SOURCE_JAVAC_CHOP_FRAME_NOT_EXACT")
    else:
        need(flag == 255 and r.u2() == 5 and
             r.u2() == 0 and r.u2() == 0,
             "ORIGINAL_FINAL_FULL_FRAME_NOT_EXACT")
    need(r.offset == len(payload), "UNEXPECTED_STACKMAP_EXTRA_FRAMES")
    return object_cp


def _class_method_layout(data):
    r = _Reader(data)
    need(r.u4() == 0xCAFEBABE, "INVALID_JVM_CLASSFILE_MAGIC")
    r.take(4)
    cp = _constant_pool(r)
    r.take(6)  # flags, this class, super class
    r.take(2 * r.u2())
    for _ in range(r.u2()):
        r.take(6)
        for __ in range(r.u2()):
            r.take(2)
            r.take(r.u4())
    method_header = r.offset
    method_count = r.u2()
    result = []
    for _ in range(method_count):
        start = r.offset
        access, name, descriptor = r.u2(), r.u2(), r.u2()
        attributes = []
        for __ in range(r.u2()):
            aidx = r.u2()
            body = r.take(r.u4())
            attributes.append((aidx, _utf8(cp, aidx), body))
        result.append((access, _utf8(cp, name),
                       _utf8(cp, descriptor), data[start:r.offset],
                       attributes, start))
    return cp, method_header, r.offset, method_count, result


def _extract_lookup_stackmap(data, descriptor, name):
    cp, start, end, n, methods = _class_method_layout(data)
    matches = [(attrs, m) for access, nme, desc, m, attrs, _ in methods
               if nme == name and desc == descriptor and access == 9]
    need(len(matches) == 1, "TARGET_LOOKUP_METHOD_NOT_UNIQUE_IN_CLASSFILE")
    for attr_index, label, body in matches[0][0]:
        if label != "Code":
            continue
        r = _Reader(body)
        stack = r.u2()
        locals_ = r.u2()
        code = r.take(r.u4())
        exceptions = r.take(8 * r.u2())
        for _ in range(r.u2()):
            idx = r.u2()
            raw = r.take(r.u4())
            if _utf8(cp, idx) == "StackMapTable":
                return raw, code, stack, locals_, cp
    raise VerifiedEnumStackMapError("CODE_STACKMAP_TABLE_REQUIRED")


def _rewrite_code_stackmap(body, cp):
    r = _Reader(body)
    prefix = r.take(4)
    code = r.take(r.u4())
    exceptions_count = r.u2()
    exceptions = r.take(8 * exceptions_count)
    n = r.u2()
    subs = []
    changed = 0
    for _ in range(n):
        attr = r.u2()
        raw = r.take(r.u4())
        if _utf8(cp, attr) == "StackMapTable":
            obj_cp = _frame_shape_only(raw, "chop")
            need(cp[obj_cp][0] == 7,
                 "SOURCE_APPEND_FRAME_NOT_JVM_REFERENCE_TYPE")
            # Replace only frame #3. Reconstruct original's semantically
            # equivalent full_frame; never copy bytes from original Code.
            raw = raw[:-3] + bytes.fromhex("ff000500000000")
            _frame_shape_only(raw, "full")
            changed += 1
        subs.append((attr, raw))
    need(r.offset == len(body) and changed == 1,
         "EXACT_ONE_CASE_INSENSITIVE_STACKMAP_REWRITE_REQUIRED")
    out = bytearray(prefix + u4(len(code)) + code +
                    u2(exceptions_count) + exceptions + u2(n))
    for attr, raw in subs:
        out.extend(u2(attr) + u4(len(raw)) + raw)
    return bytes(out), code


def normalize_one_enum_stackmap(classfile, method_name, method_descriptor,
                                original_classfile):
    orig_frame, orig_code, orig_stack, orig_locals, orig_cp = (
        _extract_lookup_stackmap(original_classfile,
                                 method_descriptor, method_name))
    old_cp_index = _frame_shape_only(orig_frame, "full")
    need(orig_cp[old_cp_index][0] == 7 and
         _class_name(orig_cp, old_cp_index) ==
             "[" + method_descriptor.split(")", 1)[1],
         "ORIGINAL_APPEND_VERIFICATION_TYPE_NOT_SELF_ARRAY")
    candidate_frame, cand_code, cand_stack, cand_locals, cand_cp = (
        _extract_lookup_stackmap(classfile,
                                 method_descriptor, method_name))
    cand_cp_index = _frame_shape_only(candidate_frame, "chop")
    need(cand_cp[cand_cp_index][0] == 7
         and _class_name(cand_cp, cand_cp_index) ==
             "[" + method_descriptor.split(")", 1)[1]
         and orig_stack == cand_stack
         and orig_locals == cand_locals
         and len(orig_code) == len(cand_code),
         "ORIGINAL_AND_CANDIDATE_LOOKUP_CODE_FRAME_SHAPES_DIFFER")
    cp, start, end, n, methods = _class_method_layout(classfile)
    rebuilt = bytearray(classfile[:start] + u2(n))
    changes = 0
    for access, name, desc, raw, attrs, offset in methods:
        header = _Reader(raw)
        header_bytes = header.take(8)
        rebuilt.extend(header_bytes)
        for attr_idx, attr_name, data in attrs:
            if (name == method_name and desc == method_descriptor
                    and access == 9 and attr_name == "Code"):
                data, code = _rewrite_code_stackmap(data, cp)
                need(code == cand_code,
                     "CANDIDATE_CODE_CHANGED_DURING_FRAME_REWRITE")
                changes += 1
            rebuilt.extend(u2(attr_idx) + u4(len(data)) + data)
    rebuilt.extend(classfile[end:])
    need(changes == 1, "EXACT_ONE_JVM_LOOKUP_CODE_ATTRIBUTE_REQUIRED")
    new_data = bytes(rebuilt)
    new_frame, updated_code, new_stack, new_locals, new_cp = (
        _extract_lookup_stackmap(new_data, method_descriptor, method_name))
    _frame_shape_only(new_frame, "full")
    need(updated_code == cand_code and
         new_stack == cand_stack and new_locals == cand_locals,
         "ORIGINAL_SOURCE_CANDIDATE_JVM_CODE_NOT_PRESERVED")
    return new_data


def repair_then_require_r105_r95(
    original_jar, candidate_jar, owner_entry, surrogate_simple, output, *,
    original_sha256, candidate_sha256,
):
    original_jar, candidate_jar, output = map(
        Path, (original_jar, candidate_jar, output))
    need(not output.exists() and not output.is_symlink()
         and output.parent.is_dir() and not output.parent.is_symlink(),
         "PRIVATE_OUTPUT_ALREADY_EXISTS")
    for path, pin in ((original_jar, original_sha256),
                      (candidate_jar, candidate_sha256)):
        need(path.is_file() and not path.is_symlink() and
             isinstance(pin, str) and
             re.fullmatch("[0-9a-fA-F]{64}", pin) and
             digest(path) == pin.lower(),
             "ORIGINAL_OR_CANDIDATE_JAR_PIN_MISMATCH")
    entry, o_profile, c_profile, mo, mc = find_original_case_insensitive_enum(
        original_jar, candidate_jar, owner_entry)
    need(mo["name"] == mc["name"]
         and mo["access"] == mc["access"]
         and [x.get("opcode") for x in mo["instructions"]] ==
             [x.get("opcode") for x in mc["instructions"]],
         "ORIGINAL_AND_SOURCE_CASE_INSENSITIVE_OPCODES_MISMATCH")
    with ZipFile(original_jar) as source, ZipFile(candidate_jar) as candidate:
        fixed = normalize_one_enum_stackmap(
            candidate.read(entry), mc["name"],
            mc["descriptor"], source.read(entry))
        # Verify decoded stackmap semantic/encoding fidelity independently
        # once the temporary candidate JAR can be reprofiled.
        with tempfile.TemporaryDirectory(
            prefix="v309-r106-frame-", dir=output.parent,
        ) as temp:
            root = Path(temp)
            patch = root / "javac-four-enums-frame-normalized.private.jar"
            with ZipFile(patch, "w") as dest:
                for info in candidate.infolist():
                    dest.writestr(info, fixed if info.filename == entry
                                  else candidate.read(info))
            normalized_profile = profile_jar_class(patch, entry)
            after = _lookup_method(normalized_profile)
            need(after.get("stackmap_frames") == mo.get("stackmap_frames"),
                 "ORIGINAL_LOOKUP_STACKMAP_FRAMES_STILL_NOT_EXACT")
            need([x.get("opcode") for x in after["instructions"]] ==
                 [x.get("opcode") for x in mc["instructions"]],
                 "PRIVATE_SOURCE_METHOD_OPCODE_SEQUENCE_CHANGED")
            fixed_pin = digest(patch)
            try:
                result = assemble_original_accessor_and_r95_candidate(
                    original_jar, patch, owner_entry, surrogate_simple,
                    root / "r105", original_sha256=original_sha256,
                    candidate_sha256=fixed_pin)
            except (SyntheticAccessorMemberRebindError,
                    OSError, ValueError, IndexError, KeyError) as exc:
                raise VerifiedEnumStackMapError(
                    "ORIGINAL_PRIVATE_R105_R104_R95_REPLAY_NOT_ACCEPTED") from exc
            need(result.get("all_four_original_nested_enums_R95_passed") is True,
                 "FOUR_ORIGINAL_ENUMS_R95_GATE_NOT_CONFIRMED")
            need(digest(original_jar) == original_sha256.lower()
                 and digest(candidate_jar) == candidate_sha256.lower()
                 and digest(patch) == fixed_pin,
                 "PINNED_CLIENTS_CHANGED_DURING_FRAME_ACCEPTANCE")
            report = {
                "schema_version": 1,
                "kind": "private_v309_javac9_stackmap_fixed_all_four_R95",
                "original_complete_jar_sha256": original_sha256.lower(),
                "original_source_candidate_sha256": candidate_sha256.lower(),
                "normalized_four_enum_candidate_sha256": fixed_pin,
                "r95_accepted_candidate_sha256":
                    result["r95_accepted_candidate_sha256"],
                "original_case_insensitive_lookup_method_frames_identical": True,
                "original_lookups_method_code_bytes_transferred": False,
                "candidate_method_code_bytes_preserved": True,
                "original_four_nested_enums_R95_accepted": True,
                "R97_outer_owner_126field_10method_gate_passed": False,
                "whole_client_runtime_equivalence_certified": False,
            }
            accepted = root / "accepted"
            accepted.mkdir()
            shutil.copyfile(
                root / "r105" / "all-four-R95-r105-accepted.private.jar",
                accepted / "all-four-R95-after-StackMap.private.jar")
            with (accepted / "R106-stackmap-R95.aggregate.json").open(
                "x", encoding="utf-8", newline="\n"
            ) as f:
                json.dump(report, f, indent=2, sort_keys=True)
                f.write("\n")
            need(not output.exists(), "PRIVATE_RESULT_OCCUPIED_AFTER_GATE")
            os.rename(accepted, output)
            return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("original_jar", "candidate_jar", "owner_entry",
                 "surrogate_simple", "new_private_output"):
        p.add_argument(name)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    a = p.parse_args(argv)
    try:
        result = repair_then_require_r105_r95(
            a.original_jar, a.candidate_jar, a.owner_entry,
            a.surrogate_simple, a.new_private_output,
            original_sha256=a.original_sha256,
            candidate_sha256=a.candidate_sha256)
        print(json.dumps(result, sort_keys=True))
    except (VerifiedEnumStackMapError, OSError, ValueError):
        p.error("PRIVATE_R106_ORIGINAL_STACKMAP_AND_R95_NOT_ACCEPTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
