"""R80: private ordered candidate for the original v309 697-op method.

Strictly compose R79's proven 48-op source prefix and the 42 original local
Exception protected source fragments under R70's IOException envelope.
This is NOT a compile pass, bytecode parity acceptance, or runtime proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from .bytecode_profile import profile_jar_class
from .mutable_scalar_initializer_source import _digest, _instructions
from .private_local_coverage import (
    FAMILIES, LocalCoverageError, need, verify_local_site_inventory,
)
from .properties_48_prefix_source import plan_private_original_48_op_prefix
from .outer_io_exception_envelope import plan_original_outer_io_source_envelope


def plan_original_private_method_candidate(
    profile: dict, method_name: str, descriptor: str,
    family_sites: dict[str, list[dict]],
) -> dict:
    """Reconstruct candidate method-body *text*, failing closed on JVM gaps."""
    proof = verify_local_site_inventory(profile, method_name, descriptor, family_sites)
    prefix = plan_private_original_48_op_prefix(profile, method_name, descriptor)
    io = plan_original_outer_io_source_envelope(profile, method_name, descriptor)
    method = [m for m in profile["methods"]
              if m.get("name") == method_name and m.get("descriptor") == descriptor]
    need(len(method) == 1, "EXPECTED_UNIQUE_ORIGINAL_METHOD")
    rows = _instructions(method[0])
    need(len(rows) == 697 and len(method[0].get("exception_handlers", [])) == 44,
         "ORIGINAL_COMPLEX_METHOD_STRUCTURE_DRIFT")
    positions = {row["offset"]: i for i, row in enumerate(rows)}
    need(len(positions) == 697, "DUPLICATE_JVM_OFFSETS")
    sites = []
    for family, (_count, a, b, c, source) in FAMILIES.items():
        for site in family_sites[family]:
            sites.append((
                positions[site[a]], positions[site[b]], positions[site[c]],
                family, site[source]
            ))
    sites.sort(key=lambda r: r[0])
    need(len(sites) == 42 and sites[0][0] == 48,
         "ORIGINAL_FIRST_PROTECTED_SITE_NOT_AFTER_48_PREFIX")

    # In the exact original each local try body is immediately followed by
    # a GOTO over exactly one ASTORE_3 catch handler. No other inter-site
    # JVM instruction can be silently discarded.
    cursor = 48
    body_instructions = 0
    catch_instructions = 0
    skip_gotos = 0
    for start, end, caught, _family, _source in sites:
        need(start == cursor, "UNACCOUNTED_INTER_REGION_INSTRUCTION")
        need(end > start and caught == end + 1 and caught + 1 < len(rows),
             "ORIGINAL_LOCAL_TRY_CATCH_LAYOUT_DRIFT")
        skip, catch = rows[end], rows[caught]
        need(skip.get("opcode") == "0xa7"
             and catch.get("opcode") == "0x4e"
             and skip.get("branch_target_offset") == rows[caught + 1]["offset"],
             "ORIGINAL_EXCEPTION_SEPARATOR_NOT_GOTO_ASTORE3")
        body_instructions += end - start
        catch_instructions += 1
        skip_gotos += 1
        cursor = caught + 1

    need(cursor == 692, "LAST_LOCAL_CATCH_NOT_BEFORE_FIVE_OP_TAIL")
    tail = rows[cursor:]
    need(len(tail) == 5
         and [x.get("opcode") for x in tail]
         == ["0xa7", "0x4b", "0x2a", "0xb6", "0xb1"]
         and tail[0].get("branch_target_offset") == tail[-1]["offset"],
         "ORIGINAL_FIVE_INSTRUCTION_IO_EPILOGUE_DRIFT")
    need(48 + body_instructions + catch_instructions + skip_gotos + 5 == 697,
         "ORIGINAL_WHOLE_METHOD_INSTRUCTION_PARTITION_INCOMPLETE")
    need(body_instructions == 560
         and catch_instructions == 42 and skip_gotos == 42,
         "ORIGINAL_560_42_42_COUNTS_DRIFT")

    # R79's exact 48-op original Java source has 11 non-comment statements:
    # one preflight outside the outer IO try and 10 inside it. R70 supplies
    # the genuine IOException printStackTrace control-flow envelope proof.
    raw_prefix = prefix["private_original_48_instruction_java_source"]
    meaningful = [line.strip() for line in raw_prefix.splitlines()
                  if line.strip() and not line.lstrip().startswith("//")]
    need(len(meaningful) == 11 and meaningful[0].endswith("();")
         and "originalLocalSlot1 = " in meaningful[3],
         "ORIGINAL_48_PREFIX_NOT_METHOD_STITCH_READY")
    need(io.get("original_io_typed_exception_handler_entries") == 2
         and io.get("original_io_catch_calls_printStackTrace_once") is True,
         "ORIGINAL_IO_EXCEPTION_ENVELOPE_NOT_PROVEN")

    protected_sources = [source.strip() for _, _, _, _, source in sites]
    method_text = (
        "    " + meaningful[0] + "\n"
        "    try {\n"
        + "".join("        " + line + "\n" for line in meaningful[1:])
        + "".join("        " + source.replace("\n", "\n        ") + "\n"
                  for source in protected_sources)
        + "    } catch (java.io.IOException originalIOException) {\n"
        "        originalIOException.printStackTrace();\n"
        "    }\n"
    )
    return {
        "private_java_method_body_candidate": method_text,
        "original_jvm_instructions_accounted_for": 697,
        "original_prefix_instructions": 48,
        "original_local_protected_body_instructions": body_instructions,
        "original_local_catch_entry_instructions": catch_instructions,
        "original_local_skip_goto_instructions": skip_gotos,
        "original_outer_tail_instructions": 5,
        "original_local_typed_exception_entries": 42,
        "original_outer_io_exception_entries": 2,
        "original_ordered_local_source_fragment_count": len(protected_sources),
        "candidate_has_been_compiled_against_original_dependencies": False,
        "original_whole_method_cfg_parity_passed": False,
        "original_operand_and_helper_side_effect_parity_passed": False,
        "original_authorial_java_source_certified": False,
        "original_client_runtime_equivalence_certified": False,
    }


def replay_private_method_candidate(
    jar: Path, class_entry: str, method: str, descriptor: str,
    site_files: dict[str, Path], output: Path, original_sha256: str,
) -> dict:
    jar, output = Path(jar), Path(output)
    need(not output.exists() and not output.is_symlink(), "OUTPUT_ALREADY_EXISTS")
    need(isinstance(original_sha256, str) and len(original_sha256) == 64
         and all(c in "0123456789abcdefABCDEF" for c in original_sha256),
         "INVALID_ORIGINAL_JAR_SHA256")
    need(jar.is_file() and not jar.is_symlink()
         and _digest(jar) == original_sha256.lower(),
         "ORIGINAL_WHOLE_JAR_SHA256_MISMATCH")
    need(isinstance(class_entry, str) and class_entry.endswith(".class")
         and not class_entry.startswith("/") and "\\" not in class_entry
         and all(part not in ("", ".", "..") and ":" not in part
                 for part in class_entry.split("/")),
         "INVALID_PRIVATE_ORIGINAL_CLASS_ENTRY")
    need(set(site_files) == set(FAMILIES), "ALL_EIGHT_SOURCE_FAMILIES_REQUIRED")
    with ZipFile(jar) as archive:
        need(archive.namelist().count(class_entry) == 1,
             "ORIGINAL_CLASSFILE_NOT_UNIQUE")
    profile = profile_jar_class(jar, class_entry)
    family_sites = {}
    for family, path in site_files.items():
        path = Path(path)
        need(path.is_file() and not path.is_symlink()
             and path.stat().st_size <= 16 * 1024 * 1024,
             "PRIVATE_FAMILY_INPUT_INVALID_" + family)
        family_sites[family] = json.loads(path.read_text(encoding="utf-8"))
    result = plan_original_private_method_candidate(
        profile, method, descriptor, family_sites)
    need(_digest(jar) == original_sha256.lower(),
         "ORIGINAL_JAR_CHANGED_DURING_RECONSTRUCTION")
    private = result.pop("private_java_method_body_candidate")
    public = {
        "schema_version": 1, "kind": "v309_original_private_697_op_method_candidate",
        "whole_original_jar_sha256": original_sha256.lower(),
        "private_candidate_source_sha256": hashlib.sha256(private.encode()).hexdigest(),
        "research_only": True, **result,
    }
    output.mkdir(parents=True, exist_ok=False)
    with (output / "method-body.private.java.txt").open(
            "x", encoding="utf-8", newline="\n") as handle:
        handle.write(private)
    with (output / "candidate.aggregate.json").open(
            "x", encoding="utf-8", newline="\n") as handle:
        json.dump(public, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return public


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar", type=Path)
    p.add_argument("private_original_owner_class")
    p.add_argument("private_original_method")
    p.add_argument("original_method_descriptor")
    p.add_argument("new_private_output", type=Path)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--site", action="append", required=True, metavar="Rxx=PRIVATE_JSON")
    a = p.parse_args(argv)
    sites = {}
    for item in a.site:
        family, sep, path = item.partition("=")
        if not sep or not path or family in sites or family not in FAMILIES:
            p.error("expected one --site Rxx=PRIVATE_JSON per R67-R76 family")
        sites[family] = Path(path)
    try:
        result = replay_private_method_candidate(
            a.original_jar, a.private_original_owner_class,
            a.private_original_method, a.original_method_descriptor,
            sites, a.new_private_output, a.original_sha256)
        print(json.dumps(result, sort_keys=True))
    except (LocalCoverageError, OSError, ValueError) as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
