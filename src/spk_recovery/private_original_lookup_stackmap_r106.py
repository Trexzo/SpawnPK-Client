"""R106: exact one-frame v309 enum lookup StackMap reconciliation before R105/R95.

The original Java9 three-constant enum's case-insensitive lookup finishes in
a full_frame with zero locals/stack, while javac reproducing identical method
instructions may emit a valid chop_frame. R95 compares exact symbolic frames.
This tool changes ONLY the final StackMapTable frame representation (3 -> 7
bytes) when exact original/candidate signatures and preceding frames prove it.
No JVM method instruction, field, or literal value is changed. Then R105
strictly requires all-four original R95 method+metadata parity.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from zipfile import ZipFile

from .bytecode_profile import (
    BytecodeProfileError, _Reader, _constant_pool,
    _utf8, _class_name, profile_jar_class, profile_class_field_accesses,
)
from .private_original_owner_innerclasses_rebuilder_r103 import digest
from .private_original_synthetic_accessor_rebind_r105 import (
    SyntheticAccessorMemberRebindError,
    assemble_original_accessor_and_r95_candidate,
)


class OriginalEnumStackmapError(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise OriginalEnumStackmapError(reason)


def _frames(classfile, method_name, descriptor):
    r = _Reader(classfile)
    need(r.u4() == 0xCAFEBABE, "INVALID_JAVA_CLASSFILE_MAGIC")
    r.take(4)
    cp = _constant_pool(r)
    r.take(6)
    r.take(2 * r.u2())

    def attributes(reader):
        result = []
        for _ in range(reader.u2()):
            offset = reader.offset
            name = _utf8(cp, reader.u2())
            length = reader.u4()
            body = reader.take(length)
            result.append((name, body, offset))
        return result

    for _ in range(r.u2()):
        r.take(6)
        attributes(r)
    found = []
    for _ in range(r.u2()):
        access, name, desc = r.u2(), _utf8(cp, r.u2()), _utf8(cp, r.u2())
        attrs = attributes(r)
        if (name, desc) != (method_name, descriptor):
            continue
        need(access == 0x0009, "LOOKUP_MUST_BE_PUBLIC_STATIC")
        for attr, blob, code_offset in attrs:
            if attr != "Code":
                continue
            block = _Reader(blob)
            block.u2()
            block.u2()
            block.take(block.u4())
            block.take(8 * block.u2())
            nested = attributes(block)
            need(block.offset == len(blob),
                 "LOOKUP_CODE_ATTRIBUTE_NOT_EXACT")
            for subname, frames, nested_offset in nested:
                if subname == "StackMapTable":
                    found.append({
                        "cp": cp,
                        "code_attr_offset": code_offset,
                        "code_attr_length": len(blob),
                        "frames_offset_in_code": nested_offset,
                        "frames": frames,
                    })
    attributes(r)
    need(r.offset == len(classfile), "CLASSFILE_TRAILING_BYTES")
    need(len(found) == 1, "EXACT_LOOKUP_STACKMAPTABLE_NOT_UNIQUE")
    return found[0]


def original_three_constant_enum_lookup(original_jar, owner_entry):
    owner = owner_entry[:-6]
    with ZipFile(original_jar) as z:
        names = z.namelist()
        nested = sorted(
            n for n in names
            if n.startswith(owner + "$") and n.endswith(".class"))
        need(len(nested) == 4 and len(set(nested)) == 4,
             "FOUR_ORIGINAL_ENUM_CLASSFILES_REQUIRED")
    matches = []
    for entry in nested:
        p = profile_jar_class(original_jar, entry)
        enumname = p["internal_name"]
        constants = [
            f for f in p["fields"]
            if f.get("descriptor") == "L" + enumname + ";"
            and f.get("access") == 0x4019
        ]
        lookups = [
            m for m in p["methods"]
            if m.get("access") == 0x0009
            and m.get("descriptor") ==
                "(Ljava/lang/String;)L" + enumname + ";"
            and m.get("name") != "valueOf"
        ]
        if len(constants) == 3 and len(p["methods"]) == 6 and len(lookups) == 1:
            matches.append((entry, lookups[0]))
    need(len(matches) == 1,
         "ORIGINAL_THREE_CONSTANT_ENUM_CASE_INSENSITIVE_LOOKUP_NOT_UNIQUE")
    return matches[0]


def restore_single_original_lookup_frame(
    original_classfile, candidate_classfile, *,
    method_name, descriptor,
):
    old = _frames(original_classfile, method_name, descriptor)
    current = _frames(candidate_classfile, method_name, descriptor)
    left, right = old["frames"], current["frames"]
    # Three exact frame entries: append locals [enum array,int,int],
    # same frame at the branch merge, and terminal chop vs full_frame.
    need(len(left) == 18 and len(right) == 14
         and left[:5] == right[:5] == b"\x00\x03\xfe\x00\x09"
         and left[7:10] == right[7:10] == b"\x01\x01\x18"
         and left[-7:] == b"\xff\x00\x05\x00\x00\x00\x00"
         and right[-3:] == b"\xf8\x00\x05",
         "ORIGINAL_CANDIDATE_LOOKUP_FINAL_FRAME_NOT_REVIEWED_SHAPE")
    old_array_idx = int.from_bytes(left[5:7], "big")
    new_array_idx = int.from_bytes(right[5:7], "big")
    original_array = _class_name(old["cp"], old_array_idx)
    candidate_array = _class_name(current["cp"], new_array_idx)
    need(original_array == candidate_array and
         original_array == "[L" + descriptor[len("(Ljava/lang/String;)L"):-1] + ";",
         "ORIGINAL_ENUM_STACKMAP_ARRAY_TYPE_CHANGED")

    corrected_frames = right[:-3] + left[-7:]
    need(len(corrected_frames) - len(right) == 4,
         "UNEXPECTED_ORIGINAL_STACKMAP_BYTE_DELTA")
    code_start = current["code_attr_offset"]
    frame_start = code_start + 6 + current["frames_offset_in_code"] + 6
    code_length_index = code_start + 2
    frame_length_index = code_start + 6 + current["frames_offset_in_code"] + 2
    patched = bytearray(candidate_classfile)
    patched[code_length_index:code_length_index + 4] = (
        current["code_attr_length"] + 4).to_bytes(4, "big")
    patched[frame_length_index:frame_length_index + 4] = (
        len(corrected_frames)).to_bytes(4, "big")
    patched = (
        patched[:frame_start] + corrected_frames +
        patched[frame_start + len(right):]
    )
    rewritten = bytes(patched)
    verified = _frames(rewritten, method_name, descriptor)
    need(verified["frames"] == corrected_frames,
         "REBUILT_ORIGINAL_STACKMAP_FRAME_NOT_EXACT")
    before = profile_class_field_accesses(candidate_classfile)
    after = profile_class_field_accesses(rewritten)
    need(before["internal_name"] == after["internal_name"]
         and before["fields"] == after["fields"]
         and len(before["methods"]) == len(after["methods"]),
         "LOOKUP_NON_CODE_CLASS_CONTENT_MODIFIED")
    for m, n in zip(before["methods"], after["methods"]):
        need(m["name"] == n["name"]
             and m["descriptor"] == n["descriptor"]
             and m["access"] == n["access"]
             and m["instructions"] == n["instructions"]
             and m.get("max_stack") == n.get("max_stack")
             and m.get("max_locals") == n.get("max_locals"),
             "LOOKUP_JVM_INSTRUCTIONS_OR_CODE_SHAPE_CHANGED")
    return rewritten


def replay_original_enum_stackmap_and_all_four(
    original_jar, candidate_jar, owner_entry, surrogate_simple, output,
    *, original_sha256, candidate_sha256,
):
    original_jar, candidate_jar, output = map(
        Path, (original_jar, candidate_jar, output))
    need(output.parent.is_dir() and not output.parent.is_symlink()
         and not output.exists() and not output.is_symlink(),
         "NEW_PRIVATE_OUTPUT_REQUIRED")
    need(original_jar.resolve() != candidate_jar.resolve(),
         "ORIGINAL_AND_CANDIDATE_JAR_MUST_DIFFER")
    for path, pin in ((original_jar, original_sha256),
                      (candidate_jar, candidate_sha256)):
        need(path.is_file() and not path.is_symlink()
             and isinstance(pin, str)
             and re.fullmatch(r"[a-fA-F0-9]{64}", pin)
             and digest(path) == pin.lower(),
             "ORIGINAL_CANDIDATE_COMPLETE_SHA256_NOT_PINNED")
    need(isinstance(owner_entry, str) and owner_entry.endswith(".class")
         and not owner_entry.startswith("/")
         and "\\" not in owner_entry and
         all(x not in ("", ".", "..") for x in owner_entry.split("/")),
         "UNSAFE_ORIGINAL_OWNER_ENTRY")
    entry, original_method = original_three_constant_enum_lookup(
        original_jar, owner_entry)
    with ZipFile(original_jar) as original, ZipFile(candidate_jar) as candidate:
        names = candidate.namelist()
        need(len(names) == len(set(names)) and names.count(entry) == 1,
             "ORIGINAL_LOOKUP_ENUM_CANDIDATE_CLASS_MISSING")
        orig_bytes = original.read(entry)
        candidate_bytes = candidate.read(entry)
        descriptor = original_method["descriptor"]
        method_name = original_method["name"]
        prior = profile_class_field_accesses(candidate_bytes)
        lookup = [
            m for m in prior["methods"]
            if m.get("name") == method_name
            and m.get("descriptor") == descriptor
            and m.get("access") == 0x0009
        ]
        need(len(lookup) == 1
             and [x.get("opcode") for x in lookup[0]["instructions"]]
                == [x.get("opcode") for x in original_method["instructions"]],
             "LOOKUP_ORIGINAL_JVM_OPCODE_SEQUENCE_NOT_EXACT")
        patched_class = restore_single_original_lookup_frame(
            orig_bytes, candidate_bytes,
            method_name=method_name, descriptor=descriptor,
        )
        verified = profile_class_field_accesses(patched_class)
        fixed_method = [
            m for m in verified["methods"]
            if m["name"] == method_name
            and m["descriptor"] == descriptor
        ]
        need(len(fixed_method) == 1 and
             fixed_method[0].get("stackmap_frames")
                == original_method.get("stackmap_frames"),
             "ORIGINAL_LOOKUP_SYMBOLIC_STACKMAP_FRAMES_NOT_IDENTICAL")
        with tempfile.TemporaryDirectory(
            prefix="v309-original-stackmap-r106-", dir=output.parent,
        ) as temporary:
            root = Path(temporary)
            corrected_candidate = root / "stackmap-corrected.private.jar"
            with ZipFile(corrected_candidate, "w") as destination:
                for info in candidate.infolist():
                    need(not info.filename.startswith("/")
                         and "\\" not in info.filename
                         and all(x not in ("", ".", "..")
                                 for x in info.filename.split("/")),
                         "UNSAFE_CANDIDATE_CLASS_ARCHIVE_ENTRY")
                    contents = (
                        patched_class if info.filename == entry
                        else candidate.read(info))
                    destination.writestr(info, contents)
            patched_sha = digest(corrected_candidate)
            try:
                final = assemble_original_accessor_and_r95_candidate(
                    original_jar, corrected_candidate,
                    owner_entry, surrogate_simple, root / "r105",
                    original_sha256=original_sha256,
                    candidate_sha256=patched_sha,
                )
            except (SyntheticAccessorMemberRebindError, ValueError,
                    KeyError, IndexError, OSError) as exc:
                raise OriginalEnumStackmapError(
                    "R105_R95_FOUR_ORIGINAL_ENUM_ACCEPTANCE_FAILED") from exc
            need(final["all_four_original_nested_enums_R95_passed"] is True
                 and final["six_original_owner_InnerClasses_rows_equal"],
                 "ORIGINAL_R95_FOUR_ENUM_AND_OWNER_GATE_NOT_ACCEPTED")
            need(digest(original_jar) == original_sha256.lower()
                 and digest(candidate_jar) == candidate_sha256.lower()
                 and digest(corrected_candidate) == patched_sha,
                 "ORIGINAL_JARS_CHANGED_DURING_R106_ACCEPTANCE")
            report = {
                "schema_version": 1,
                "kind": "v309_private_exact_lookup_stackmap_and_four_enum_r95",
                "original_complete_jar_sha256": original_sha256.lower(),
                "original_compiled_source_candidate_sha256": candidate_sha256.lower(),
                "single_original_lookup_stackmap_reconciled": True,
                "original_four_enum_R95_passed": True,
                "exact_original_owner_six_InnerClasses_rows": 6,
                "original_executable_method_instructions_changed": False,
                "private_R95_accepted_candidate_sha256":
                    final["r95_accepted_candidate_sha256"],
                "R97_complete_126field_10method_owner_certified": False,
                "whole_client_runtime_equivalence_certified": False,
            }
            accepted = root / "accepted"
            accepted.mkdir()
            shutil.copyfile(
                root / "r105" / "all-four-R95-r105-accepted.private.jar",
                accepted / "all-four-original-enums-R95-r106.private.jar",
            )
            with (accepted / "original-four-enums-R106.aggregate.json").open(
                "x", encoding="utf-8", newline="\n",
            ) as stream:
                json.dump(report, stream, sort_keys=True, indent=2)
                stream.write("\n")
            need(not output.exists() and not output.is_symlink(),
                 "OUTPUT_OCCUPIED_BEFORE_R106_PROMOTION")
            os.rename(accepted, output)
            return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original_jar", "candidate_jar", "owner_entry",
                 "surrogate_simple", "new_private_output"):
        parser.add_argument(name)
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(replay_original_enum_stackmap_and_all_four(
            args.original_jar, args.candidate_jar, args.owner_entry,
            args.surrogate_simple, args.new_private_output,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
        ), sort_keys=True))
    except (OriginalEnumStackmapError, BytecodeProfileError,
            ValueError, OSError, EOFError):
        parser.error("PRIVATE_R106_ORIGINAL_FOUR_ENUM_R95_NOT_ACCEPTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
