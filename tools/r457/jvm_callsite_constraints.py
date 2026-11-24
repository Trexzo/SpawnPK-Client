"""R457 conservative JVM callsite operand and special-method constraints.

Only reads already decoded Java 11 Code instruction sites from R456:
  * invokeinterface's encoded count must equal 1 + descriptor argument slots
    (long/double = 2 slots unless inside an array).
  * <init> must use invokespecial, a class Methodref, and a void return.
  * <clinit> must never be called directly by any invoke instruction.
  * An available reference-owner class/interface flag is compared with
    the CP Methodref/InterfaceMethodref kind; absence stays unverified.

This is bounded *syntactic static evidence*. No stack dataflow, JVM bytecode
verification, reachable execution, dynamic linking, constructor initialization
state, protected receiver or runtime classloader rules are proven.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from tools.r453 import classfile_member_reference as members
from tools.r456 import member_opcode_evidence as prior

MAX_DESCRIPTOR_CHARS = 65535
MAX_PARAMETER_TYPES = 255
MAX_PARAMETER_SLOTS = 255
MAX_SITES = prior.MAX_TOTAL_SITES
ACC_INTERFACE = 0x0200


class Refused(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Refused(code)


@dataclass(frozen=True)
class MethodShape:
    parameter_count: int
    parameter_slots: int
    return_slots: int
    void_return: bool


def method_shape(descriptor: str) -> MethodShape:
    """Strict JVMS method descriptor and category-2 slot-width parser."""
    require(type(descriptor) is str and 3 <= len(descriptor) <=
            MAX_DESCRIPTOR_CHARS and descriptor.isascii()
            and descriptor.startswith("("), "R457_BAD_METHOD_DESCRIPTOR")
    cursor = 1

    def field_type(*, return_type: bool = False) -> int:
        nonlocal cursor
        arrays = 0
        while cursor < len(descriptor) and descriptor[cursor] == "[":
            arrays += 1
            cursor += 1
            require(arrays <= 255, "R457_TOO_MANY_ARRAY_DIMENSIONS")
        require(cursor < len(descriptor), "R457_TRUNCATED_TYPE")
        char = descriptor[cursor]
        cursor += 1
        if char in "BCFISZ":
            return 1
        if char in "JD":
            return 1 if arrays else 2
        if char == "V" and return_type and not arrays:
            return 0
        if char != "L":
            raise Refused("R457_INVALID_DESCRIPTOR_TYPE")
        pos = descriptor.find(";", cursor)
        require(pos > cursor, "R457_INVALID_OBJECT_DESCRIPTOR_END")
        path = descriptor[cursor:pos]
        try:
            members.valid_internal_name(path)
        except members.Refused:
            raise Refused("R457_UNSAFE_OBJECT_DESCRIPTOR") from None
        cursor = pos + 1
        return 1

    params = 0
    slots = 0
    while cursor < len(descriptor) and descriptor[cursor] != ")":
        params += 1
        require(params <= MAX_PARAMETER_TYPES, "R457_PARAMETER_COUNT_BUDGET")
        slots += field_type()
        require(slots <= MAX_PARAMETER_SLOTS, "R457_ARGUMENT_SLOT_BUDGET")
    require(cursor < len(descriptor) and descriptor[cursor] == ")",
            "R457_METHOD_CLOSING_PAREN_MISSING")
    cursor += 1
    ret = field_type(return_type=True)
    require(cursor == len(descriptor), "R457_DESCRIPTOR_TRAILING_DATA")
    return MethodShape(
        parameter_count=params, parameter_slots=slots,
        return_slots=ret, void_return=ret == 0)


def site_issues(
    site: prior.Site,
    reference_owner: members.ClassMembers | None,
    *, method_shape_resolver=None,
) -> tuple[str, ...]:
    """List advisory static callsite inconsistencies, never runtime verdicts."""
    require(isinstance(site, prior.Site),
            "R457_INVALID_SITE_EVIDENCE")
    methods = {label: static for label, static in prior.METHOD_OPS.values()}
    fields = {label: static for label, static in prior.FIELD_OPS.values()}
    expected = {**methods, **fields}
    require(site.operation in expected and site.static_opcode is
            expected[site.operation], "R457_OPCODE_STATIC_FLAG_FORGED")
    if site.operation != "invokeinterface":
        require(site.interface_encoded_count is None,
                "R457_NONINTERFACE_ENCODED_COUNT_UNEXPECTED")
    else:
        require(site.interface_encoded_count is None or
                (type(site.interface_encoded_count) is int and
                 1 <= site.interface_encoded_count <= 255),
                "R457_INTERFACE_ENCODED_COUNT_INVALID")
    require((site.operation in fields) == (site.target.kind == "field"),
            "R457_MEMBER_KIND_INCOMPATIBLE_WITH_OPCODE")

    findings: list[str] = []
    if site.operation in methods:
        shape = (method_shape_resolver or method_shape)(site.target.descriptor)
        if site.operation == "invokeinterface":
            expect = shape.parameter_slots + 1
            if expect > 255:
                findings.append("invokeinterface_argument_slot_count_unencodable")
            elif site.interface_encoded_count is None:
                findings.append("invokeinterface_encoded_count_unavailable")
            elif site.interface_encoded_count != expect:
                findings.append("invokeinterface_encoded_count_mismatch")
        name = site.target.name
        if name == "<init>":
            if site.operation != "invokespecial":
                findings.append("constructor_requires_invokespecial")
            if site.target.kind != "method":
                findings.append("constructor_requires_class_methodref")
            if not shape.void_return:
                findings.append("constructor_requires_void_return")
        elif name == "<clinit>":
            findings.append("class_initializer_must_not_be_invoked")
        elif site.operation == "invokespecial" and name == "finalize":
            # Regular invokespecial on nonconstructors is permitted;
            # do not create fabricated special-name rules.
            pass

        if reference_owner is not None:
            require(reference_owner.class_name == site.target.owner,
                    "R457_REFERENCE_OWNER_RECORD_MISMATCH")
            is_interface = bool(reference_owner.access_flags & ACC_INTERFACE)
            if site.target.kind == "interface_method" and not is_interface:
                findings.append("interface_methodref_owner_not_interface")
            elif site.target.kind == "method" and is_interface:
                findings.append("class_methodref_owner_is_interface")
    else:
        require(site.interface_encoded_count is None,
                "R457_FIELD_SITE_HAS_INTERFACE_OPERAND")
        try:
            members.validate_descriptor(site.target.descriptor, "field")
        except members.Refused:
            raise Refused("R457_BAD_FIELD_DESCRIPTOR") from None

    return tuple(sorted(set(findings)))


def analyze(
    rebuilt: dict[str, members.ClassMembers],
    selected_dependencies: dict[str, members.ClassMembers],
    sites: list[prior.Site],
    dynamic_sites: int,
    *, prior_witness=None, method_shape_resolver=None,
) -> tuple[dict, dict]:
    """Aggregate only; detailed site identities belong in private TEMP."""
    if prior_witness is None:
        previous, _ = prior.analyze(
            rebuilt, selected_dependencies, sites, dynamic_sites)
    else:
        from tools.r463 import reuse_validated_metadata as shared
        previous = shared.admit(
            prior_witness, rebuilt, selected_dependencies, sites,
            dynamic_sites)
    merged = dict(selected_dependencies)
    merged.update(rebuilt)
    counts: Counter[str] = Counter()
    flagged: list[dict] = []
    total = 0
    for site in sites:
        issues = site_issues(
            site, merged.get(site.target.owner),
            method_shape_resolver=method_shape_resolver)
        total += 1
        for issue in issues:
            counts[issue] += 1
        if issues:
            flagged.append({
                "source_class": site.source_class,
                "source_method": site.source_method,
                "bytecode_pc": site.pc,
                "actual_opcode": site.operation,
                "reference_owner": site.target.owner,
                "member_name": site.target.name,
                "descriptor": site.target.descriptor,
                "constant_pool_kind": site.target.kind,
                "encoded_invokeinterface_count": site.interface_encoded_count,
                "static_syntax_findings": list(issues),
                "jvm_execution_or_linkage_proven": False,
            })
    require(total == previous["field_and_method_bytecode_sites_inspected"]
            and total <= MAX_SITES, "R457_R456_OPCODE_SITE_COUNT_DRIFT")
    summary = {
        "rebuilt_classfiles_checked": len(rebuilt),
        "selected_preferred_dependency_classes": len(selected_dependencies),
        "decoded_field_and_method_sites": total,
        "method_invocation_sites": previous["invoke_method_site_count"],
        "field_read_write_sites": previous["get_put_field_site_count"],
        "invokedynamic_sites_not_resolved": dynamic_sites,
        "sites_with_one_or_more_syntactic_findings": len(flagged),
        "invokeinterface_argument_slot_count_mismatches":
            counts["invokeinterface_encoded_count_mismatch"],
        "invokeinterface_argument_slot_count_unencodable":
            counts["invokeinterface_argument_slot_count_unencodable"],
        "invokeinterface_encoded_operand_missing":
            counts["invokeinterface_encoded_count_unavailable"],
        "constructor_calls_using_non_invokespecial":
            counts["constructor_requires_invokespecial"],
        "constructor_calls_using_interface_methodref":
            counts["constructor_requires_class_methodref"],
        "constructor_descriptors_not_returning_void":
            counts["constructor_requires_void_return"],
        "explicit_class_initializer_invocations":
            counts["class_initializer_must_not_be_invoked"],
        "interface_methodref_to_known_noninterface_owners":
            counts["interface_methodref_owner_not_interface"],
        "class_methodref_to_known_interface_owners":
            counts["class_methodref_owner_is_interface"],
        "inherited_R456_static_instance_opcode_conflicts":
            previous["static_instance_opcode_declaration_conflicts"],
        "inherited_R456_unavailable_member_owners":
            previous["method_or_field_owner_unavailable"],
        "method_descriptor_category_two_slot_width_tracked": True,
        "complete_JVM_verification_performed": False,
        "callsite_operand_stack_proven": False,
        "constructor_initialization_state_proven": False,
        "dynamic_callsite_reachability_proven": False,
        "JVM_runtime_or_linking_errors_proven": False,
    }
    details = {
        "private_violating_or_unresolved_JVM_callsite_candidates": flagged,
        "findings_are_static_syntax_not_runtime_verdicts": True,
        "actual_original_client_source_or_bytes_included": False,
        "historical_R421_full_inventory_approved": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return summary, details
