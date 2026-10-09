from __future__ import annotations

"""Local-only v309 changed-method continuity evidence; never identity acceptance.

Read original pinned JARs, locate the only removed static call to a *verified
accepted* target, and compare its containing Code method with its uniquely
same-named/typed v309 counterpart. Export counts and scores, not private Code.
"""

import argparse
from collections import Counter
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import zipfile

from .bytecode_profile import profile_class_field_accesses
from .classfile import parse_class, _descriptor_shape
from .descriptor_class_dependencies import build_descriptor_class_dependency_report
from .descriptor_class_private_jar_replay import (
    _read_json_exact, write_research_report_no_clobber,
)
from .indexer import sha256_file
from .lineage import validate_lineage


class V309MethodDeltaResearchError(ValueError):
    pass


def _opcode_grams(method: dict, window: int = 5) -> Counter:
    instructions = method.get("instructions")
    if not isinstance(instructions, list) or any(
        not isinstance(row, dict) or not isinstance(row.get("opcode"), str)
        for row in instructions
    ):
        raise V309MethodDeltaResearchError("invalid decoded Code")
    opcodes = tuple(row["opcode"] for row in instructions)
    return Counter(tuple(opcodes[i:i + window]) for i in range(
        max(0, len(opcodes) - window + 1)
    ))


def _dice(first: Counter, second: Counter) -> float:
    denominator = sum(first.values()) + sum(second.values())
    return 2 * sum((first & second).values()) / denominator if denominator else 0.0


def _removed_invokestatic_continuity(old: dict, new: dict, *,
                                      old_target: str, new_target: str) -> dict:
    """Conservative method-level observation, not JVM semantic equivalence."""
    for profile in (old, new):
        if not isinstance(profile.get("methods"), list):
            raise V309MethodDeltaResearchError("no decoded class methods")
    old_methods = old["methods"]
    new_methods = new["methods"]

    def call_indices(method: dict, owner: str) -> list[int]:
        return [
            i for i, row in enumerate(method.get("instructions", []))
            if row["opcode"] == "0xb8" and row.get("owner") == owner
        ]

    source = [
        (method, calls)
        for method in old_methods
        if (calls := call_indices(method, old_target))
    ]
    if len(source) != 1 or len(source[0][1]) != 1:
        raise V309MethodDeltaResearchError("removed static-call preimage not unique")
    if any(call_indices(method, new_target) for method in new_methods):
        raise V309MethodDeltaResearchError("target static call still present in new class")
    original, indices = source[0]
    if original.get("name") in ("<init>", "<clinit>"):
        raise V309MethodDeltaResearchError("unsupported constructor identity")
    if not all(key in original for key in ("name", "descriptor", "access", "code_length")):
        raise V309MethodDeltaResearchError("old method signature incomplete")
    exact_candidates = [
        method for method in new_methods
        if (
            method.get("name"), method.get("descriptor"), method.get("access")
        ) == (
            original["name"], original["descriptor"], original["access"]
        )
    ]
    if len(exact_candidates) != 1:
        raise V309MethodDeltaResearchError("no unique same-named/typed method")
    counterpart = exact_candidates[0]
    source_ops = [row["opcode"] for row in original["instructions"]]
    target_ops = [row["opcode"] for row in counterpart["instructions"]]
    if len(source_ops) < 5 or len(target_ops) < 5:
        raise V309MethodDeltaResearchError("method too short for 5-gram proof")
    source_grams = _opcode_grams(original)
    rankings = sorted(
        (_dice(source_grams, _opcode_grams(method)), method)
        for method in new_methods
        if isinstance(method.get("instructions"), list)
        and method.get("name") not in ("<init>", "<clinit>")
    )
    best_score = _dice(source_grams, _opcode_grams(counterpart))
    other_scores = [
        score for score, method in rankings if method is not counterpart
    ]
    second_score = max(other_scores, default=0.0)
    align = SequenceMatcher(a=source_ops, b=target_ops, autojunk=False)
    changes = [
        (tag, old_start, old_end, new_start, new_end)
        for tag, old_start, old_end, new_start, new_end in align.get_opcodes()
        if tag != "equal"
    ]
    involved = [
        (tag, left, right, new_left, new_right)
        for tag, left, right, new_left, new_right in changes
        if left <= indices[0] < right
    ]
    if len(involved) != 1:
        raise V309MethodDeltaResearchError("removed static-call edit not isolated")

    return {
        "old_method_opcodes": len(source_ops),
        "new_method_opcodes": len(target_ops),
        "old_method_code_bytes": original["code_length"],
        "new_method_code_bytes": counterpart["code_length"],
        "old_method_exception_handlers": len(original["exception_handlers"]),
        "new_method_exception_handlers": len(counterpart["exception_handlers"]),
        "old_static_call_occurrences": 1,
        "new_static_call_occurrences": 0,
        "exact_new_same_name_descriptor_access_matches": len(exact_candidates),
        "new_methods_compared": len(rankings),
        "same_access_and_erased_descriptor_new_methods": sum(
            (method.get("access"), _descriptor_shape(method["descriptor"])) ==
            (original["access"], _descriptor_shape(original["descriptor"]))
            for method in new_methods if isinstance(method.get("descriptor"), str)
        ),
        "opcode_5gram_dice": round(best_score, 8),
        "next_best_opcode_5gram_dice": round(second_score, 8),
        "opcode_sequence_alignment_ratio": round(align.ratio(), 8),
        "changed_opcode_hunks": len(changes),
        "old_deleted_or_replaced_opcode_occurrences": sum(
            right - left for _, left, right, _, _ in changes
        ),
        "new_inserted_or_replaced_opcode_occurrences": sum(
            right - left for _, _, _, left, right in changes
        ),
        "removed_call_is_inside_changed_region": True,
        "removed_call_hunk_old_opcode_count": involved[0][2] - involved[0][1],
        "removed_call_hunk_new_opcode_count": involved[0][4] - involved[0][3],
        "canonical_member_identity_accepted": False,
    }


def build_v309_accepted_anchor_method_delta(
    old_jar: Path, new_jar: Path,
    frontier_path: Path, lineage_path: Path, global_report_path: Path,
) -> dict:
    frontier, lineage, usage = (
        _read_json_exact(path)
        for path in (frontier_path, lineage_path, global_report_path)
    )
    if (
        frontier.get("kind") != "v309_recovery_frontier"
        or frontier.get("state") != "ACCEPTED_INCOMPLETE"
        or frontier.get("frontier", {}).get("unresolved") != 143
        or frontier.get("frontier", {}).get("descriptor_identity_guard_rejected") != 26
        or usage.get("kind") != "global_field_usage_identity_candidates"
        or usage.get("canonical") is not False
        or len(usage.get("review_outcomes", [])) != 143
        or usage.get("report_id") != frontier.get("files", {}).get("global_field_usage", {}).get("report_id")
    ):
        raise V309MethodDeltaResearchError("expected incomplete v309 frontier")
    for key, path in (("class_lineage", lineage_path),
                      ("global_field_usage", global_report_path)):
        if sha256_file(path).lower() != frontier["files"][key]["sha256"].lower():
            raise V309MethodDeltaResearchError("protected input SHA drift")
    validate_lineage(lineage)
    pins = frontier["exact_clients"]
    builds = {item["build_id"]: item["sha256"] for item in lineage["builds"]}
    if (
        set(builds) != {"v308", "v309"}
        or any(builds[b].lower() != pins[b + "_sha256"].lower() for b in builds)
    ):
        raise V309MethodDeltaResearchError("accepted class lineage build drift")
    for build, path in (("v308", old_jar), ("v309", new_jar)):
        if sha256_file(path).lower() != pins[build + "_sha256"].lower():
            raise V309MethodDeltaResearchError("original private JAR SHA drift")

    classes = {
        row["logical_id"]: {v["build_id"]: v for v in row["lineage"]}
        for row in lineage["classes"]
    }
    anchor = classes["CLIENT_CLASS_000081"]
    source = classes["CLIENT_CLASS_000029"]
    if set(anchor) != {"v308", "v309"} or set(source) != {"v308"}:
        raise V309MethodDeltaResearchError("accepted/static-call class authority drift")
    deps = build_descriptor_class_dependency_report(usage)["class_dependencies"]
    proposals = [
        item for item in deps
        if item["old_canonical_class_id"] == "CLIENT_CLASS_000029"
    ]
    if (
        len(proposals) != 1 or proposals[0]["blocked_fields"] != 14
        or len(proposals[0]["new_raw_descriptors"]) != 1
    ):
        raise V309MethodDeltaResearchError("v309 proposed owner changed")
    new_owner_descriptor = proposals[0]["new_raw_descriptors"][0]
    if (
        not new_owner_descriptor.startswith("L")
        or not new_owner_descriptor.endswith(";")
    ):
        raise V309MethodDeltaResearchError("non-class new owner proposal")
    candidates = {
        "v308": source["v308"]["internal_name"],
        "v309": new_owner_descriptor[1:-1],
    }
    profiles: dict[str, dict] = {}
    with zipfile.ZipFile(old_jar) as oldz, zipfile.ZipFile(new_jar) as newz:
        for build, archive in (("v308", oldz), ("v309", newz)):
            candidate = candidates[build]
            if candidate + ".class" not in archive.namelist():
                raise V309MethodDeltaResearchError("missing candidate classfile")
            candidate_bytes = archive.read(candidate + ".class")
            if parse_class(candidate_bytes).name != candidate:
                raise V309MethodDeltaResearchError("candidate entry owner mismatch")
            if build == "v308" and (
                hashlib.sha256(candidate_bytes).hexdigest() != source[build]["entry_sha256"]
            ):
                raise V309MethodDeltaResearchError("pinned old candidate class hash drift")
            a = anchor[build]
            if (
                a["entry_path"] != a["internal_name"] + ".class"
                or hashlib.sha256(archive.read(a["entry_path"])).hexdigest() != a["entry_sha256"]
            ):
                raise V309MethodDeltaResearchError("accepted target original hash drift")
            profiles[build] = profile_class_field_accesses(candidate_bytes)
            if profiles[build]["internal_name"] != candidate:
                raise V309MethodDeltaResearchError("decoded candidate class drift")

    measurement = _removed_invokestatic_continuity(
        profiles["v308"], profiles["v309"],
        old_target=anchor["v308"]["internal_name"],
        new_target=anchor["v309"]["internal_name"],
    )
    for build, path in (("v308", old_jar), ("v309", new_jar)):
        if sha256_file(path).lower() != pins[build + "_sha256"].lower():
            raise V309MethodDeltaResearchError("private JAR changed after scan")
    for key, path in (("class_lineage", lineage_path),
                      ("global_field_usage", global_report_path)):
        if sha256_file(path).lower() != frontier["files"][key]["sha256"].lower():
            raise V309MethodDeltaResearchError("protected file changed during scan")

    body = {
        "schema_version": 1,
        "kind": "v309_accepted_anchor_method_delta_research",
        "canonical": False,
        "state": "CONTINUITY_CORROBORATION_ONLY_NO_MEMBER_OR_CLASS_ACCEPTANCE",
        "source_class_id": "CLIENT_CLASS_000029",
        "lost_accepted_target_class_id": "CLIENT_CLASS_000081",
        "exact_clients": pins,
        "source_report_id": usage["report_id"],
        "summary": {
            **measurement,
            "canonical_unresolved_field_relationships": 143,
            "descriptor_blocked_field_relationships": 26,
            "new_canonical_class_identities_accepted": 0,
            "new_canonical_field_identities_accepted": 0,
        },
        "note": (
            "Near-identical opcode method body and unique exact member name/"
            "descriptor/access in one proposed pair are independent research "
            "only, not complete JVM method semantics or accepted lineage. "
            "No private class/member names or raw Code/CP values exported."
        ),
    }
    digest = hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()[:20].upper()
    return {"report_id": "V309METHODDELTA_" + digest, **body}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spk-v309-accepted-anchor-method-delta")
    parser.add_argument("--v308-jar", required=True, type=Path)
    parser.add_argument("--v309-jar", required=True, type=Path)
    parser.add_argument("--frontier", required=True, type=Path)
    parser.add_argument("--class-lineage", required=True, type=Path)
    parser.add_argument("--global-report", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    a = parser.parse_args(argv)
    protected = (a.v308_jar, a.v309_jar, a.frontier, a.class_lineage, a.global_report)
    try:
        if a.out.exists() or a.out.is_symlink():
            raise V309MethodDeltaResearchError("research output already exists")
        result = build_v309_accepted_anchor_method_delta(
            a.v308_jar, a.v309_jar, a.frontier, a.class_lineage, a.global_report)
        write_research_report_no_clobber(result, a.out, protected)
    except Exception as exc:
        print("SPK_V309_METHOD_DELTA_FAIL_CLOSED")
        print("error_category=" + type(exc).__name__)
        return 1
    print("SPK_V309_METHOD_DELTA_PASS_RESEARCH_ONLY")
    print("report_id=" + result["report_id"])
    print("canonical_changes=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
