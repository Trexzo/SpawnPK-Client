"""R458 bounded Java 11 invokedynamic / condy BootstrapMethods inspection.

Static classfile parsing only: never classloads, runs a bootstrap method,
resolves a CallSite, executes a ConstantDynamic, or evaluates Java code.
Typed CP tags, BootstrapMethods records, MethodHandle reference kinds and
actual Code-attribute bytecode operands are validated fail-closed. Bootstrap
target/argument identities are *reconstruction leads*, not runtime proof.
"""
from __future__ import annotations

from tools.r461 import shared_constant_pool as r461_cp

from dataclasses import dataclass

from tools.r450 import classfile_signature_resource as code_reader
from tools.r453 import classfile_member_reference as jvm
from tools.r457 import jvm_callsite_constraints as method_descriptor

MAX_CLASS = jvm.MAX_CLASS_BYTES
MAX_BOOTSTRAPS = 8192
MAX_BOOTSTRAP_ARGUMENTS = 8192
MAX_TOTAL_BOOTSTRAP_ARGUMENTS = 32768
MAX_CODE_SITES = 50000
MAX_METHODS = 60000
MAX_ATTRIBUTES = 4000
MAX_ATTRIBUTE_BYTES = 16 * 1024 * 1024
LOADABLE_TAGS = frozenset((3, 4, 5, 6, 7, 8, 15, 16, 17))
METHOD_HANDLE_TAGS = {1: (9,), 2: (9,), 3: (9,), 4: (9,),
                      5: (10,), 6: (10, 11), 7: (10, 11),
                      8: (10,), 9: (11,)}
HANDLE_NAMES = {1: "getField", 2: "getStatic", 3: "putField",
                4: "putStatic", 5: "invokeVirtual",
                6: "invokeStatic", 7: "invokeSpecial",
                8: "newInvokeSpecial", 9: "invokeInterface"}


class Refused(ValueError):
    pass


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise Refused(reason)


@dataclass(frozen=True)
class Handle:
    kind: int
    owner: str
    name: str
    descriptor: str
    target_cp_tag: int


@dataclass(frozen=True)
class DynamicSite:
    source_method: str
    pc: int
    cp_index: int
    nature: str  # invokedynamic or constant_dynamic
    name: str
    descriptor: str
    bootstrap_index: int
    bootstrap: Handle
    argument_tags: tuple[int, ...]
    # MethodHandle bootstrap arguments include lambda implementation handles.
    # These are explicit CP identities, never executed/resolved targets.
    bootstrap_handle_arguments: tuple[Handle, ...]


@dataclass(frozen=True)
class Evidence:
    class_name: str
    invokedynamic_sites: tuple[DynamicSite, ...]
    constant_dynamic_load_sites: tuple[DynamicSite, ...]
    constant_pool_invokedynamic: int
    constant_pool_dynamic: int
    method_handle_entries: int
    method_type_entries: int
    bootstrap_entries: int
    bootstrap_argument_entries: int
    bootstrap_dynamic_arguments: int
    unused_invokedynamic_cp_entries: int
    unused_dynamic_cp_entries: int
    unreferenced_bootstrap_entries: int


def scan_class(raw: bytes, *, shared_pool=None,
               shared_instructions=None) -> Evidence:
    """Strict class-file CP + BootstrapMethods + selected Code site reader."""
    need(type(raw) is bytes and 10 <= len(raw) <= MAX_CLASS
         and raw[:4] == b"\xca\xfe\xba\xbe"
         and int.from_bytes(raw[6:8], "big") == 55,
         "R458_JAVA11_CLASS_REQUIRED")
    pos = 8

    def take(n: int) -> bytes:
        nonlocal pos
        need(0 <= n <= len(raw) - pos, "R458_TRUNCATED_CLASSFILE")
        result = raw[pos:pos+n]
        pos += n
        return result

    def u1() -> int:
        return take(1)[0]

    def u2() -> int:
        return int.from_bytes(take(2), "big")

    def u4() -> int:
        return int.from_bytes(take(4), "big")

    if shared_pool is None:
        cp_count = u2()
        need(1 <= cp_count <= 65535, "R458_CP_COUNT_INVALID")
        tags = [0] * cp_count
        cp: list[object | None] = [None] * cp_count
        i = 1
        while i < cp_count:
            tag = u1()
            tags[i] = tag
            if tag == 1:
                size = u2()
                cp[i] = take(size).decode("utf-8", "replace")
            elif tag in (3, 4):
                take(4)
            elif tag in (5, 6):
                take(8)
                i += 1
            elif tag in (7, 8, 16, 19, 20):
                cp[i] = u2()
            elif tag in (9, 10, 11, 12, 17, 18):
                cp[i] = (u2(), u2())
            elif tag == 15:
                cp[i] = (u1(), u2())
            else:
                raise Refused("R458_UNKNOWN_CP_TAG")
            i += 1
    else:
        cp_count, tags, cp, pos = r461_cp.admit(shared_pool, raw)

    def typed(index: int, expected: tuple[int, ...], reason: str):
        need(type(index) is int and 0 < index < cp_count
             and tags[index] in expected, reason)
        return cp[index]

    def utf(index: int) -> str:
        value = typed(index, (1,), "R458_BAD_UTF_INDEX")
        need(type(value) is str, "R458_BAD_UTF_CONSTANT")
        return value

    def own(index: int) -> str:
        return jvm.valid_internal_name(
            utf(typed(index, (7,), "R458_BAD_CLASS_INDEX")))

    def member(index: int) -> tuple[str, str, str, int]:
        tag = tags[index] if type(index) is int and 0 < index < cp_count else 0
        owner_idx, nt_idx = typed(
            index, (9, 10, 11), "R458_HANDLE_TARGET_NOT_MEMBERREF")
        kind = "field" if tag == 9 else "method"
        ni, di = typed(nt_idx, (12,), "R458_BAD_MEMBER_NAME_TYPE")
        name, desc = utf(ni), utf(di)
        jvm.valid_member_name(name, kind)
        jvm.validate_descriptor(desc, kind)
        return own(owner_idx), name, desc, tag

    def handle(index: int) -> Handle:
        kind, target_index = typed(
            index, (15,), "R458_BAD_METHOD_HANDLE_INDEX")
        need(type(kind) is int and kind in METHOD_HANDLE_TAGS,
             "R458_INVALID_METHOD_HANDLE_KIND")
        owner, name, descriptor, tag = member(target_index)
        need(tag in METHOD_HANDLE_TAGS[kind],
             "R458_HANDLE_REFERENCE_KIND_TAG_MISMATCH")
        if kind == 8:
            need(name == "<init>",
                 "R458_NEW_INVOKE_SPECIAL_REQUIRES_INIT")
            try:
                need(method_descriptor.method_shape(descriptor).void_return,
                     "R458_NEW_INVOKE_SPECIAL_INIT_RETURNS_NONVOID")
            except method_descriptor.Refused:
                raise Refused("R458_INVALID_HANDLE_METHOD_DESCRIPTOR") from None
        elif kind >= 5:
            need(name not in ("<init>", "<clinit>"),
                 "R458_NONCONSTRUCTOR_HANDLE_SPECIAL_NAME")
        return Handle(kind, owner, name, descriptor, tag)

    def nat(index: int, kind: str) -> tuple[str, str]:
        ni, di = typed(index, (12,), "R458_DYNAMIC_NAME_AND_TYPE_INVALID")
        name, desc = utf(ni), utf(di)
        need(name not in ("<init>", "<clinit>"),
             "R458_DYNAMIC_SPECIAL_NAME_FORBIDDEN")
        jvm.valid_member_name(name, kind)
        jvm.validate_descriptor(desc, kind)
        return name, desc

    # Validate every handle and MethodType, including unused CP entries.
    handles = 0
    method_types = 0
    for idx in range(1, cp_count):
        if tags[idx] == 15:
            handle(idx)
            handles += 1
        elif tags[idx] == 16:
            desc = utf(cp[idx])
            try:
                method_descriptor.method_shape(desc)
            except method_descriptor.Refused:
                raise Refused("R458_INVALID_METHODTYPE_DESCRIPTOR") from None
            method_types += 1

    this_access = u2()
    class_path = own(u2())
    super_idx = u2()
    if super_idx:
        own(super_idx)
    count = u2()
    need(count <= MAX_METHODS, "R458_INTERFACE_COUNT_LIMIT")
    for _ in range(count):
        own(u2())

    raw_sites: list[tuple[str, int, int, int]] = []
    invokedynamic_used: set[int] = set()
    dynamic_used: set[int] = set()

    def read_attributes(context: str, method_label: str = "") -> list[tuple[str, bytes]]:
        num = u2()
        need(num <= MAX_ATTRIBUTES, "R458_ATTRIBUTE_COUNT_BUDGET")
        result = []
        for _ in range(num):
            name = utf(u2())
            length = u4()
            need(length <= MAX_ATTRIBUTE_BYTES,
                 "R458_ATTRIBUTE_BYTE_BUDGET")
            data = take(length)
            if context == "method" and name == "Code":
                parse_code(data, method_label)
            if context == "class" and name == "BootstrapMethods":
                result.append((name, data))
        return result

    def parse_code(data: bytes, method_label: str) -> None:
        p = 0

        def part(n: int) -> bytes:
            nonlocal p
            need(0 <= n <= len(data) - p, "R458_TRUNCATED_CODE")
            result = data[p:p+n]
            p += n
            return result

        def short() -> int:
            return int.from_bytes(part(2), "big")

        def word() -> int:
            return int.from_bytes(part(4), "big")

        short()  # max stack
        short()  # max locals
        length = word()
        need(length <= code_reader.MAX_CODE_BYTES,
             "R458_CODE_TOO_LARGE")
        body = part(length)
        exception_count = short()
        part(exception_count * 8)
        attrs = short()
        need(attrs <= MAX_ATTRIBUTES,
             "R458_CODE_NESTED_ATTRIBUTE_BUDGET")
        for _ in range(attrs):
            utf(short())
            nested_len = word()
            need(nested_len <= MAX_ATTRIBUTE_BYTES,
                 "R458_CODE_NESTED_ATTRIBUTE_TOO_LARGE")
            part(nested_len)
        need(p == len(data), "R458_CODE_ATTRIBUTE_TRAILING_BYTES")
        try:
            instructions = code_reader.instructions(
                body, shared_instructions=shared_instructions)
        except code_reader.Refused:
            raise Refused("R458_BAD_JVM_INSTRUCTION_BOUNDARY") from None
        for pc, op, operand in instructions:
            if op == 0xba:
                need(len(operand) == 4 and operand[2:] == b"\x00\x00",
                     "R458_BAD_INVOKEDYNAMIC_RESERVED_OPERANDS")
                ix = int.from_bytes(operand[:2], "big")
                typed(ix, (18,), "R458_INVOKEDYNAMIC_NEEDS_TAG18")
                invokedynamic_used.add(ix)
                raw_sites.append((method_label, pc, ix, 18))
            elif op in (0x12, 0x13, 0x14):
                ix = operand[0] if op == 0x12 else int.from_bytes(
                    operand, "big")
                typed(ix, tuple(range(1, 21)),
                      "R458_LDC_CP_INDEX_INVALID")
                if tags[ix] == 17:
                    bsm, nt = cp[ix]
                    _name, desc = nat(nt, "field")
                    category_two = desc in ("J", "D")
                    need((op == 0x14) == category_two,
                         "R458_CONDY_LDC_SLOT_CATEGORY_MISMATCH")
                    dynamic_used.add(ix)
                    raw_sites.append((method_label, pc, ix, 17))
            need(len(raw_sites) <= MAX_CODE_SITES,
                 "R458_CODE_DYNAMIC_SITE_BUDGET")

    for kind in ("field", "method"):
        count = u2()
        need(count <= MAX_METHODS, "R458_MEMBER_COUNT_LIMIT")
        for _ in range(count):
            u2()  # access flags
            member_name = utf(u2())
            descriptor = utf(u2())
            jvm.valid_member_name(member_name, kind)
            jvm.validate_descriptor(descriptor, kind)
            read_attributes(kind, member_name + descriptor)

    class_attrs = read_attributes("class")
    need(pos == len(raw), "R458_CLASSFILE_TRAILING_BYTES")
    bootstrap_attrs = [value for name, value in class_attrs
                       if name == "BootstrapMethods"]
    need(len(bootstrap_attrs) <= 1,
         "R458_DUPLICATE_BOOTSTRAP_METHODS_ATTRIBUTE")
    bootstrap: list[tuple[Handle, tuple[int, ...]]] = []
    total_args = 0
    if bootstrap_attrs:
        data = bootstrap_attrs[0]
        p = 0

        def short() -> int:
            nonlocal p
            need(p + 2 <= len(data), "R458_TRUNCATED_BOOTSTRAP_RECORD")
            v = int.from_bytes(data[p:p+2], "big")
            p += 2
            return v

        n = short()
        need(n <= MAX_BOOTSTRAPS, "R458_BOOTSTRAP_COUNT_LIMIT")
        for _ in range(n):
            mh = handle(short())
            need(mh.kind in (6, 8),
                 "R458_BOOTSTRAP_HANDLE_MUST_INVOKE_STATIC_OR_NEW")
            argc = short()
            need(argc <= MAX_BOOTSTRAP_ARGUMENTS,
                 "R458_BOOTSTRAP_ARG_COUNT_LIMIT")
            total_args += argc
            need(total_args <= MAX_TOTAL_BOOTSTRAP_ARGUMENTS,
                 "R458_TOTAL_BOOTSTRAP_ARGS_LIMIT")
            arguments = []
            for _ in range(argc):
                ix = short()
                typed(ix, tuple(LOADABLE_TAGS),
                      "R458_BOOTSTRAP_ARG_NOT_LOADABLE_CP")
                arguments.append(ix)
            bootstrap.append((mh, tuple(arguments)))
        need(p == len(data), "R458_BOOTSTRAP_ATTRIBUTE_TRAILING_BYTES")

    # Validate all CP17/CP18 metadata, even never-used constants. This does
    # NOT recursively resolve condy cycles or execute bootstrap arguments.
    dynamic_cp: dict[int, tuple[int, str, str]] = {}
    invoke_cp: dict[int, tuple[int, str, str]] = {}
    referenced_bsm: set[int] = set()
    for idx in range(1, cp_count):
        tag = tags[idx]
        if tag not in (17, 18):
            continue
        bsm_index, nat_index = cp[idx]
        need(bsm_index < len(bootstrap),
             "R458_DYNAMIC_BOOTSTRAP_INDEX_MISSING")
        name, descriptor = nat(
            nat_index, "field" if tag == 17 else "method")
        referenced_bsm.add(bsm_index)
        (dynamic_cp if tag == 17 else invoke_cp)[idx] = (
            bsm_index, name, descriptor)

    calls: list[DynamicSite] = []
    constants: list[DynamicSite] = []
    for method, pc, cpidx, tag in raw_sites:
        bsmidx, name, descriptor = (
            dynamic_cp if tag == 17 else invoke_cp)[cpidx]
        mh, args = bootstrap[bsmidx]
        result = DynamicSite(
            method, pc, cpidx,
            "constant_dynamic" if tag == 17 else "invokedynamic",
            name, descriptor, bsmidx, mh, tuple(tags[a] for a in args),
            tuple(handle(a) for a in args if tags[a] == 15))
        (constants if tag == 17 else calls).append(result)

    return Evidence(
        class_name=class_path,
        invokedynamic_sites=tuple(calls),
        constant_dynamic_load_sites=tuple(constants),
        constant_pool_invokedynamic=len(invoke_cp),
        constant_pool_dynamic=len(dynamic_cp),
        method_handle_entries=handles,
        method_type_entries=method_types,
        bootstrap_entries=len(bootstrap),
        bootstrap_argument_entries=total_args,
        bootstrap_dynamic_arguments=sum(
            tags[a] == 17 for _, args in bootstrap for a in args),
        unused_invokedynamic_cp_entries=len(set(invoke_cp) -
                                             invokedynamic_used),
        unused_dynamic_cp_entries=len(set(dynamic_cp) - dynamic_used),
        unreferenced_bootstrap_entries=len(set(range(len(bootstrap))) -
                                           referenced_bsm),
    )
