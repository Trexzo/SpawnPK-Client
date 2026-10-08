from __future__ import annotations

"""Exact-private changed-class literal witnesses; research ONLY.

All class String literals are counted in memory. Output contains aggregate counts
and a single salted set digest per candidate, never raw literals or a full index.
Co-located literals may correlate: this does NOT accept class/member identity.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any

from .descriptor_class_dependencies import build_descriptor_class_dependency_report
from .descriptor_class_private_jar_replay import (
    _read_json_exact,
    write_research_report_no_clobber,
)
from .indexer import index_jar, sha256_file
from .lineage import validate_lineage


class V309LiteralClassWitnessError(ValueError):
    pass


_EXPECTED_CLASSES = {"v308": 10472, "v309": 10502}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _unique_literals(
    index: dict[str, Any], build: str,
) -> tuple[dict[str, set[str]], dict[str, str]]:
    classes = index.get("classes")
    entries = index.get("entries")
    summary = index.get("summary")
    expected = _EXPECTED_CLASSES[build]
    if (
        not isinstance(classes, dict) or not isinstance(entries, dict)
        or not isinstance(summary, dict) or len(classes) != expected
        or summary.get("class_count") != expected
        or summary.get("class_parse_error_count") != 0
    ):
        raise V309LiteralClassWitnessError(
            f"{build}: requires complete pinned, parse-error-free class index"
        )
    owners: dict[str, list[str]] = defaultdict(list)
    by_class: dict[str, set[str]] = {}
    for path, record in classes.items():
        if (
            not isinstance(path, str) or not path.endswith(".class")
            or not isinstance(record, dict)
            or record.get("internal_name") != path[:-6]
            or path not in entries
            or not isinstance(entries[path], dict)
            or not isinstance(entries[path].get("sha256"), str)
        ):
            raise V309LiteralClassWitnessError(f"{build}: malformed class/index path")
        literals = record.get("literal_strings")
        if not isinstance(literals, list) or any(not isinstance(v, str) for v in literals):
            raise V309LiteralClassWitnessError(f"{build}: missing literal strings")
        # Filter short, whitespace-only constants and deduplicate within each
        # class before computing GLOBAL archive-wide ownership.
        keep = {v for v in literals if len(v) >= 6 and not v.isspace()}
        by_class[path] = keep
        for literal in keep:
            owners[literal].append(path)
    unique_owner = {
        literal: paths[0] for literal, paths in owners.items() if len(paths) == 1
    }
    return by_class, unique_owner


def build_v309_changed_class_literal_witness(
    global_report: dict[str, Any],
    class_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
) -> dict[str, Any]:
    """Rank exact-archive literal anchors for the eight blocked descriptors."""
    if (
        global_report.get("kind") != "global_field_usage_identity_candidates"
        or global_report.get("canonical") is not False
        or global_report.get("old_build_id") != "v308"
        or global_report.get("new_build_id") != "v309"
        or len(global_report.get("review_outcomes", [])) != 143
        or global_report.get("summary", {}).get("descriptor_identity_guard_rejected") != 26
    ):
        raise V309LiteralClassWitnessError("requires pinned 143/26 v309 research report")
    validate_lineage(class_lineage)
    builds = {row["build_id"]: row["sha256"] for row in class_lineage["builds"]}
    for build, key, index in (
        ("v308", "old_sha256", old_index), ("v309", "new_sha256", new_index),
    ):
        fingerprint = global_report.get(key)
        if (
            not isinstance(fingerprint, str) or len(fingerprint) != 64
            or index.get("sha256", "").lower() != fingerprint.lower()
            or builds.get(build, "").lower() != fingerprint.lower()
        ):
            raise V309LiteralClassWitnessError(f"{build}: index/class-lineage SHA mismatch")
    deps = build_descriptor_class_dependency_report(global_report)
    if (
        deps["summary"]["blocked_fields"] != 26
        or deps["summary"]["blocking_old_class_identities"] != 8
    ):
        raise V309LiteralClassWitnessError("v309 descriptor dependency count drift")
    old_classes, old_unique_owner = _unique_literals(old_index, "v308")
    new_classes, new_unique_owner = _unique_literals(new_index, "v309")
    records = {c["logical_id"]: c for c in class_lineage["classes"]}
    already_paired = {
        entry["internal_name"]: c["logical_id"]
        for c in class_lineage["classes"]
        for entry in c["lineage"] if entry["build_id"] == "v309"
    }
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for group in deps["class_dependencies"]:
        cid = group["old_canonical_class_id"]
        rows = records[cid]["lineage"]
        old_rows = [r for r in rows if r["build_id"] == "v308"]
        new_rows = [r for r in rows if r["build_id"] == "v309"]
        if len(old_rows) != 1 or new_rows:
            raise V309LiteralClassWitnessError(f"{cid}: existing lineage changed")
        old = old_rows[0]
        old_path = old["entry_path"]
        descriptor = group["new_raw_descriptors"]
        if (
            group.get("state") != "UNPROVEN_NEW_CLASS_IDENTITY"
            or group["old_raw_descriptors"] != ["L" + old["internal_name"] + ";"]
            or not isinstance(descriptor, list) or len(descriptor) != 1
            or not descriptor[0].startswith("Lrs/") or not descriptor[0].endswith(";")
        ):
            raise V309LiteralClassWitnessError(f"{cid}: invalid unproven class dependency")
        target = descriptor[0][1:-1] + ".class"
        old_record = old_index["classes"].get(old_path)
        old_entry = old_index["entries"].get(old_path)
        new_record = new_index["classes"].get(target)
        new_entry = new_index["entries"].get(target)
        if (
            old_record is None or old_entry is None
            or old_record.get("structural_sha256", "").lower()
                != old["structural_sha256"].lower()
            or old_entry.get("sha256", "").lower() != old["entry_sha256"].lower()
        ):
            raise V309LiteralClassWitnessError(f"{cid}: pinned old class proof differs")
        base = {
            "old_canonical_class_id": cid,
            "blocked_fields": group["blocked_fields"],
            "blocked_relationship_ids": group["relationship_ids"],
            "proposed_new_class": target[:-6],
        }
        def reject(reason: str, **details: Any) -> None:
            rejected.append({**base, "reason": reason, **details})
        if new_record is None or new_entry is None:
            reject("proposed_new_class_missing_from_exact_index")
            continue
        if target[:-6] in already_paired:
            reject("proposed_class_already_owned")
            continue
        if (
            old_entry["sha256"].lower() == new_entry["sha256"].lower()
            or old_record["structural_sha256"].lower()
               == new_record["structural_sha256"].lower()
        ):
            reject("not_a_changed_class_literal_research_case")
            continue

        # A constant is a witness only when it belongs to exactly one class
        # in each WHOLE archive; count rival new owners separately.
        owners = Counter(
            new_unique_owner[literal]
            for literal in old_classes[old_path]
            if old_unique_owner.get(literal) == old_path
            and literal in new_unique_owner
        )
        exact_anchors = sorted(
            literal for literal in old_classes[old_path]
            if old_unique_owner.get(literal) == old_path
            and new_unique_owner.get(literal) == target
        )
        rival_anchor_count = sum(n for path, n in owners.items() if path != target)
        if rival_anchor_count:
            reject("conflicting_new_class_unique_literal_witness",
                   matching_anchor_count=len(exact_anchors),
                   competing_anchor_count=rival_anchor_count)
            continue
        if len(exact_anchors) < 3:
            reject("insufficient_global_unique_literal_witness",
                   matching_anchor_count=len(exact_anchors),
                   competing_anchor_count=0)
            continue
        candidates.append({
            **base,
            "strategy": "globally_unique_two_build_literal_set_research",
            "classification": "RESEARCH_CANDIDATE_NOT_ACCEPTED",
            "matching_anchor_count": len(exact_anchors),
            "competing_anchor_count": 0,
            "anchor_set_digest": _digest(exact_anchors),
        })
    candidates.sort(key=lambda v: v["old_canonical_class_id"])
    rejected.sort(key=lambda v: v["old_canonical_class_id"])
    if len(candidates) + len(rejected) != 8:
        raise V309LiteralClassWitnessError("candidate accounting drift")
    body = {
        "schema_version": 1,
        "kind": "v309_changed_class_unique_literal_research",
        "canonical": False,
        "state": "GLOBAL_LITERAL_ANCHORS_NOT_CANONICAL_IDENTITY_PROOF",
        "old_sha256": old_index["sha256"],
        "new_sha256": new_index["sha256"],
        "global_report_id": global_report["report_id"],
        "global_report_digest": _digest(global_report),
        "class_lineage_digest": _digest(class_lineage),
        "dependency_digest": _digest(deps),
        "summary": {
            "input_class_dependencies": 8,
            "input_blocked_fields": 26,
            "candidate_classes": len(candidates),
            "candidate_blocked_fields": sum(r["blocked_fields"] for r in candidates),
            "rejected_classes": len(rejected),
            "remaining_blocked_fields": sum(r["blocked_fields"] for r in rejected),
            "accepted_unresolved_fields": 143,
            "canonical_identities_accepted": 0,
        },
        "candidates": candidates,
        "rejected": rejected,
        "note": (
            "A globally unique class-local String set is independent of class names "
            "and structural hash equality, but multiple literals may share a source "
            "or initialization site. These remain review-only; no lineage or authority "
            "is modified. Raw String literals, JARs and full indexes are not emitted."
        ),
    }
    return {"report_id": "V309LITERAL_" + _digest(body)[:20].upper(), **body}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-v309-changed-class-literal-witness")
    p.add_argument("--v308-jar", type=Path, required=True)
    p.add_argument("--v309-jar", type=Path, required=True)
    p.add_argument("--frontier", type=Path, default=Path("research/v309-field-recovery/frontier.json"))
    p.add_argument("--class-lineage", type=Path, default=Path("research/v309-field-recovery/class-lineage.json"))
    p.add_argument("--global-report", type=Path, default=Path("research/v309-field-recovery/global-field-usage.json"))
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        frontier = _read_json_exact(args.frontier)
        if (
            frontier.get("state") != "ACCEPTED_INCOMPLETE"
            or frontier.get("kind") != "v309_recovery_frontier"
            or frontier.get("build_id") != "v309"
            or frontier.get("frontier", {}).get("unresolved") != 143
        ):
            raise V309LiteralClassWitnessError("expected pinned incomplete v309 frontier")
        for key, path in (
            ("class_lineage", args.class_lineage),
            ("global_field_usage", args.global_report),
        ):
            pinned = frontier.get("files", {}).get(key, {}).get("sha256")
            if (
                not isinstance(pinned, str) or len(pinned) != 64
                or sha256_file(path).lower() != pinned.lower()
            ):
                raise V309LiteralClassWitnessError(f"tracked {key} hash mismatch")
        for build, path in (("v308", args.v308_jar), ("v309", args.v309_jar)):
            pinned = frontier.get("exact_clients", {}).get(build + "_sha256")
            if (
                not isinstance(pinned, str) or len(pinned) != 64
                or sha256_file(path).lower() != pinned.lower()
            ):
                raise V309LiteralClassWitnessError(f"exact {build} JAR hash mismatch")
        report = build_v309_changed_class_literal_witness(
            _read_json_exact(args.global_report),
            _read_json_exact(args.class_lineage),
            index_jar(args.v308_jar), index_jar(args.v309_jar),
        )
        write_research_report_no_clobber(
            report, args.out,
            (args.v308_jar, args.v309_jar, args.frontier,
             args.class_lineage, args.global_report),
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"SPK_V309_LITERAL_WITNESS_FAIL: {exc}")
        return 1
    print("SPK_V309_LITERAL_WITNESS_PASS_RESEARCH_ONLY")
    print(f"report_id={report['report_id']}")
    for key, value in report["summary"].items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
