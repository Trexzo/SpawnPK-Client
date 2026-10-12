"""R70: exact original-v309 Java IOException catch and File/Properties envelope.

The original method's TWO IOException exception-table entries arise when an
ordinary Java try block encloses a file-exists early return. Prove original
protected start/end bytecode boundaries, shared IOException handler and
actual printStackTrace body, then emit a PRIVATE method-body source envelope
containing R69's genuine prefix. The 697-op inner method remains incomplete.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _digest, _instructions,
)
from .properties_load_prefix_source import (
    PropertiesPrefixSourceError, plan_original_properties_method_prefix,
)


class OuterIoSourceError(ValueError):
    """Original Java IOException envelope not exactly proved."""


_SHA = re.compile(r"[a-f0-9A-F]{64}\Z")


def _need(ok: bool, why: str) -> None:
    if not ok:
        raise OuterIoSourceError(why)


def plan_original_outer_io_source_envelope(
    original: dict, method_name: str, descriptor: str,
) -> dict:
    prefix = plan_original_properties_method_prefix(
        original, method_name, descriptor
    )
    methods = [
        m for m in original.get("methods", [])
        if m.get("name") == method_name
        and m.get("descriptor") == descriptor
    ]
    _need(len(methods) == 1, "PRIVATE_ORIGINAL_METHOD_NOT_UNIQUE")
    method = methods[0]
    rows = _instructions(method)
    _need(len(rows) >= 29, "ORIGINAL_JVM_METHOD_TOO_SHORT")
    last = rows[-5:]
    _need([r.get("opcode") for r in last]
          == ["0xa7", "0x4b", "0x2a", "0xb6", "0xb1"],
          "ORIGINAL_IO_CATCH_TAIL_NOT_EXACT_GOTO_ASTORE_ALOAD_INVOKE_RETURN")
    _need(last[0].get("branch_target_offset") == last[-1]["offset"],
          "ORIGINAL_NORMAL_IO_PATH_NOT_BYPASSING_CATCH")
    _need(all(a["offset"] + a["length"] == b["offset"]
              for a,b in zip(last,last[1:])),
          "ORIGINAL_IO_CATCH_INSTRUCTION_GAP")
    _need(last[3].get("owner") == "java/io/IOException"
          and last[3].get("name") == "printStackTrace"
          and last[3].get("descriptor") == "()V",
          "ORIGINAL_IO_EXCEPTION_HANDLER_SIDE_EFFECT_NOT_PRINTSTACKTRACE")
    handlers=method.get("exception_handlers")
    _need(isinstance(handlers,list),
          "ORIGINAL_EXCEPTION_TABLE_MISSING")
    io=[
        h for h in handlers
        if h.get("catch_type") == "java/io/IOException"
    ]
    _need(len(io)==2,
          "EXACT_TWO_ORIGINAL_IO_EXCEPTION_REGIONS_REQUIRED")
    # JVM protected ranges are split at the early return at row9.
    # The first runs from new File to before return, the second from
    # new Properties to before the final goto across the handler.
    expected=(
        (rows[1]["offset"],rows[9]["offset"],last[1]["offset"]),
        (rows[10]["offset"],last[0]["offset"],last[1]["offset"]),
    )
    original_regions=tuple(
        (h.get("start_pc"),h.get("end_pc"),h.get("handler_pc"))
        for h in io
    )
    _need(original_regions==expected,
          "ORIGINAL_TWO_IO_PROTECTED_RANGES_OR_SHARED_HANDLER_NOT_EXACT")
    # Nothing outside the explicit handler may jump into the catch body.
    caught=last[1]["offset"]
    _need(all(row.get("branch_target_offset") != caught
              for row in rows if "branch_target_offset" in row),
          "UNACCOUNTED_NORMAL_BRANCH_INTO_IO_EXCEPTION_CATCH")
    private_prefix=prefix["private_source_prefix"]
    lines=[
        line for line in private_prefix.splitlines()
        if line.strip() and not line.startswith("//")
    ]
    _need(len(lines)==7 and "originalLocalSlot1 = " in lines[3],
          "R69_ORIGINAL_PRIVATE_PREFIX_NOT_SOURCE_SPLIT_READY")
    source=(
        "// PRIVATE original-v309 Java method-body prefix + IOException envelope.\n"
        "// OTHER original instructions between load/close and catch UNRECOVERED.\n"
        + lines[0] + "\n"
        + "    try {\n"
        + "".join("    "+line+"\n" for line in lines[1:])
        + "        // UNRECOVERED original protected JVM body: NOT ASSUMED EMPTY.\n"
        + "    } catch (java.io.IOException originalIOException) {\n"
        + "        originalIOException.printStackTrace();\n"
        + "    }\n"
    )
    return {
        "private_outer_io_source_envelope":source,
        "original_whole_method_instruction_count":len(rows),
        "original_io_typed_exception_handler_entries":len(io),
        "shared_original_io_handler_target":True,
        "original_first_io_range_early_return_boundary_exact":True,
        "original_second_io_range_after_prefix_and_before_final_goto_exact":True,
        "original_io_catch_calls_printStackTrace_once":True,
        "original_normal_path_skips_io_exception_handler":True,
        "source_R69_properties_prefix_integrated":True,
        "original_internal_protected_method_body_recovered":False,
        "whole_original_io_try_catch_source_compiled_and_compared":False,
        "remaining_original_method_helper_side_effects_proved":False,
        "complete_client_runtime_equivalence_certified":False,
    }


def recover_private_outer_io_envelope(
    original_jar:Path,original_class_entry:str,
    method_name:str,descriptor:str,out:Path,*,sha256:str
)->dict:
    jar,dest=Path(original_jar),Path(out)
    _need(not dest.exists() and not dest.is_symlink(),
          "OUTPUT_ALREADY_EXISTS")
    _need(type(sha256) is str
          and _SHA.fullmatch(sha256) is not None,
          "INVALID_COMPLETE_ORIGINAL_JAR_SHA256")
    _need(jar.is_file() and not jar.is_symlink(),
          "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _need(_digest(jar)==sha256.lower(),
          "ORIGINAL_JAR_SHA256_MISMATCH")
    _need(type(original_class_entry) is str
          and original_class_entry.endswith(".class")
          and not original_class_entry.startswith("/")
          and "\\" not in original_class_entry
          and all(x not in ("",".","..") and ":" not in x
                  for x in original_class_entry.split("/")),
          "INVALID_PRIVATE_ORIGINAL_CLASS_ENTRY")
    try:
        with ZipFile(jar) as archive:
            _need(archive.namelist().count(original_class_entry)==1,
                  "ORIGINAL_CLASS_ENTRY_NOT_UNIQUE")
            original=profile_jar_class(jar,original_class_entry)
        report=plan_original_outer_io_source_envelope(
            original,method_name,descriptor)
    except (OSError,BadZipFile,BytecodeProfileError,
            ScalarInitializerRecoveryError,PropertiesPrefixSourceError,
            KeyError,IndexError,TypeError):
        raise OuterIoSourceError(
            "ORIGINAL_OUTER_IO_EXCEPTION_ENVELOPE_NOT_VERIFIABLE"
        ) from None
    _need(_digest(jar)==sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_IO_SOURCE_RECOVERY")
    source=report.pop("private_outer_io_source_envelope")
    aggregate={
        "schema_version":1,
        "kind":"original_v309_private_properties_and_io_catch_source_envelope",
        "original_complete_jar_sha256":sha256.lower(),
        "private_method_source_envelope_sha256":
            hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "research_only":True,
        **report,
    }
    dest.mkdir(parents=True,exist_ok=False)
    with (dest/"outer-io-envelope.private.java.txt").open(
        "x",encoding="utf-8",newline="\n"
    ) as fd:fd.write(source)
    with (dest/"outer-io-envelope.aggregate.json").open(
        "x",encoding="utf-8",newline="\n"
    ) as fd:json.dump(aggregate,fd,sort_keys=True,indent=2);fd.write("\n")
    return aggregate


def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar",type=Path)
    p.add_argument("private_original_class_entry")
    p.add_argument("private_method_name")
    p.add_argument("private_method_descriptor")
    p.add_argument("new_private_output",type=Path)
    p.add_argument("--sha256",required=True)
    args=p.parse_args(argv)
    try:
        print(json.dumps(recover_private_outer_io_envelope(
            args.original_jar,args.private_original_class_entry,
            args.private_method_name,args.private_method_descriptor,
            args.new_private_output,sha256=args.sha256,
        ),sort_keys=True))
    except OuterIoSourceError as exc:
        p.error(str(exc))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
