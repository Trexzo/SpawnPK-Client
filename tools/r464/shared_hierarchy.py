"""R464 strict scan-local reused ancestry and member-resolution witness.

R455 and R456 independently construct the SAME selected-dependency/rebuilt
class graph and repeatedly compute ancestry and inherited-member candidates.
This opt-in bounded index shares ONLY frozen R454 Ancestry/Resolution results,
never JVM execution or source/JAR bytes.

The index is bound to an immutable-by-construction snapshot of the exact
R453 frozen ClassMembers records. Each admitting analyzer independently
validates its merged class map and object identity before reuse.
The rebuilt-only R454 audit remains separate: it has a DIFFERENT graph.
"""
from __future__ import annotations

from tools.r454 import member_ancestry_evidence as ancestry
from tools.r453 import classfile_member_reference as parser

MAX_CLASSES = 100000
MAX_OWNERS = 100000
MAX_RESOLUTIONS = 220000


class Refused(ValueError):
    pass


class Index:
    __slots__ = ("_records", "_chains", "_resolutions",
                 "ancestry_hits", "ancestry_misses",
                 "resolution_hits", "resolution_misses", "admissions")

    def __init__(self, rebuilt: dict, selected: dict):
        if (type(rebuilt) is not dict or type(selected) is not dict
                or rebuilt.keys() & selected.keys()):
            raise Refused("R464_CLASS_GRAPH_INPUT_INVALID")
        merged = dict(selected)
        merged.update(rebuilt)
        if len(merged) > MAX_CLASSES or any(
                type(name) is not str
                or type(record) is not parser.ClassMembers
                or record.class_name != name for name, record in merged.items()):
            raise Refused("R464_CLASS_GRAPH_RECORD_INVALID")
        # ClassMembers is frozen and its indexed fields are frozen collections.
        self._records = merged
        self._chains: dict[str, ancestry.Ancestry] = {}
        self._resolutions: dict[parser.Member, ancestry.Resolution] = {}
        self.ancestry_hits = 0
        self.ancestry_misses = 0
        self.resolution_hits = 0
        self.resolution_misses = 0
        self.admissions = 0

    def admit(self, merged: dict) -> None:
        """Reject missing/replaced records and graph drift before cache reuse."""
        if (type(merged) is not dict
                or len(merged) != len(self._records)
                or merged.keys() != self._records.keys()
                or any(merged[name] is not original
                       for name, original in self._records.items())):
            raise Refused("R464_CLASS_GRAPH_IDENTITY_DRIFT")
        self.admissions += 1

    def chain(self, owner: str) -> ancestry.Ancestry:
        if type(owner) is not str or owner not in self._records:
            raise Refused("R464_OWNER_NOT_ON_ADMITTED_GRAPH")
        if owner in self._chains:
            self.ancestry_hits += 1
            return self._chains[owner]
        if len(self._chains) >= MAX_OWNERS:
            raise Refused("R464_ANCESTRY_CACHE_BUDGET")
        result = ancestry.ancestry(self._records, owner)
        self._chains[owner] = result
        self.ancestry_misses += 1
        return result

    def resolve(self, target: parser.Member,
                chain: ancestry.Ancestry) -> ancestry.Resolution:
        if (type(target) is not parser.Member
                or target.owner not in self._records
                or self._chains.get(target.owner) is not chain):
            raise Refused("R464_RESOLUTION_CHAIN_OWNER_MISMATCH")
        if target in self._resolutions:
            self.resolution_hits += 1
            return self._resolutions[target]
        if len(self._resolutions) >= MAX_RESOLUTIONS:
            raise Refused("R464_RESOLUTION_CACHE_BUDGET")
        result = ancestry.lookup(self._records, target, chain)
        self._resolutions[target] = result
        self.resolution_misses += 1
        return result
