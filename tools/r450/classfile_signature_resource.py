"""R450 pure, bounded Java 11 Signature/Code attribute inspection.

Only parse classfile bytes. No filesystem, client runtime, reflection, network
or external process. Recover *possible* generic signature class references and
CONSTANT_String tokens near resource-API invokes in the *same method*.
Proximity is NOT proof that the string reaches the call: branches/stack flow,
reflection, JNI and dynamic resource names are outside this analysis.
"""
from __future__ import annotations

import re

MAX_SIGNATURE_CHARS = 65535
MAX_GENERIC_DEPTH = 48
MAX_CODE_BYTES = 65535
MAX_CODE_INSTRUCTIONS = 65535
MAX_RESOURCE_WINDOW_BYTES = 96
MAX_ATTRIBUTE_BYTES = 16 * 1024 * 1024
MAX_ATTRIBUTES = 4000
MAX_MEMBER_COUNT = 60000

RESOURCE_APIS = frozenset({
    ("java/lang/Class", "getResource",
     "(Ljava/lang/String;)Ljava/net/URL;"),
    ("java/lang/Class", "getResourceAsStream",
     "(Ljava/lang/String;)Ljava/io/InputStream;"),
    ("java/lang/ClassLoader", "getResource",
     "(Ljava/lang/String;)Ljava/net/URL;"),
    ("java/lang/ClassLoader", "getResourceAsStream",
     "(Ljava/lang/String;)Ljava/io/InputStream;"),
    ("java/lang/ClassLoader", "getResources",
     "(Ljava/lang/String;)Ljava/util/Enumeration;"),
    ("java/lang/ClassLoader", "getSystemResource",
     "(Ljava/lang/String;)Ljava/net/URL;"),
    ("java/lang/ClassLoader", "getSystemResourceAsStream",
     "(Ljava/lang/String;)Ljava/io/InputStream;"),
    ("java/lang/ClassLoader", "getSystemResources",
     "(Ljava/lang/String;)Ljava/util/Enumeration;"),
})


class Refused(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise Refused(reason)


def safe_name(name: str, *, binary: bool = True) -> str:
    require(type(name) is str and len(name) <= 4096
            and name and "\\" not in name and "\x00" not in name
            and all(re.fullmatch(r"[A-Za-z0-9_$]+", part)
                    for part in name.split("/")),
            "R450_UNSAFE_SIGNATURE_CLASS_NAME")
    return name + ".class" if binary else name


def generic_signature_refs(signature: str, kind: str) -> set[str]:
    """JVMS Signature grammar for class, field, method; includes inner types.

    Does not interpret non-signature attributes such as annotation strings.
    A type-variable is *not* a class reference. Inner segments after '.' use
    binary '$' in the resulting name, not a path separator.
    """
    require(kind in ("class", "field", "method"), "R450_UNKNOWN_SIGNATURE_KIND")
    require(type(signature) is str and 0 < len(signature) <= MAX_SIGNATURE_CHARS
            and signature.isascii(), "R450_INVALID_SIGNATURE_TEXT")
    pos = 0
    depth = 0
    refs: set[str] = set()

    def ch() -> str:
        return signature[pos] if pos < len(signature) else ""

    def take(value: str) -> None:
        nonlocal pos
        require(ch() == value, "R450_SIGNATURE_GRAMMAR_EXPECTED")
        pos += 1

    def identifier(stops: str) -> str:
        nonlocal pos
        start = pos
        while ch() and ch() not in stops:
            pos += 1
        value = signature[start:pos]
        require(value and re.fullmatch(r"[A-Za-z0-9_$]+", value) is not None,
                "R450_INVALID_SIGNATURE_IDENTIFIER")
        return value

    def nested(action) -> None:
        nonlocal depth
        depth += 1
        require(depth <= MAX_GENERIC_DEPTH, "R450_SIGNATURE_DEPTH_LIMIT")
        try:
            action()
        finally:
            depth -= 1

    def type_args() -> None:
        take("<")
        num = 0
        while ch() != ">":
            require(ch() != "", "R450_UNTERMINATED_GENERIC_ARGUMENTS")
            num += 1
            require(num <= 256, "R450_GENERIC_ARG_LIMIT")
            if ch() == "*":
                take("*")
                continue
            if ch() in "+-":
                take(ch())
            reference()
        take(">")

    def class_type() -> None:
        nonlocal pos
        take("L")
        name = identifier("/.;<")
        while ch() == "/":
            take("/")
            name += "/" + identifier("/.;<")
        safe_name(name, binary=False)
        if ch() == "<":
            nested(type_args)
        while ch() == ".":
            take(".")
            name += "$" + identifier(".;<")
            safe_name(name, binary=False)
            if ch() == "<":
                nested(type_args)
        take(";")
        refs.add(safe_name(name))

    def variable() -> None:
        take("T")
        identifier(";")
        take(";")

    def reference() -> None:
        if ch() == "L":
            nested(class_type)
        elif ch() == "T":
            variable()
        elif ch() == "[":
            take("[")
            nested(java_type)
        else:
            raise Refused("R450_INVALID_REFERENCE_SIGNATURE")

    def java_type() -> None:
        if ch() in ("B", "C", "D", "F", "I", "J", "S", "Z"):
            take(ch())
        else:
            reference()

    def type_params() -> None:
        take("<")
        num = 0
        while ch() != ">":
            require(ch() != "", "R450_UNTERMINATED_TYPE_PARAMETERS")
            num += 1
            require(num <= 256, "R450_TYPE_PARAMETER_LIMIT")
            identifier(":")
            take(":")
            if ch() != ":":
                reference()
            while ch() == ":":
                take(":")
                reference()
        take(">")

    if kind == "field":
        reference()
    elif kind == "class":
        if ch() == "<":
            type_params()
        # Supertype is a class signature, not type variable/array.
        require(ch() == "L", "R450_CLASS_SUPERTYPE_REQUIRED")
        nested(class_type)
        while ch():
            require(ch() == "L", "R450_CLASS_INTERFACE_REQUIRED")
            nested(class_type)
    else:
        if ch() == "<":
            type_params()
        take("(")
        arguments = 0
        while ch() != ")":
            require(ch() != "", "R450_UNTERMINATED_METHOD_SIGNATURE")
            arguments += 1
            require(arguments <= 255, "R450_METHOD_SIGNATURE_ARGS_LIMIT")
            java_type()
        take(")")
        if ch() == "V":
            take("V")
        else:
            java_type()
        while ch() == "^":
            take("^")
            require(ch() in ("L", "T"), "R450_INVALID_THROWS_SIGNATURE")
            reference()
    require(pos == len(signature), "R450_TRAILING_SIGNATURE_TEXT")
    return refs


# Instructions with operands, excluding variable-length switch/wide.
ONE_OPERAND = frozenset({0x10, 0x12, 0x15, 0x16, 0x17, 0x18, 0x19,
                         0x36, 0x37, 0x38, 0x39, 0x3a, 0xa9, 0xbc})
TWO_OPERANDS = frozenset({0x11, 0x13, 0x14, 0x84, *range(0x99, 0xa9),
                          *range(0xb2, 0xb9), 0xbb, 0xbd, 0xc0, 0xc1,
                          0xc6, 0xc7})
THREE_OPERANDS = frozenset({0xc5})
FOUR_OPERANDS = frozenset({0xb9, 0xba, 0xc8, 0xc9})


def instructions(code: bytes) -> list[tuple[int, int, bytes]]:
    """Exact opcode boundaries, including wide, switch alignment, and bounds."""
    require(type(code) is bytes and len(code) <= MAX_CODE_BYTES,
            "R450_CODE_LENGTH_INVALID")
    answer: list[tuple[int, int, bytes]] = []
    offset = 0
    while offset < len(code):
        start = offset
        opcode = code[offset]
        offset += 1
        require(opcode <= 0xc9, "R450_RESERVED_BYTECODE_OPCODE")
        if opcode in ONE_OPERAND:
            amount = 1
        elif opcode in TWO_OPERANDS:
            amount = 2
        elif opcode in THREE_OPERANDS:
            amount = 3
        elif opcode in FOUR_OPERANDS:
            amount = 4
        elif opcode == 0xc4:  # wide
            require(offset < len(code), "R450_TRUNCATED_WIDE")
            widened = code[offset]
            require(widened in {0x15, 0x16, 0x17, 0x18, 0x19,
                                0x36, 0x37, 0x38, 0x39, 0x3a, 0xa9, 0x84},
                    "R450_INVALID_WIDE_OPCODE")
            amount = 5 if widened == 0x84 else 3
        elif opcode in (0xaa, 0xab):
            pad = (-offset) % 4
            offset += pad
            require(offset + 8 <= len(code),
                    "R450_TRUNCATED_SWITCH_HEADER")
            if opcode == 0xaa:
                require(offset + 12 <= len(code),
                        "R450_TRUNCATED_TABLESWITCH")
                low = int.from_bytes(code[offset+4:offset+8], "big", signed=True)
                high = int.from_bytes(code[offset+8:offset+12], "big",
                                      signed=True)
                require(high >= low, "R450_INVALID_TABLESWITCH_RANGE")
                n = high - low + 1
                amount = 12 + 4*n
            else:
                n = int.from_bytes(code[offset+4:offset+8], "big",
                                   signed=True)
                require(n >= 0, "R450_INVALID_LOOKUPSWITCH_COUNT")
                amount = 8 + 8*n
        else:
            amount = 0
        require(amount <= len(code) - offset,
                "R450_TRUNCATED_BYTECODE_INSTRUCTION")
        operands = code[offset:offset+amount]
        offset += amount
        answer.append((start, opcode, operands))
        require(len(answer) <= MAX_CODE_INSTRUCTIONS,
                "R450_BYTECODE_INSTRUCTION_BUDGET")
    return answer


def classfile_evidence(raw: bytes, resource_filter) -> tuple[
        set[str], list[tuple[str, str]], int]:
    """Returns (generic types, [(method, resource literal)], API call count).

    Only constant strings within <=96 code bytes *before* the known
    resource-loading API invocation are candidates. This does not prove data
    flow or that the method is reachable or executes a resource load.
    """
    require(type(raw) is bytes and len(raw) >= 10
            and raw[:4] == b"\xca\xfe\xba\xbe"
            and int.from_bytes(raw[6:8], "big") == 55,
            "R450_JAVA11_CLASSFILE_REQUIRED")
    cursor = 8

    def grab(n: int) -> bytes:
        nonlocal cursor
        require(0 <= n <= len(raw) - cursor, "R450_TRUNCATED_CLASSFILE")
        piece = raw[cursor:cursor+n]
        cursor += n
        return piece

    def two() -> int:
        return int.from_bytes(grab(2), "big")

    def four() -> int:
        return int.from_bytes(grab(4), "big")

    cp_count = two()
    require(1 <= cp_count <= 65535, "R450_INVALID_CP_COUNT")
    tags = [0] * cp_count
    cp: list[object | None] = [None] * cp_count
    i = 1
    while i < cp_count:
        tag = grab(1)[0]
        tags[i] = tag
        if tag == 1:
            length = two()
            cp[i] = grab(length).decode("utf-8", "replace")
        elif tag in (3, 4):
            grab(4)
        elif tag in (5, 6):
            grab(8)
            i += 1
        elif tag in (7, 8, 16, 19, 20):
            cp[i] = two()
        elif tag in (9, 10, 11, 12, 17, 18):
            cp[i] = (two(), two())
        elif tag == 15:
            cp[i] = (grab(1)[0], two())
        else:
            raise Refused("R450_INVALID_CP_TAG")
        i += 1

    def utf(index: int) -> str:
        require(type(index) is int and 1 <= index < cp_count
                and tags[index] == 1 and type(cp[index]) is str,
                "R450_CP_UTF8_INDEX_INVALID")
        return cp[index]

    def class_owner(index: int) -> str:
        require(1 <= index < cp_count and tags[index] == 7,
                "R450_CP_CLASS_INDEX_INVALID")
        return utf(cp[index])

    def methodref(index: int) -> tuple[str, str, str]:
        require(1 <= index < cp_count and tags[index] in (10, 11),
                "R450_CP_METHODREF_INDEX_INVALID")
        owner_idx, nat_idx = cp[index]
        require(1 <= nat_idx < cp_count and tags[nat_idx] == 12,
                "R450_CP_NAMEANDTYPE_INDEX_INVALID")
        name_idx, desc_idx = cp[nat_idx]
        return class_owner(owner_idx), utf(name_idx), utf(desc_idx)

    generic_refs: set[str] = set()
    proximity: list[tuple[str, str]] = []
    api_calls = 0

    def code_attribute(data: bytes, method_label: str) -> None:
        nonlocal api_calls
        p = 0

        def consume(n: int) -> bytes:
            nonlocal p
            require(0 <= n <= len(data)-p, "R450_TRUNCATED_CODE_ATTRIBUTE")
            result = data[p:p+n]
            p += n
            return result

        def short() -> int:
            return int.from_bytes(consume(2), "big")

        def integer() -> int:
            return int.from_bytes(consume(4), "big")

        short()  # max_stack
        short()  # max_locals
        code_size = integer()
        require(code_size <= MAX_CODE_BYTES,
                "R450_EXCESSIVE_METHOD_CODE_LENGTH")
        method_code = consume(code_size)
        exceptions = short()
        consume(exceptions * 8)
        nested = short()
        require(nested <= MAX_ATTRIBUTES, "R450_NESTED_ATTRIBUTE_BUDGET")
        for _ in range(nested):
            utf(short())
            consume(integer())
        require(p == len(data), "R450_CODE_ATTRIBUTE_TRAILING_DATA")

        string_sites: list[tuple[int, str]] = []
        for offset, opcode, operand in instructions(method_code):
            if opcode in (0x12, 0x13):
                index = operand[0] if opcode == 0x12 else int.from_bytes(
                    operand, "big")
                require(1 <= index < cp_count, "R450_LDC_INDEX_INVALID")
                if tags[index] == 8:
                    literal = resource_filter(utf(cp[index]))
                    if literal is not None:
                        string_sites.append((offset, literal))
            if opcode in (0xb6, 0xb7, 0xb8, 0xb9):
                idx = int.from_bytes(operand[:2], "big")
                owner, name, signature = methodref(idx)
                if (owner, name, signature) not in RESOURCE_APIS:
                    continue
                api_calls += 1
                for prior_offset, literal in string_sites:
                    if (0 < offset-prior_offset <= MAX_RESOURCE_WINDOW_BYTES):
                        proximity.append((method_label, literal))

    def attributes(kind: str, method_label: str = "") -> None:
        number = two()
        require(number <= MAX_ATTRIBUTES, "R450_ATTRIBUTE_COUNT_BUDGET")
        for _ in range(number):
            name = utf(two())
            length = four()
            require(length <= MAX_ATTRIBUTE_BYTES,
                    "R450_ATTRIBUTE_TOO_LARGE")
            if name == "Signature":
                require(length == 2, "R450_INVALID_SIGNATURE_ATTRIBUTE_LENGTH")
                generic_refs.update(generic_signature_refs(
                    utf(two()), kind))
            elif name == "Code" and kind == "method":
                code_attribute(grab(length), method_label)
            else:
                grab(length)

    two()  # access_flags
    two()  # this_class
    two()  # super_class
    interfaces = two()
    grab(2*interfaces)
    for kind in ("field", "method"):
        member_count = two()
        require(member_count <= MAX_MEMBER_COUNT,
                "R450_CLASS_MEMBER_COUNT_BUDGET")
        for _ in range(member_count):
            two()  # flags
            member_name = utf(two())
            member_desc = utf(two())
            attributes(kind, member_name + member_desc)
    attributes("class")
    require(cursor == len(raw), "R450_CLASSFILE_TRAILING_BYTES")
    return generic_refs, proximity, api_calls
