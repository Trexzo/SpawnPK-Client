from __future__ import annotations

"""Research-only v308/v309 changed-class method-shape witnesses.

A proposed mapping survives only when its exact method/field structure is the
sole qualifying match in *both directions across both entire exact archives*.
This never accepts canonical class or member identities.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any

from .classfile import _descriptor_shape
from .descriptor_class_dependencies import build_descriptor_class_dependency_report
from .descriptor_class_private_jar_replay import _read_json_exact, write_research_report_no_clobber
from .indexer import index_jar, sha256_file
from .lineage import validate_lineage


class V309MethodShapeWitnessError(ValueError):
    pass


_COUNTS = {"v308": 10472, "v309": 10502}
_MIN_CODE_METHODS = 3
_MIN_JACCARD = 0.75


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _shapes(
    index: dict[str, Any], build: str,
) -> tuple[dict[str, tuple[tuple, Counter]], dict[tuple, list[str]]]:
    classes = index.get("classes")
    entries = index.get("entries")
    summary = index.get("summary")
    if (
        not isinstance(classes, dict) or not isinstance(entries, dict)
        or not isinstance(summary, dict)
        or len(classes) != _COUNTS[build]
        or summary.get("class_count") != _COUNTS[build]
        or summary.get("class_parse_error_count") != 0
    ):
        raise V309MethodShapeWitnessError(f"{build}: incomplete or unparsed exact class index")
    by_class: dict[str, tuple[tuple, Counter]] = {}
    field_buckets: dict[tuple, list[str]] = defaultdict(list)
    for path, record in classes.items():
        if (
            not isinstance(path, str) or not path.endswith(".class")
            or not isinstance(record, dict)
            or record.get("internal_name") != path[:-6]
            or not isinstance(entries.get(path), dict)
            or not isinstance(entries[path].get("sha256"), str)
        ):
            raise V309MethodShapeWitnessError(f"{build}: invalid class path/index record")
        fields = record.get("fields")
        methods = record.get("methods")
        if (
            not isinstance(fields, list) or not isinstance(methods, list)
            or len(fields) != record.get("field_count")
            or len(methods) != record.get("method_count")
        ):
            raise V309MethodShapeWitnessError(f"{build}: missing exact class members")
        f_shapes = []
        for field in fields:
            if (
                not isinstance(field, dict)
                or type(field.get("access")) is not int
                or not isinstance(field.get("descriptor"), str)
            ):
                raise V309MethodShapeWitnessError(f"{build}: malformed class field")
            f_shapes.append((field["access"], _descriptor_shape(field["descriptor"])))
        f_key = tuple(sorted(f_shapes))
        m_shapes: Counter = Counter()
        for method in methods:
            if (
                not isinstance(method, dict)
                or not isinstance(method.get("name"), str)
                or type(method.get("access")) is not int
                or not isinstance(method.get("descriptor"), str)
            ):
                raise V309MethodShapeWitnessError(f"{build}: malformed class method")
            if method["name"] in ("<init>", "<clinit>"):
                continue
            length = method.get("code_length")
            if length is None:
                continue  # abstract/native methods are never structural witnesses
            if type(length) is not int or length <= 0:
                raise V309MethodShapeWitnessError(f"{build}: invalid exact Code length")
            m_shapes[(method["access"], _descriptor_shape(method["descriptor"]), length)] += 1
        by_class[path] = (f_key, m_shapes)
        if len(f_key) >= 2 and sum(m_shapes.values()) >= _MIN_CODE_METHODS:
            field_buckets[f_key].append(path)
    return by_class, dict(field_buckets)


def _match(
    left: tuple[tuple, Counter], right: tuple[tuple, Counter],
) -> tuple[int, int] | None:
    if left[0] != right[0] or len(left[0]) < 2:
        return None
    intersection = sum((left[1] & right[1]).values())
    union = sum((left[1] | right[1]).values())
    if (
        intersection < _MIN_CODE_METHODS or union <= 0
        or intersection / union < _MIN_JACCARD
    ):
        return None
    return intersection, union


def build_v309_changed_class_method_shape_witness(
    global_report: dict[str, Any],
    class_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
) -> dict[str, Any]:
    if (
        global_report.get("kind") != "global_field_usage_identity_candidates"
        or global_report.get("canonical") is not False
        or global_report.get("old_build_id") != "v308"
        or global_report.get("new_build_id") != "v309"
        or len(global_report.get("review_outcomes", [])) != 143
        or global_report.get("summary", {}).get("descriptor_identity_guard_rejected") != 26
    ):
        raise V309MethodShapeWitnessError("requires pinned 143/26 v309 research report")
    validate_lineage(class_lineage)
    builds = {r["build_id"]: r["sha256"] for r in class_lineage["builds"]}
    for version, report_key, index in (
        ("v308", "old_sha256", old_index),
        ("v309", "new_sha256", new_index),
    ):
        sha = global_report.get(report_key)
        if (
            not isinstance(sha, str)
            or len(sha) != 64
            or index.get("sha256", "").lower() != sha.lower()
            or builds.get(version, "").lower() != sha.lower()
        ):
            raise V309MethodShapeWitnessError(f"{version}: exact SHA/lineage mismatch")
    deps = build_descriptor_class_dependency_report(global_report)
    if (
        deps["summary"]["blocking_old_class_identities"] != 8
        or deps["summary"]["blocked_fields"] != 26
    ):
        raise V309MethodShapeWitnessError("descriptor field-group accounting drift")
    old_shapes, old_buckets = _shapes(old_index, "v308")
    new_shapes, new_buckets = _shapes(new_index, "v309")
    lineage = {row["logical_id"]: row for row in class_lineage["classes"]}
    new_owners = {
        item["internal_name"]: row["logical_id"]
        for row in class_lineage["classes"]
        for item in row["lineage"] if item["build_id"] == "v309"
    }
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for dep in deps["class_dependencies"]:
        cid = dep["old_canonical_class_id"]
        entries = lineage[cid]["lineage"]
        olds = [r for r in entries if r["build_id"] == "v308"]
        news = [r for r in entries if r["build_id"] == "v309"]
        if len(olds) != 1 or news:
            raise V309MethodShapeWitnessError(f"{cid}: class lineage status drift")
        old = olds[0]
        new_desc = dep["new_raw_descriptors"]
        if (
            dep.get("state") != "UNPROVEN_NEW_CLASS_IDENTITY"
            or dep["old_raw_descriptors"] != ["L" + old["internal_name"] + ";"]
            or not isinstance(new_desc, list) or len(new_desc) != 1
            or not new_desc[0].startswith("Lrs/") or not new_desc[0].endswith(";")
        ):
            raise V309MethodShapeWitnessError(f"{cid}: invalid descriptor-derived research target")
        old_path = old["entry_path"]
        new_path = new_desc[0][1:-1] + ".class"
        old_record = old_index["classes"].get(old_path)
        old_entry = old_index["entries"].get(old_path)
        if (
            not isinstance(old_record, dict) or not isinstance(old_entry, dict)
            or old_record.get("structural_sha256", "").lower()
                != old["structural_sha256"].lower()
            or old_entry.get("sha256", "").lower() != old["entry_sha256"].lower()
        ):
            raise V309MethodShapeWitnessError(f"{cid}: pinned old class fingerprint drift")
        base = {
            "old_canonical_class_id": cid,
            "blocked_fields": dep["blocked_fields"],
            "blocked_relationship_ids": dep["relationship_ids"],
            "proposed_new_class": new_path[:-6],
        }
        def refuse(reason: str, **details: Any) -> None:
            rejected.append({**base, "reason": reason, **details})

        if new_path not in new_shapes:
            refuse("new_proposed_class_absent")
            continue
        if new_path[:-6] in new_owners:
            refuse("new_proposed_class_already_owned")
            continue
        new_entry = new_index["entries"][new_path]
        new_record = new_index["classes"][new_path]
        if (
            old_entry["sha256"].lower() == new_entry["sha256"].lower()
            or old_record["structural_sha256"].lower()
                == new_record["structural_sha256"].lower()
        ):
            refuse("not_a_changed_class_method_research_case")
            continue
        matched = _match(old_shapes[old_path], new_shapes[new_path])
        if matched is None:
            refuse("insufficient_exact_field_and_method_shape_overlap")
            continue
        fkey = old_shapes[old_path][0]
        possible_new = [
            path for path in new_buckets.get(fkey, ())
            if _match(old_shapes[old_path], new_shapes[path]) is not None
        ]
        possible_old = [
            path for path in old_buckets.get(fkey, ())
            if _match(old_shapes[path], new_shapes[new_path]) is not None
        ]
        if possible_new != [new_path] or possible_old != [old_path]:
            refuse(
                "bidirectional_whole_archive_uniqueness_failed",
                eligible_new_class_count=len(possible_new),
                eligible_old_class_count=len(possible_old),
            )
            continue
        intersection, union = matched
        candidates.append({
            **base,
            "strategy": "exact_method_code_length_and_field_shape_mutual_unique_research",
            "classification": "RESEARCH_CANDIDATE_NOT_ACCEPTED",
            "matched_code_method_shapes": intersection,
            "union_code_method_shapes": union,
            "field_shape_count": len(fkey),
            "jaccard": round(intersection / union, 6),
            "eligible_new_class_count": 1,
            "eligible_old_class_count": 1,
        })
    candidates.sort(key=lambda v: v["old_canonical_class_id"])
    rejected.sort(key=lambda v: v["old_canonical_class_id"])
    if len(candidates) + len(rejected) != 8:
        raise V309MethodShapeWitnessError("bidirectional class accounting drift")
    body = {
        "schema_version": 1,
        "kind": "v309_changed_class_method_shape_research",
        "canonical": False,
        "state": "MUTUAL_METHOD_SHAPE_WITNESS_NOT_CANONICAL_IDENTITY_PROOF",
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
            "candidate_blocked_fields": sum(x["blocked_fields"] for x in candidates),
            "rejected_classes": len(rejected),
            "remaining_blocked_fields": sum(x["blocked_fields"] for x in rejected),
            "accepted_unresolved_fields": 143,
            "canonical_identities_accepted": 0,
        },
        "candidates": candidates,
        "rejected": rejected,
        "note": (
            "Equal Java-access/erased-method-descriptor/exact-bytecode-length shapes "
            "are research context, not independently authenticated semantic class "
            "identity. Code byte sequences, method bodies, canonical lineage and "
            "dependent field mappings are NOT proved or modified."
        ),
    }
    return {"report_id": "V309METHODSHAPE_" + _digest(body)[:20].upper(), **body}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-v309-changed-class-method-shape-witness")
    p.add_argument("--v308-jar", type=Path, required=True)
    p.add_argument("--v309-jar", type=Path, required=True)
    p.add_argument("--frontier", type=Path, default=Path("research/v309-field-recovery/frontier.json"))
    p.add_argument("--class-lineage", type=Path, default=Path("research/v309-field-recovery/class-lineage.json"))
    p.add_argument("--global-report", type=Path, default=Path("research/v309-field-recovery/global-field-usage.json"))
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        frontier = _read_json_exact(a.frontier)
        if (
            frontier.get("kind") != "v309_recovery_frontier"
            or frontier.get("build_id") != "v309"
            or frontier.get("state") != "ACCEPTED_INCOMPLETE"
            or frontier.get("frontier", {}).get("unresolved") != 143
        ):
            raise V309MethodShapeWitnessError("wrong accepted incomplete v309 frontier")
        for key, path in (("class_lineage", a.class_lineage), ("global_field_usage", a.global_report)):
            sha = frontier.get("files", {}).get(key, {}).get("sha256")
            if not isinstance(sha, str) or len(sha) != 64 or sha256_file(path).lower() != sha.lower():
                raise V309MethodShapeWitnessError(f"{key}: tracked source hash drift")
        for build, path in (("v308", a.v308_jar), ("v309", a.v309_jar)):
            sha = frontier.get("exact_clients", {}).get(build + "_sha256")
            if not isinstance(sha, str) or len(sha) != 64 or sha256_file(path).lower() != sha.lower():
                raise V309MethodShapeWitnessError(f"{build}: exact private JAR hash drift")
        result = build_v309_changed_class_method_shape_witness(
            _read_json_exact(a.global_report), _read_json_exact(a.class_lineage),
            index_jar(a.v308_jar), index_jar(a.v309_jar),
        )
        write_research_report_no_clobber(
            result, a.out, (a.v308_jar, a.v309_jar, a.frontier, a.class_lineage, a.global_report),
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"SPK_V309_METHOD_SHAPE_WITNESS_FAIL: {exc}")
        return 1
    print("SPK_V309_METHOD_SHAPE_WITNESS_PASS_RESEARCH_ONLY")
    print(f"report_id={result['report_id']}")
    for key, value in result["summary"].items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
