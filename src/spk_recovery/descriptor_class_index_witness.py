from __future__ import annotations

"""Independent, index-bound witnesses for descriptor-blocked class identities.

Only proposes reviewable v308->v309 class links. Never mutates either lineage
or bypasses the field descriptor-identity veto.
"""

from collections import defaultdict
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .lineage import validate_lineage


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


def _index_hits(index: dict[str, Any], key: str, *, entry: bool) -> dict[str, list[str]]:
    classes = index.get("classes")
    entries = index.get("entries")
    if not isinstance(classes, dict) or not isinstance(entries, dict):
        raise ValueError("index requires complete classes and entries objects")
    hits: dict[str, list[str]] = defaultdict(list)
    for path, record in classes.items():
        if not isinstance(path, str) or not path.endswith(".class") or not isinstance(record, dict):
            raise ValueError("invalid index class entry")
        if record.get("internal_name") != path[:-6]:
            raise ValueError(f"index path/name mismatch: {path}")
        value = entries.get(path) if entry else record
        if not isinstance(value, dict):
            raise ValueError(f"index entry missing: {path}")
        fingerprint = value.get(key)
        if not isinstance(fingerprint, str) or len(fingerprint) != 64:
            raise ValueError(f"missing index {key}: {path}")
        try:
            int(fingerprint, 16)
        except ValueError as exc:
            raise ValueError(f"invalid index {key}: {path}") from exc
        hits[fingerprint.lower()].append(path)
    return dict(hits)


def _single(hits: dict[str, list[str]], key: str) -> str | None:
    paths = hits.get(key.lower(), [])
    return paths[0] if len(paths) == 1 else None


def build_descriptor_class_index_witness(
    dependency_report: dict[str, Any],
    class_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
) -> dict[str, Any]:
    if (
        dependency_report.get("schema_version") != 1
        or dependency_report.get("kind") != "v309_descriptor_class_dependency_research_queue"
        or dependency_report.get("state") != "RESEARCH_ONLY_NO_IDENTITIES_ACCEPTED"
        or dependency_report.get("old_build_id") != "v308"
        or dependency_report.get("new_build_id") != "v309"
    ):
        raise ValueError("wrong v309 descriptor dependency input")
    from .descriptor_class_dependencies import build_descriptor_class_dependency_report
    # The inventory may only be constructed from the actual global report; it
    # cannot stand alone as accepted identity evidence. This function binds it
    # to independently validated indexes and class-lineage hashes.
    validate_lineage(class_lineage)
    builds = {
        row["build_id"]: row for row in class_lineage["builds"]
    }
    for build_id, index in (("v308", old_index), ("v309", new_index)):
        pinned = builds.get(build_id, {}).get("sha256")
        actual = index.get("sha256")
        if (
            not isinstance(pinned, str) or not isinstance(actual, str)
            or pinned.lower() != actual.lower()
        ):
            raise ValueError(f"{build_id} index SHA-256 differs from class lineage")

    deps = dependency_report.get("class_dependencies")
    if not isinstance(deps, list):
        raise ValueError("missing descriptor dependency rows")
    if (
        dependency_report.get("summary", {}).get("blocking_old_class_identities")
        != len(deps)
    ):
        raise ValueError("dependency inventory group count mismatch")
    if sum(row.get("blocked_fields", 0) for row in deps) != (
        dependency_report.get("summary", {}).get("blocked_fields")
    ):
        raise ValueError("dependency inventory field count mismatch")

    records = {c["logical_id"]: c for c in class_lineage["classes"]}
    old_sha = _index_hits(old_index, "sha256", entry=True)
    new_sha = _index_hits(new_index, "sha256", entry=True)
    old_struct = _index_hits(old_index, "structural_sha256", entry=False)
    new_struct = _index_hits(new_index, "structural_sha256", entry=False)
    already_mapped = {
        entry["internal_name"]: c["logical_id"]
        for c in class_lineage["classes"]
        for entry in c["lineage"]
        if entry["build_id"] == "v309"
    }

    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    visited: set[str] = set()
    for group in deps:
        cid = group.get("old_canonical_class_id")
        if not isinstance(cid, str) or cid in visited or cid not in records:
            raise ValueError(f"missing or duplicate class dependency: {cid}")
        visited.add(cid)
        if (
            group.get("state") != "UNPROVEN_NEW_CLASS_IDENTITY"
            or type(group.get("blocked_fields")) is not int
            or group["blocked_fields"] <= 0
            or len(group.get("relationship_ids", [])) != group["blocked_fields"]
            or len(set(group["relationship_ids"])) != group["blocked_fields"]
        ):
            raise ValueError(f"{cid}: malformed or already accepted dependency")
        lineage_entries = records[cid]["lineage"]
        old_rows = [e for e in lineage_entries if e["build_id"] == "v308"]
        new_rows = [e for e in lineage_entries if e["build_id"] == "v309"]
        if len(old_rows) != 1:
            raise ValueError(f"{cid}: expected exactly one old lineage coordinate")
        old = old_rows[0]
        old_path = old["entry_path"]
        old_name = old["internal_name"]
        old_entry = old_index["entries"].get(old_path)
        old_cls = old_index["classes"].get(old_path)
        if (
            not isinstance(old_entry, dict) or not isinstance(old_cls, dict)
            or old_entry.get("sha256", "").lower() != old["entry_sha256"].lower()
            or old_cls.get("structural_sha256", "").lower() != old["structural_sha256"].lower()
            or old_cls.get("internal_name") != old_name
            or group.get("old_raw_descriptors") != ["L" + old_name + ";"]
        ):
            raise ValueError(f"{cid}: old lineage/index/descriptor binding drift")

        base = {
            "old_canonical_class_id": cid,
            "old_class": old_name,
            "blocked_relationship_ids": group["relationship_ids"],
            "blocked_fields": group["blocked_fields"],
        }
        def reject(reason: str, **details: Any) -> None:
            rejected.append({**base, "reason": reason, **details})

        if new_rows:
            reject("class_already_paired_requires_replay")
            continue
        new_names = group.get("new_raw_descriptors")
        if not isinstance(new_names, list) or len(new_names) != 1:
            reject("ambiguous_new_descriptor")
            continue
        descriptor = new_names[0]
        if not isinstance(descriptor, str) or not descriptor.startswith("Lrs/") or not descriptor.endswith(";"):
            reject("non_rs_new_descriptor")
            continue
        expected_new_path = descriptor[1:-1] + ".class"
        if expected_new_path not in new_index["classes"]:
            reject("referenced_new_class_absent_from_index")
            continue
        if expected_new_path in already_mapped:
            reject(
                "new_class_already_owned",
                owner_logical_id=already_mapped[expected_new_path[:-6]],
            )
            continue

        exact_candidate = (
            _single(old_sha, old["entry_sha256"])
            if _single(new_sha, old["entry_sha256"]) is not None
            else None
        )
        exact_new = _single(new_sha, old["entry_sha256"])
        structural_old = _single(old_struct, old["structural_sha256"])
        structural_new = _single(new_struct, old["structural_sha256"])
        strategy = None
        proof_value = None
        proven_new = None
        if exact_candidate == old_path and exact_new is not None:
            strategy = "globally_unique_exact_entry_sha256"
            proof_value = old["entry_sha256"].lower()
            proven_new = exact_new
        elif structural_old == old_path and structural_new is not None:
            strategy = "globally_unique_structural_sha256_research"
            proof_value = old["structural_sha256"].lower()
            proven_new = structural_new
        if strategy is None:
            reject("no_independent_global_index_identity_witness")
            continue
        if proven_new != expected_new_path:
            reject(
                "independent_witness_disagrees_with_field_descriptor",
                witness_new_class=proven_new[:-6],
            )
            continue
        if proven_new in already_mapped:
            reject("new_class_already_owned", owner_logical_id=already_mapped[proven_new[:-6]])
            continue

        candidates.append({
            **base,
            "proposed_new_class": proven_new[:-6],
            "strategy": strategy,
            "proof_fingerprint": proof_value,
            "classification": "RESEARCH_CANDIDATE_NOT_ACCEPTED",
            "old_index_sha256": old_index["sha256"],
            "new_index_sha256": new_index["sha256"],
            "new_entry_sha256": new_index["entries"][proven_new]["sha256"],
            "new_structural_sha256": new_index["classes"][proven_new]["structural_sha256"],
            "independent_global_uniqueness": True,
        })
    candidates.sort(key=lambda x: x["old_canonical_class_id"])
    rejected.sort(key=lambda x: x["old_canonical_class_id"])
    if len(candidates) + len(rejected) != len(deps):
        raise ValueError("class witness accounting error")
    return {
        "schema_version": 1,
        "kind": "v309_descriptor_class_index_witness_research",
        "canonical": False,
        "state": "CANDIDATES_REQUIRE_INDEPENDENT_REVIEW_NO_ACCEPTANCE",
        "dependency_report_digest": _digest(dependency_report),
        "class_lineage_digest": _digest(class_lineage),
        "old_index_sha256": old_index["sha256"],
        "new_index_sha256": new_index["sha256"],
        "summary": {
            "input_class_dependencies": len(deps),
            "candidate_classes": len(candidates),
            "rejected_classes": len(rejected),
            "candidate_fields_blocked": sum(x["blocked_fields"] for x in candidates),
            "still_blocked_fields": sum(x["blocked_fields"] for x in rejected),
        },
        "candidates": candidates,
        "rejected": rejected,
        "note": "Global index uniqueness is evidence, not class-lineage authority. Raw descriptor/name equality alone is never a witness; no class or field lineage is modified.",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-v309-descriptor-class-index-witness")
    for name in ("dependency_report", "class_lineage", "old_index", "new_index"):
        p.add_argument(name, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        values = [
            json.loads(getattr(args, name).read_text(encoding="utf-8"))
            for name in ("dependency_report", "class_lineage", "old_index", "new_index")
        ]
        result = build_descriptor_class_index_witness(*values)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"SPK_V309_DESCRIPTOR_CLASS_INDEX_WITNESS_FAIL: {exc}")
        return 1
    print("SPK_V309_DESCRIPTOR_CLASS_INDEX_WITNESS_PASS")
    for key, value in result["summary"].items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
