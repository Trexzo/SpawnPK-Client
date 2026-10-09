from __future__ import annotations

from pathlib import Path
import struct
from typing import Any
import zipfile

from .modified_utf8 import ModifiedUtf8Error, decode_modified_utf8


class BytecodeProfileError(ValueError):
    pass


_FIELD_OPS = {
    0xB2: "getstatic",
    0xB3: "putstatic",
    0xB4: "getfield",
    0xB5: "putfield",
}

_INVOKE_OPS = {
    0xB6: "invokevirtual",
    0xB7: "invokespecial",
    0xB8: "invokestatic",
    0xB9: "invokeinterface",
}

_MEMBER_REF_KINDS = {
    9: "field",
    10: "method",
    11: "interface_method",
}

_LOCAL_INDEXED_OPS = {
    0x15: "iload",
    0x16: "lload",
    0x17: "fload",
    0x18: "dload",
    0x19: "aload",
    0x36: "istore",
    0x37: "lstore",
    0x38: "fstore",
    0x39: "dstore",
    0x3A: "astore",
}

_LOCAL_SHORT_OPS = {
    **{0x1A + i: ("iload", i) for i in range(4)},
    **{0x1E + i: ("lload", i) for i in range(4)},
    **{0x22 + i: ("fload", i) for i in range(4)},
    **{0x26 + i: ("dload", i) for i in range(4)},
    **{0x2A + i: ("aload", i) for i in range(4)},
    **{0x3B + i: ("istore", i) for i in range(4)},
    **{0x3F + i: ("lstore", i) for i in range(4)},
    **{0x43 + i: ("fstore", i) for i in range(4)},
    **{0x47 + i: ("dstore", i) for i in range(4)},
    **{0x4B + i: ("astore", i) for i in range(4)},
}

_SIMPLE_INSTRUCTION_NAMES = {
    0x00: "nop",
    0x01: "aconst_null",
    0x02: "iconst_m1",
    0x03: "iconst_0",
    0x04: "iconst_1",
    0x05: "iconst_2",
    0x06: "iconst_3",
    0x07: "iconst_4",
    0x08: "iconst_5",
    0x4F: "iastore",
    0x57: "pop",
    0x58: "pop2",
    0x59: "dup",
    0x5A: "dup_x1",
    0x5B: "dup_x2",
    0x5C: "dup2",
    0x60: "iadd",
    0x64: "isub",
    0x68: "imul",
    0x6C: "idiv",
    0x70: "irem",
    0x74: "ineg",
    0x78: "ishl",
    0x7A: "ishr",
    0x7C: "iushr",
    0x7E: "iand",
    0x80: "ior",
    0x82: "ixor",
    0x85: "i2l",
    0x86: "i2f",
    0x87: "i2d",
    0xAC: "ireturn",
    0xAD: "lreturn",
    0xAE: "freturn",
    0xAF: "dreturn",
    0xB0: "areturn",
    0xB1: "return",
    0xBE: "arraylength",
    0xBF: "athrow",
    0xC2: "monitorenter",
    0xC3: "monitorexit",
}


class _Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def take(self, n: int) -> bytes:
        end = self.offset + n
        if end > len(self.data):
            raise BytecodeProfileError("unexpected EOF")
        value = self.data[self.offset:end]
        self.offset = end
        return value

    def u1(self) -> int:
        return self.take(1)[0]

    def u2(self) -> int:
        return struct.unpack(">H", self.take(2))[0]

    def u4(self) -> int:
        return struct.unpack(">I", self.take(4))[0]


def _constant_pool(r: _Reader) -> list[Any]:
    count = r.u2()
    cp: list[Any] = [None] * count
    i = 1
    while i < count:
        tag = r.u1()
        if tag == 1:
            try:
                cp[i] = (tag, decode_modified_utf8(r.take(r.u2())))
            except ModifiedUtf8Error as exc:
                raise BytecodeProfileError(f"invalid constant-pool Modified UTF-8 #{i}") from exc
        elif tag in (3, 4):
            cp[i] = (tag, r.take(4))
        elif tag in (5, 6):
            cp[i] = (tag, r.take(8))
            i += 1
        elif tag in (7, 8, 16, 19, 20):
            cp[i] = (tag, r.u2())
        elif tag in (9, 10, 11, 12, 17, 18):
            cp[i] = (tag, r.u2(), r.u2())
        elif tag == 15:
            cp[i] = (tag, r.u1(), r.u2())
        else:
            raise BytecodeProfileError(
                f"unknown constant-pool tag {tag}"
            )
        i += 1
    return cp


def _utf8(cp: list[Any], index: int) -> str:
    value = cp[index]
    if not value or value[0] != 1:
        raise BytecodeProfileError(
            f"constant pool #{index} is not Utf8"
        )
    return value[1]


def _class_name(cp: list[Any], index: int) -> str:
    value = cp[index]
    if not value or value[0] != 7:
        raise BytecodeProfileError(
            f"constant pool #{index} is not Class"
        )
    return _utf8(cp, value[1])


def _member_ref(
    cp: list[Any],
    index: int,
) -> tuple[str, str, str]:
    value = cp[index]
    if not value or value[0] not in (9, 10, 11):
        raise BytecodeProfileError(
            f"constant pool #{index} is not a member ref"
        )
    owner = _class_name(cp, value[1])
    nt = cp[value[2]]
    if not nt or nt[0] != 12:
        raise BytecodeProfileError(
            f"constant pool #{value[2]} is not NameAndType"
        )
    return owner, _utf8(cp, nt[1]), _utf8(cp, nt[2])


def _invokedynamic_ref(
    cp: list[Any],
    index: int,
) -> tuple[int, str, str]:
    value = cp[index]
    if not value or value[0] != 18:
        raise BytecodeProfileError(
            f"constant pool #{index} is not InvokeDynamic"
        )
    bootstrap_method_attr_index = int(value[1])
    nt = cp[value[2]]
    if not nt or nt[0] != 12:
        raise BytecodeProfileError(
            f"constant pool #{value[2]} is not NameAndType"
        )
    return (
        bootstrap_method_attr_index,
        _utf8(cp, nt[1]),
        _utf8(cp, nt[2]),
    )



def _bootstrap_cp_entry(
    cp: list[Any],
    index: int,
    *,
    role: str,
) -> Any:
    if not (0 < index < len(cp)):
        raise BytecodeProfileError(
            f"{role} constant-pool index out of range: {index}"
        )
    value = cp[index]
    if value is None:
        raise BytecodeProfileError(
            f"{role} constant-pool entry #{index} is unusable"
        )
    return value


def _method_handle_profile(
    cp: list[Any],
    index: int,
) -> dict[str, Any]:
    value = _bootstrap_cp_entry(
        cp,
        index,
        role="MethodHandle",
    )
    if value[0] != 15:
        raise BytecodeProfileError(
            f"constant pool #{index} is not MethodHandle"
        )
    reference_kind = int(value[1])
    if not (1 <= reference_kind <= 9):
        raise BytecodeProfileError(
            f"invalid MethodHandle reference kind: {reference_kind}"
        )
    reference_index = int(value[2])
    target = _bootstrap_cp_entry(
        cp,
        reference_index,
        role="MethodHandle target",
    )
    if target[0] not in (9, 10, 11):
        raise BytecodeProfileError(
            "MethodHandle target is not a member reference"
        )
    owner, name, descriptor = _member_ref(
        cp,
        reference_index,
    )
    target_kind = {
        9: "field",
        10: "method",
        11: "interface_method",
    }[target[0]]
    return {
        "reference_kind": reference_kind,
        "reference_index": reference_index,
        "target_kind": target_kind,
        "owner": owner,
        "name": name,
        "descriptor": descriptor,
    }


def _bootstrap_argument_profile(
    cp: list[Any],
    index: int,
) -> dict[str, Any]:
    value = _bootstrap_cp_entry(
        cp,
        index,
        role="bootstrap argument",
    )
    tag = int(value[0])
    if tag == 15:
        return {
            "constant_pool_index": index,
            "kind": "method_handle",
            "method_handle": _method_handle_profile(cp, index),
        }
    if tag == 16:
        return {
            "constant_pool_index": index,
            "kind": "method_type",
            "descriptor": _utf8(cp, int(value[1])),
        }
    if tag == 7:
        return {
            "constant_pool_index": index,
            "kind": "class",
            "name": _class_name(cp, index),
        }
    if tag == 8:
        return {
            "constant_pool_index": index,
            "kind": "string",
            "value": _utf8(cp, int(value[1])),
        }
    if tag in (3, 4):
        return {
            "constant_pool_index": index,
            "kind": "constant",
            "tag": tag,
            "value": _constant_probe_value(cp, index),
            # CP float NaN payloads and signed zero require bit-level proof.
            "constant_raw_bits": value[1].hex(),
        }
    return {
        "constant_pool_index": index,
        "kind": "constant_pool_entry",
        "tag": tag,
    }


def _bootstrap_methods_profile(
    payload: bytes,
    cp: list[Any],
) -> list[dict[str, Any]]:
    r = _Reader(payload)
    methods: list[dict[str, Any]] = []
    for index in range(r.u2()):
        method_ref = r.u2()
        argument_indices = [
            r.u2() for _ in range(r.u2())
        ]
        methods.append(
            {
                "index": index,
                "bootstrap_method_ref": method_ref,
                "bootstrap_method": _method_handle_profile(
                    cp,
                    method_ref,
                ),
                "arguments": [
                    _bootstrap_argument_profile(cp, arg)
                    for arg in argument_indices
                ],
            }
        )
    if r.offset != len(payload):
        raise BytecodeProfileError(
            "trailing bytes in BootstrapMethods attribute"
        )
    return methods


def _signature_attribute_value(
    payload: bytes,
    cp: list[Any],
    *,
    role: str,
) -> str:
    if len(payload) != 2:
        raise BytecodeProfileError(
            f"{role} Signature attribute must contain exactly one u2 index"
        )
    index = (payload[0] << 8) | payload[1]
    if not (0 < index < len(cp)):
        raise BytecodeProfileError(
            f"{role} Signature constant-pool index out of range: {index}"
        )
    value = cp[index]
    if not value or value[0] != 1:
        raise BytecodeProfileError(
            f"{role} Signature constant-pool entry #{index} is not Utf8"
        )
    return str(value[1])


def _skip_attributes(
    r: _Reader,
    cp: list[Any],
) -> None:
    for _ in range(r.u2()):
        _utf8(cp, r.u2())
        r.take(r.u4())


def _jvm_field_descriptor_end(desc: str, start: int, *, returns: bool = False) -> tuple[int, int]:
    """Parse one JVM field/return type, returning end index and argument slots."""
    i = start
    if i >= len(desc):
        raise BytecodeProfileError("truncated JVM method descriptor")
    code = desc[i]
    if code == "V" and returns:
        return i + 1, 0
    if code == "[":
        while i < len(desc) and desc[i] == "[":
            i += 1
        if i >= len(desc):
            raise BytecodeProfileError("missing JVM array component")
        if desc[i] == "L":
            end = desc.find(";", i + 1)
            if end <= i + 1:
                raise BytecodeProfileError("invalid JVM array object component")
            return end + 1, 1
        if desc[i] not in "BCDFIJSZ":
            raise BytecodeProfileError("invalid JVM array component")
        return i + 1, 1
    if code == "L":
        end = desc.find(";", i + 1)
        if end <= i + 1:
            raise BytecodeProfileError("invalid JVM object descriptor")
        return end + 1, 1
    if code in "BCFISZ":
        return i + 1, 1
    if code in "DJ":
        return i + 1, 2
    raise BytecodeProfileError("invalid JVM field descriptor type")


def _invokeinterface_argument_slots(desc: str) -> int:
    """JVM invokeinterface count includes receiver + wide primitive slots."""
    if not isinstance(desc, str) or not desc.startswith("("):
        raise BytecodeProfileError("invokeinterface requires method descriptor")
    i = 1
    count = 1
    while i < len(desc) and desc[i] != ")":
        i, slots = _jvm_field_descriptor_end(desc, i)
        count += slots
    if i >= len(desc) or desc[i] != ")":
        raise BytecodeProfileError("unterminated JVM method argument descriptor")
    i, _ = _jvm_field_descriptor_end(desc, i + 1, returns=True)
    if i != len(desc) or count > 255:
        raise BytecodeProfileError("invalid JVM method descriptor or slot count")
    return count


def _instruction_length(
    code: bytes,
    offset: int,
) -> int:
    opcode = code[offset]
    # 0xCA..0xFF are not defined classfile Code instructions (reserved
    # for debuggers/implementation use); treating them as one byte could
    # silently misalign every later decoded CP reference.
    if opcode >= 0xCA:
        raise BytecodeProfileError(f"reserved JVM Code opcode 0x{opcode:02x}")
    if opcode == 0xAA:
        padding = (4 - ((offset + 1) % 4)) % 4
        base = offset + 1 + padding
        if base + 12 > len(code):
            raise BytecodeProfileError("truncated tableswitch")
        low = struct.unpack_from(">i", code, base + 4)[0]
        high = struct.unpack_from(">i", code, base + 8)[0]
        if high < low:
            raise BytecodeProfileError("tableswitch reversed case bounds")
        count = high - low + 1
        if count > (len(code) - base - 12) // 4:
            raise BytecodeProfileError("tableswitch case table exceeds Code")
        return 1 + padding + 12 + 4 * count
    if opcode == 0xAB:
        padding = (4 - ((offset + 1) % 4)) % 4
        base = offset + 1 + padding
        if base + 8 > len(code):
            raise BytecodeProfileError("truncated lookupswitch")
        pairs = struct.unpack_from(">i", code, base + 4)[0]
        if pairs < 0 or pairs > (len(code) - base - 8) // 8:
            raise BytecodeProfileError("lookupswitch invalid pair count")
        return 1 + padding + 8 + 8 * pairs
    if opcode == 0xC4:
        if offset + 1 >= len(code):
            raise BytecodeProfileError("truncated wide")
        nested = code[offset + 1]
        if nested not in _LOCAL_INDEXED_OPS and nested != 0x84:
            raise BytecodeProfileError("invalid JVM wide nested opcode")
        return 6 if nested == 0x84 else 4

    if opcode in {
        0x10, 0x12,
        0x15, 0x16, 0x17, 0x18, 0x19,
        0x36, 0x37, 0x38, 0x39, 0x3A,
        0xA9, 0xBC,
    }:
        return 2
    if opcode in {
        0x11, 0x13, 0x14, 0x84,
        *range(0x99, 0xA9),
        0xB2, 0xB3, 0xB4, 0xB5,
        0xB6, 0xB7, 0xB8,
        0xBB, 0xBD, 0xC0, 0xC1,
        0xC6, 0xC7,
    }:
        return 3
    if opcode == 0xC5:
        return 4
    if opcode in {0xB9, 0xBA, 0xC8, 0xC9}:
        return 5
    return 1


def _field_accesses(
    code: bytes,
    cp: list[Any],
) -> list[dict[str, str]]:
    result = []
    offset = 0
    while offset < len(code):
        opcode = code[offset]
        if opcode in _FIELD_OPS:
            if offset + 3 > len(code):
                raise BytecodeProfileError(
                    "truncated field instruction"
                )
            cp_index = struct.unpack_from(
                ">H",
                code,
                offset + 1,
            )[0]
            owner, name, descriptor = _member_ref(
                cp,
                cp_index,
            )
            result.append(
                {
                    "operation": _FIELD_OPS[opcode],
                    "owner": owner,
                    "name": name,
                    "descriptor": descriptor,
                    "offset": offset,
                }
            )
        length = _instruction_length(code, offset)
        if length <= 0 or offset + length > len(code):
            raise BytecodeProfileError(
                f"invalid instruction length at {offset}"
            )
        offset += length
    return result


def _method_invocations(
    code: bytes,
    cp: list[Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    offset = 0
    while offset < len(code):
        opcode = code[offset]
        if opcode in _INVOKE_OPS:
            if offset + 3 > len(code):
                raise BytecodeProfileError(
                    "truncated method invocation"
                )
            cp_index = struct.unpack_from(
                ">H",
                code,
                offset + 1,
            )[0]
            owner, name, descriptor = _member_ref(
                cp,
                cp_index,
            )
            result.append(
                {
                    "operation": _INVOKE_OPS[opcode],
                    "owner": owner,
                    "name": name,
                    "descriptor": descriptor,
                    "offset": offset,
                }
            )
        elif opcode == 0xBA:
            if offset + 5 > len(code):
                raise BytecodeProfileError(
                    "truncated invokedynamic instruction"
                )
            cp_index = struct.unpack_from(
                ">H",
                code,
                offset + 1,
            )[0]
            bootstrap_index, name, descriptor = _invokedynamic_ref(
                cp,
                cp_index,
            )
            result.append(
                {
                    "operation": "invokedynamic",
                    "bootstrap_method_attr_index": bootstrap_index,
                    "name": name,
                    "descriptor": descriptor,
                    "offset": offset,
                }
            )
        length = _instruction_length(code, offset)
        if length <= 0 or offset + length > len(code):
            raise BytecodeProfileError(
                f"invalid instruction length at {offset}"
            )
        offset += length
    return result


def _constant_probe_value(
    cp: list[Any],
    index: int,
) -> Any:
    value = cp[index]
    if value is None:
        return None
    tag = value[0]
    if tag == 3:
        return struct.unpack(">i", value[1])[0]
    if tag == 4:
        return struct.unpack(">f", value[1])[0]
    if tag == 5:
        return struct.unpack(">q", value[1])[0]
    if tag == 6:
        return struct.unpack(">d", value[1])[0]
    if tag == 8:
        return _utf8(cp, value[1])
    if tag == 7:
        return _class_name(cp, index)
    return None


def _decoded_instructions(
    code: bytes,
    cp: list[Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    offset = 0
    while offset < len(code):
        opcode = code[offset]
        length = _instruction_length(code, offset)
        if length <= 0 or offset + length > len(code):
            raise BytecodeProfileError(f"invalid instruction length at {offset}")
        row: dict[str, Any] = {
            "offset": offset,
            "opcode": f"0x{opcode:02x}",
            "mnemonic": _SIMPLE_INSTRUCTION_NAMES.get(
                opcode,
                f"opcode_{opcode:02x}",
            ),
        }

        if opcode in _LOCAL_INDEXED_OPS:
            row["mnemonic"] = _LOCAL_INDEXED_OPS[opcode]
            row["local_index"] = int(code[offset + 1])
        elif opcode in _LOCAL_SHORT_OPS:
            mnemonic, local_index = _LOCAL_SHORT_OPS[opcode]
            row["mnemonic"] = mnemonic
            row["local_index"] = local_index
        elif 0x02 <= opcode <= 0x08:
            row["int_constant"] = opcode - 0x03
        elif opcode == 0x10:
            row["mnemonic"] = "bipush"
            row["int_constant"] = struct.unpack(
                ">b", code[offset + 1:offset + 2]
            )[0]
        elif opcode == 0x11:
            row["mnemonic"] = "sipush"
            row["int_constant"] = struct.unpack_from(
                ">h", code, offset + 1
            )[0]
        elif opcode in {0x12, 0x13, 0x14}:
            row["mnemonic"] = {
                0x12: "ldc",
                0x13: "ldc_w",
                0x14: "ldc2_w",
            }[opcode]
            cp_index = (
                int(code[offset + 1])
                if opcode == 0x12
                else struct.unpack_from(">H", code, offset + 1)[0]
            )
            row["constant_pool_index"] = cp_index
            # Preserve the JVM CP entry kind. CONSTANT_Class and
            # CONSTANT_String can resolve to identical text but are not
            # interchangeable LDC referents across client builds.
            entry = _bootstrap_cp_entry(cp, cp_index, role="ldc")
            row["constant_pool_tag"] = int(entry[0])
            if entry[0] in (3, 4, 5, 6):
                # Do not collapse NaN payloads or other raw IEEE constants.
                row["constant_raw_bits"] = entry[1].hex()
            constant = _constant_probe_value(cp, cp_index)
            if constant is not None:
                row["constant"] = constant
        elif opcode == 0x84:
            row["mnemonic"] = "iinc"
            row["local_index"] = int(code[offset + 1])
            row["increment"] = struct.unpack(
                ">b", code[offset + 2:offset + 3]
            )[0]
        elif opcode == 0xC4:
            nested = code[offset + 1]
            row["mnemonic"] = "wide"
            row["wide_opcode"] = f"0x{nested:02x}"
            if nested in _LOCAL_INDEXED_OPS:
                row["wide_mnemonic"] = _LOCAL_INDEXED_OPS[nested]
                row["local_index"] = struct.unpack_from(
                    ">H", code, offset + 2
                )[0]
            elif nested == 0x84:
                row["wide_mnemonic"] = "iinc"
                row["local_index"] = struct.unpack_from(
                    ">H", code, offset + 2
                )[0]
                row["increment"] = struct.unpack_from(
                    ">h", code, offset + 4
                )[0]
        elif opcode in _FIELD_OPS:
            row["mnemonic"] = _FIELD_OPS[opcode]
            cp_index = struct.unpack_from(">H", code, offset + 1)[0]
            owner, name, descriptor = _member_ref(cp, cp_index)
            cp_entry = _bootstrap_cp_entry(cp, cp_index, role="field instruction")
            row.update(
                {
                    "owner": owner,
                    "name": name,
                    "descriptor": descriptor,
                    "member_constant_pool_tag": cp_entry[0],
                }
            )
        elif opcode in _INVOKE_OPS:
            row["mnemonic"] = _INVOKE_OPS[opcode]
            cp_index = struct.unpack_from(">H", code, offset + 1)[0]
            owner, name, descriptor = _member_ref(cp, cp_index)
            cp_entry = _bootstrap_cp_entry(cp, cp_index, role="method instruction")
            row.update(
                {
                    "owner": owner,
                    "name": name,
                    "descriptor": descriptor,
                    "member_constant_pool_tag": cp_entry[0],
                }
            )
            if opcode == 0xB9:
                # Last two JVM invokeinterface operands: argument-slot
                # count and a reserved zero byte.
                row["invokeinterface_count"] = int(code[offset + 3])
                row["invokeinterface_reserved"] = int(code[offset + 4])
                if (
                    row["invokeinterface_reserved"] != 0
                    or row["invokeinterface_count"]
                    != _invokeinterface_argument_slots(descriptor)
                ):
                    raise BytecodeProfileError(
                        "invokeinterface argument slot count/reserved mismatch"
                    )
        elif opcode == 0xBA:
            row["mnemonic"] = "invokedynamic"
            cp_index = struct.unpack_from(">H", code, offset + 1)[0]
            bootstrap_index, name, descriptor = _invokedynamic_ref(
                cp, cp_index
            )
            row.update(
                {
                    "bootstrap_method_attr_index": bootstrap_index,
                    "name": name,
                    "descriptor": descriptor,
                    "invokedynamic_reserved": (
                        (code[offset + 3] << 8) | code[offset + 4]
                    ),
                }
            )
        elif opcode in {*range(0x99, 0xA9), 0xC6, 0xC7}:
            if offset + 3 > len(code):
                raise BytecodeProfileError(
                    f"truncated branch instruction at {offset}"
                )
            row["branch_target_offset"] = (
                offset
                + struct.unpack_from(">h", code, offset + 1)[0]
            )
        elif opcode in {0xC8, 0xC9}:
            if offset + 5 > len(code):
                raise BytecodeProfileError(
                    f"truncated wide branch instruction at {offset}"
                )
            row["branch_target_offset"] = (
                offset
                + struct.unpack_from(">i", code, offset + 1)[0]
            )
        elif opcode in {0xBB, 0xBD, 0xC0, 0xC1}:
            row["mnemonic"] = {
                0xBB: "new",
                0xBD: "anewarray",
                0xC0: "checkcast",
                0xC1: "instanceof",
            }[opcode]
            cp_index = struct.unpack_from(">H", code, offset + 1)[0]
            row["type"] = _class_name(cp, cp_index)

        row["length"] = length
        result.append(row)
        offset += length
    return result


def _normalized_class_reference(name: str) -> str | None:
    if not name.startswith("["):
        return name
    while name.startswith("["):
        name = name[1:]
    if name.startswith("L") and name.endswith(";"):
        return name[1:-1]
    return None


def profile_class_utf8_constants(
    data: bytes,
) -> list[str]:
    """Return the exact distinct CONSTANT_Utf8 payloads in a class file."""
    r = _Reader(data)
    if r.u4() != 0xCAFEBABE:
        raise BytecodeProfileError("not a JVM class")
    r.u2()
    r.u2()
    cp = _constant_pool(r)
    return sorted(
        {
            str(value[1])
            for value in cp
            if value is not None and value[0] == 1
        }
    )


def profile_class_constant_pool_references(
    data: bytes,
) -> dict[str, Any]:
    """Extract exact JVM class/member references from a class constant pool."""
    r = _Reader(data)
    if r.u4() != 0xCAFEBABE:
        raise BytecodeProfileError("not a JVM class")
    r.u2()
    r.u2()
    cp = _constant_pool(r)

    r.u2()
    this_class = r.u2()
    r.u2()
    internal_name = _class_name(cp, this_class)

    class_references: list[str] = []
    member_references: list[dict[str, str]] = []
    for index, value in enumerate(cp):
        if value is None:
            continue
        tag = value[0]
        if tag == 7:
            reference = _normalized_class_reference(
                _class_name(cp, index)
            )
            if reference is not None:
                class_references.append(reference)
        elif tag in _MEMBER_REF_KINDS:
            owner, name, descriptor = _member_ref(cp, index)
            member_references.append(
                {
                    "kind": _MEMBER_REF_KINDS[tag],
                    "owner": owner,
                    "name": name,
                    "descriptor": descriptor,
                }
            )

    return {
        "internal_name": internal_name,
        "class_references": sorted(set(class_references)),
        "member_references": sorted(
            member_references,
            key=lambda row: (
                row["owner"],
                row["kind"],
                row["name"],
                row["descriptor"],
            ),
        ),
    }


def profile_class_field_accesses(
    data: bytes,
) -> dict[str, Any]:
    """Extract declared fields plus per-method field and invocation observations."""
    r = _Reader(data)
    if r.u4() != 0xCAFEBABE:
        raise BytecodeProfileError("not a JVM class")
    r.u2()
    r.u2()
    cp = _constant_pool(r)

    r.u2()
    this_class = r.u2()
    r.u2()
    internal_name = _class_name(cp, this_class)

    for _ in range(r.u2()):
        r.u2()

    fields = []
    for _ in range(r.u2()):
        access = r.u2()
        name = _utf8(cp, r.u2())
        descriptor = _utf8(cp, r.u2())
        signature: str | None = None
        signature_seen = False
        constant_value: Any = None
        constant_value_seen = False
        for _ in range(r.u2()):
            attr_name = _utf8(cp, r.u2())
            attr_length = r.u4()
            payload = r.take(attr_length)
            if attr_name == "ConstantValue":
                if constant_value_seen:
                    raise BytecodeProfileError(
                        f"duplicate field ConstantValue attribute: {name}:{descriptor}"
                    )
                if len(payload) != 2:
                    raise BytecodeProfileError(
                        f"field {name}:{descriptor} ConstantValue must contain one u2 index"
                    )
                constant_value_seen = True
                cp_index = (payload[0] << 8) | payload[1]
                constant_value = _constant_probe_value(cp, cp_index)
                continue
            if attr_name != "Signature":
                continue
            if signature_seen:
                raise BytecodeProfileError(
                    f"duplicate field Signature attribute: {name}:{descriptor}"
                )
            signature_seen = True
            signature = _signature_attribute_value(
                payload,
                cp,
                role=f"field {name}:{descriptor}",
            )
        fields.append(
            {
                "name": name,
                "descriptor": descriptor,
                "access": access,
                "signature": signature,
                "constant_value": constant_value,
            }
        )

    methods = []
    for _ in range(r.u2()):
        access = r.u2()
        name = _utf8(cp, r.u2())
        descriptor = _utf8(cp, r.u2())
        accesses: list[dict[str, str]] = []
        invocations: list[dict[str, Any]] = []
        instructions: list[dict[str, Any]] = []
        exception_handlers: list[dict[str, Any]] = []
        code_length = None
        signature: str | None = None
        signature_seen = False
        for _ in range(r.u2()):
            attr_name = _utf8(cp, r.u2())
            attr_length = r.u4()
            payload = r.take(attr_length)
            if attr_name == "Signature":
                if signature_seen:
                    raise BytecodeProfileError(
                        f"duplicate method Signature attribute: {name}{descriptor}"
                    )
                signature_seen = True
                signature = _signature_attribute_value(
                    payload,
                    cp,
                    role=f"method {name}{descriptor}",
                )
                continue
            if attr_name != "Code":
                continue
            cr = _Reader(payload)
            cr.u2()
            cr.u2()
            code_length = cr.u4()
            code = cr.take(code_length)
            accesses = _field_accesses(code, cp)
            invocations = _method_invocations(code, cp)
            instructions = _decoded_instructions(code, cp)

            exception_handlers = []
            for _ in range(cr.u2()):
                start_pc = cr.u2()
                end_pc = cr.u2()
                handler_pc = cr.u2()
                catch_type_index = cr.u2()
                if not (
                    0 <= start_pc <= end_pc <= code_length
                    and 0 <= handler_pc < code_length
                ):
                    raise BytecodeProfileError(
                        f"invalid exception handler in {name}{descriptor}"
                    )
                exception_handlers.append(
                    {
                        "start_pc": start_pc,
                        "end_pc": end_pc,
                        "handler_pc": handler_pc,
                        "catch_type": (
                            None
                            if catch_type_index == 0
                            else _class_name(cp, catch_type_index)
                        ),
                    }
                )

            for _ in range(cr.u2()):
                cr.u2()
                cr.take(cr.u4())
            if cr.offset != len(payload):
                raise BytecodeProfileError(
                    f"trailing Code bytes in {name}{descriptor}"
                )

        methods.append(
            {
                "name": name,
                "descriptor": descriptor,
                "access": access,
                "code_length": code_length,
                "signature": signature,
                "field_accesses": accesses,
                "method_invocations": invocations,
                "instructions": instructions,
                "exception_handlers": exception_handlers,
            }
        )

    bootstrap_methods: list[dict[str, Any]] = []
    bootstrap_seen = False
    class_signature: str | None = None
    class_signature_seen = False
    for _ in range(r.u2()):
        attr_name = _utf8(cp, r.u2())
        attr_length = r.u4()
        payload = r.take(attr_length)
        if attr_name == "Signature":
            if class_signature_seen:
                raise BytecodeProfileError(
                    "duplicate class Signature attribute"
                )
            class_signature_seen = True
            class_signature = _signature_attribute_value(
                payload,
                cp,
                role=f"class {internal_name}",
            )
            continue
        if attr_name != "BootstrapMethods":
            continue
        if bootstrap_seen:
            raise BytecodeProfileError(
                "duplicate BootstrapMethods attribute"
            )
        bootstrap_seen = True
        bootstrap_methods = _bootstrap_methods_profile(
            payload,
            cp,
        )

    if r.offset != len(data):
        raise BytecodeProfileError(
            "trailing bytes after class attributes"
        )

    return {
        "internal_name": internal_name,
        "signature": class_signature,
        "fields": fields,
        "methods": methods,
        "bootstrap_methods": bootstrap_methods,
    }



def profile_jar_class(
    jar_path: Path,
    entry_path: str,
) -> dict[str, Any]:
    with zipfile.ZipFile(jar_path, "r") as archive:
        return profile_class_field_accesses(archive.read(entry_path))
