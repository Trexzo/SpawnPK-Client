"""R456 read-only JVM instruction-level member access-kind evidence.

Records actual get/put field and invoke opcodes in rebuilt Java11 Code
attributes. The *opcode* is decoded and its typed CONSTANT_{Field,Method,
InterfaceMethod}ref resolved; this avoids mistaking unused CP entries for
actual instructions. Selected rebuilt/dependency member declaration flags
then provide advisory static-vs-instance mismatch signals, NOT proof of
execution, JVM linkage, method reachability or legal access.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from tools.r450 import classfile_signature_resource as bytecode
from tools.r453 import classfile_member_reference as members
from tools.r454 import member_ancestry_evidence as ancestry
from tools.r455 import dependency_member_access as dependencies

FIELD_OPS = {
    0xb2: ("getstatic", True),
    0xb3: ("putstatic", True),
    0xb4: ("getfield", False),
    0xb5: ("putfield", False),
}
METHOD_OPS = {
    0xb6: ("invokevirtual", False),
    0xb7: ("invokespecial", False),
    0xb8: ("invokestatic", True),
    0xb9: ("invokeinterface", False),
}
MAX_SITES_PER_CLASS = 50000
MAX_TOTAL_SITES = 250000
ACC_STATIC = 0x0008
ACC_INTERFACE = 0x0200


class Refused(ValueError):
    pass


@dataclass(frozen=True, order=True)
class Site:
    source_class: str
    source_method: str
    pc: int
    operation: str
    static_opcode: bool
    target: members.Member
    # R457: actual unsigned invokeinterface count operand, if applicable.
    # Default retains the R456 six-argument synthetic Site constructor.
    interface_encoded_count: int | None = None


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise Refused(reason)


def decoded_sites(
    source_class: str,
    method_label: str,
    code: bytes,
    typed_memberref,
) -> tuple[tuple[Site, ...], int]:
    """Count direct field/method access instructions only, never CP-only refs.

    The R450 instruction decoder supplies exact bounded bytecode offsets;
    the typed resolver enforces constant-pool indexes/tags. invokedynamic is
    a separate, unresolvable callsite, never assigned an invented method.
    """
    members.valid_internal_name(source_class.removesuffix(".class"))
    sites: list[Site] = []
    dynamic = 0
    try:
        instructions = bytecode.instructions(code)
    except bytecode.Refused:
        raise Refused("R456_UNSAFE_INSTRUCTION_BOUNDARY") from None
    for pc, op, operand in instructions:
        if op == 0xba:
            require(len(operand) == 4 and operand[2:] == b"\x00\x00",
                    "R456_INVOKEDYNAMIC_ZERO_OPERANDS_REQUIRED")
            dynamic += 1
            continue
        if op not in FIELD_OPS and op not in METHOD_OPS:
            continue
        expected_field = op in FIELD_OPS
        operation, static = (
            FIELD_OPS[op] if expected_field else METHOD_OPS[op])
        require(len(operand) == (4 if op == 0xb9 else 2),
                "R456_UNEXPECTED_MEMBER_OPCODE_LENGTH")
        index = int.from_bytes(operand[:2], "big")
        owner, name, descriptor, kind = typed_memberref(index)
        require(kind in ("field", "method", "interface_method"),
                "R456_CP_MEMBER_TAG_UNSUPPORTED")
        require((kind == "field") == expected_field,
                "R456_FIELD_OR_METHOD_CP_TAG_MISMATCH")
        if op == 0xb6:
            require(kind == "method", "R456_INVOKEVIRTUAL_NEEDS_METHODREF")
        if op == 0xb9:
            require(kind == "interface_method",
                    "R456_INVOKEINTERFACE_NEEDS_INTERFACE_METHODREF")
            require(operand[2] > 0 and operand[3] == 0,
                    "R456_INVOKEINTERFACE_COUNT_OR_ZERO_INVALID")
        # Invokespecial and invokestatic may reference interface methods in
        # newer Java classfiles, so both typed CP method kinds are accepted.
        owner_path = members.valid_internal_name(owner)
        members.valid_member_name(name, kind)
        members.validate_descriptor(descriptor, kind)
        sites.append(Site(
            source_class, method_label, pc, operation, static,
            members.Member(owner_path, name, descriptor, kind),
            interface_encoded_count=(operand[2] if op == 0xb9 else None)))
        require(len(sites) <= MAX_SITES_PER_CLASS,
                "R456_CLASS_INVOKE_FIELD_SITE_BUDGET")
    return tuple(sites), dynamic


class Collector:
    """Optional member_observer callback to the R450 Java11 Code reader."""
    def __init__(self, source_class: str):
        self.source_class = source_class
        self.sites: list[Site] = []
        self.dynamic_sites = 0
        self.methods_with_code = 0

    def __call__(self, method_label: str, code: bytes, typed_memberref) -> None:
        self.methods_with_code += 1
        sites, dynamic = decoded_sites(
            self.source_class, method_label, code, typed_memberref)
        self.sites.extend(sites)
        self.dynamic_sites += dynamic
        require(len(self.sites) <= MAX_SITES_PER_CLASS,
                "R456_CLASS_TOTAL_MEMBER_SITES_BUDGET")


def analyze(
    rebuilt: dict[str, members.ClassMembers],
    selected: dict[str, members.ClassMembers],
    sites: list[Site],
    dynamic: int,
) -> tuple[dict, dict]:
    """Return non-identifying aggregate + owner-private name-only worklist.

    For an inherited candidate we report every reconstructed or selected
    declaration but NEVER claim JVM would select a particular ancestor;
    multiple providers and unknown superclass interfaces are unresolved.
    """
    require(not (rebuilt.keys() & selected.keys()),
            "R456_CLASS_PRECEDENCE_CONFLICT")
    merged = dict(selected)
    merged.update(rebuilt)
    for path, rec in merged.items():
        require(path == rec.class_name, "R456_MEMBER_OWNER_RECORD_MISMATCH")
    require(len(sites) <= MAX_TOTAL_SITES and type(dynamic) is int
            and 0 <= dynamic <= MAX_TOTAL_SITES,
            "R456_TOTAL_OPCODE_SITES_BUDGET")
    counter: Counter[str] = Counter()
    evidence: list[dict] = []
    ancestry_cache = {}
    encountered = set()
    for site in sites:
        require(site.source_class in rebuilt,
                "R456_SITE_SOURCE_NOT_IN_REBUILT_TREE")
        require(site.operation in {x[0] for x in FIELD_OPS.values()} |
                {x[0] for x in METHOD_OPS.values()},
                "R456_OPCODE_NAME_INVALID")
        require((site.operation in {x[0] for x in FIELD_OPS.values()}) ==
                (site.target.kind == "field"),
                "R456_TARGET_KIND_MISMATCH")
        key = (site.source_class, site.source_method, site.pc)
        require(key not in encountered, "R456_DUPLICATE_BYTECODE_PC_SITE")
        encountered.add(key)
        target = site.target
        counter["inspected"] += 1
        if target.owner not in merged:
            counter["owner_unavailable"] += 1
            result = "member_owner_not_inspected"
            providers = ()
            unknown_edges = ()
        else:
            if target.owner not in ancestry_cache:
                ancestry_cache[target.owner] = ancestry.ancestry(
                    merged, target.owner)
            chain = ancestry_cache[target.owner]
            resolved = ancestry.lookup(merged, target, chain)
            providers = (
                (target.owner,) if resolved.category == "direct_declaration"
                else resolved.candidates)
            unknown_edges = (*chain.external, *chain.platform)
            if not providers:
                result = ("signature_not_resolved_in_available_classes"
                          if not unknown_edges and not chain.cycle
                          and not chain.bounded_unknown
                          else "incomplete_or_uncertain_ancestry")
            elif len(providers) > 1 or chain.cycle or chain.bounded_unknown:
                result = "ambiguous_inherited_declarations"
            else:
                provider = providers[0]
                record = merged[provider]
                entries = (record.declared_field_access
                           if target.kind == "field" else
                           record.declared_method_access)
                match = [flags for name, desc, flags in entries
                         if (name, desc) == (target.name, target.descriptor)]
                if len(match) != 1:
                    result = "declaration_flags_unknown"
                else:
                    is_static = bool(match[0] & ACC_STATIC)
                    if is_static != site.static_opcode:
                        result = "static_instance_opcode_declaration_conflict"
                    elif site.operation == "invokevirtual" and (
                            record.access_flags & ACC_INTERFACE):
                        result = "invokevirtual_class_interface_uncertainty"
                    elif site.operation == "invokeinterface" and (
                            provider == target.owner and
                            not (record.access_flags & ACC_INTERFACE)):
                        result = "invokeinterface_owner_not_interface"
                    elif target.name in ("<init>", "<clinit>") and (
                            site.operation != "invokespecial"
                            or target.name == "<clinit>"):
                        result = "special_initializer_invocation_uncertainty"
                    else:
                        result = "opcode_declaration_static_flag_agrees"
        counter[result] += 1
        # These are bytecode instructions, but may lie on unreachable paths.
        # Access risk remains tentative even with matching staticness.
        assessments = [
            {
                "declaring_owner": p,
                "advisory_visibility": dependencies.member_access(
                    site.source_class, p, merged[p], target),
            }
            for p in providers
        ]
        if result != "opcode_declaration_static_flag_agrees" or any(
                a["advisory_visibility"] !=
                "public_member_classloader_access_unchecked"
                for a in assessments):
            evidence.append({
                "source_class": site.source_class,
                "source_method": site.source_method,
                "bytecode_pc": site.pc,
                "actual_opcode": site.operation,
                "reference_owner": target.owner,
                "member_name": target.name,
                "member_descriptor": target.descriptor,
                "constant_pool_member_kind": target.kind,
                "selected_declaration_owners": list(providers),
                "declaration_visibility_signals": assessments,
                "unparsed_ancestry_edges": list(unknown_edges),
                "advisory_classification": result,
                "instruction_reachability_or_jvm_linkage_proven": False,
            })
    summary = {
        "rebuilt_classes_inspected": len(rebuilt),
        "selected_dependency_classes_available": len(selected),
        "field_and_method_bytecode_sites_inspected": counter["inspected"],
        "get_put_field_site_count": sum(
            site.target.kind == "field" for site in sites),
        "invoke_method_site_count": sum(
            site.target.kind != "field" for site in sites),
        "invokedynamic_sites_without_static_owner_resolution": dynamic,
        "opcode_and_declaration_static_flags_agree":
            counter["opcode_declaration_static_flag_agrees"],
        "static_instance_opcode_declaration_conflicts":
            counter["static_instance_opcode_declaration_conflict"],
        "method_or_field_owner_unavailable":
            counter["member_owner_not_inspected"],
        "signature_absent_from_available_direct_or_inherited_members":
            counter["signature_not_resolved_in_available_classes"],
        "incomplete_or_uncertain_ancestry":
            counter["incomplete_or_uncertain_ancestry"],
        "ambiguous_inherited_declarations":
            counter["ambiguous_inherited_declarations"],
        "declaration_access_flags_not_available":
            counter["declaration_flags_unknown"],
        "interface_invoke_kind_uncertainties":
            counter["invokevirtual_class_interface_uncertainty"]
            + counter["invokeinterface_owner_not_interface"],
        "special_initializer_invocation_uncertainties":
            counter["special_initializer_invocation_uncertainty"],
        "exact_invocation_opcodes_decoded": True,
        "unreachable_bytecode_excluded": False,
        "jvm_linkage_or_runtime_dispatch_verified": False,
        "all_opcode_static_conflicts_proven_runtime_errors": False,
    }
    return summary, {
        "private_bytecode_member_opcode_leads": evidence,
        "opcode_sites_are_static_not_proven_executed": True,
        "possible_linkage_error_requires_real_JVM_verification": True,
        "source_or_class_bytes_embedded": False,
        "historical_R421_provenance_approved": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
