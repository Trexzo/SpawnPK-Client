"""R455 selective, bounded preferred-dependency class member inspection.

No Java execution, external network or source export. Given the already
SHA-pinned preferred dependency JAR and rebuilt R421 class metadata, load
only member-owner and ancestor .class entries needed for *static* linkage
investigation. Exact class member declarations and access flags are
candidate evidence, not JVMS linkage, access resolution or runtime proof.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from hashlib import sha256
import io
import zipfile

from tools.r388 import audit_offline_classpath as r388
from tools.r447 import audit_original_class_asset_coverage as r447
from tools.r453 import classfile_member_reference as member_parser
from tools.r454 import member_ancestry_evidence as ancestry

MAX_SELECTED_CLASS_BYTES = 8 * 1024 * 1024
MAX_TOTAL_SELECTED_BYTES = 64 * 1024 * 1024
MAX_SELECTED_CLASSES = 2048
MAX_QUEUE_STEPS = 8192
MAX_REFERENCES = 220000
SUPPORTED_DEPENDENCY_MAJORS = tuple(range(45, 56))
ACC_PUBLIC = 0x0001
ACC_PRIVATE = 0x0002
ACC_PROTECTED = 0x0004


class Refused(ValueError):
    pass


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise Refused(reason)


def eligible_parents(record: member_parser.ClassMembers) -> set[str]:
    return ({record.superclass_name} if record.superclass_name else set()) | set(
        record.interfaces)


def selected_dependencies(
    raw: bytes,
    expected_sha: str,
    names: set[str],
    rebuilt: dict[str, member_parser.ClassMembers],
) -> dict[str, member_parser.ClassMembers]:
    """Only needed direct member owners and their preferred-JAR ancestors.

    R447 verifies the *entire* ZIP central directory, duplicate paths,
    symlinks, entries, encryption and total declared byte budgets first.
    Each selected member is then decompressed with independent tight caps,
    CRC and exact internal name checks. Rebuilt classes always take
    precedence over dependency classes with duplicate names.
    """
    need(type(raw) is bytes and sha256(raw).hexdigest() == expected_sha,
         "R455_PREFERRED_JAR_SHA_MISMATCH")
    archive_names, _, _ = r447.archive(raw, "dependency")
    need(names == archive_names, "R455_DEPENDENCY_CLASS_INDEX_DRIFT")
    queue = deque()
    for record in rebuilt.values():
        for target in record.references:
            if target.owner in names and target.owner not in rebuilt:
                queue.append(target.owner)
        for parent in eligible_parents(record):
            if parent in names and parent not in rebuilt:
                queue.append(parent)
    selected: dict[str, member_parser.ClassMembers] = {}
    visited: set[str] = set()
    budget = 0
    steps = 0
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as jar:
            while queue:
                path = queue.popleft()
                steps += 1
                need(steps <= MAX_QUEUE_STEPS,
                     "R455_DEPENDENCY_ANCESTRY_QUEUE_BUDGET")
                if path in visited or path in rebuilt or path not in names:
                    continue
                visited.add(path)
                need(len(visited) <= MAX_SELECTED_CLASSES,
                     "R455_SELECTED_DEPENDENCY_CLASSES_BUDGET")
                r447.zip_path(path)
                member = jar.getinfo(path)
                need(0 < member.file_size <= MAX_SELECTED_CLASS_BYTES,
                     "R455_SELECTED_CLASS_SIZE_LIMIT")
                # Bounded decompression of one nominated archive member.
                with jar.open(member, "r") as stream:
                    code = stream.read(MAX_SELECTED_CLASS_BYTES + 1)
                    need(len(code) == member.file_size,
                         "R455_SELECTED_DEPENDENCY_DECOMPRESSED_SIZE_DRIFT")
                    need(not stream.read(1),
                         "R455_SELECTED_DEPENDENCY_EXCESS_DECOMPRESSED_BYTES")
                budget += len(code)
                need(budget <= MAX_TOTAL_SELECTED_BYTES,
                     "R455_SELECTED_DEPENDENCY_TOTAL_BYTE_BUDGET")
                try:
                    record = member_parser.parse_class(
                        code, allowed_majors=SUPPORTED_DEPENDENCY_MAJORS)
                except member_parser.Refused:
                    raise Refused("R455_SELECTED_DEPENDENCY_CLASS_UNPARSABLE") from None
                need(record.class_name == path,
                     "R455_SELECTED_DEPENDENCY_PATH_NAME_MISMATCH")
                selected[path] = record
                for parent in eligible_parents(record):
                    if parent in names and parent not in rebuilt:
                        queue.append(parent)
    except (zipfile.BadZipFile, zipfile.LargeZipFile, EOFError, OSError,
            ValueError, RuntimeError) as e:
        if isinstance(e, Refused):
            raise
        raise Refused("R455_DEPENDENCY_ARCHIVE_READ_FAILURE") from None
    return selected


def member_access(
    caller: str,
    provider: str,
    record: member_parser.ClassMembers,
    target: member_parser.Member,
) -> str:
    """Partial member visibility classification, never an allow/deny verdict.

    Ignores classloader-defined runtime packages, protected receiver type,
    nest host membership and module boundaries; these are explicitly
    unverified. A cross-package package-private signal is a risk, not
    a confirmed IllegalAccessError.
    """
    declarations = (record.declared_field_access if target.kind == "field"
                    else record.declared_method_access)
    flags = next((flags for name, desc, flags in declarations
                  if (name, desc) == (target.name, target.descriptor)), None)
    if flags is None:
        return "declaration_access_flags_unavailable"
    if not (record.access_flags & ACC_PUBLIC):
        return "declaring_class_visibility_not_proven"
    if flags & ACC_PUBLIC:
        return "public_member_classloader_access_unchecked"
    if flags & ACC_PRIVATE:
        return ("private_same_class_candidate" if caller == provider
                else "private_nestmate_or_access_unknown")
    if flags & ACC_PROTECTED:
        return "protected_receiver_or_package_access_unknown"
    caller_package = caller.rpartition("/")[0]
    provider_package = provider.rpartition("/")[0]
    return ("package_private_same_package_candidate"
            if caller_package == provider_package
            else "package_private_cross_package_access_risk")


def analyze(
    rebuilt: dict[str, member_parser.ClassMembers],
    dependencies: dict[str, member_parser.ClassMembers],
    original: set[str],
    alternate: set[str],
) -> tuple[dict, dict]:
    """Aggregate only; detailed identifiers belong in owner-private TEMP."""
    need(not (rebuilt.keys() & dependencies.keys()),
         "R455_DEPENDENCY_REBUILT_OWNER_SHADOWED")
    merged = dict(dependencies)
    merged.update(rebuilt)
    for name, record in merged.items():
        need(record.class_name == name, "R455_CLASS_RECORD_PATH_MISMATCH")
    incoming: dict[member_parser.Member, set[str]] = defaultdict(set)
    for caller, record in rebuilt.items():
        for reference in record.references:
            incoming[reference].add(caller)
    need(len(incoming) <= MAX_REFERENCES, "R455_MEMBER_REFERENCE_BUDGET")

    results: list[dict] = []
    chain_cache: dict[str, ancestry.Ancestry] = {}
    for target in sorted(incoming):
        if target.owner.startswith(r388.PLATFORM_ROOTS):
            category = "platform_owner_not_inspected"
            providers: tuple[str, ...] = ()
            chain = None
        elif target.owner not in merged:
            category = "owner_absent_from_selected_classpath"
            providers = ()
            chain = None
        else:
            if target.owner not in chain_cache:
                chain_cache[target.owner] = ancestry.ancestry(
                    merged, target.owner)
            chain = chain_cache[target.owner]
            resolved = ancestry.lookup(merged, target, chain)
            category = resolved.category
            providers = (target.owner,) if category == "direct_declaration" else (
                resolved.candidates)
        results.append({
            "reference": target,
            "category": category,
            "providers": providers,
            "external_edges": chain.external if chain is not None else (),
            "platform_edges": chain.platform if chain is not None else (),
            "sources": incoming[target],
        })

    access_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    private_rows = []
    direct_deps = 0
    inherited_deps = 0
    for item in results:
        reference = item["reference"]
        status_counts[item["category"]] += 1
        providers = item["providers"]
        if item["category"] == "direct_declaration" and reference.owner in dependencies:
            direct_deps += 1
        if item["category"] in ("superclass_signature_candidate",
                                "interface_signature_candidate") and any(
                                    p in dependencies for p in providers):
            inherited_deps += 1
        assessments = []
        for caller in sorted(item["sources"]):
            if not providers:
                continue
            for provider in providers:
                outcome = member_access(
                    caller, provider, merged[provider], reference)
                access_counts[outcome] += 1
                assessments.append({
                    "caller": caller, "declaration_owner": provider,
                    "access_risk": outcome,
                })
        if (item["category"] != "direct_declaration"
                or reference.owner in dependencies
                or any(x["access_risk"] not in (
                    "public_member_classloader_access_unchecked",
                    "private_same_class_candidate")
                    for x in assessments)):
            private_rows.append({
                "reference_owner": reference.owner,
                "member_name": reference.name,
                "descriptor": reference.descriptor,
                "member_kind": reference.kind,
                "category": item["category"],
                "referencers": sorted(item["sources"]),
                "possible_declaration_owners": list(providers),
                "access_signals": assessments,
                "external_ancestry_edges": list(item["external_edges"]),
                "platform_ancestry_edges": list(item["platform_edges"]),
                "owner_present_in_exact_original_v309":
                    reference.owner in original,
                "owner_present_in_alternate_dependency":
                    reference.owner in alternate,
                "jvm_linkage_verified": False,
            })

    summary = {
        "rebuilt_classfiles_examined": len(rebuilt),
        "preferred_dependency_classfiles_selected_and_parsed":
            len(dependencies),
        "unique_member_references_in_rebuilt_classfiles": len(incoming),
        "reference_owners_preferred_dependency_direct_exact_declaration":
            direct_deps,
        "possible_inherited_signatures_from_preferred_dependency":
            inherited_deps,
        "direct_declaration_signatures_in_rebuilt_or_preferred":
            status_counts["direct_declaration"],
        "possible_superclass_declaration_signatures":
            status_counts["superclass_signature_candidate"],
        "possible_interface_declaration_signatures":
            status_counts["interface_signature_candidate"],
        "unresolved_missing_preferred_owner":
            status_counts["owner_absent_from_selected_classpath"],
        "platform_owner_not_inspected":
            status_counts["platform_owner_not_inspected"],
        "unresolved_ancestry_external_or_platform":
            status_counts["ancestry_external_or_platform_unknown"],
        "unresolved_not_found_in_scanned_ancestry":
            status_counts["not_found_in_available_rebuilt_ancestry"],
        "noninheritable_or_access_unknown_ancestral_declarations":
            status_counts["ancestor_declaration_noninheritable_or_access_unknown"],
        "special_initializer_or_constructor_not_inherited":
            status_counts["special_method_not_inheritable"],
        "cycle_or_budget_uncertain":
            status_counts["cycle_or_budget_uncertain"],
        "potential_package_private_cross_package_risks":
            access_counts["package_private_cross_package_access_risk"],
        "potential_private_nestmate_or_access_uncertainties":
            access_counts["private_nestmate_or_access_unknown"],
        "protected_receiver_or_package_uncertainties":
            access_counts["protected_receiver_or_package_access_unknown"],
        "declaring_class_visibility_uncertainties":
            access_counts["declaring_class_visibility_not_proven"],
        "dependency_class_names_in_original_v309":
            len(set(dependencies) & original),
        "dependency_method_and_field_linkage_proven": False,
        "complete_dependency_runtime_classpath_proven": False,
        "jvm_nestmate_package_classloader_and_module_access_verified": False,
        "runtime_method_invocation_or_field_access_proven": False,
    }
    private = {
        "member_reference_access_and_dependency_leads": private_rows,
        "access_signals_are_advisory_not_verdicts": True,
        "preferred_dependency_bytes_are_read_only": True,
        "historical_R421_inventory_approved": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return summary, private
