"""R451 bounded straight-line JVM operand attribution for resource calls.

An actual literal on the operand stack at Class/ClassLoader.getResource* is
stronger evidence than R450's nearby-byte heuristic. This is NOT general JVM
verification or control-flow/dataflow, and never proves real resource loading.
Methods with branches, exception tables, unsupported opcodes, wide primitive
values, or uncertain stack states are excluded completely, not guessed.
"""
from __future__ import annotations

from collections import defaultdict

from tools.r450 import classfile_signature_resource as r450

MAX_TRACKED_METHODS = 60000
MAX_TRACKED_CALLS = 100000
MAX_STACK_ENTRIES = 256
MAX_LOCALS = 65535
MAX_METHOD_CODE = r450.MAX_CODE_BYTES
UNKNOWN = object()
CONTROL_FLOW = frozenset({
    *range(0x99, 0xaa),  # conditional branches, goto, jsr, ret
    0xaa, 0xab,         # switch instructions
    0xbf,              # athrow: exception control flow not modeled
    0xc6, 0xc7,        # ifnull, ifnonnull
    0xc8, 0xc9,        # goto_w, jsr_w
})


class Refused(ValueError):
    pass


class UnsupportedFlow(Exception):
    """Not a parser failure; skip proof for this method completely."""
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise Refused(code)


def method_shape(descriptor: str) -> tuple[int, bool, bool]:
    """Valid JVMS method descriptor -> (argument count, returns value, wide).

    Wide indicates a category-2 long/double argument or return, which the
    limited R451 symbolic stack deliberately refuses to model.
    """
    need(isinstance(descriptor, str) and descriptor.startswith("(")
         and len(descriptor) <= 65535, "R451_BAD_METHOD_DESCRIPTOR")
    i = 1
    args = 0
    wide = False

    def field_type(allow_void: bool = False) -> tuple[bool, bool]:
        nonlocal i
        dimensions = 0
        while i < len(descriptor) and descriptor[i] == "[":
            i += 1
            dimensions += 1
            need(dimensions <= 255, "R451_ARRAY_DIMENSION_LIMIT")
        need(i < len(descriptor), "R451_TRUNCATED_METHOD_DESCRIPTOR")
        typ = descriptor[i]
        i += 1
        if typ in "BCDFIJSZ":
            return True, typ in "JD" and dimensions == 0
        if allow_void and typ == "V" and dimensions == 0:
            return False, False
        if typ != "L":
            raise Refused("R451_INVALID_METHOD_TYPE")
        end = descriptor.find(";", i)
        need(end > i, "R451_UNTERMINATED_OBJECT_DESCRIPTOR")
        value = descriptor[i:end]
        need(value and all(s and s not in (".", "..") for s in value.split("/"))
             and "\\" not in value and "\x00" not in value,
             "R451_BAD_OBJECT_DESCRIPTOR")
        i = end + 1
        return True, False

    while i < len(descriptor) and descriptor[i] != ")":
        used, pair = field_type()
        need(used, "R451_VOID_ARGUMENT_REFUSED")
        args += 1
        need(args <= 255, "R451_METHOD_ARGUMENT_LIMIT")
        wide |= pair
    need(i < len(descriptor) and descriptor[i] == ")",
         "R451_METHOD_CLOSING_PAREN_MISSING")
    i += 1
    returns, pair = field_type(allow_void=True)
    wide |= pair
    need(i == len(descriptor), "R451_TRAILING_METHOD_DESCRIPTOR")
    return args, returns, wide


def trace_method(
    code: bytes,
    max_stack: int,
    max_locals: int,
    exception_count: int,
    literal_resolver,
    method_resolver,
    resource_filter,
) -> tuple[list[str], int] | None:
    """Trace only a fully modeled straight-line body, otherwise return None.

    A result contains actual symbolic string operands at recognized resource
    calls, plus the number of those calls; all other method bodies are
    refused as uncertain and do not produce any verified-argument counts.
    """
    need(isinstance(code, bytes) and len(code) <= MAX_METHOD_CODE
         and type(max_stack) is int and 0 <= max_stack <= 65535
         and type(max_locals) is int and 0 <= max_locals <= MAX_LOCALS,
         "R451_INVALID_CODE_LIMITS")
    need(type(exception_count) is int and 0 <= exception_count <= 65535,
         "R451_BAD_EXCEPTION_COUNT")
    if exception_count:
        return None
    try:
        instructions = r450.instructions(code)
    except r450.Refused:
        raise Refused("R451_MALFORMED_INSTRUCTION_STREAM") from None
    if any(opcode in CONTROL_FLOW for _, opcode, _ in instructions):
        return None

    stack: list[object] = []
    locals_known: dict[int, object] = {}
    known_arguments: list[str] = []
    calls = 0

    def push(value: object) -> None:
        stack.append(value)
        if len(stack) > MAX_STACK_ENTRIES or len(stack) > max_stack:
            raise UnsupportedFlow()

    def pop() -> object:
        if not stack:
            raise UnsupportedFlow()
        return stack.pop()

    def local_index(index: int) -> int:
        if not (0 <= index < max_locals):
            raise UnsupportedFlow()
        return index

    try:
        for pc, opcode, operand in instructions:
            if opcode in (0x00,):  # nop
                continue
            if opcode == 0x01 or 0x02 <= opcode <= 0x11:
                # aconst_null, iconst, lconst, fconst, dconst, bipush,
                # sipush; category-2 values not modeled.
                if opcode in (0x09, 0x0a, 0x0e, 0x0f):
                    raise UnsupportedFlow()
                push(UNKNOWN)
            elif opcode in (0x12, 0x13):
                index = (operand[0] if opcode == 0x12 else
                         int.from_bytes(operand, "big"))
                value = literal_resolver(index)
                push(value if isinstance(value, str) else UNKNOWN)
            elif opcode == 0x19:  # aload index
                push(locals_known.get(local_index(operand[0]), UNKNOWN))
            elif 0x2a <= opcode <= 0x2d:  # aload_0 .. aload_3
                push(locals_known.get(local_index(opcode - 0x2a), UNKNOWN))
            elif opcode == 0x3a:  # astore index
                locals_known[local_index(operand[0])] = pop()
            elif 0x4b <= opcode <= 0x4e:  # astore_0 .. astore_3
                locals_known[local_index(opcode - 0x4b)] = pop()
            elif opcode == 0x57:  # pop
                pop()
            elif opcode == 0x59:  # dup
                value = pop()
                push(value)
                push(value)
            elif opcode == 0x5f:  # swap
                a, b = pop(), pop()
                push(a)
                push(b)
            elif opcode == 0xc0:  # checkcast preserves a reference
                need(len(operand) == 2, "R451_CAST_OPERAND_TRUNCATED")
                if not stack:
                    raise UnsupportedFlow()
            elif opcode in (0xb6, 0xb7, 0xb8, 0xb9):
                index = int.from_bytes(operand[:2], "big")
                owner, name, descriptor = method_resolver(index)
                argc, returns_value, wide = method_shape(descriptor)
                if wide:
                    raise UnsupportedFlow()
                arguments = [pop() for _ in range(argc)][::-1]
                if opcode != 0xb8:  # virtual/special/interface receiver
                    pop()
                if (owner, name, descriptor) in r450.RESOURCE_APIS:
                    # For every allowlisted API, the sole method parameter is
                    # the name String. We require it to be a literal value
                    # propagated by *modeled* stack/local instructions.
                    if argc != 1:
                        raise UnsupportedFlow()
                    calls += 1
                    if isinstance(arguments[0], str):
                        candidate = resource_filter(arguments[0])
                        if candidate is not None:
                            known_arguments.append(candidate)
                if returns_value:
                    push(UNKNOWN)
            elif opcode in (0xb0,):  # areturn
                pop()
            elif opcode == 0xb1:  # return
                pass
            else:
                # Never infer stack effect for an unmodeled JVM opcode.
                # Full method discarded even if earlier calls looked good.
                raise UnsupportedFlow()
            if calls > MAX_TRACKED_CALLS:
                raise Refused("R451_METHOD_CALL_BUDGET")
    except UnsupportedFlow:
        return None
    return known_arguments, calls


class Collector:
    """R450's read-only Code callback; no state shared across method traces."""
    def __init__(self):
        self.methods_observed = 0
        self.methods_straightline_analyzed = 0
        self.methods_unsupported_or_control_flow = 0
        self.resource_calls_analyzed = 0
        self.matched_arguments: list[tuple[str, str]] = []
        self.possible_method_names: set[str] = set()

    def __call__(
        self, label: str, code: bytes, max_stack: int, max_locals: int,
        exception_count: int, literal, methodref, resource_filter,
    ) -> None:
        self.methods_observed += 1
        need(self.methods_observed <= MAX_TRACKED_METHODS,
             "R451_METHOD_BUDGET_EXCEEDED")
        result = trace_method(
            code, max_stack, max_locals, exception_count, literal,
            methodref, resource_filter)
        if result is None:
            self.methods_unsupported_or_control_flow += 1
            return
        paths, calls = result
        self.methods_straightline_analyzed += 1
        self.resource_calls_analyzed += calls
        need(self.resource_calls_analyzed <= MAX_TRACKED_CALLS,
             "R451_CLASS_RESOURCE_CALL_BUDGET")
        self.matched_arguments.extend((label, path) for path in paths)
        need(len(self.matched_arguments) <= MAX_TRACKED_CALLS,
             "R451_CLASS_LITERAL_ARGUMENT_BUDGET")
