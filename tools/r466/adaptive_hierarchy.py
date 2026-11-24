"""R466 conservative no-cache gate for low/no-overlap R455/R456 graphs.

This only chooses whether to enable R464's optional ephemeral hierarchy cache.
It NEVER makes a correctness, authorization, classpath, or release decision.
Both analyzers retain their independent validation and refusal behavior.
No private name, source byte, JAR, hash or path is retained by the decision.
"""
from __future__ import annotations

from dataclasses import dataclass

from tools.r388 import audit_offline_classpath as platform
from tools.r453 import classfile_member_reference as members
from tools.r456 import member_opcode_evidence as opcode

MIN_SHARED_UNIQUE_TARGETS = 16
MAX_SITE_HINTS = opcode.MAX_TOTAL_SITES
MAX_REFERENCE_VISITS = 500_000


class Refused(ValueError):
    pass


@dataclass(frozen=True)
class Decision:
    use_cache: bool
    overlapping_unique_targets: int
    required_unique_targets: int
    candidate_unique_opcode_targets: int
    reference_visits: int
    bounded_probe: bool
    reason: str


def choose(rebuilt: dict, selected: dict, sites,
           *, threshold: int = MIN_SHARED_UNIQUE_TARGETS) -> Decision:
    """Select cache only for >=threshold exact overlapping member targets.

    R455 observes the deduplicated member references in rebuilt records;
    R456 observes actual opcode member targets. Count intersection with
    exact Member equality and an owner in the combined admitted graph.
    Stop scanning as soon as a safe positive decision is established.
    A large/unsupported probe *disables* the optimization rather than
    weakening an existing analyzer's full input validation.
    """
    if type(threshold) is not int or not 1 <= threshold <= 256:
        raise Refused("R466_HIERARCHY_SELECTOR_THRESHOLD_INVALID")
    if type(rebuilt) is not dict or type(selected) is not dict:
        raise Refused("R466_HIERARCHY_SELECTOR_MAP_INVALID")
    if type(sites) not in (list, tuple):
        raise Refused("R466_HIERARCHY_SELECTOR_SITES_INVALID")
    if not sites:
        return Decision(False, 0, threshold, 0, 0, False,
                        "no_opcode_sites")
    if (len(sites) > MAX_SITE_HINTS
            or len(rebuilt) + len(selected) > 100000):
        return Decision(False, 0, threshold, 0, 0, True,
                        "unbounded_hint_skip")
    owners = rebuilt.keys() | selected.keys()
    candidates = set()
    for site in sites:
        # No semantic validation here: only use well-formed hints.
        # R456 still validates every site on either selected path.
        if type(site) is not opcode.Site or type(site.target) is not members.Member:
            return Decision(False, 0, threshold, 0, 0, False,
                            "invalid_hint_skip")
        target = site.target
        if target.owner in owners and not target.owner.startswith(
                platform.PLATFORM_ROOTS):
            candidates.add(target)
    if len(candidates) < threshold:
        return Decision(False, 0, threshold, len(candidates), 0, False,
                        "too_few_opcode_targets")
    matched = set()
    visits = 0
    for record in rebuilt.values():
        if type(record) is not members.ClassMembers:
            return Decision(False, 0, threshold, len(candidates),
                            visits, False, "invalid_record_hint_skip")
        for reference in record.references:
            visits += 1
            if visits > MAX_REFERENCE_VISITS:
                return Decision(False, len(matched), threshold,
                                len(candidates), visits, True,
                                "reference_probe_budget_skip")
            if reference in candidates:
                matched.add(reference)
                if len(matched) >= threshold:
                    return Decision(True, len(matched), threshold,
                                    len(candidates), visits, False,
                                    "sufficient_exact_overlap")
    return Decision(False, len(matched), threshold, len(candidates),
                    visits, False, "insufficient_exact_overlap")


def should_reuse(rebuilt: dict, selected: dict, sites) -> bool:
    """R459 opt-in selector: return literal bool, never private details."""
    return choose(rebuilt, selected, sites).use_cache
