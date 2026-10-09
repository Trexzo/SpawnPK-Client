from __future__ import annotations

"""Research-only exact-JAR CP method witness rival-owner veto.

The coarse whole-archive shape filter is a provable SUPERSET of any class
sharing >=3 exact CP-bearing method fingerprints; it is never used to ACCEPT
a class identity. All candidate owner mappings remain research hypotheses.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Callable
import zipfile

from .bytecode_profile import BytecodeProfileError, profile_class_field_accesses
from .classfile import _descriptor_shape
from .descriptor_class_dependencies import build_descriptor_class_dependency_report
from .descriptor_class_private_jar_replay import _read_json_exact, write_research_report_no_clobber
from .indexer import index_jar, sha256_file
from .v309_cp_method_referent_research import (
    V309CpMethodWitnessError,
    _method_semantics,
    build_v309_cp_method_research,
)


class V309CpRivalWitnessError(ValueError):
    pass


_PINNED_CLASS_COUNTS = {"v308": 10472, "v309": 10502}
_MIN_INDEPENDENT_METHODS = 3
_MAX_PREFILTER_CLASSES = 500
_SELF_ALIAS = "@SPK_PROPOSED_SELF@"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _coarse(record: dict[str, Any]) -> Counter:
    """Necessary (never sufficient) prefilter for 3 full CP fingerprints."""
    if not isinstance(record, dict) or not isinstance(record.get("methods"), list):
        raise V309CpRivalWitnessError("missing indexed class methods")
    shapes: Counter = Counter()
    for method in record["methods"]:
        if not isinstance(method, dict):
            raise V309CpRivalWitnessError("malformed indexed method")
        if method.get("name") in ("<init>", "<clinit>"):
            continue
        n = method.get("code_length")
        if n is None:
            continue
        access = method.get("access")
        desc = method.get("descriptor")
        if (
            type(n) is not int or n <= 0
            or type(access) is not int
            or not isinstance(desc, str)
        ):
            raise V309CpRivalWitnessError("invalid indexed method shape")
        shapes[(access, _descriptor_shape(desc), n)] += 1
    return shapes


def _coarse_intersection(a: Counter, b: Counter) -> int:
    # A shared exact CP semantic method necessarily shares all three fields.
    return sum((a & b).values())


def _cp_fingerprints(profile: dict[str, Any]) -> dict[str, Any]:
    owner = profile.get("internal_name")
    methods = profile.get("methods")
    bootstraps = profile.get("bootstrap_methods")
    if (
        not isinstance(owner, str)
        or not isinstance(methods, list)
        or not isinstance(bootstraps, list)
    ):
        raise V309CpRivalWitnessError("malformed decoded class profile")
    unique: Counter = Counter()
    unsupported = 0
    non_cp = 0
    for m in methods:
        if not isinstance(m, dict):
            raise V309CpRivalWitnessError("malformed decoded method")
        if m.get("name") in ("<init>", "<clinit>") or m.get("code_length") is None:
            continue
        try:
            signature, cp_refs = _method_semantics(
                m, bootstraps, old_owner=owner, new_owner=_SELF_ALIAS,
            )
        except V309CpMethodWitnessError:
            unsupported += 1
            continue
        if cp_refs < 1:
            non_cp += 1
            continue
        unique[signature] += 1
    return {
        "fingerprints": unique,
        "eligible": sum(unique.values()),
        "unsupported": unsupported,
        "non_cp": non_cp,
    }


def _unique_cp_matches(a: Counter, b: Counter) -> int:
    return sum(
        1 for shape in a.keys() & b.keys()
        if a[shape] == 1 and b[shape] == 1
    )


def _scan_direction(
    source: dict[str, Any],
    source_coarse: Counter,
    exact_proposed_path: str,
    whole_target: dict[str, Counter],
    fetch_profile: Callable[[str], dict[str, Any] | None],
    *,
    maximum: int = _MAX_PREFILTER_CLASSES,
) -> dict[str, Any]:
    """Check every coarse-viable rival without exporting identifying bytecode."""
    pool = [
        path for path, coarse in whole_target.items()
        if _coarse_intersection(source_coarse, coarse) >= _MIN_INDEPENDENT_METHODS
    ]
    pool.sort()
    result: dict[str, Any] = {
        "coarse_viable_classes": len(pool),
        "unsupported_target_classes": 0,
        "qualified_rivals": 0,
        "proposed_target_qualified": False,
        "exhaustive_supported_scan": False,
    }
    if exact_proposed_path not in whole_target:
        result["state"] = "PROPOSED_CLASS_MISSING"
        return result
    if exact_proposed_path not in pool:
        result["state"] = "PROPOSED_CLASS_FAILS_NECESSARY_COARSE_GATE"
        return result
    if len(pool) > maximum:
        result["state"] = "PREFILTER_TOO_BROAD_NO_UNIQUENESS_CLAIM"
        return result

    for path in pool:
        other = fetch_profile(path)
        if other is None:
            result["unsupported_target_classes"] += 1
            continue
        if path == exact_proposed_path:
            # Positive evidence requires distinct fingerprints occurring
            # exactly once within EACH class; ambiguous duplicates never
            # establish an identifiable method witness.
            if _unique_cp_matches(
                source["fingerprints"], other["fingerprints"],
            ) >= _MIN_INDEPENDENT_METHODS:
                result["proposed_target_qualified"] = True
        else:
            # Negative evidence is deliberately MORE conservative:
            # duplicate CP-bearing method fingerprints still represent a
            # competing owner. Never suppress a possible rival merely
            # because its methods are ambiguous.
            if sum((source["fingerprints"] & other["fingerprints"]).values()) >= _MIN_INDEPENDENT_METHODS:
                result["qualified_rivals"] += 1

    result["exhaustive_supported_scan"] = True
    if result["unsupported_target_classes"]:
        result["state"] = "UNSCANNABLE_COARSE_RIVALS_NO_UNIQUENESS_CLAIM"
    elif result["qualified_rivals"]:
        result["state"] = "RIVAL_CLASS_CP_WITNESS_VETO"
    elif not result["proposed_target_qualified"]:
        result["state"] = "INSUFFICIENT_PROPOSED_CP_METHOD_WITNESSES"
    else:
        result["state"] = "NO_QUALIFYING_RIVAL_IN_FULL_COARSE_SUPERSET_RESEARCH_ONLY"
    return result


def _indexed_shapes(
    index: dict[str, Any], version: str, expected_sha: str,
) -> dict[str, Counter]:
    classes = index.get("classes")
    summary = index.get("summary")
    if (
        index.get("sha256", "").lower() != expected_sha.lower()
        or not isinstance(classes, dict)
        or not isinstance(summary, dict)
        or summary.get("class_count") != _PINNED_CLASS_COUNTS[version]
        or summary.get("class_parse_error_count") != 0
        or len(classes) != _PINNED_CLASS_COUNTS[version]
    ):
        raise V309CpRivalWitnessError(
            f"{version}: exact complete class index missing or drifted"
        )
    ret: dict[str, Counter] = {}
    for entry, record in classes.items():
        if (
            not isinstance(entry, str) or not entry.endswith(".class")
            or not isinstance(record, dict)
            or record.get("internal_name") != entry[:-6]
        ):
            raise V309CpRivalWitnessError("invalid whole-archive indexed class")
        ret[entry] = _coarse(record)
    return ret


def build_v309_cp_rival_witness(
    frontier: dict[str, Any],
    global_report: dict[str, Any],
    lineage: dict[str, Any],
    old_jar: Path, new_jar: Path,
) -> dict[str, Any]:
    # Reuse the parent research gate for all pinned exact SHA/lineage,
    # canonical old-entry fingerprints, descriptor groups, and proposal state.
    pairwise = build_v309_cp_method_research(
        frontier, global_report, lineage, old_jar, new_jar,
    )
    if (
        pairwise.get("kind") != "v309_cp_method_referent_pairwise_research"
        or pairwise.get("canonical") is not False
        or pairwise.get("summary", {}).get("reviewed_descriptor_class_pairs") != 8
        or pairwise["summary"].get("class_identities_accepted") != 0
        or pairwise["summary"].get("accepted_frontier_unresolved") != 143
    ):
        raise V309CpRivalWitnessError("exact CP pairwise baseline drift")
    old_index = index_jar(old_jar)
    new_index = index_jar(new_jar)
    old_shapes = _indexed_shapes(old_index, "v308", pairwise["old_sha256"])
    new_shapes = _indexed_shapes(new_index, "v309", pairwise["new_sha256"])
    deps = build_descriptor_class_dependency_report(global_report)
    if (
        deps["summary"]["blocking_old_class_identities"] != 8
        or deps["summary"]["blocked_fields"] != 26
    ):
        raise V309CpRivalWitnessError("descriptor class queue changed")
    classes = {x["logical_id"]: x for x in lineage["classes"]}
    cache: dict[tuple[str, str], dict[str, Any] | None] = {}
    scan_errors = 0
    with zipfile.ZipFile(old_jar) as old_archive, zipfile.ZipFile(new_jar) as new_archive:
        def retrieve(build: str, path: str) -> dict[str, Any] | None:
            nonlocal scan_errors
            key = (build, path)
            if key in cache:
                return cache[key]
            archive = old_archive if build == "v308" else new_archive
            try:
                profile = profile_class_field_accesses(archive.read(path))
                if profile.get("internal_name") != path[:-6]:
                    raise V309CpRivalWitnessError("archive entry owner mismatch")
                entry = _cp_fingerprints(profile)
            except (OSError, KeyError, ValueError, BytecodeProfileError) as exc:
                # A plausible competing class that cannot be completely
                # decoded is a VETO to a uniqueness claim, not an omission.
                scan_errors += 1
                entry = None
            cache[key] = entry
            return entry

        rows = []
        for dep in deps["class_dependencies"]:
            cid = dep["old_canonical_class_id"]
            old_rows = [
                x for x in classes[cid]["lineage"] if x["build_id"] == "v308"
            ]
            if len(old_rows) != 1 or any(
                x["build_id"] == "v309" for x in classes[cid]["lineage"]
            ):
                raise V309CpRivalWitnessError(f"{cid}: canonical lineage changed")
            old_path = old_rows[0]["entry_path"]
            desc = dep["new_raw_descriptors"]
            if len(desc) != 1:
                raise V309CpRivalWitnessError(f"{cid}: proposed descriptor ambiguous")
            new_path = desc[0][1:-1] + ".class"
            old_profile = retrieve("v308", old_path)
            new_profile = retrieve("v309", new_path)
            row: dict[str, Any] = {
                "old_canonical_class_id": cid,
                "blocked_fields": dep["blocked_fields"],
                "research_only": True,
                "canonical_identity_accepted": False,
            }
            if old_profile is None or new_profile is None:
                row["state"] = "PROPOSED_PAIR_COULD_NOT_BE_DECODED"
                rows.append(row)
                continue
            observed = _unique_cp_matches(
                old_profile["fingerprints"], new_profile["fingerprints"],
            )
            row.update({
                "proposed_pair_unique_cp_method_matches": observed,
                "old_supported_methods": old_profile["eligible"],
                "new_supported_methods": new_profile["eligible"],
                "old_unsupported_methods": old_profile["unsupported"],
                "new_unsupported_methods": new_profile["unsupported"],
            })
            if observed < _MIN_INDEPENDENT_METHODS:
                row["state"] = "PROPOSED_PAIR_INSUFFICIENT_WITNESSES"
                rows.append(row)
                continue

            new_direction = _scan_direction(
                old_profile, old_shapes[old_path], new_path,
                new_shapes, lambda p: retrieve("v309", p),
            )
            old_direction = _scan_direction(
                new_profile, new_shapes[new_path], old_path,
                old_shapes, lambda p: retrieve("v308", p),
            )
            row["old_to_all_new"] = new_direction
            row["new_to_all_old"] = old_direction
            row["state"] = (
                "MUTUAL_WHOLE_ARCHIVE_SUPPORTED_SUBSET_RESEARCH_ONLY"
                if all(
                    d["state"] ==
                    "NO_QUALIFYING_RIVAL_IN_FULL_COARSE_SUPERSET_RESEARCH_ONLY"
                    for d in (new_direction, old_direction)
                ) else "MUTUAL_CP_RIVAL_PROOF_NOT_AVAILABLE"
            )
            rows.append(row)

    rows.sort(key=lambda x: x["old_canonical_class_id"])
    if len(rows) != 8 or sum(x["blocked_fields"] for x in rows) != 26:
        raise V309CpRivalWitnessError("8/26 class frontier accounting failed")
    summary = {
        "examined_descriptor_classes": 8,
        "blocked_field_relationships_preserved": 26,
        "whole_archive_class_count_v308": _PINNED_CLASS_COUNTS["v308"],
        "whole_archive_class_count_v309": _PINNED_CLASS_COUNTS["v309"],
        "candidate_supported_subset_mutual_unique": sum(
            x["state"] == "MUTUAL_WHOLE_ARCHIVE_SUPPORTED_SUBSET_RESEARCH_ONLY"
            for x in rows
        ),
        "unsupported_competing_class_decodes": scan_errors,
        "class_identities_accepted": 0,
        "member_identities_accepted": 0,
        "canonical_unresolved_fields": 143,
    }
    body = {
        "schema_version": 1,
        "kind": "v309_cp_method_whole_archive_rival_research",
        "canonical": False,
        "state": "RESEARCH_ONLY_NO_CLASS_OR_MEMBER_ACCEPTANCE",
        "old_sha256": pairwise["old_sha256"],
        "new_sha256": pairwise["new_sha256"],
        "source_cp_pair_report_id": pairwise["report_id"],
        "source_global_field_report_id": global_report["report_id"],
        "summary": summary,
        "rows": rows,
        "note": (
            "Covers all classes in each exact archive through a necessary coarse "
            "superset and exact CP-referent comparison of supported methods. "
            "A positive state is only mutual uniqueness of the SUPPORTED "
            "CP-bearing method subset; unsupported opcodes, renamed external "
            "owners/members, unmatched methods, methods without CP references, "
            "duplicate fingerprints and source selection remain unresolved. "
            "No canonical class or field identities are established."
        ),
    }
    return {"report_id": "V309CPRIVALS_" + _digest(body)[:20].upper(), **body}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-v309-cp-whole-archive-rival-research")
    p.add_argument("--v308-jar", type=Path, required=True)
    p.add_argument("--v309-jar", type=Path, required=True)
    p.add_argument("--frontier", type=Path,
                   default=Path("research/v309-field-recovery/frontier.json"))
    p.add_argument("--class-lineage", type=Path,
                   default=Path("research/v309-field-recovery/class-lineage.json"))
    p.add_argument("--global-report", type=Path,
                   default=Path("research/v309-field-recovery/global-field-usage.json"))
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        frontier = _read_json_exact(args.frontier)
        for label, path in (
            ("class_lineage", args.class_lineage),
            ("global_field_usage", args.global_report),
        ):
            pinned = frontier.get("files", {}).get(label, {}).get("sha256")
            if (
                not isinstance(pinned, str) or len(pinned) != 64
                or sha256_file(path).lower() != pinned.lower()
            ):
                raise V309CpRivalWitnessError(f"{label}: tracked report SHA drift")
        result = build_v309_cp_rival_witness(
            frontier, _read_json_exact(args.global_report),
            _read_json_exact(args.class_lineage),
            args.v308_jar, args.v309_jar,
        )
        write_research_report_no_clobber(
            result, args.out,
            (args.v308_jar, args.v309_jar, args.frontier,
             args.class_lineage, args.global_report),
        )
    except (OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile) as exc:
        print(f"SPK_V309_CP_RIVALS_FAIL: {exc}")
        return 1
    print("SPK_V309_CP_RIVALS_PASS_RESEARCH_ONLY")
    print("report_id=" + result["report_id"])
    for key, val in result["summary"].items():
        print(f"{key}={val}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
