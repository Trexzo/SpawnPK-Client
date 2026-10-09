from __future__ import annotations

"""One-shot exact-private v309 five-lane replay; research and review ONLY.

The pinned private JARs and class indexes never leave this process. The only
file written is one new, privacy-bounded multilane concordance JSON; no
intermediate index, method fingerprints, literal table or JAR is exported.
"""

import argparse
from pathlib import Path
from typing import Any

from .descriptor_class_private_jar_replay import (
    _read_json_exact, write_research_report_no_clobber,
)
from .indexer import index_jar, sha256_file
from .lineage import validate_lineage
from .v309_changed_class_literal_witness import build_v309_changed_class_literal_witness
from .v309_changed_class_method_shape_witness import build_v309_changed_class_method_shape_witness
from .v309_cp_method_referent_research import build_v309_cp_method_research
from .v309_cp_whole_archive_rival_research import build_v309_cp_rival_witness
from .v309_pinned_structural_audit import build_v309_pinned_structural_audit
from .v309_multilane_concordance import build_v309_multilane_concordance


class V309PrivateConcordanceReplayError(ValueError):
    pass


def _pinned_sha(frontier: dict[str, Any], key: str, file_path: Path) -> None:
    expected = frontier.get("files", {}).get(key, {}).get("sha256")
    if (
        not isinstance(expected, str) or len(expected) != 64
        or sha256_file(file_path).lower() != expected.lower()
    ):
        raise V309PrivateConcordanceReplayError(
            f"protected tracked {key} SHA mismatch"
        )


def run_v309_exact_private_concordance(
    old_jar: Path,
    new_jar: Path,
    frontier_path: Path,
    lineage_path: Path,
    global_report_path: Path,
) -> dict[str, Any]:
    """Compute the five independent reports in memory, then join them.

    No intermediate private files are written. A positive review bucket is
    *never* a canonical class/field identity acceptance.
    """
    frontier = _read_json_exact(frontier_path)
    if (
        frontier.get("kind") != "v309_recovery_frontier"
        or frontier.get("state") != "ACCEPTED_INCOMPLETE"
        or frontier.get("build_id") != "v309"
        or frontier.get("frontier", {}).get("unresolved") != 143
        or frontier.get("frontier", {}).get("descriptor_identity_guard_rejected") != 26
    ):
        raise V309PrivateConcordanceReplayError("expected protected 143/26 incomplete frontier")
    _pinned_sha(frontier, "class_lineage", lineage_path)
    _pinned_sha(frontier, "global_field_usage", global_report_path)

    exact = frontier.get("exact_clients", {})
    if not isinstance(exact, dict):
        raise V309PrivateConcordanceReplayError("missing protected exact clients")
    for name, path in (("v308", old_jar), ("v309", new_jar)):
        expected = exact.get(name + "_sha256")
        if (
            not isinstance(expected, str) or len(expected) != 64
            or sha256_file(path).lower() != expected.lower()
        ):
            raise V309PrivateConcordanceReplayError(f"{name}: private client hash mismatch")

    lineage = _read_json_exact(lineage_path)
    report = _read_json_exact(global_report_path)
    validate_lineage(lineage)
    builds = {row["build_id"]: row["sha256"] for row in lineage["builds"]}
    if (
        set(builds) != {"v308", "v309"}
        or any(builds[b].lower() != exact[b + "_sha256"].lower() for b in builds)
        or report.get("report_id") != (
            frontier.get("files", {}).get("global_field_usage", {}).get("report_id")
        )
        or report.get("kind") != "global_field_usage_identity_candidates"
        or report.get("canonical") is not False
        or report.get("summary", {}).get("descriptor_identity_guard_rejected") != 26
        or len(report.get("review_outcomes", [])) != 143
        or report.get("old_sha256", "").lower() != exact["v308_sha256"].lower()
        or report.get("new_sha256", "").lower() != exact["v309_sha256"].lower()
    ):
        raise V309PrivateConcordanceReplayError("protected lineage/global report authority drift")

    # Check the strongest prerequisite first. Exact previously pinned class
    # fingerprints must remain intact under lossless Modified UTF-8 parsing.
    structural = build_v309_pinned_structural_audit(
        frontier, lineage, old_jar, new_jar
    )
    if (
        structural.get("canonical") is not False
        or structural.get("state") !=
            "PINNED_STRUCTURAL_FINGERPRINTS_EXACT_MATCH_RESEARCH_ONLY"
        or structural.get("summary", {}).get("structural_hash_drifts") != 0
        or structural.get("summary", {}).get("structural_hash_matches") != 2221
    ):
        raise V309PrivateConcordanceReplayError(
            "pinned structural fingerprint mismatch requires separate review"
        )

    # Two archive indexes are private in-memory inputs only; no index output.
    old_index = index_jar(old_jar)
    new_index = index_jar(new_jar)
    for build, archive_index in (("v308", old_index), ("v309", new_index)):
        if (
            archive_index.get("sha256", "").lower() !=
                exact[build + "_sha256"].lower()
            or archive_index.get("summary", {}).get("class_parse_error_count") != 0
            or archive_index.get("summary", {}).get("class_count") !=
                (10472 if build == "v308" else 10502)
        ):
            raise V309PrivateConcordanceReplayError(
                f"{build}: incomplete or drifted private archive index"
            )

    literal = build_v309_changed_class_literal_witness(
        report, lineage, old_index, new_index
    )
    method_shape = build_v309_changed_class_method_shape_witness(
        report, lineage, old_index, new_index
    )

    # These two lanes deliberately use the existing strict code/CP profiler.
    # #879's rival witness internally reproduces the #878 pair report; its
    # exact provenance ID is checked by the final concordance joiner.
    cp_pair = build_v309_cp_method_research(
        frontier, report, lineage, old_jar, new_jar
    )
    cp_rivals = build_v309_cp_rival_witness(
        frontier, report, lineage, old_jar, new_jar,
        precomputed_old_index=old_index,
        precomputed_new_index=new_index,
        precomputed_pairwise=cp_pair,
    )
    concordance = build_v309_multilane_concordance(
        frontier, lineage, report,
        literal, method_shape, cp_pair, cp_rivals, structural,
    )
    summary = concordance.get("summary", {})
    if (
        concordance.get("canonical") is not False
        or concordance.get("state") != "CONCORDANCE_ONLY_NO_CLASS_OR_FIELD_ACCEPTANCE"
        or summary.get("descriptor_class_groups") != 8
        or summary.get("blocked_field_relationships") != 26
        or summary.get("canonical_unresolved_field_relationships") != 143
        or summary.get("canonical_class_identities_accepted") != 0
        or summary.get("canonical_field_identities_accepted") != 0
    ):
        raise V309PrivateConcordanceReplayError("multilane research-only boundary drift")
    return concordance


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-v309-exact-private-five-lane-replay")
    p.add_argument("--v308-jar", required=True, type=Path)
    p.add_argument("--v309-jar", required=True, type=Path)
    p.add_argument("--frontier", type=Path,
                   default=Path("research/v309-field-recovery/frontier.json"))
    p.add_argument("--class-lineage", type=Path,
                   default=Path("research/v309-field-recovery/class-lineage.json"))
    p.add_argument("--global-report", type=Path,
                   default=Path("research/v309-field-recovery/global-field-usage.json"))
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    protected = (
        a.v308_jar, a.v309_jar, a.frontier, a.class_lineage, a.global_report,
    )
    try:
        if a.out.exists() or a.out.is_symlink():
            raise V309PrivateConcordanceReplayError("research output path already exists")
        if any(a.out.resolve() == input_path.resolve() for input_path in protected):
            raise V309PrivateConcordanceReplayError("output overlaps protected input")
        result = run_v309_exact_private_concordance(
            a.v308_jar, a.v309_jar, a.frontier,
            a.class_lineage, a.global_report,
        )
        write_research_report_no_clobber(result, a.out, protected)
    except Exception as exc:
        # Upstream parser errors may embed private class names, CP literals,
        # archive locations or method descriptors: do NOT print them or their
        # tracebacks from the aggregate one-shot privacy boundary.
        print("SPK_V309_PRIVATE_REPLAY_FAIL_CLOSED")
        print("error_category=" + type(exc).__name__)
        print("no_canonical_changes=True")
        return 1
    print("SPK_V309_PRIVATE_REPLAY_PASS_RESEARCH_ONLY")
    print("report_id=" + result["report_id"])
    for key, value in result["summary"].items():
        if type(value) is int:
            print(key + "=" + str(value))
    print("no_canonical_changes=True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
