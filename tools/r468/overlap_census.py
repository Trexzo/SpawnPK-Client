"""R468 complete, aggregate-only R455/R456 member-overlap census.

Given already decoded SHA-admitted R453 ClassMembers and R456 Sites, compute
the exact FULL unique intersection of in-graph non-platform opcode targets
and rebuilt-class member references. Unlike R466's early-exit gate, this
census never calls a partial result a complete count. Names/paths/bytecode
never leave this module or appear in returned records.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from tools.r388 import audit_offline_classpath as platform
from tools.r453 import classfile_member_reference as members
from tools.r456 import member_opcode_evidence as opcodes
from tools.r466 import adaptive_hierarchy as policy

MAX_REBUILT_REFERENCE_VISITS = 1_000_000
MAX_UNIQUE_MEMBER_REFERENCES = 220_000
MAX_GRAPH_RECORDS = 100_000
MAX_MEMBER_OPCODE_SITES = opcodes.MAX_TOTAL_SITES


class Refused(ValueError):
    pass


@dataclass(frozen=True)
class Census:
    rebuilt_class_records: int
    selected_dependency_records: int
    decoded_member_opcode_sites: int
    distinct_opcode_member_targets: int
    eligible_in_graph_opcode_targets: int
    rebuilt_reference_occurrences: int
    distinct_rebuilt_reference_targets: int
    exact_overlapping_distinct_targets: int
    exact_overlapping_opcode_site_occurrences: int
    exact_overlapping_owner_count: int
    threshold_2_met: bool
    threshold_4_met: bool
    threshold_8_met: bool
    threshold_16_met: bool
    complete_reference_enumeration: bool


def count(rebuilt: dict, selected: dict, sites) -> Census:
    """Fail closed on incomplete input, invalid hints or inventory budgets."""
    if (type(rebuilt) is not dict or type(selected) is not dict
            or type(sites) not in (list, tuple)
            or rebuilt.keys() & selected.keys()
            or len(rebuilt) + len(selected) > MAX_GRAPH_RECORDS
            or len(sites) > MAX_MEMBER_OPCODE_SITES):
        raise Refused("R468_CENSUS_INPUT_OR_GRAPH_BUDGET_INVALID")
    for name, record in tuple(rebuilt.items()) + tuple(selected.items()):
        if (type(name) is not str or type(record) is not members.ClassMembers
                or record.class_name != name):
            raise Refused("R468_CENSUS_CLASS_RECORD_INVALID")

    owners = rebuilt.keys() | selected.keys()
    opcode_counts: Counter[members.Member] = Counter()
    eligible: set[members.Member] = set()
    for site in sites:
        if type(site) is not opcodes.Site or type(site.target) is not members.Member:
            raise Refused("R468_CENSUS_UNSAFE_OPCODE_EVIDENCE")
        opcode_counts[site.target] += 1
        if (site.target.owner in owners and not
                site.target.owner.startswith(platform.PLATFORM_ROOTS)):
            eligible.add(site.target)

    referenced: set[members.Member] = set()
    total_reference_entries = 0
    matched: set[members.Member] = set()
    for record in rebuilt.values():
        for reference in record.references:
            total_reference_entries += 1
            if total_reference_entries > MAX_REBUILT_REFERENCE_VISITS:
                raise Refused("R468_CENSUS_REFERENCE_VISIT_BUDGET")
            if type(reference) is not members.Member:
                raise Refused("R468_CENSUS_UNSAFE_MEMBER_REFERENCE")
            referenced.add(reference)
            if len(referenced) > MAX_UNIQUE_MEMBER_REFERENCES:
                raise Refused("R468_CENSUS_UNIQUE_REFERENCE_BUDGET")
            if reference in eligible:
                matched.add(reference)
    overlap = len(matched)
    return Census(
        rebuilt_class_records=len(rebuilt),
        selected_dependency_records=len(selected),
        decoded_member_opcode_sites=len(sites),
        distinct_opcode_member_targets=len(opcode_counts),
        eligible_in_graph_opcode_targets=len(eligible),
        rebuilt_reference_occurrences=total_reference_entries,
        distinct_rebuilt_reference_targets=len(referenced),
        exact_overlapping_distinct_targets=overlap,
        exact_overlapping_opcode_site_occurrences=sum(
            opcode_counts[target] for target in matched),
        exact_overlapping_owner_count=len({x.owner for x in matched}),
        threshold_2_met=overlap >= 2,
        threshold_4_met=overlap >= 4,
        threshold_8_met=overlap >= 8,
        threshold_16_met=overlap >= 16,
        complete_reference_enumeration=True,
    )


def compare_with_gate(rebuilt: dict, selected: dict, sites,
                      *, threshold: int = 8):
    """Run independent R466 selector and refuse any inconsistent full census.

    Returns only a bool and immutable aggregate Census; the actual optimized
    analyzers still perform independent R464 record identity admission.
    """
    whole = count(rebuilt, selected, sites)
    decision = policy.choose(
        rebuilt, selected, sites, threshold=threshold)
    if not decision.bounded_probe and decision.use_cache != (
            whole.exact_overlapping_distinct_targets >= threshold):
        raise Refused("R468_SELECTOR_VS_COMPLETE_CENSUS_DISAGREEMENT")
    return decision.use_cache, whole
