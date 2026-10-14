"""R159: read-only original JVM straight-line float-array stack → Java expression.

This conservative source-recovery candidate generator recognizes only
aload_0/getfield float[], small integer index literals, faload, and ordered
float arithmetic. It rejects branches, calls, conversions, writes, stack
rearrangements, unverified class identities, and unexpected method Code.
Reconstructed Java is PRIVATE and has no method-body acceptance until
independently compiled and compared with original JVM instructions.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
from zipfile import ZipFile

from .private_client_source_ast_census_r126 import sha_file
from .classfile import parse_class


class OriginalFloatStackR159Error(ValueError):
    pass


def _check(ok, code):
    if not ok:
        raise OriginalFloatStackR159Error(code)


def private_float_array_expression(original_jar, *, original_sha256,
                                   owner, method_name, float_array_field,
                                   expected_instructions,
                                   expected_last_offset,
                                   original_owner_sha256=None):
    _check(sha_file(original_jar) == original_sha256,
           "R159_ORIGINAL_JAR_SHA256_MISMATCH")
    for part in owner.split("/"):
        _check(bool(re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", part)),
               "R159_JVM_OWNER_NOT_JAVA_IDENTIFIER")
    _check(bool(re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", method_name))
           and bool(re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", float_array_field)),
           "R159_SOURCE_METHOD_OR_FIELD_UNSAFE")
    _check(isinstance(expected_instructions, int) and
           4 <= expected_instructions <= 2000 and
           isinstance(expected_last_offset, int) and
           3 <= expected_last_offset <= 10000,
           "R159_EXPECTED_BYTECODE_BOUND_INVALID")
    with ZipFile(original_jar) as zip_:
        original_path = owner + ".class"
        _check(zip_.namelist().count(original_path) == 1,
               "R159_ORIGINAL_CLASSFILE_IDENTITY_NOT_UNIQUE")
        original = zip_.read(original_path)
    digest = hashlib.sha256(original).hexdigest()
    if original_owner_sha256 is not None:
        _check(digest == original_owner_sha256,
               "R159_ORIGINAL_OWNER_SHA256_MISMATCH")
    parsed = parse_class(original)
    _check(parsed.name == owner and
           sum(m["name"] == method_name and m["descriptor"] == "()F"
               for m in parsed.methods) == 1 and
           sum(f["name"] == float_array_field and
               f["descriptor"] == "[F" and not f["access"] & 8
               for f in parsed.fields) == 1,
           "R159_ORIGINAL_CLASS_METHOD_OR_FIELD_NOT_PROVEN")
    javap = shutil.which("javap")
    _check(javap is not None, "R159_TRUSTED_JAVAP_REQUIRED")
    env = os.environ.copy()
    for name in ("CLASSPATH", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS",
                 "_JAVA_OPTIONS"):
        env.pop(name, None)
    try:
        result = subprocess.run([
            javap, "-p", "-s", "-c", "-classpath", str(original_jar),
            owner.replace("/", ".")], capture_output=True,
            stdin=subprocess.DEVNULL, env=env,
            timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OriginalFloatStackR159Error(
            "R159_TRUSTED_JAVAP_FAILED") from exc
    _check(result.returncode == 0 and len(result.stdout) <= 4_000_000,
           "R159_TRUSTED_JAVAP_OUTPUT_NOT_BOUNDED")
    content = result.stdout.decode("utf-8", errors="strict")
    needle = (r"(?m)^  (?:public |private |protected )?"
              + re.escape("float " + method_name + "();")
              + r"\s*\n    descriptor: \(\)F\s*\n    Code:\s*\n")
    matches = list(re.finditer(needle, content))
    _check(len(matches) == 1, "R159_BYTECODE_METHOD_HEADER_NOT_UNIQUE")
    body = content[matches[0].end():]
    instructions = []
    for line in body.splitlines():
        item = re.match(
            r"^\s*(\d+):\s+([a-z0-9_]+)"
            r"(?:\s+([^/]*?))?(?:\s+//\s*(.*))?$", line)
        if not item:
            if instructions:
                break
            continue
        offset = int(item.group(1))
        opcode = item.group(2)
        operand = (item.group(3) or "").strip()
        comment = (item.group(4) or "").strip()
        instructions.append((offset, opcode, operand, comment))
        if opcode == "freturn":
            break
    _check(len(instructions) == expected_instructions and
           instructions[-1][:2] == (expected_last_offset, "freturn") and
           all(instructions[i][0] < instructions[i+1][0]
               for i in range(len(instructions)-1)),
           "R159_JVM_INSTRUCTION_COUNT_OR_OFFSETS_DRIFTED")
    stack = []
    result_expr = None
    binary = {"fmul": "*", "fadd": "+", "fsub": "-", "fdiv": "/"}
    for offset, opcode, operand, comment in instructions:
        if opcode == "aload_0":
            stack.append("this")
        elif opcode == "getfield":
            _check(stack and stack.pop() == "this" and
                   operand.startswith("#") and
                   re.search(r"(?:^|[./])" +
                             re.escape(float_array_field) +
                             r":\[F$", comment) is not None,
                   "R159_JVM_FIELD_LOAD_NOT_EXPECTED_FLOAT_ARRAY")
            stack.append("this." + float_array_field)
        elif opcode.startswith("iconst_") and opcode[7:].isdigit():
            stack.append(opcode[7:])
        elif opcode in ("bipush", "sipush"):
            _check(bool(re.fullmatch(r"\d{1,4}", operand)),
                   "R159_INDEX_LITERAL_NOT_SAFE")
            stack.append(operand)
        elif opcode == "faload":
            _check(len(stack) >= 2, "R159_FLOAT_ARRAY_STACK_UNDERFLOW")
            index = stack.pop()
            arr = stack.pop()
            _check(arr == "this." + float_array_field and index.isdigit()
                   and 0 <= int(index) <= 255,
                   "R159_ONLY_DIRECT_FLOAT_ARRAY_INDEX_ALLOWED")
            stack.append(arr + "[" + index + "]")
        elif opcode in binary:
            _check(len(stack) >= 2, "R159_FLOAT_ARITHMETIC_STACK_UNDERFLOW")
            right, left = stack.pop(), stack.pop()
            stack.append("(" + left + binary[opcode] + right + ")")
        elif opcode == "freturn":
            _check(len(stack) == 1 and
                   "this." + float_array_field + "[" in stack[0],
                   "R159_FLOAT_RETURN_EXPRESSION_NOT_UNIQUE")
            result_expr = stack.pop()
        else:
            raise OriginalFloatStackR159Error(
                "R159_UNSUPPORTED_OR_SIDE_EFFECT_JVM_OPCODE")
        _check(len(stack) < 100 and
               sum(len(x) for x in stack) <= 100_000,
               "R159_EXPRESSION_COMPLEXITY_LIMIT_EXCEEDED")
    _check(result_expr is not None and len(result_expr) <= 30_000,
           "R159_FLOAT_SOURCE_EXPRESSION_MISSING_OR_UNBOUNDED")
    _check(sha_file(original_jar) == original_sha256,
           "R159_ORIGINAL_JAR_CHANGED_DURING_LIFT")
    return {
        "private_java_method_source": (
            "float " + method_name + "(){return " + result_expr + ";}"),
        "original_owner_class_sha256": digest,
        "original_instruction_count": len(instructions),
        "original_last_instruction_offset": expected_last_offset,
        "float_array_access_count": result_expr.count(
            "this." + float_array_field + "["),
        "source_only_not_recompiled_or_accepted": True,
    }
