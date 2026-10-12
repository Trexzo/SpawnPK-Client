"""R77: compare all private R67-R76 protected fragments to ONE original JVM method.

The output is a private ordered fragment inventory, not a compilable or
runtime-equivalent reconstructed v309 method.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile
from .bytecode_profile import profile_jar_class
from .mutable_scalar_initializer_source import _digest, _instructions

class LocalCoverageError(ValueError):
    pass

# Count, original site start/end/handler keys, generated source key.
FAMILIES = {
    "R67": (29, "original_start_pc", "original_end_pc", "original_handler_pc", "private_source"),
    "R68": (2, "original_start_pc", "original_end_pc", "original_handler_pc", "private_source"),
    "R71": (5, "original_protected_start", "original_protected_end", "original_exception_handler_pc", "private_java_source"),
    "R72": (1, "original_start_pc", "original_end_pc", "original_handler_pc", "private_source"),
    "R73": (1, "original_protected_start", "original_protected_end", "original_exception_handler_pc", "private_java_source"),
    "R74": (2, "original_protected_start", "original_protected_end", "original_exception_handler_pc", "private_java_source"),
    "R75": (1, "original_start_pc", "original_end_pc", "original_exception_handler_pc", "private_java_source"),
    "R76": (1, "original_start_pc", "original_end_pc", "original_exception_handler_pc", "private_generated_java_source"),
}
SHA = re.compile(r"[0-9a-fA-F]{64}\Z")

def need(ok, code):
    if not ok:
        raise LocalCoverageError(code)

def verify_local_site_inventory(profile, method_name, descriptor, artifacts):
    methods = [m for m in profile.get("methods", [])
               if m.get("name") == method_name and m.get("descriptor") == descriptor]
    need(len(methods) == 1, "ORIGINAL_METHOD_NOT_UNIQUE")
    m = methods[0]
    rows = _instructions(m)
    need(len(rows) == 697 and rows[0]["offset"] == 0
         and all(x["offset"] + x["length"] == y["offset"]
                 for x, y in zip(rows, rows[1:])), "ORIGINAL_697_INSTRUCTION_LAYOUT_MISMATCH")
    need(sum(x.get("opcode") == "0xb3" for x in rows) == 78,
         "ORIGINAL_78_STATIC_WRITES_MISMATCH")
    table = m.get("exception_handlers")
    need(isinstance(table, list) and len(table) == 44,
         "ORIGINAL_44_EXCEPTION_HANDLERS_MISMATCH")
    local = [h for h in table if h.get("catch_type") == "java/lang/Exception"]
    io = [h for h in table if h.get("catch_type") == "java/io/IOException"]
    need(len(local) == 42 and len(io) == 2, "ORIGINAL_EXCEPTION_TYPE_COUNTS_MISMATCH")
    positions = {row["offset"]: i for i, row in enumerate(rows)}
    original = set()
    for h in local:
        item = (h.get("start_pc"), h.get("end_pc"), h.get("handler_pc"))
        need(all(type(v) is int and v in positions for v in item)
             and item[0] < item[1] and item not in original,
             "ORIGINAL_LOCAL_EXCEPTION_BOUNDARY_INVALID")
        original.add(item)
    need(isinstance(artifacts, dict) and set(artifacts) == set(FAMILIES),
         "EIGHT_PRIVATE_FAMILY_ARTIFACTS_REQUIRED")
    found = {}
    for family, (count, a, b, c, source_key) in FAMILIES.items():
        sites = artifacts[family]
        need(isinstance(sites, list) and len(sites) == count,
             "WRONG_SITE_COUNT_" + family)
        for site in sites:
            need(isinstance(site, dict), "INVALID_PRIVATE_SITE_" + family)
            identity = (site.get(a), site.get(b), site.get(c))
            need(identity in original, "UNKNOWN_ORIGINAL_SITE_" + family)
            need(identity not in found, "DUPLICATE_PRIVATE_SITE")
            source = site.get(source_key)
            need(isinstance(source, str) and source.strip()
                 and "try {" in source and "catch (java.lang.Exception" in source,
                 "SOURCE_FRAGMENT_MISSING_" + family)
            found[identity] = (family, source)
    need(set(found) == original, "INCOMPLETE_ORIGINAL_HANDLER_COVERAGE")
    ordered = sorted(original, key=lambda item: positions[item[0]])
    need(all(positions[left[1]] <= positions[right[0]]
             for left, right in zip(ordered, ordered[1:])),
         "OVERLAPPING_PROTECTED_REGIONS")
    text = "".join("// PRIVATE bounded fragment " + found[site][0]
                   + "; missing inter-region and outer method statements\n"
                   + found[site][1].rstrip() + "\n\n" for site in ordered)
    return {
        "private_ordered_java_fragments": text,
        "covered_original_local_exception_entries": 42,
        "covered_original_protected_instructions":
            sum(positions[x[1]] - positions[x[0]] for x in ordered),
        "source_families": {k: value[0] for k, value in FAMILIES.items()},
        "complete_697_instruction_method_compiled": False,
        "original_44_entry_exception_parity_passed": False,
        "original_operand_and_side_effect_parity_passed": False,
        "runtime_equivalence_certified": False,
    }

def replay_private_local_coverage(jar, class_entry, method, descriptor,
                                  family_files, output, original_sha256):
    jar, output = Path(jar), Path(output)
    need(not output.exists() and not output.is_symlink(), "OUTPUT_ALREADY_EXISTS")
    need(isinstance(original_sha256, str) and SHA.fullmatch(original_sha256),
         "INVALID_WHOLE_ORIGINAL_JAR_SHA")
    need(jar.is_file() and not jar.is_symlink()
         and _digest(jar) == original_sha256.lower(),
         "ORIGINAL_JAR_PIN_MISMATCH")
    need(isinstance(class_entry, str) and class_entry.endswith(".class")
         and not class_entry.startswith("/") and "\\" not in class_entry
         and all(s not in ("", ".", "..") and ":" not in s
                 for s in class_entry.split("/")), "INVALID_PRIVATE_CLASS_ENTRY")
    need(set(family_files) == set(FAMILIES), "ALL_FAMILY_JSON_REQUIRED")
    with ZipFile(jar) as archive:
        need(archive.namelist().count(class_entry) == 1,
             "ORIGINAL_CLASS_ENTRY_NOT_UNIQUE")
    profile = profile_jar_class(jar, class_entry)
    artifacts = {}
    for family, path in family_files.items():
        path = Path(path)
        need(path.is_file() and not path.is_symlink()
             and path.stat().st_size <= 16 * 1024 * 1024,
             "INVALID_PRIVATE_ARTIFACT_" + family)
        artifacts[family] = json.loads(path.read_text(encoding="utf-8"))
    result = verify_local_site_inventory(profile, method, descriptor, artifacts)
    need(_digest(jar) == original_sha256.lower(),
         "ORIGINAL_JAR_CHANGED_DURING_PROOF")
    fragment = result.pop("private_ordered_java_fragments")
    report = {
        "schema_version": 1,
        "kind": "v309_private_42_exception_region_inventory",
        "whole_original_jar_sha256": original_sha256.lower(),
        "private_ordered_fragments_sha256": hashlib.sha256(fragment.encode()).hexdigest(),
        "research_only": True, **result,
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "42-regions.private.java.txt").write_text(fragment, encoding="utf-8")
    (output / "coverage.aggregate.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar")
    p.add_argument("private_class")
    p.add_argument("private_method")
    p.add_argument("descriptor")
    p.add_argument("new_private_output")
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--site", action="append", required=True, metavar="Rxx=FILE")
    a = p.parse_args(argv)
    family_files = {}
    for entry in a.site:
        family, sep, path = entry.partition("=")
        if not sep or not path or family not in FAMILIES or family in family_files:
            p.error("one --site FAMILY=PRIVATE_JSON required per original family")
        family_files[family] = path
    try:
        print(json.dumps(replay_private_local_coverage(
            a.original_jar, a.private_class, a.private_method, a.descriptor,
            family_files, a.new_private_output, a.original_sha256), sort_keys=True))
    except (LocalCoverageError, OSError, ValueError) as exc:
        p.error(str(exc))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
