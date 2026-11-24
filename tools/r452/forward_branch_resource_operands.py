"""R452 bounded forward-only JVM control-flow resource argument analysis.

Extends R451's fail-closed straight-line model to a deliberately restricted,
acyclic, forward-branch CFG subset. Every possible static path is explored
without executing Java. A literal is attributed at a resource call site only
when *all visited paths reaching that site* carry the same String literal in
the actual parameter slot. Differing/unknown values are NOT attributed.

No loops, switches, exception handlers, jsr/ret, unmodeled instructions,
category-two values or arbitrary stack effects. Branch reachability is
conservative: both successors of a conditional are considered feasible.
This never proves a method is called or that a resource loads at runtime.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Callable

from tools.r450 import classfile_signature_resource as r450
from tools.r451 import straightline_resource_operands as r451

MAX_CODE = r450.MAX_CODE_BYTES
MAX_STATES = 4096
MAX_BRANCHES = 96
MAX_RESOURCE_SITES = 1024
MAX_STACK_ENTRIES = 256
MAX_LOCAL_STRING_SLOTS = 256

# Conditional branches supported by the restricted abstract interpreter.
ONE_VALUE_CONDITIONS = frozenset({
    *range(0x99, 0x9f),  # ifeq/ifne/iflt/ifge/ifgt/ifle
    0xc6, 0xc7,          # ifnull/ifnonnull
})
TWO_VALUE_CONDITIONS = frozenset(range(0x9f, 0xa7))
JUMPS = ONE_VALUE_CONDITIONS | TWO_VALUE_CONDITIONS | {0xa7, 0xc8}
FORBIDDEN_CONTROL = {0xa8, 0xa9, 0xaa, 0xab, 0xc9, 0xbf}
RETURN_OPS = frozenset({0xb0, 0xb1})


class Refused(ValueError):
    pass


class Unsupported(Exception):
    """Conservative exclusion, not malformed classfile acceptance."""


@dataclass(frozen=True)
class Evidence:
    # (bytecode pc, literal) pairs from fully attributed static call sites.
    attributed: tuple[tuple[int, str], ...]
    resource_call_sites: int
    ambiguous_resource_call_sites: int
    branch_instructions: int
    states_explored: int
    terminal_paths: int


def need(value: bool, code: str) -> None:
    if not value:
        raise Refused(code)


def analyze_method(
    code: bytes,
    max_stack: int,
    max_locals: int,
    exception_count: int,
    literal_resolver: Callable[[int], str | None],
    method_resolver: Callable[[int], tuple[str, str, str]],
    resource_filter: Callable[[str], str | None],
    *, shared_instructions=None,
) -> Evidence | None:
    """Return None unless every reachable path is supported and terminates.

    Abstract values are either known constant Strings or None (unknown).
    Branch predicates are not evaluated; both successors are traversed.
    Cycles/backward offsets and invalid branch destinations are refused.
    Any unsupported path invalidates the entire method's evidence.
    """
    need(type(code) is bytes and len(code) <= MAX_CODE
         and type(max_stack) is int and 0 <= max_stack <= 65535
         and type(max_locals) is int and 0 <= max_locals <= 65535
         and type(exception_count) is int and 0 <= exception_count <= 65535,
         "R452_INVALID_METHOD_CODE_LIMITS")
    if exception_count:
        return None
    try:
        decoded = r450.instructions(
            code, shared_instructions=shared_instructions)
    except r450.Refused:
        raise Refused("R452_INVALID_JVM_INSTRUCTION_BOUNDARIES") from None
    if not decoded:
        return None
    code_by_pc = {pc: (op, operand) for pc, op, operand in decoded}
    boundaries = set(code_by_pc)
    num_branches = 0
    destinations: dict[int, int] = {}

    for pc, op, operand in decoded:
        if op in FORBIDDEN_CONTROL:
            return None
        if op in JUMPS:
            num_branches += 1
            if num_branches > MAX_BRANCHES:
                return None
            need(len(operand) in (2, 4),
                 "R452_TRUNCATED_FORWARD_BRANCH_OFFSET")
            offset = int.from_bytes(operand, "big", signed=True)
            dest = pc + offset
            if dest <= pc:
                # Cycles and zero offset require fixpoint reasoning not
                # provided by this bounded forward-only model.
                return None
            need(dest in boundaries, "R452_FORWARD_BRANCH_MISALIGNED")
            destinations[pc] = dest

    if max_stack > MAX_STACK_ENTRIES:
        return None

    # Immutable, hashable worklist state: (pc, stack, known string locals).
    # A local absent from the tuple is an unknown symbolic value.
    initial: tuple[int, tuple[str | None, ...], tuple[tuple[int, str], ...]] = (
        0, (), ())
    pending = deque([initial])
    visited: set[tuple] = set()
    values_by_site: dict[int, set[str | None]] = defaultdict(set)
    terminal_paths = 0

    while pending:
        state = pending.popleft()
        if state in visited:
            continue
        visited.add(state)
        if len(visited) > MAX_STATES:
            return None
        pc, old_stack, known_local_pairs = state
        need(pc in code_by_pc, "R452_CONTROL_FLOW_TARGET_NOT_IN_METHOD")
        op, operand = code_by_pc[pc]
        stack = list(old_stack)
        known_locals = dict(known_local_pairs)
        next_pc = pc + 1 + len(operand)

        def push(value: str | None) -> None:
            stack.append(value)
            if len(stack) > max_stack or len(stack) > MAX_STACK_ENTRIES:
                raise Unsupported()

        def pop() -> str | None:
            if not stack:
                raise Unsupported()
            return stack.pop()

        def local(index: int) -> int:
            if index < 0 or index >= max_locals:
                raise Unsupported()
            return index

        def successors() -> tuple[int, ...]:
            if op in ONE_VALUE_CONDITIONS:
                pop()
                return next_pc, destinations[pc]
            if op in TWO_VALUE_CONDITIONS:
                pop()
                pop()
                return next_pc, destinations[pc]
            if op in (0xa7, 0xc8):
                return (destinations[pc],)
            return (next_pc,)

        try:
            if op in JUMPS:
                next_offsets = successors()
            elif op == 0x00:
                next_offsets = (next_pc,)
            elif op == 0x01 or 0x02 <= op <= 0x11:
                if op in (0x09, 0x0a, 0x0e, 0x0f):
                    raise Unsupported()  # long/double category-two
                push(None)
                next_offsets = (next_pc,)
            elif op in (0x12, 0x13):
                index = operand[0] if op == 0x12 else int.from_bytes(
                    operand, "big")
                raw = literal_resolver(index)
                push(raw if isinstance(raw, str) else None)
                next_offsets = (next_pc,)
            elif op in (0x15, 0x19):
                # For iload the integer branch predicate remains unknown.
                index = local(operand[0])
                push(known_locals.get(index) if op == 0x19 else None)
                next_offsets = (next_pc,)
            elif 0x1a <= op <= 0x1d:  # iload_0..3
                local(op - 0x1a)
                push(None)
                next_offsets = (next_pc,)
            elif 0x2a <= op <= 0x2d:  # aload_0..3
                push(known_locals.get(local(op - 0x2a)))
                next_offsets = (next_pc,)
            elif op in (0x36, 0x3a):  # istore, astore
                index = local(operand[0])
                value = pop()
                if op == 0x3a and isinstance(value, str):
                    known_locals[index] = value
                else:
                    known_locals.pop(index, None)
                next_offsets = (next_pc,)
            elif 0x3b <= op <= 0x3e:  # istore_0..3
                known_locals.pop(local(op - 0x3b), None)
                pop()
                next_offsets = (next_pc,)
            elif 0x4b <= op <= 0x4e:  # astore_0..3
                index = local(op - 0x4b)
                value = pop()
                if isinstance(value, str):
                    known_locals[index] = value
                else:
                    known_locals.pop(index, None)
                next_offsets = (next_pc,)
            elif op == 0x57:
                pop()
                next_offsets = (next_pc,)
            elif op == 0x59:
                value = pop()
                push(value)
                push(value)
                next_offsets = (next_pc,)
            elif op == 0x5f:
                first, second = pop(), pop()
                push(first)
                push(second)
                next_offsets = (next_pc,)
            elif op == 0xc0:  # checkcast
                if not stack:
                    raise Unsupported()
                next_offsets = (next_pc,)
            elif op in (0xb6, 0xb7, 0xb8, 0xb9):
                index = int.from_bytes(operand[:2], "big")
                owner, name, descriptor = method_resolver(index)
                argc, has_return, wide = r451.method_shape(descriptor)
                if wide:
                    raise Unsupported()
                args = [pop() for _ in range(argc)][::-1]
                if op != 0xb8:
                    pop()  # instance receiver
                if (owner, name, descriptor) in r450.RESOURCE_APIS:
                    if argc != 1:
                        raise Unsupported()
                    raw_value = args[0]
                    resource = (
                        resource_filter(raw_value)
                        if isinstance(raw_value, str) else None)
                    values_by_site[pc].add(resource)
                    if len(values_by_site) > MAX_RESOURCE_SITES:
                        raise Unsupported()
                if has_return:
                    push(None)
                next_offsets = (next_pc,)
            elif op in RETURN_OPS:
                if op == 0xb0:
                    pop()
                if stack:
                    raise Unsupported()
                terminal_paths += 1
                next_offsets = ()
            else:
                raise Unsupported()

            for nxt in next_offsets:
                if nxt not in code_by_pc:
                    # Reaching end-of-code without a modeled return is
                    # unknown or malformed; refuse any candidate from method.
                    raise Unsupported()
                if nxt <= pc:
                    # Should have been checked above for explicit branches.
                    raise Unsupported()
                if len(known_locals) > MAX_LOCAL_STRING_SLOTS:
                    raise Unsupported()
                pending.append(
                    (nxt, tuple(stack), tuple(sorted(known_locals.items()))))
        except Unsupported:
            return None

    if not terminal_paths:
        return None

    attributed: list[tuple[int, str]] = []
    for pc, alternatives in sorted(values_by_site.items()):
        if len(alternatives) == 1:
            sole = next(iter(alternatives))
            if isinstance(sole, str):
                attributed.append((pc, sole))
    return Evidence(
        attributed=tuple(attributed),
        resource_call_sites=len(values_by_site),
        ambiguous_resource_call_sites=sum(
            len(names) != 1 or None in names
            for names in values_by_site.values()),
        branch_instructions=num_branches,
        states_explored=len(visited),
        terminal_paths=terminal_paths,
    )


class Collector:
    """Additive observer compatible with R450's optional Code callback."""
    def __init__(self, *, shared_instructions=None):
        self.shared_instructions = shared_instructions
        self.methods_seen = 0
        self.methods_modeled = 0
        self.methods_skipped = 0
        self.methods_with_forward_branches_modeled = 0
        self.resource_call_sites = 0
        self.ambiguous_resource_call_sites = 0
        self.literal_argument_sites: list[tuple[str, int, str]] = []
        self.states_explored = 0

    def __call__(
        self, method_label: str, code: bytes, max_stack: int,
        max_locals: int, exceptions: int, literal, methodref,
        resource_filter,
    ) -> None:
        self.methods_seen += 1
        need(self.methods_seen <= 60000, "R452_METHOD_BUDGET")
        outcome = analyze_method(
            code, max_stack, max_locals, exceptions,
            literal, methodref, resource_filter,
            shared_instructions=self.shared_instructions)
        if outcome is None:
            self.methods_skipped += 1
            return
        self.methods_modeled += 1
        if outcome.branch_instructions:
            self.methods_with_forward_branches_modeled += 1
        self.states_explored += outcome.states_explored
        need(self.states_explored <= 150000,
             "R452_CLASS_STATES_BUDGET")
        self.resource_call_sites += outcome.resource_call_sites
        self.ambiguous_resource_call_sites += (
            outcome.ambiguous_resource_call_sites)
        need(self.resource_call_sites <= 20000,
             "R452_CLASS_RESOURCE_SITE_BUDGET")
        for pc, path in outcome.attributed:
            self.literal_argument_sites.append((method_label, pc, path))
        need(len(self.literal_argument_sites) <= 20000,
             "R452_CLASS_LITERAL_ARGUMENT_BUDGET")
