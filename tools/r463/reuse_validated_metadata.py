"""R463 ephemeral exact-input opcode witness and bounded descriptor-shape reuse.

An R456 witness is admitted only for the exact in-process objects analyzed by
R456 immediately before R457. It does not certify provenance or replace any
source/class/dependency SHA gate. Cache entries independently use the existing
R451 and R457 method descriptor parsers (different validation contracts).
Nothing is serialized, persisted or promoted.
"""
from __future__ import annotations

from dataclasses import dataclass


class Refused(ValueError):
    pass


_REQUIRED = (
    "field_and_method_bytecode_sites_inspected",
    "invoke_method_site_count",
    "get_put_field_site_count",
    "static_instance_opcode_declaration_conflicts",
    "method_or_field_owner_unavailable",
)
MAX_DESCRIPTORS_PER_DOMAIN = 250000
MAX_TOTAL_DESCRIPTOR_CHARS = 16 * 1024 * 1024


@dataclass(frozen=True)
class OpcodeWitness:
    rebuilt: object
    selected: object
    sites: object
    dynamic: int
    summary_items: tuple[tuple[str, int], ...]


def witness(rebuilt, selected, sites, dynamic, summary) -> OpcodeWitness:
    if type(summary) is not dict or any(
            type(summary.get(name)) is not int or summary[name] < 0
            for name in _REQUIRED):
        raise Refused("R463_INVALID_PRIOR_OPCODE_SUMMARY")
    if type(dynamic) is not int or dynamic < 0:
        raise Refused("R463_INVALID_DYNAMIC_SITE_COUNT")
    if (summary["field_and_method_bytecode_sites_inspected"] != len(sites)
            or summary["invoke_method_site_count"] +
            summary["get_put_field_site_count"] != len(sites)):
        raise Refused("R463_PRIOR_OPCODE_SITE_TOTAL_DISAGREEMENT")
    # Retain only required immutable aggregate values, not private evidence.
    return OpcodeWitness(
        rebuilt, selected, sites, dynamic,
        tuple((key, summary[key]) for key in _REQUIRED))


def admit(w: OpcodeWitness, rebuilt, selected, sites, dynamic) -> dict:
    if (type(w) is not OpcodeWitness or w.rebuilt is not rebuilt
            or w.selected is not selected or w.sites is not sites
            or type(dynamic) is not int or w.dynamic != dynamic):
        raise Refused("R463_PRIOR_OPCODE_INPUT_IDENTITY_MISMATCH")
    result = dict(w.summary_items)
    if len(result) != len(_REQUIRED) or set(result) != set(_REQUIRED):
        raise Refused("R463_PRIOR_OPCODE_KEYS_MISMATCH")
    # Check primitive counts against actual input without redoing R456's
    # costly ancestry/member-visibility analysis.
    fields = sum(site.target.kind == "field" for site in sites)
    methods = len(sites) - fields
    if (result["field_and_method_bytecode_sites_inspected"] != len(sites)
            or result["get_put_field_site_count"] != fields
            or result["invoke_method_site_count"] != methods
            or any(type(v) is not int or v < 0 for v in result.values())):
        raise Refused("R463_PRIOR_OPCODE_COUNTS_DISAGREE")
    return result


class DescriptorShapes:
    """One transient scan-local cache with two independently parsed domains."""
    __slots__ = ("_resources", "_callsites", "resource_hits",
                 "resource_misses", "callsite_hits", "callsite_misses",
                 "_chars")

    def __init__(self):
        self._resources = {}
        self._callsites = {}
        self.resource_hits = 0
        self.resource_misses = 0
        self.callsite_hits = 0
        self.callsite_misses = 0
        self._chars = 0

    def _lookup(self, value: str, data: dict, domain: str, parser):
        if type(value) is not str:
            raise Refused("R463_DESCRIPTOR_INPUT_INVALID")
        if value in data:
            if domain == "resource":
                self.resource_hits += 1
            else:
                self.callsite_hits += 1
            return data[value]
        if (len(data) >= MAX_DESCRIPTORS_PER_DOMAIN
                or self._chars + len(value) > MAX_TOTAL_DESCRIPTOR_CHARS):
            raise Refused("R463_DESCRIPTOR_CACHE_BUDGET")
        result = parser(value)  # Never cache failed independent validation.
        data[value] = result
        self._chars += len(value)
        if domain == "resource":
            self.resource_misses += 1
        else:
            self.callsite_misses += 1
        return result

    def resource_shape(self, descriptor: str):
        from tools.r451 import straightline_resource_operands as r451
        return self._lookup(descriptor, self._resources, "resource",
                            r451.method_shape)

    def callsite_shape(self, descriptor: str):
        from tools.r457 import jvm_callsite_constraints as r457
        return self._lookup(descriptor, self._callsites, "callsite",
                            r457.method_shape)
