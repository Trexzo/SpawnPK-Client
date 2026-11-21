"""R454 bounded offline JVM ancestry-name / member declaration evidence.

Given SHA-verified rebuilt Java 11 class metadata, distinguish direct member
declarations from possible superclass and interface inherited signatures.
This is NOT JVMS resolution: package access, overrides, default-method
specificity, linking, transitive external dependencies and runtime dispatch
remain unverified. Invalid cycles/too-deep graphs fail closed as UNKNOWN.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from tools.r388 import audit_offline_classpath as r388
from tools.r453 import classfile_member_reference as parser

MAX_ANCESTORS = 512
MAX_DEPTH = 64
MAX_PATH_STATES = 4096
MAX_MEMBER_REFERENCES = 220000
ACC_PRIVATE = 0x0002
ACC_STATIC = 0x0008


class Refused(ValueError):
    pass


@dataclass(frozen=True)
class Ancestry:
    ancestors: tuple[tuple[str, str], ...]  # class path, edge attribution
    external: tuple[str, ...]
    platform: tuple[str, ...]
    bounded_unknown: bool
    cycle: bool


def require(ok: bool, code: str) -> None:
    if not ok:
        raise Refused(code)


def ancestry(records: dict[str, parser.ClassMembers], owner: str) -> Ancestry:
    """Traverse *declared* superclasses and interfaces, never the JVM.

    Class hierarchy input is read from R453 ClassMembers. A repeated node
    reached by separate diamond paths is not a cycle; only a node already
    in the *current path* is a cycle. Every path is finite and bounded.
    """
    require(owner in records, "R454_OWNER_ABSENT_FROM_REBUILT_TREE")
    for name, record in records.items():
        require(record.class_name == name,
                "R454_CLASS_PATH_INTERNAL_NAME_MISMATCH")
    start = records[owner]

    def neighbors(record: parser.ClassMembers):
        links = []
        if record.superclass_name:
            links.append((record.superclass_name, "superclass"))
        for iface in sorted(record.interfaces):
            links.append((iface, "interface"))
        return links

    queue = deque()
    for node, route in neighbors(start):
        queue.append((node, route, 1, frozenset({owner})))
    found: set[tuple[str, str]] = set()
    external = set()
    platform = set()
    cycle = False
    bounded = False
    steps = 0
    while queue:
        name, route, depth, history = queue.popleft()
        steps += 1
        if steps > MAX_PATH_STATES or depth > MAX_DEPTH:
            bounded = True
            break
        if name in history:
            cycle = True
            continue
        if name not in records:
            if name.startswith(r388.PLATFORM_ROOTS):
                platform.add(name)
            else:
                external.add(name)
            continue
        found.add((name, route))
        if len(found) > MAX_ANCESTORS:
            bounded = True
            break
        here = records[name]
        branch_history = history | {name}
        for parent, edge in neighbors(here):
            # If any edge crosses an interface, the declaration originates
            # in an interface even when reached through a superclass.
            next_route = "interface" if "interface" in (route, edge) else "superclass"
            queue.append((parent, next_route, depth + 1, branch_history))
    return Ancestry(
        tuple(sorted(found)), tuple(sorted(external)), tuple(sorted(platform)),
        bounded_unknown=bounded, cycle=cycle,
    )


@dataclass(frozen=True)
class Resolution:
    category: str
    candidates: tuple[str, ...]
    non_inheritable: tuple[str, ...]
    external_edges: tuple[str, ...]
    platform_edges: tuple[str, ...]
    cycle: bool
    bounded: bool


def lookup(
    records: dict[str, parser.ClassMembers],
    reference: parser.Member,
    chain: Ancestry,
) -> Resolution:
    """Structural signature evidence, not a proven invocation/linkage."""
    require(reference.owner in records, "R454_OWNER_NOT_REBUILT")
    own = records[reference.owner]
    signature = (reference.name, reference.descriptor)
    direct_set = (own.declared_fields if reference.kind == "field"
                  else own.declared_methods)
    if signature in direct_set:
        return Resolution("direct_declaration", (), (), (),
                          (), False, False)
    # Java constructors and class initializers are never inherited.
    if reference.name in ("<init>", "<clinit>"):
        return Resolution("special_method_not_inheritable", (), (),
                          chain.external, chain.platform, chain.cycle,
                          chain.bounded_unknown)

    candidate_super = set()
    candidate_iface = set()
    non_inheritable = set()
    for path, route in chain.ancestors:
        record = records[path]
        declarations = (record.declared_fields if reference.kind == "field"
                        else record.declared_methods)
        if signature not in declarations:
            continue
        flags_list = (record.declared_field_access if reference.kind == "field"
                      else record.declared_method_access)
        matching_flags = [flags for name, desc, flags in flags_list
                          if (name, desc) == signature]
        if not matching_flags:
            # Manually constructed old R453 metadata may lack flags. Treat
            # as unknown; never label a declaration as inheritable.
            non_inheritable.add(path + "#access-unknown")
            continue
        flags = matching_flags[0]
        if flags & ACC_PRIVATE:
            non_inheritable.add(path + "#private")
            continue
        if route == "interface" and reference.kind != "field" and flags & ACC_STATIC:
            # Interface static methods are not inherited by subinterfaces
            # or implementing classes.
            non_inheritable.add(path + "#static-interface-method")
            continue
        if route == "interface":
            candidate_iface.add(path)
        else:
            candidate_super.add(path)

    if chain.cycle or chain.bounded_unknown:
        category = "cycle_or_budget_uncertain"
    elif candidate_super:
        category = "superclass_signature_candidate"
    elif candidate_iface:
        category = "interface_signature_candidate"
    elif non_inheritable:
        category = "ancestor_declaration_noninheritable_or_access_unknown"
    elif chain.external or chain.platform:
        category = "ancestry_external_or_platform_unknown"
    else:
        category = "not_found_in_available_rebuilt_ancestry"

    return Resolution(
        category,
        tuple(sorted(candidate_super | candidate_iface)),
        tuple(sorted(non_inheritable)),
        chain.external, chain.platform, chain.cycle, chain.bounded_unknown,
    )


def analyze(
    records: dict[str, parser.ClassMembers],
    preferred_names: set[str],
    alternate_names: set[str],
    original_names: set[str],
) -> tuple[dict, dict]:
    """Aggregate only; names go to explicit owner-private report."""
    all_references: dict[parser.Member, set[str]] = defaultdict(set)
    for name, record in records.items():
        require(name == record.class_name, "R454_CLASS_MAP_MISMATCH")
        for member in record.references:
            all_references[member].add(name)
    require(len(all_references) <= MAX_MEMBER_REFERENCES,
            "R454_MEMBER_REFERENCE_BUDGET")

    rebuilt = set(records)
    chain_cache: dict[str, Ancestry] = {}
    results: dict[parser.Member, Resolution] = {}
    for target in all_references:
        if target.owner not in rebuilt:
            continue
        if target.owner not in chain_cache:
            chain_cache[target.owner] = ancestry(records, target.owner)
        results[target] = lookup(records, target, chain_cache[target.owner])

    categories = (
        "direct_declaration",
        "superclass_signature_candidate",
        "interface_signature_candidate",
        "ancestor_declaration_noninheritable_or_access_unknown",
        "ancestry_external_or_platform_unknown",
        "not_found_in_available_rebuilt_ancestry",
        "special_method_not_inheritable",
        "cycle_or_budget_uncertain",
    )
    counts = {
        kind: sum(r.category == kind for r in results.values())
        for kind in categories
    }
    unresolved = {
        member: r for member, r in results.items()
        if r.category != "direct_declaration"
    }
    reference_count = sum(len(x) for x in all_references.values())

    def info(member: parser.Member, result: Resolution):
        return {
            "referenced_owner": member.owner,
            "member_name": member.name,
            "descriptor": member.descriptor,
            "reference_kind": member.kind,
            "referencing_rebuilt_classfiles": sorted(all_references[member]),
            "source_count": len(all_references[member]),
            "evidence_category": result.category,
            "structural_ancestor_declarations": list(result.candidates),
            "noninheritable_or_unverified_access": list(result.non_inheritable),
            "unknown_external_ancestor_edges": list(result.external_edges),
            "unknown_platform_ancestor_edges": list(result.platform_edges),
            "owner_original_v309_name_present": member.owner in original_names,
            "owner_alternate_dependency_name_present": member.owner in alternate_names,
            "cycle_in_ancestry": result.cycle,
            "analysis_budget_reached": result.bounded,
            "java_access_resolution_performed": False,
            "runtime_linkage_verified": False,
        }

    report = {
        "parsed_rebuilt_classfiles": len(records),
        "unique_rebuilt_constant_pool_member_references": len(all_references),
        "class_to_member_reference_pairs": reference_count,
        "references_with_rebuilt_owner_checked": len(results),
        "references_to_unparsed_platform_dependency_or_missing_owner":
            len(all_references) - len(results),
        "exact_direct_declaration": counts["direct_declaration"],
        "possible_inherited_superclass_member_signature":
            counts["superclass_signature_candidate"],
        "possible_inherited_interface_member_signature":
            counts["interface_signature_candidate"],
        "ancestor_declaration_private_static_or_access_unverified":
            counts["ancestor_declaration_noninheritable_or_access_unknown"],
        "ancestor_graph_external_or_platform_unknown":
            counts["ancestry_external_or_platform_unknown"],
        "member_signature_absent_from_available_ancestry":
            counts["not_found_in_available_rebuilt_ancestry"],
        "special_constructor_or_initializer_not_inheritable":
            counts["special_method_not_inheritable"],
        "cyclic_or_budget_limited_ancestry_unknown":
            counts["cycle_or_budget_uncertain"],
        "reconstructed_owner_references_with_no_direct_declaration":
            len(unresolved),
        "possible_inherited_declaration_signatures":
            counts["superclass_signature_candidate"]
            + counts["interface_signature_candidate"],
        "jvm_classloading_or_access_checks_performed": False,
        "inherited_methods_proven_accessible": False,
        "bytecode_linkage_verified": False,
        "dynamic_dispatch_verified": False,
        "production_client_executed": False,
    }
    private = {
        "unresolved_or_potentially_inherited_member_signatures": [
            info(member, result)
            for member, result in sorted(
                unresolved.items(),
                key=lambda item: (-len(all_references[item[0]]),
                                  item[1].category,
                                  item[0].owner, item[0].name,
                                  item[0].descriptor))
        ],
        "inherited_signatures_are_structural_candidates_only": True,
        "direct_declaration_is_not_runtime_resolution": True,
        "historical_R421_inventory_approved": False,
        "merge_authorized": False,
        "release_authorized": False,
    }
    return report, private
