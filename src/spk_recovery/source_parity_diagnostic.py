"""Bounded first-mismatch diagnostic for original-vs-rebuilt JVM source parity.

Never emit raw method bodies, arbitrary constant operands, bytecode transcripts
or original source. Source parity is still decided by the *entire* normalized
disassembly; this module only makes a refusal actionable.
"""
from __future__ import annotations

import re
from itertools import zip_longest
from typing import Sequence


_INSN = re.compile(r"^([0-9]+): ([a-z][a-z_0-9]*)(?: (.*))?$")


def first_jvm_parity_difference(
    original_rows: Sequence[str], rebuilt_rows: Sequence[str]
) -> str | None:
    """Identify the earliest mismatch without displaying original code."""
    method_index = 0
    for index, (original, rebuilt) in enumerate(
        zip_longest(original_rows, rebuilt_rows, fillvalue=None)
    ):
        if original == rebuilt:
            if original is not None and (
                original.startswith("DECL ")
                or original.startswith("CLASS ")
            ):
                method_index += 1
            continue
        left = _INSN.fullmatch(original or "")
        right = _INSN.fullmatch(rebuilt or "")
        reason = "declaration_or_descriptor"
        original_offset = "none"
        rebuilt_offset = "none"
        original_opcode = "none"
        rebuilt_opcode = "none"
        if left is not None and right is not None:
            original_offset, original_opcode, original_operand = left.groups()
            rebuilt_offset, rebuilt_opcode, rebuilt_operand = right.groups()
            if original_offset != rebuilt_offset:
                reason = "instruction_offset"
            elif original_opcode != rebuilt_opcode:
                reason = "instruction_opcode"
            else:
                reason = "instruction_operand_or_branch_target"
        elif left is not None or right is not None:
            reason = "instruction_or_declaration_shape"
            if left is not None:
                original_offset, original_opcode = left.groups()[:2]
            if right is not None:
                rebuilt_offset, rebuilt_opcode = right.groups()[:2]
        return (
            f"first_row={index} method_region={method_index}"
            f" reason={reason} original_offset={original_offset}"
            f" rebuilt_offset={rebuilt_offset}"
            f" original_opcode={original_opcode}"
            f" rebuilt_opcode={rebuilt_opcode}"
        )
    return None
