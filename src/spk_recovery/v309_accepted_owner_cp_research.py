from __future__ import annotations

"""Exact-private accepted-class owner CP corroboration for 000943 ONLY.

Purely supplemental research: never mutates canonical identity/field lineage.
Only previously accepted and SHA-verified v308/v309 class identities may be
aliased. Raw class names, CP referents and method fingerprints stay private.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import zipfile

from .bytecode_profile import profile_class_field_accesses
from .classfile import parse_class
from .descriptor_class_dependencies import build_descriptor_class_dependency_report
from .descriptor_class_private_jar_replay import (
    _read_json_exact, write_research_report_no_clobber,
)
from .indexer import sha256_file
from .lineage import validate_lineage
from .v309_cp_method_referent_research import compare_cp_method_profiles
from .v309_cp_whole_archive_rival_research import (
    _coarse, _coarse_intersection, _MIN_INDEPENDENT_METHODS,
)

TARGET_ID = "CLIENT_CLASS_000943"
_COUNTS = {"v308": (10472, 10970), "v309": (10502, 10921)}
_ALIASES = 1092


class V309AcceptedOwnerResearchError(ValueError):
    pass


def _digest(body: dict) -> str:
    return hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


def rewrite_accepted_class_types(profile: dict, aliases: dict[str, str]) -> dict:
    """Rewrite only typed CP/descriptor class identities; NEVER literals or members.

    The map must come exclusively from SHA-verified accepted class lineage.
    Unaccepted and third-party names are left EXACT. The source method owner
    stays unchanged for the existing conservative proposed-self normalization.
    """
    if (
        not isinstance(profile, dict) or not isinstance(profile.get("internal_name"), str)
        or not isinstance(aliases, dict) or not aliases
        or any(not isinstance(k, str) or not isinstance(v, str) or not k or not v
               for k, v in aliases.items())
        or len(set(aliases.values())) != len(aliases)
    ):
        raise V309AcceptedOwnerResearchError("invalid accepted class alias authority")
    transformed = copy.deepcopy(profile)
    def typed(value: str) -> str:
        if value in aliases:
            return aliases[value]
        return re.sub(r"L([^;]+);", lambda m:
                      "L" + aliases.get(m.group(1), m.group(1)) + ";", value)

    def walk(value):
        if isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for key, element in list(value.items()):
                if key == "internal_name":
                    continue
                if key in ("owner", "type", "descriptor", "catch_type") and isinstance(element, str):
                    value[key] = typed(element)
                elif key == "constant" and value.get("constant_pool_tag") == 7 and isinstance(element, str):
                    value[key] = typed(element)
                elif key == "name" and value.get("kind") == "class" and isinstance(element, str):
                    value[key] = typed(element)
                else:
                    walk(element)
    walk(transformed)
    return transformed


def _exact_accepted_aliases(lineage: dict, original: dict[str, zipfile.ZipFile]) -> dict:
    validate_lineage(lineage)
    accepted: dict[str, dict[str, str]] = {"v308": {}, "v309": {}}
    paired = 0
    for item in lineage["classes"]:
        branches = {row["build_id"]: row for row in item["lineage"]}
        if set(branches) != {"v308", "v309"}:
            continue
        paired += 1
        for version in ("v308", "v309"):
            entry = branches[version]
            path, name = entry["entry_path"], entry["internal_name"]
            if (
                path != name + ".class" or path not in original[version].namelist()
                or name in accepted[version]
                or hashlib.sha256(original[version].read(path)).hexdigest() != entry["entry_sha256"]
            ):
                raise V309AcceptedOwnerResearchError("unverified accepted class anchor")
            accepted[version][name] = "@ACCEPTED_" + item["logical_id"]
    if (
        paired != _ALIASES
        or any(len(accepted[v]) != paired for v in accepted)
        or set(accepted["v308"].values()) != set(accepted["v309"].values())
    ):
        raise V309AcceptedOwnerResearchError("accepted class anchor coverage drift")
    return accepted


def _whole_archive_necessary_pool(archive: zipfile.ZipFile, version: str, proposed: str) -> int:
    names = archive.namelist()
    expected_classes, expected_entries = _COUNTS[version]
    if (
        len(names) != expected_entries or len(set(names)) != len(names)
        or sum(path.endswith(".class") for path in names) != expected_classes
        or proposed not in names
    ):
        raise V309AcceptedOwnerResearchError("original full-archive manifest drift")
    target = parse_class(archive.read(proposed))
    if target.name + ".class" != proposed:
        raise V309AcceptedOwnerResearchError("proposed owner identity drift")
    target_shape = _coarse({"methods": target.methods})
    matching = 0
    for path in names:
        if not path.endswith(".class"):
            continue
        parsed = parse_class(archive.read(path))
        if parsed.name + ".class" != path:
            raise V309AcceptedOwnerResearchError("parsed archive owner drift")
        if _coarse_intersection(target_shape, _coarse({"methods": parsed.methods})) >= _MIN_INDEPENDENT_METHODS:
            matching += 1
    return matching


def build_v309_accepted_owner_cp_research(
    frontier: dict, lineage: dict, global_report: dict,
    old_jar: Path, new_jar: Path,
) -> dict:
    if (
        frontier.get("kind") != "v309_recovery_frontier"
        or frontier.get("state") != "ACCEPTED_INCOMPLETE"
        or frontier.get("frontier", {}).get("unresolved") != 143
        or frontier.get("frontier", {}).get("descriptor_identity_guard_rejected") != 26
        or global_report.get("kind") != "global_field_usage_identity_candidates"
        or global_report.get("canonical") is not False
        or global_report.get("report_id") != frontier.get("files", {}).get("global_field_usage", {}).get("report_id")
    ):
        raise V309AcceptedOwnerResearchError("expected pinned 143/26 research frontier")
    exact = frontier["exact_clients"]
    for version, file in (("v308", old_jar), ("v309", new_jar)):
        if sha256_file(file).lower() != exact[version + "_sha256"].lower():
            raise V309AcceptedOwnerResearchError("exact original client SHA drift")
    deps = build_descriptor_class_dependency_report(global_report)
    if (
        deps["summary"]["blocked_fields"] != 26
        or deps["summary"]["blocking_old_class_identities"] != 8
    ):
        raise V309AcceptedOwnerResearchError("descriptor dependency drift")
    matching = [row for row in deps["class_dependencies"]
                if row["old_canonical_class_id"] == TARGET_ID]
    if len(matching) != 1 or matching[0]["blocked_fields"] != 1:
        raise V309AcceptedOwnerResearchError("target class identity frontier drift")
    records = {row["logical_id"]: row for row in lineage["classes"]}
    old_classes = [row for row in records[TARGET_ID]["lineage"] if row["build_id"] == "v308"]
    if len(old_classes) != 1 or len(records[TARGET_ID]["lineage"]) != 1:
        raise V309AcceptedOwnerResearchError("target already accepted or missing")
    descriptor = matching[0]["new_raw_descriptors"]
    if len(descriptor) != 1 or not descriptor[0].startswith("L") or not descriptor[0].endswith(";"):
        raise V309AcceptedOwnerResearchError("target new descriptor ambiguous")
    paths = {"v308": old_classes[0]["entry_path"],
             "v309": descriptor[0][1:-1] + ".class"}

    with zipfile.ZipFile(old_jar) as oldz, zipfile.ZipFile(new_jar) as newz:
        archives = {"v308": oldz, "v309": newz}
        aliases = _exact_accepted_aliases(lineage, archives)
        if any(paths[v][:-6] in aliases[v] for v in aliases):
            raise V309AcceptedOwnerResearchError("unaccepted target already mapped")
        profiles = {v: profile_class_field_accesses(archives[v].read(paths[v])) for v in archives}
        before = compare_cp_method_profiles(
            profiles["v308"], profiles["v309"],
            old_owner=paths["v308"][:-6], new_owner=paths["v309"][:-6])
        after = compare_cp_method_profiles(
            rewrite_accepted_class_types(profiles["v308"], aliases["v308"]),
            rewrite_accepted_class_types(profiles["v309"], aliases["v309"]),
            old_owner=paths["v308"][:-6], new_owner=paths["v309"][:-6])
        pool = {v: _whole_archive_necessary_pool(archives[v], v, paths[v]) for v in archives}

    summary = {
        "verified_accepted_class_pairs": _ALIASES,
        "old_full_archive_classes": _COUNTS["v308"][0],
        "new_full_archive_classes": _COUNTS["v309"][0],
        "old_coarse_necessary_pool": pool["v308"],
        "new_coarse_necessary_pool": pool["v309"],
        "self_alias_only_cp_witnesses": before["unique_cp_semantic_method_matches"],
        "accepted_owner_alias_cp_witnesses": after["unique_cp_semantic_method_matches"],
        "old_supported_cp_methods": after["old_eligible"],
        "new_supported_cp_methods": after["new_eligible"],
        "old_unsupported_cp_methods": after["old_unsupported"],
        "new_unsupported_cp_methods": after["new_unsupported"],
        "canonical_unresolved_fields": 143,
        "descriptor_blocked_fields": 26,
        "accepted_class_identities": 0,
        "accepted_field_identities": 0,
    }
    body = {
        "schema_version": 1,
        "kind": "v309_pinned_accepted_owner_cp_witness_research",
        "canonical": False,
        "state": "OWNER_ALIAS_CORROBORATION_ONLY_NO_IDENTITY_ACCEPTANCE",
        "target_id": TARGET_ID,
        "old_sha256": exact["v308_sha256"],
        "new_sha256": exact["v309_sha256"],
        "summary": summary,
        "note": "Research-only: aliases derive only from pinned, classfile-SHA-verified accepted class IDs; raw class names, member names, literal strings and CP tags remain exact. Complete method-shape necessary pools do not replace explicit class/member identity review. No canonical authority changes.",
    }
    return {"report_id": "V309ACCEPTEDCP_" + _digest(body)[:20].upper(), **body}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-v309-accepted-owner-cp-research")
    p.add_argument("--v308-jar", required=True, type=Path)
    p.add_argument("--v309-jar", required=True, type=Path)
    p.add_argument("--frontier", type=Path, default=Path("research/v309-field-recovery/frontier.json"))
    p.add_argument("--class-lineage", type=Path, default=Path("research/v309-field-recovery/class-lineage.json"))
    p.add_argument("--global-report", type=Path, default=Path("research/v309-field-recovery/global-field-usage.json"))
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args(argv)
    protected = (a.v308_jar, a.v309_jar, a.frontier, a.class_lineage, a.global_report)
    try:
        if a.out.exists() or a.out.is_symlink():
            raise V309AcceptedOwnerResearchError("existing output must not be overwritten")
        if any(a.out.resolve() == path.resolve() for path in protected):
            raise V309AcceptedOwnerResearchError("output overlaps protected input")
        frontier = _read_json_exact(a.frontier)
        for key, path in (("class_lineage", a.class_lineage),
                          ("global_field_usage", a.global_report)):
            expected = frontier.get("files", {}).get(key, {}).get("sha256")
            if not isinstance(expected, str) or sha256_file(path).lower() != expected.lower():
                raise V309AcceptedOwnerResearchError("protected source SHA drift")
        result = build_v309_accepted_owner_cp_research(
            frontier, _read_json_exact(a.class_lineage),
            _read_json_exact(a.global_report), a.v308_jar, a.v309_jar,
        )
        write_research_report_no_clobber(result, a.out, protected)
    except Exception as exc:
        # Never print private paths, CP values, decoded class/method names, or tracebacks.
        print("SPK_V309_ACCEPTED_OWNER_CP_FAIL_CLOSED")
        print("error_category=" + type(exc).__name__)
        return 1
    print("SPK_V309_ACCEPTED_OWNER_CP_PASS_RESEARCH_ONLY")
    print("report_id=" + result["report_id"])
    for key, value in result["summary"].items():
        print(key + "=" + str(value))
    print("canonical_changes=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
