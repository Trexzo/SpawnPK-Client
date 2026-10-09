from __future__ import annotations

"""Supplemental exact-private accepted-anchor graph research, NEVER identity acceptance.

Only canonical logical IDs and aggregate counts leave this process. Every
readable private archive entry/class name stays ephemeral and local.
"""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import zipfile

from .bytecode_profile import profile_class_field_accesses
from .classfile import parse_class
from .descriptor_class_dependencies import build_descriptor_class_dependency_report
from .descriptor_class_private_jar_replay import _read_json_exact, write_research_report_no_clobber
from .indexer import sha256_file
from .lineage import validate_lineage


class V309AnchorGraphError(ValueError):
    pass


_TYPED = re.compile(r"L([^;]+);")
_COUNTS = {"v308": 10472, "v309": 10502}


def _type_names(value: object, *, owner: bool = False) -> set[str]:
    if not isinstance(value, str):
        return set()
    names = set(_TYPED.findall(value))
    if owner and not names and "/" in value and not any(
        ch in value for ch in "<>;()"
    ):
        names.add(value)
    return names


def _typed_references(data: bytes, profile: dict) -> set[str]:
    """Count only declared JVM types and decoded Code referents, not raw CP strings."""
    parsed = parse_class(data)
    refs: set[str] = set()

    if parsed.super_name:
        refs.update(_type_names(parsed.super_name, owner=True))
    for value in parsed.interfaces:
        refs.update(_type_names(value, owner=True))
    for member in (*parsed.fields, *parsed.methods):
        refs.update(_type_names(member.get("descriptor")))
    for method in profile["methods"]:
        for ins in method["instructions"]:
            refs.update(_type_names(ins.get("owner"), owner=True))
            refs.update(_type_names(ins.get("type"), owner=True))
            refs.update(_type_names(ins.get("descriptor")))
            if ins.get("constant_pool_tag") == 7:
                refs.update(_type_names(ins.get("constant"), owner=True))
        for handler in method.get("exception_handlers", []):
            refs.update(_type_names(handler.get("catch_type"), owner=True))
    return refs


def _summarize_incoming(
    incoming: dict[str, set[str]], proposed: str,
    all_classes: set[str], paired: set[str],
) -> dict[str, int | bool]:
    if proposed not in all_classes:
        raise V309AnchorGraphError("proposed candidate missing in original archive")
    sources = incoming.get(proposed, set())
    if not sources:
        # Empty anchor sets cannot distinguish anything; fail closed.
        raise V309AnchorGraphError("candidate has no independently trusted anchors")
    others = [
        (name, witnesses) for name, witnesses in incoming.items()
        if name != proposed and name in all_classes
    ]
    return {
        "incoming_accepted_anchor_count": len(sources),
        "other_archive_classes_same_anchor_set": sum(
            group == sources for _, group in others
        ),
        "other_unpaired_classes_same_anchor_set": sum(
            name not in paired and group == sources for name, group in others
        ),
        "other_archive_classes_superset_anchor_set": sum(
            sources <= group for _, group in others
        ),
        "other_unpaired_classes_superset_anchor_set": sum(
            name not in paired and sources <= group for name, group in others
        ),
    }



def _joint_outgoing_discrimination(
    incoming: dict[str, set[str]], proposed: str, paired: set[str],
    outgoing_targets,
) -> tuple[dict[str, int], set[str]]:
    """Conservatively inspect every unpaired incoming-superset alternative."""
    sources = incoming.get(proposed, set())
    if not sources:
        raise V309AnchorGraphError("candidate has no trusted incoming graph")
    others = sorted(
        name for name, witnesses in incoming.items()
        if name != proposed and name not in paired and sources <= witnesses
    )
    proposed_outgoing = outgoing_targets(proposed)
    if not proposed_outgoing:
        raise V309AnchorGraphError("candidate has no trusted outgoing graph")
    rival_outgoing = [outgoing_targets(name) for name in others]
    return ({
        "proposed_outgoing_accepted_targets": len(proposed_outgoing),
        "unpaired_incoming_superset_alternatives": len(others),
        "unpaired_alternatives_with_outgoing_superset": sum(
            proposed_outgoing <= other for other in rival_outgoing
        ),
        "unpaired_alternatives_with_identical_outgoing_targets": sum(
            proposed_outgoing == other for other in rival_outgoing
        ),
        "maximum_outgoing_target_overlap_among_unpaired_alternatives": max(
            (len(proposed_outgoing & other) for other in rival_outgoing),
            default=0,
        ),
    }, proposed_outgoing)


def build_v309_anchor_graph(
    old_jar: Path, new_jar: Path, frontier_path: Path,
    lineage_path: Path, global_report_path: Path,
) -> dict:
    frontier_input_sha = sha256_file(frontier_path).lower()
    frontier = _read_json_exact(frontier_path)
    if (
        frontier.get("kind") != "v309_recovery_frontier"
        or frontier.get("state") != "ACCEPTED_INCOMPLETE"
        or frontier.get("frontier", {}).get("unresolved") != 143
        or frontier.get("frontier", {}).get("descriptor_identity_guard_rejected") != 26
    ):
        raise V309AnchorGraphError("requires protected incomplete v309 frontier")
    pins = frontier["exact_clients"]
    for key, path in (
        ("class_lineage", lineage_path), ("global_field_usage", global_report_path),
    ):
        if sha256_file(path).lower() != frontier["files"][key]["sha256"].lower():
            raise V309AnchorGraphError("protected source authority SHA mismatch")
    for name, path in (("v308", old_jar), ("v309", new_jar)):
        if sha256_file(path).lower() != pins[name + "_sha256"].lower():
            raise V309AnchorGraphError("original private client SHA mismatch")

    lineage = _read_json_exact(lineage_path)
    usage = _read_json_exact(global_report_path)
    validate_lineage(lineage)
    builds = {row["build_id"]: row["sha256"] for row in lineage["builds"]}
    if (
        set(builds) != {"v308", "v309"}
        or any(builds[b].lower() != pins[b + "_sha256"].lower() for b in builds)
        or usage.get("report_id") != frontier["files"]["global_field_usage"]["report_id"]
        or usage.get("summary", {}).get("descriptor_identity_guard_rejected") != 26
        or len(usage.get("review_outcomes", [])) != 143
    ):
        raise V309AnchorGraphError("lineage or global-field provenance mismatch")
    deps = build_descriptor_class_dependency_report(usage)["class_dependencies"]
    classes = {
        row["logical_id"]: {entry["build_id"]: entry for entry in row["lineage"]}
        for row in lineage["classes"]
    }
    anchors = {cid: d for cid, d in classes.items() if set(d) == {"v308", "v309"}}
    if len(anchors) != 1092 or len(deps) != 8:
        raise V309AnchorGraphError("expected 1092 pinned anchors and eight candidates")

    candidates: dict[str, dict[str, str]] = {}
    for dep in deps:
        cid = dep["old_canonical_class_id"]
        old = classes[cid]
        raw_new = dep["new_raw_descriptors"]
        if (
            set(old) != {"v308"} or len(raw_new) != 1
            or not raw_new[0].startswith("L") or not raw_new[0].endswith(";")
        ):
            raise V309AnchorGraphError("unaccepted class dependency changed")
        candidates[cid] = {
            "v308": old["v308"]["internal_name"],
            "v309": raw_new[0][1:-1],
        }

    incoming_candidates: dict[str, dict[str, set[str]]] = {
        cid: {} for cid in candidates
    }
    outgoing_candidates: dict[str, dict[str, set[str]]] = {
        cid: {} for cid in candidates
    }
    rows = {cid: {"old_canonical_class_id": cid,
                   "blocked_fields": next(d["blocked_fields"] for d in deps
                                          if d["old_canonical_class_id"] == cid),
                   "accepted_class_identity": False}
            for cid in candidates}

    for build, jar in (("v308", old_jar), ("v309", new_jar)):
        with zipfile.ZipFile(jar) as archive:
            entries = archive.namelist()
            available = {name[:-6] for name in entries if name.endswith(".class")}
            if len(entries) != len(set(entries)) or len(available) != _COUNTS[build]:
                raise V309AnchorGraphError("private archive manifest/count drift")
            inbound: dict[str, set[str]] = defaultdict(set)
            for cid, anchor in anchors.items():
                entry = anchor[build]
                data = archive.read(entry["entry_path"])
                if hashlib.sha256(data).hexdigest() != entry["entry_sha256"]:
                    raise V309AnchorGraphError("pinned anchor class SHA drift")
                profile = profile_class_field_accesses(data)
                if profile.get("internal_name") != entry["internal_name"]:
                    raise V309AnchorGraphError("anchor archive owner mismatch")
                for name in _typed_references(data, profile) & available:
                    inbound[name].add(cid)
            paired_ids = {
                a[build]["internal_name"]: cid for cid, a in anchors.items()
            }
            paired = set(paired_ids)
            def outbound(name: str) -> set[str]:
                # Decode only proposed owners and unpaired classes that are
                # genuinely compatible with their incoming anchor superset.
                data = archive.read(name + ".class")
                profile = profile_class_field_accesses(data)
                if profile.get("internal_name") != name:
                    raise V309AnchorGraphError("candidate/rival owner drift")
                return {
                    paired_ids[ref] for ref in _typed_references(data, profile)
                    if ref in paired_ids
                }
            for cid, target in candidates.items():
                name = target[build]
                if build == "v309" and name in paired:
                    raise V309AnchorGraphError("proposed class already canonically paired")
                incoming_candidates[cid][build] = set(inbound.get(name, set()))
                rows[cid][build] = _summarize_incoming(inbound, name, available, paired)
                joint, outgoing = _joint_outgoing_discrimination(
                    inbound, name, paired, outbound,
                )
                outgoing_candidates[cid][build] = outgoing
                rows[cid][build]["joint_incoming_outgoing"] = joint
        if sha256_file(jar).lower() != pins[build + "_sha256"].lower():
            raise V309AnchorGraphError("original private archive mutated during research")

    # A correct initial pin must not be used to endorse a report if any
    # protected input was concurrently replaced during the scan.
    if (
        sha256_file(frontier_path).lower() != frontier_input_sha
        or sha256_file(lineage_path).lower() !=
            frontier["files"]["class_lineage"]["sha256"].lower()
        or sha256_file(global_report_path).lower() !=
            frontier["files"]["global_field_usage"]["sha256"].lower()
    ):
        raise V309AnchorGraphError("protected input mutated during private replay")

    for cid in candidates:
        before, after = incoming_candidates[cid]["v308"], incoming_candidates[cid]["v309"]
        rows[cid]["same_accepted_anchor_class_ids"] = before == after
        rows[cid]["old_only_anchor_identities"] = len(before - after)
        rows[cid]["new_only_anchor_identities"] = len(after - before)
        old_targets = outgoing_candidates[cid]["v308"]
        new_targets = outgoing_candidates[cid]["v309"]
        rows[cid]["same_outgoing_accepted_target_identities"] = (
            old_targets == new_targets
        )
        rows[cid]["old_only_outgoing_target_identities"] = len(
            old_targets - new_targets
        )
        rows[cid]["new_only_outgoing_target_identities"] = len(
            new_targets - old_targets
        )

    body = {
        "schema_version": 1,
        "kind": "v309_accepted_anchor_full_archive_research",
        "state": "ANCHOR_GRAPH_ONLY_NO_CLASS_OR_FIELD_ACCEPTANCE",
        "canonical": False, "exact_clients": pins,
        "source_frontier_sha256": frontier_input_sha,
        "source_class_lineage_sha256":
            frontier["files"]["class_lineage"]["sha256"].lower(),
        "source_global_field_report_sha256":
            frontier["files"]["global_field_usage"]["sha256"].lower(),
        "source_global_field_report_id": usage["report_id"],
        "summary": {
            "accepted_anchor_class_pairs_verified": 1092,
            "proposed_unaccepted_class_pairs": 8,
            "descriptor_blocked_fields_preserved": 26,
            "unresolved_fields_preserved": 143,
            "new_class_identities_accepted": 0,
            "new_field_identities_accepted": 0,
        },
        "rows": [rows[cid] for cid in sorted(rows)],
        "note": (
            "Complete original archives checked against decoded typed-reference "
            "neighborhoods of all pinned accepted anchor classes. Positive "
            "neighborhood and accepted-target graph uniqueness is research "
            "only; existing CP rival vetoes remain untouched. No private class "
            "paths, CP members or Code exported."
        ),
    }
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    return {"report_id": "V309FULLANCHOR_" +
            hashlib.sha256(canonical).hexdigest()[:20].upper(), **body}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-v309-accepted-anchor-graph")
    p.add_argument("--v308-jar", type=Path, required=True)
    p.add_argument("--v309-jar", type=Path, required=True)
    p.add_argument("--frontier", type=Path, required=True)
    p.add_argument("--class-lineage", type=Path, required=True)
    p.add_argument("--global-report", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        result = build_v309_anchor_graph(
            a.v308_jar, a.v309_jar, a.frontier,
            a.class_lineage, a.global_report,
        )
        write_research_report_no_clobber(
            result, a.out,
            (a.v308_jar, a.v309_jar, a.frontier,
             a.class_lineage, a.global_report),
        )
    except Exception as exc:
        # Never leak private original class/CP names through exceptions.
        print("SPK_V309_ANCHOR_GRAPH_FAIL_CLOSED")
        print("error_category=" + type(exc).__name__)
        return 1
    print("SPK_V309_ANCHOR_GRAPH_PASS_RESEARCH_ONLY")
    print("report_id=" + result["report_id"])
    print("no_canonical_changes=True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
