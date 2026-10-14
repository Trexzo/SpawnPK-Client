"""R160: recover selected original JVM float-array local/store methods as private Java.

Recognizes a BOUNDED, straight-line stack subset: float operations, this/one
self-type parameter, float[] field loads/writes, local float slot loads/stores
and exactly one verified same-owner zero-arg float reader call. Produces Java
candidate source, NOT method acceptance; independently recompile and compare
the exact original instruction stream before accepting even a single method.

All original-source output is private. No execution of original client code.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
from zipfile import ZipFile

from .classfile import parse_class
from .private_client_source_ast_census_r126 import sha_file


class PrivateJVMFloatLocalsR160Error(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise PrivateJVMFloatLocalsR160Error(reason)


def _instructions(javap_text, header, signature):
    # Avoid matching an overloaded method with a different JVM descriptor.
    preface = "  " + header + ";\n    descriptor: " + signature + "\n    Code:\n"
    require(javap_text.count(preface) == 1,
            "R160_EXACT_JVM_METHOD_HEADER_NOT_UNIQUE")
    section = javap_text.split(preface, 1)[1]
    instructions = []
    started = False
    for line in section.splitlines():
        row = re.fullmatch(
            r"\s*(\d+):\s+([a-z][a-z0-9_]*)"
            r"(?:\s+(.*))?", line)
        if row:
            offset, opcode, raw = int(row[1]), row[2], (row[3] or "").strip()
            operand, _, comment = raw.partition("//")
            instructions.append((offset, opcode, operand.strip(), comment.strip()))
            started = True
            if opcode == "return":
                break
        elif started:
            break
    require(len(instructions) >= 4 and
            instructions[-1][1] == "return" and
            all(instructions[i][0] < instructions[i+1][0]
                for i in range(len(instructions)-1)),
            "R160_INCOMPLETE_OR_INVALID_JVM_CODE")
    return instructions


def _translate(instructions, *, field_name, method_name,
               parameter_name=None, allowed_float_reader=None):
    stack, declared, statements = [], set(), []
    limit = 8000

    def pop():
        require(bool(stack), "R160_STACK_UNDERFLOW")
        return stack.pop()

    for offset, opcode, operand, comment in instructions:
        if opcode in ("aload_0", "aload_1"):
            require(opcode != "aload_1" or parameter_name is not None,
                    "R160_UNEXPECTED_OBJECT_PARAMETER")
            stack.append("this" if opcode == "aload_0" else parameter_name)
        elif opcode == "getfield":
            owner = pop()
            require(owner in ("this", parameter_name) and
                    comment.endswith("Field " + field_name + ":[F"),
                    "R160_FIELD_IDENTITY_OR_TYPE_MISMATCH")
            stack.append(owner + "." + field_name)
        elif opcode.startswith("iconst_") and opcode[7:].isdigit():
            stack.append(opcode[7:])
        elif opcode in ("bipush", "sipush"):
            require(bool(re.fullmatch(r"\d{1,3}", operand)) and
                    int(operand) <= 255,
                    "R160_UNSAFE_ARRAY_INDEX")
            stack.append(operand)
        elif opcode == "faload":
            index, array = pop(), pop()
            require(array in ("this."+field_name,
                              parameter_name+"."+field_name
                              if parameter_name else "") and
                    index.isdecimal() and int(index) <= 255,
                    "R160_NOT_DIRECT_FLOAT_ARRAY_READ")
            stack.append(array + "["+index+"]")
        elif opcode == "fconst_1":
            stack.append("1.0F")
        elif opcode == "invokevirtual":
            receiver = pop()
            require(receiver == "this" and
                    allowed_float_reader is not None and
                    comment.endswith(
                        "Method " + allowed_float_reader + ":()F"),
                    "R160_CALL_TARGET_NOT_EXPLICITLY_PROVEN")
            stack.append("this." + allowed_float_reader + "()")
        elif opcode in ("fadd", "fsub", "fmul", "fdiv"):
            right, left = pop(), pop()
            operation = {"fadd":"+","fsub":"-","fmul":"*","fdiv":"/"}[opcode]
            stack.append("("+left+operation+right+")")
        elif opcode == "fneg":
            stack.append("(-"+pop()+")")
        elif opcode.startswith("fstore"):
            match = re.fullmatch(r"fstore_(\d+)", opcode)
            slot = int(match[1] if match else operand)
            require(1 <= slot <= 64 and
                    (match is not None or opcode == "fstore"),
                    "R160_LOCAL_FLOAT_SLOT_INVALID")
            rhs = pop()
            stm = "float v" if slot not in declared else "v"
            stm += str(slot) + "=" + rhs + ";"
            declared.add(slot)
            statements.append(stm)
        elif opcode.startswith("fload"):
            match = re.fullmatch(r"fload_(\d+)", opcode)
            slot = int(match[1] if match else operand)
            require((match is not None or opcode == "fload") and
                    slot in declared, "R160_LOCAL_FLOAT_NOT_DEFINED")
            stack.append("v" + str(slot))
        elif opcode == "fastore":
            value, index, array = pop(), pop(), pop()
            require(array == "this." + field_name and
                    index.isdecimal() and int(index) <= 255,
                    "R160_ONLY_SELF_FLOAT_ARRAY_WRITES_ALLOWED")
            statements.append(array + "[" + index + "]=" + value + ";")
        elif opcode == "return":
            require(not stack, "R160_RETURN_WITH_NONEMPTY_STACK")
        else:
            raise PrivateJVMFloatLocalsR160Error(
                "R160_UNSUPPORTED_JVM_OPCODE_REQUIRES_NEW_EVIDENCE")
        require(len(stack) <= 80 and
                len(statements) <= 128 and
                sum(map(len, stack))+sum(map(len, statements)) <= limit * 4,
                "R160_SOURCE_EXPRESSION_UNBOUNDED")
    require(1 <= len(statements) <= 128,
            "R160_NO_RECOVERABLE_SOURCE_STATEMENTS")
    params = "" if parameter_name is None else method_name[1]
    signature_name = method_name[0]
    return ("public void " + signature_name + "(" + params + "){\n"
            + "\n".join(statements) + "\n}")


def recover_original_float_local_method(
        original_jar, *, original_sha256, owner, name, descriptor,
        java_header, matrix_float_array_field,
        expected_instruction_count, expected_final_offset,
        exact_original_owner_sha256, parameter_type=None,
        allow_float_reader=None):
    """Return a PRIVATE candidate source body; NOT a verified Java recovery."""
    require(sha_file(original_jar) == original_sha256,
            "R160_ORIGINAL_JAR_HASH_DRIFT")
    require(type(owner) is str and bool(re.fullmatch(
        r"[A-Za-z_$][A-Za-z0-9_$/]*", owner)) and
        type(name) is str and bool(re.fullmatch(
            r"[A-Za-z_$][A-Za-z0-9_$]*", name)) and
        type(descriptor) is str and
        descriptor in ("()V", "(L"+owner+";)V") and
        type(matrix_float_array_field) is str and bool(re.fullmatch(
            r"[A-Za-z_$][A-Za-z0-9_$]*", matrix_float_array_field)),
        "R160_ORIGINAL_OWNER_SIGNATURE_UNSAFE")
    require(type(expected_instruction_count) is int and
            5 <= expected_instruction_count <= 2000 and
            type(expected_final_offset) is int and
            5 <= expected_final_offset <= 10000,
            "R160_EXPECTED_JVM_INSTRUCTION_BOUNDS_INVALID")
    with ZipFile(original_jar) as zip_:
        entry = owner + ".class"
        require(zip_.namelist().count(entry) == 1,
                "R160_ORIGINAL_BINARY_ID_NOT_UNIQUE")
        class_bytes = zip_.read(entry)
    digest = hashlib.sha256(class_bytes).hexdigest()
    require(digest == exact_original_owner_sha256,
            "R160_ORIGINAL_BINARY_CLASS_DIGEST_MISMATCH")
    parsed = parse_class(class_bytes)
    require(parsed.name == owner and
            sum(m["name"] == name and m["descriptor"] == descriptor
                for m in parsed.methods) == 1 and
            sum(f["name"] == matrix_float_array_field and
                f["descriptor"] == "[F" and not f["access"] & 8
                for f in parsed.fields) == 1,
            "R160_CLASS_OR_METHOD_FIELD_IDENTITY_INVALID")
    javap = shutil.which("javap")
    require(javap, "R160_TRUSTED_JDK_JAVAP_NOT_FOUND")
    env = os.environ.copy()
    for flag in ("CLASSPATH","JAVA_TOOL_OPTIONS","JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
        env.pop(flag, None)
    try:
        output = subprocess.run(
            [javap, "-p", "-s", "-c", "-classpath", str(original_jar),
             owner.replace("/", ".")],
            env=env, stdin=subprocess.DEVNULL,
            capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PrivateJVMFloatLocalsR160Error(
            "R160_TRUSTED_JAVAP_DID_NOT_FINISH") from exc
    require(output.returncode == 0 and
            len(output.stdout) <= 5_000_000,
            "R160_JAVAP_BINARY_INSPECTION_REJECTED")
    parsed_output = output.stdout.decode("utf-8",errors="strict")
    ins = _instructions(parsed_output, java_header, descriptor)
    require(len(ins) == expected_instruction_count and
            ins[-1][:2] == (expected_final_offset, "return"),
            "R160_ACTUAL_BYTECODE_BOUND_DRIFTED")
    java_params = owner.split("/")[-1] + " other" if parameter_type else ""
    generated = _translate(
        ins, field_name=matrix_float_array_field,
        method_name=(name, java_params),
        parameter_name="other" if parameter_type else None,
        allowed_float_reader=allow_float_reader)
    require(sha_file(original_jar) == original_sha256,
            "R160_ORIGINAL_INPUT_MUTATED_DURING_DECOMPILATION")
    return {
        "private_java_method_source_not_accepted": generated,
        "original_owner_class_sha256": digest,
        "original_instruction_count": len(ins),
        "original_final_offset": ins[-1][0],
        "java_source_must_be_recompiled_and_compared": True,
        "source_equivalent_to_full_original_class_verified": False,
    }
