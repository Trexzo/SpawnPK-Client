"""R78: exact original 697-op method instruction partition, private only.

R77 verifies original handler-to-source membership. R78 records ALL original
instruction positions, identifying which are inside those 42 source regions,
which are local catch-handler entry instructions, and which still lack source.
No Java is invented to fill the gaps.
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


def plan_original_method_gap_atlas(profile, method_name, descriptor, artifacts):
    proof = verify_local_site_inventory(profile, method_name, descriptor, artifacts)
    selected = [m for m in profile["methods"] if m.get("name") == method_name
                and m.get("descriptor") == descriptor]
    need(len(selected) == 1, "ORIGINAL_METHOD_NOT_UNIQUE")
    method = selected[0]
    instructions = _instructions(method)
    positions = {insn["offset"]: i for i, insn in enumerate(instructions)}
    site_families = {}
    local_handler_ordinals = set()
    local_intervals = []
    for family, (_count, start_key, end_key, handler_key, _source_key) in FAMILIES.items():
        for site in artifacts[family]:
            start, end, handler = (site[start_key], site[end_key], site[handler_key])
            a, b, h = positions[start], positions[end], positions[handler]
            need(a < b, "ORIGINAL_PROTECTED_RANGE_EMPTY")
            need(h not in local_handler_ordinals, "LOCAL_HANDLER_REUSED")
            local_handler_ordinals.add(h)
            local_intervals.append((a, b, family, h))
            for ordinal in range(a, b):
                need(ordinal not in site_families, "OVERLAPPING_SOURCE_FRAGMENTS")
                site_families[ordinal] = family
    need(len(local_intervals) == 42 and len(local_handler_ordinals) == 42,
         "EXPECTED_42_UNIQUE_PROTECTED_RANGES")
    need(not any(i in site_families for i in local_handler_ordinals),
         "LOCAL_CATCH_ENTRY_INSIDE_ANOTHER_PROTECTED_SOURCE")
    classifications = [
        ("protected:" + site_families[i]) if i in site_families
        else ("local-catch-entry" if i in local_handler_ordinals else "not-yet-sourced")
        for i in range(len(instructions))
    ]
    spans = []
    for i, insn in enumerate(instructions):
        kind = classifications[i]
        if not spans or spans[-1]["kind"] != kind:
            spans.append({
                "kind": kind, "first_ordinal": i, "end_ordinal_exclusive": i+1,
                "first_bytecode_offset": insn["offset"],
                "instruction_count": 1,
                "putstatic_count": int(insn["opcode"] == "0xb3"),
                "private_original_instructions": [insn],
            })
        else:
            span = spans[-1]
            span["end_ordinal_exclusive"] = i+1
            span["instruction_count"] += 1
            span["putstatic_count"] += int(insn["opcode"] == "0xb3")
            span["private_original_instructions"].append(insn)
    need(sum(span["instruction_count"] for span in spans) == 697
         and sum(span["putstatic_count"] for span in spans) == 78,
         "ORIGINAL_FULL_INSTRUCTION_PARTITION_FAILED")
    count = {
        "protected_source_body": sum(k.startswith("protected:") for k in classifications),
        "local_catch_entry": classifications.count("local-catch-entry"),
        "not_yet_sourced": classifications.count("not-yet-sourced"),
    }
    need(sum(count.values()) == 697, "INSTRUCTION_CLASSIFICATION_INCOMPLETE")
    raw = json.dumps(spans, sort_keys=True, separators=(",", ":"))
    del proof["private_ordered_java_fragments"]
    return {
        "private_original_method_gap_spans": spans,
        "private_original_span_details_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "total_original_instructions": 697,
        "total_original_putstatic_writes": 78,
        "original_typed_exception_entries": 44,
        "original_local_exception_regions": 42,
        "original_local_catch_entries": len(local_handler_ordinals),
        "classification_instruction_counts": count,
        "total_partition_spans": len(spans),
        "protected_source_blocks_all_compiled_as_one_method": False,
        "every_not_yet_sourced_instruction_has_recovered_java": False,
        "whole_original_44_handler_parity_tested": False,
        "whole_original_operand_side_effects_equivalent": False,
        "runtime_equivalence_certified": False,
    }


def replay_private_method_gap_atlas(jar, class_entry, method_name, descriptor,
                                    family_files, output, original_sha256):
    jar, output = Path(jar), Path(output)
    need(not output.exists() and not output.is_symlink(), "OUTPUT_ALREADY_EXISTS")
    need(jar.is_file() and not jar.is_symlink()
         and isinstance(original_sha256, str)
         and len(original_sha256) == 64
         and all(c in "0123456789abcdefABCDEF" for c in original_sha256)
         and _digest(jar) == original_sha256.lower(), "ORIGINAL_WHOLE_JAR_PIN_MISMATCH")
    need(isinstance(class_entry, str) and class_entry.endswith(".class")
         and not class_entry.startswith("/") and "\\" not in class_entry
         and all(part not in ("", ".", "..") and ":" not in part
                 for part in class_entry.split("/")), "INVALID_PRIVATE_CLASS_ENTRY")
    need(set(family_files) == set(FAMILIES), "ALL_FAMILY_INPUTS_REQUIRED")
    with ZipFile(jar) as archive:
        need(archive.namelist().count(class_entry) == 1,
             "ORIGINAL_CLASS_ENTRY_NOT_UNIQUE")
    profile = profile_jar_class(jar, class_entry)
    artifacts = {}
    for family, path in family_files.items():
        path = Path(path)
        need(path.is_file() and not path.is_symlink()
             and path.stat().st_size <= 16 * 1024 * 1024,
             "PRIVATE_SOURCE_FILE_INVALID_" + family)
        artifacts[family] = json.loads(path.read_text(encoding="utf-8"))
    proof = plan_original_method_gap_atlas(profile, method_name, descriptor, artifacts)
    need(_digest(jar) == original_sha256.lower(),
         "ORIGINAL_JAR_CHANGED_DURING_ANALYSIS")
    private = proof.pop("private_original_method_gap_spans")
    report = {
        "schema_version": 1, "kind": "v309_private_original_method_gap_atlas",
        "whole_original_jar_sha256": original_sha256.lower(),
        "research_only": True, **proof,
    }
    output.mkdir(parents=True, exist_ok=False)
    with (output / "full-method-gaps.private.json").open("x", encoding="utf-8") as f:
        json.dump(private, f, indent=2, sort_keys=True)
        f.write("\n")
    with (output / "full-method-gaps.aggregate.json").open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar")
    p.add_argument("private_class")
    p.add_argument("private_method")
    p.add_argument("descriptor")
    p.add_argument("new_private_output")
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--site", action="append", required=True, metavar="Rxx=PRIVATE_JSON")
    a = p.parse_args(argv)
    family_files = {}
    for item in a.site:
        family, sep, path = item.partition("=")
        if not sep or not path or family not in FAMILIES or family in family_files:
            p.error("each family must be specified exactly once as Rxx=PRIVATE_JSON")
        family_files[family] = path
    try:
        result = replay_private_method_gap_atlas(
            a.original_jar, a.private_class, a.private_method, a.descriptor,
            family_files, a.new_private_output, a.original_sha256)
        print(json.dumps(result, sort_keys=True))
    except (LocalCoverageError, OSError, ValueError) as e:
        p.error(str(e))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
