#!/usr/bin/env python3
"""R450: read-only generic Signature and adjacent resource-callsite audit.

Requires R449's exact original-v309 SHA and isolated R421 Store/source/class
gates. Only fabricated data reaches public CI. Never executes a JVM, loads
client classes, changes game assets, or accesses persistence/history.

An adjacent ldc/ldc_w -> known resource-loader invoke is *static evidence*
of a possible resource lookup, NOT proof of flow, execution, or correctness.
Generic signatures identify additional references, NOT runtime dependencies.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.r388 import audit_offline_classpath as r388
from tools.r440 import read_only_private_acceptance_preflight as r440
from tools.r444 import scan_owner_r421_artifacts as scanner
from tools.r446 import observe_owner_private_inventory as r446
from tools.r447 import audit_original_class_asset_coverage as r447
from tools.r448 import audit_rebuilt_class_linkage as r448
from tools.r449 import audit_descriptor_resource_gaps as r449

SCHEMA = "SpawnPK-R450-generic-and-adjacent-callsite-UNAPPROVED-v1"
PREFIX = "SpawnPK-R450-Private-Callsites-"
REPORT_NAME = "R450-UNAPPROVED-GENERIC-AND-RESOURCE-CALLSITES.json"
MAX_ENTRIES = 65535
MAX_SIGNATURE = 65535
MAX_DEPTH = 48
MAX_OPERATIONS = 150000
MAX_REFS = 220000
MAX_EVIDENCE = 50000
MAX_REPORT_BYTES = 6 * 1024 * 1024

RESOURCE_METHODS = {
    ("java/lang/Class", "getResource",
     "(Ljava/lang/String;)Ljava/net/URL;"),
    ("java/lang/Class", "getResourceAsStream",
     "(Ljava/lang/String;)Ljava/io/InputStream;"),
    ("java/lang/ClassLoader", "getResource",
     "(Ljava/lang/String;)Ljava/net/URL;"),
    ("java/lang/ClassLoader", "getResourceAsStream",
     "(Ljava/lang/String;)Ljava/io/InputStream;"),
    ("java/lang/ClassLoader", "getSystemResource",
     "(Ljava/lang/String;)Ljava/net/URL;"),
    ("java/lang/ClassLoader", "getSystemResourceAsStream",
     "(Ljava/lang/String;)Ljava/io/InputStream;"),
}


class Refused(RuntimeError):
    pass


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise Refused(reason)


class Reader:
    def __init__(self, blob: bytes):
        self.blob = blob
        self.p = 0

    def take(self, count: int) -> bytes:
        need(0 <= count <= len(self.blob) - self.p,
             "R450_TRUNCATED_CLASSFILE")
        got = self.blob[self.p:self.p + count]
        self.p += count
        return got

    def u1(self) -> int:
        return self.take(1)[0]

    def u2(self) -> int:
        return int.from_bytes(self.take(2), "big")

    def u4(self) -> int:
        return int.from_bytes(self.take(4), "big")


class Signature:
    """Bounded JVM generic-signature grammar for class/field/method contexts."""

    def __init__(self, value: str):
        need(type(value) is str and 0 < len(value) <= MAX_SIGNATURE
             and value.isascii(), "R450_INVALID_SIGNATURE_TEXT")
        self.s = value
        self.p = 0
        self.refs: set[str] = set()
        self.ops = 0

    def current(self) -> str:
        return self.s[self.p:self.p + 1]

    def eat(self, token: str) -> None:
        need(self.current() == token, "R450_INVALID_SIGNATURE_GRAMMAR")
        self.p += 1

    def identifier(self, terminators: str) -> str:
        start = self.p
        while self.current() and self.current() not in terminators:
            ch = self.current()
            need(ch.isalnum() or ch in "_$/",
                 "R450_UNSAFE_SIGNATURE_IDENTIFIER")
            self.p += 1
        value = self.s[start:self.p]
        need(value and len(value) <= 4096,
             "R450_EMPTY_OR_LONG_SIGNATURE_IDENTIFIER")
        return value

    def operation(self, depth: int) -> None:
        self.ops += 1
        need(depth <= MAX_DEPTH and self.ops <= MAX_OPERATIONS,
             "R450_SIGNATURE_COMPLEXITY_LIMIT")

    def java_type(self, depth: int = 0) -> None:
        self.operation(depth)
        token = self.current()
        need(bool(token), "R450_TRUNCATED_SIGNATURE")
        if token in "BCDFIJSZ":
            self.p += 1
        else:
            self.reference(depth + 1)

    def reference(self, depth: int = 0) -> None:
        self.operation(depth)
        token = self.current()
        if token == "[":
            self.p += 1
            self.java_type(depth + 1)
        elif token == "T":
            self.p += 1
            self.identifier(";")
            self.eat(";")
        elif token == "L":
            self.p += 1
            name = self.identifier("<.;")
            self.valid_internal(name)
            self.refs.add(name + ".class")
            if self.current() == "<":
                self.type_args(depth + 1)
            while self.current() == ".":
                self.p += 1
                child = self.identifier("<.;")
                need("/" not in child,
                     "R450_INVALID_INNER_CLASS_SIGNATURE")
                name += "$" + child
                self.valid_internal(name)
                self.refs.add(name + ".class")
                if self.current() == "<":
                    self.type_args(depth + 1)
            self.eat(";")
        else:
            raise Refused("R450_INVALID_REFERENCE_SIGNATURE")

    @staticmethod
    def valid_internal(name: str) -> None:
        need(name and "\\" not in name and not name.startswith("/")
             and all(segment and segment not in (".", "..")
                     for segment in name.split("/")),
             "R450_INVALID_GENERIC_CLASS_PATH")

    def type_args(self, depth: int) -> None:
        self.operation(depth)
        self.eat("<")
        found = 0
        while self.current() and self.current() != ">":
            found += 1
            need(found <= 255, "R450_TYPE_ARG_BUDGET_EXCEEDED")
            if self.current() == "*":
                self.p += 1
            else:
                if self.current() in "+-":
                    self.p += 1
                self.reference(depth + 1)
        need(found > 0, "R450_EMPTY_GENERIC_ARGUMENTS")
        self.eat(">")

    def parameters(self, depth: int) -> None:
        self.operation(depth)
        if self.current() != "<":
            return
        self.eat("<")
        found = 0
        while self.current() and self.current() != ">":
            found += 1
            need(found <= 255, "R450_TYPE_PARAMETER_BUDGET")
            self.identifier(":")
            self.eat(":")
            if self.current() != ":":
                self.reference(depth + 1)
            while self.current() == ":":
                self.p += 1
                self.reference(depth + 1)
        need(found > 0, "R450_EMPTY_TYPE_PARAMETER_LIST")
        self.eat(">")

    def parse(self, kind: str) -> set[str]:
        need(kind in ("class", "field", "method"),
             "R450_UNKNOWN_SIGNATURE_CONTEXT")
        if kind == "field":
            self.reference()
        elif kind == "class":
            self.parameters(0)
            self.reference()
            while self.current():
                self.reference()
        else:
            self.parameters(0)
            self.eat("(")
            args = 0
            while self.current() and self.current() != ")":
                self.java_type()
                args += 1
                need(args <= 255, "R450_SIGNATURE_METHOD_ARITY_LIMIT")
            self.eat(")")
            if self.current() == "V":
                self.p += 1
            else:
                self.java_type()
            while self.current() == "^":
                self.p += 1
                need(self.current() in "LT",
                     "R450_INVALID_THROW_SIGNATURE")
                self.reference()
        need(self.p == len(self.s), "R450_SIGNATURE_TRAILING_BYTES")
        return self.refs


def generic_signature_types(value: str, kind: str) -> set[str]:
    return Signature(value).parse(kind)


def decode_instructions(code: bytes) -> list[tuple[int, int, int | None]]:
    """Parse JVM bytecode boundaries without executing or following jumps."""
    instructions = []
    p = 0
    size = len(code)
    while p < size:
        opcode = code[p]
        if opcode in (0xca, 0xfe, 0xff) or 0xcb <= opcode <= 0xfd:
            raise Refused("R450_RESERVED_BYTECODE_OPCODE")
        length = 1
        operand = None
        if opcode in (0x10, 0x12, 0x15, 0x16, 0x17, 0x18, 0x19,
                      0x36, 0x37, 0x38, 0x39, 0x3a, 0xa9, 0xbc):
            length = 2
        elif opcode in (0x11, 0x13, 0x14, 0x84, 0xbb, 0xbd,
                        0xc0, 0xc1, 0xc6, 0xc7) or (
                            0x99 <= opcode <= 0xa8) or (
                            0xb2 <= opcode <= 0xb8):
            length = 3
        elif opcode in (0xb9, 0xba, 0xc8, 0xc9):
            length = 5
        elif opcode == 0xc5:
            length = 4
        elif opcode == 0xc4:
            need(p + 1 < size, "R450_TRUNCATED_WIDE_OPCODE")
            next_opcode = code[p + 1]
            need(next_opcode in (0x15, 0x16, 0x17, 0x18, 0x19,
                                 0x36, 0x37, 0x38, 0x39, 0x3a,
                                 0x84, 0xa9),
                 "R450_INVALID_WIDE_OPCODE")
            length = 6 if next_opcode == 0x84 else 4
        elif opcode in (0xaa, 0xab):
            pad = (4 - ((p + 1) % 4)) % 4
            data = p + 1 + pad
            need(data + 8 <= size, "R450_TRUNCATED_SWITCH")
            if opcode == 0xaa:
                need(data + 12 <= size, "R450_TRUNCATED_TABLESWITCH")
                low = int.from_bytes(code[data+4:data+8], "big", signed=True)
                high = int.from_bytes(code[data+8:data+12], "big", signed=True)
                count = high - low + 1
                need(0 <= count <= size // 4, "R450_INVALID_TABLESWITCH_RANGE")
                length = 1 + pad + 12 + 4 * count
            else:
                pairs = int.from_bytes(code[data+4:data+8], "big", signed=True)
                need(0 <= pairs <= size // 8, "R450_INVALID_LOOKUPSWITCH_PAIRS")
                length = 1 + pad + 8 + 8 * pairs
        need(p + length <= size, "R450_TRUNCATED_INSTRUCTION")
        if opcode == 0x12:
            operand = code[p+1]
        elif opcode in (0x13, 0xb6, 0xb7, 0xb8, 0xb9):
            operand = int.from_bytes(code[p+1:p+3], "big")
        instructions.append((p, opcode, operand))
        need(len(instructions) <= 65535, "R450_TOO_MANY_BYTECODE_INSTRUCTIONS")
        p += length
    return instructions


def class_evidence(raw: bytes) -> tuple[set[str], set[str], list[tuple[str, str, str]]]:
    """Parse signatures/Code attributes with CP index and size validation.

    A direct adjacent ldc resource string -> known resource method invocation
    is recorded as a static callsite *candidate*; not dataflow proof.
    """
    need(type(raw) is bytes and len(raw) >= 10
         and raw[:4] == b"\xca\xfe\xba\xbe"
         and int.from_bytes(raw[6:8], "big") == 55,
         "R450_EXPECTED_JAVA11_CLASSFILE")
    r = Reader(raw)
    r.take(8)
    count = r.u2()
    need(1 <= count <= MAX_ENTRIES, "R450_BAD_CONSTANT_POOL_COUNT")
    tags = [0] * count
    pool: list[object | None] = [None] * count
    i = 1
    while i < count:
        tag = r.u1()
        tags[i] = tag
        if tag == 1:
            pool[i] = r.take(r.u2()).decode("utf-8", "replace")
        elif tag in (3, 4):
            r.take(4)
        elif tag in (5, 6):
            r.take(8)
            i += 1
        elif tag in (7, 8, 16, 19, 20):
            pool[i] = r.u2()
        elif tag in (9, 10, 11, 12, 17, 18):
            pool[i] = (r.u2(), r.u2())
        elif tag == 15:
            pool[i] = (r.u1(), r.u2())
        else:
            raise Refused("R450_BAD_CONSTANT_POOL_TAG")
        i += 1

    def utf(index: int) -> str:
        need(type(index) is int and 0 < index < count and
             tags[index] == 1 and type(pool[index]) is str,
             "R450_INVALID_UTF8_POOL_REFERENCE")
        return pool[index]

    def string_at(index: int) -> str | None:
        need(type(index) is int and 0 < index < count,
             "R450_INVALID_LDC_INDEX")
        if tags[index] != 8:
            return None
        return r449.resource_literal(utf(pool[index]))

    def resource_method(index: int) -> tuple[str, str] | None:
        need(type(index) is int and 0 < index < count,
             "R450_INVALID_METHODREF_INDEX")
        if tags[index] not in (10, 11):
            return None
        class_index, nt_index = pool[index]
        need(0 < class_index < count and tags[class_index] == 7
             and 0 < nt_index < count and tags[nt_index] == 12,
             "R450_BAD_METHODREF_POOL_REFERENCE")
        owner = utf(pool[class_index])
        method_name_index, descriptor_index = pool[nt_index]
        method_name, descriptor = utf(method_name_index), utf(descriptor_index)
        if (owner, method_name, descriptor) in RESOURCE_METHODS:
            return owner, method_name
        return None

    signature_refs: set[str] = set()
    raw_signatures: set[tuple[str, str]] = set()
    literal_strings: set[str] = set()
    callsites: list[tuple[str, str, str]] = []

    for idx in range(1, count):
        if tags[idx] == 8:
            candidate = r449.resource_literal(utf(pool[idx]))
            if candidate is not None:
                literal_strings.add(candidate)

    def parse_code(contents: bytes) -> None:
        c = Reader(contents)
        c.u2()  # max_stack
        c.u2()  # max_locals
        code_len = c.u4()
        need(0 < code_len <= 65535, "R450_INVALID_CODE_LENGTH")
        code = c.take(code_len)
        instruction_stream = decode_instructions(code)
        for index in range(1, len(instruction_stream)):
            _, prev_op, prev_id = instruction_stream[index-1]
            _, op, method_id = instruction_stream[index]
            if prev_op not in (0x12, 0x13) or op not in (0xb6, 0xb8):
                continue
            resource = string_at(prev_id)
            if resource is None:
                continue
            method = resource_method(method_id)
            if method is not None:
                callsites.append((resource, method[0], method[1]))
                need(len(callsites) <= MAX_EVIDENCE, "R450_CALLSITE_BUDGET_EXCEEDED")
        exceptions = c.u2()
        c.take(exceptions * 8)
        nested = c.u2()
        need(nested <= MAX_ENTRIES, "R450_NESTED_ATTRIBUTE_BUDGET")
        for _ in range(nested):
            utf(c.u2())
            c.take(c.u4())
        need(c.p == len(contents), "R450_CODE_ATTRIBUTE_TRAILING_BYTES")

    def attrs(kind: str) -> None:
        n = r.u2()
        need(n <= MAX_ENTRIES, "R450_ATTRIBUTE_COUNT_LIMIT")
        signature_seen = False
        code_seen = False
        for _ in range(n):
            label = utf(r.u2())
            length = r.u4()
            need(length <= len(raw) - r.p,
                 "R450_ATTRIBUTE_LENGTH_OUT_OF_RANGE")
            if label == "Signature":
                need(not signature_seen and length == 2,
                     "R450_DUPLICATE_OR_INVALID_SIGNATURE_ATTRIBUTE")
                signature_seen = True
                signature_index = int.from_bytes(r.take(2), "big")
                raw_signatures.add((kind, utf(signature_index)))
            elif label == "Code" and kind == "method":
                need(not code_seen, "R450_DUPLICATE_CODE_ATTRIBUTE")
                code_seen = True
                parse_code(r.take(length))
            else:
                r.take(length)

    r.u2()  # access
    class_index = r.u2()
    superclass = r.u2()
    need(0 < class_index < count and tags[class_index] == 7,
         "R450_INVALID_THIS_CLASS")
    need(superclass == 0 or
         (superclass < count and tags[superclass] == 7),
         "R450_INVALID_SUPER_CLASS")
    interfaces = r.u2()
    need(interfaces <= MAX_ENTRIES, "R450_INTERFACE_COUNT_LIMIT")
    for _ in range(interfaces):
        idx = r.u2()
        need(0 < idx < count and tags[idx] == 7,
             "R450_BAD_INTERFACE_CLASS_INDEX")
    for kind in ("field", "method"):
        n = r.u2()
        need(n <= MAX_ENTRIES, "R450_MEMBER_COUNT_LIMIT")
        for _ in range(n):
            r.u2()  # access flags
            utf(r.u2())  # member name
            descriptor = utf(r.u2())
            r449.descriptor_classes(descriptor)
            attrs(kind)
    attrs("class")
    need(r.p == len(raw), "R450_CLASSFILE_TRAILING_BYTES")
    for kind, signature in raw_signatures:
        signature_refs.update(generic_signature_types(signature, kind))
    return signature_refs, literal_strings, callsites


def observed_evidence(observation: dict) -> tuple[
        dict[str, set[str]], dict[str, set[str]],
        dict[str, set[str]], dict[str, list[tuple[str, str, str]]]]:
    """Re-read/hash original isolated compiled classes, reject live drift."""
    _, _, root, _, _ = r446.roots()
    class_graph: dict[str, set[str]] = {}
    signature_graph: dict[str, set[str]] = {}
    literal_graph: dict[str, set[str]] = {}
    calls: dict[str, list[tuple[str, str, str]]] = {}
    total_bytes = 0
    total_refs = 0
    for name, fingerprint in sorted(observation["class_inventory"].items()):
        r447.zip_path(name)
        need(name.endswith(".class"), "R450_NON_CLASS_IN_OBSERVATION")
        blob = scanner.read_bounded_regular(
            root.joinpath(*name.split("/")), r448.MAX_CLASS_BYTES,
            "R450_COMPILED_CLASS_TOO_LARGE")
        need(blob is not None and sha256(blob).hexdigest() == fingerprint,
             "R450_R421_COMPILED_MEMBER_CHANGED")
        total_bytes += len(blob)
        need(total_bytes <= r448.MAX_CLASS_TOTAL_BYTES,
             "R450_CLASS_TREE_BYTES_OVER_BUDGET")
        class_refs, desc_refs, _ = r449.class_metadata(blob)
        signatures, literals, pairs = class_evidence(blob)
        class_graph[name] = class_refs | desc_refs
        signature_graph[name] = signatures
        literal_graph[name] = literals
        calls[name] = pairs
        total_refs += len(class_refs) + len(desc_refs) + len(signatures)
        need(total_refs <= MAX_REFS, "R450_REFERENCE_BUDGET_EXCEEDED")
    return class_graph, signature_graph, literal_graph, calls


def aggregate(
    known_graph: dict[str, set[str]],
    generic_graph: dict[str, set[str]],
    literal_graph: dict[str, set[str]],
    call_graph: dict[str, list[tuple[str, str, str]]],
    original_classes: set[str], preferred: set[str], alternate: set[str],
    original_resources: set[str],
) -> tuple[dict, dict]:
    need(known_graph.keys() == generic_graph.keys() ==
         literal_graph.keys() == call_graph.keys(),
         "R450_CLASS_GRAPH_KEYS_MISMATCH")
    rebuilt = set(known_graph)
    already = set().union(*known_graph.values()) if rebuilt else set()
    generic_all = set().union(*generic_graph.values()) if rebuilt else set()
    additional = generic_all - already
    additional_nonplatform = {
        name for name in additional
        if not name.startswith(r388.PLATFORM_ROOTS)}
    runtime = rebuilt | preferred
    missing = additional_nonplatform - runtime
    generic_owners: dict[str, set[str]] = defaultdict(set)
    for user, names in generic_graph.items():
        for ref in names & missing:
            generic_owners[ref].add(user)
    possible_strings = set().union(*literal_graph.values()) if rebuilt else set()
    sites: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for user, found in call_graph.items():
        for path, owner, method in found:
            need(path in possible_strings,
                 "R450_CALLSITE_NOT_IN_STRING_INDEX")
            sites[(path, owner, method)].add(user)
    resources_with_sites = {path for path, _, _ in sites}
    summary = {
        "parsed_reconstructed_classfiles": len(rebuilt),
        "unique_generic_signature_class_targets": len(generic_all),
        "incremental_generic_targets_not_in_R449_index": len(additional),
        "incremental_nonplatform_generic_targets":
            len(additional_nonplatform),
        "incremental_unresolved_generic_class_targets": len(missing),
        "incremental_unresolved_generic_targets_in_original_v309":
            len(missing & original_classes),
        "incremental_unresolved_generic_targets_absent_original_v309":
            len(missing - original_classes),
        "incremental_unresolved_generic_targets_in_alternate_dependency":
            len(missing & alternate),
        "possible_resource_string_paths": len(possible_strings),
        "adjacent_resource_loader_instruction_sites":
            sum(len(found) for found in call_graph.values()),
        "unique_resource_paths_with_adjacent_loader_instructions":
            len(resources_with_sites),
        "adjacent_loader_resource_paths_present_in_original_v309":
            len(resources_with_sites & original_resources),
        "adjacent_loader_resource_paths_absent_from_original_v309":
            len(resources_with_sites - original_resources),
        "runtime_resource_load_proven": False,
        "generic_signature_runtime_dependency_proven": False,
        "original_instruction_parity_proven": False,
        "complete_java_source_proven": False,
    }
    private = {
        "incremental_unresolved_generic_targets": [
            {"class_name": name, "referencing_reconstructed_class_names":
             sorted(generic_owners[name]), "present_original_v309":
             name in original_classes,
             "available_alternate_dependency": name in alternate,
             "behavioral_reachability_proven": False}
            for name in sorted(missing,
                               key=lambda n: (-len(generic_owners[n]), n))],
        "adjacent_string_to_resource_loader_candidates": [
            {"resource_path": path, "loader_owner": owner,
             "loader_method": method, "reconstructed_referencers":
             sorted(users), "present_in_original_v309": path in original_resources,
             "resource_load_executed": False}
            for (path, owner, method), users in sorted(sites.items())],
        "historical_R421_reference_approved": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return summary, private


def inspect(original: Path, companion: Path | None = None) -> tuple[dict, dict]:
    older, _ = r449.inspect(original, companion)
    observed, _ = r446.observe()
    known, generic, literal, sites = observed_evidence(observed)
    raw = r447.read_pinned_original(original)
    original_classes, original_resources, _ = r447.archive(raw, "original")
    _, _, _, preferred_file, alternate_file = r446.roots()
    preferred_bytes = scanner.read_bounded_regular(
        preferred_file, r447.MAX_DEPENDENCY_BYTES, "R450_PREFERRED_TOO_LARGE")
    alternate_bytes = scanner.read_bounded_regular(
        alternate_file, r447.MAX_DEPENDENCY_BYTES, "R450_ALTERNATE_TOO_LARGE")
    need(preferred_bytes is not None and alternate_bytes is not None,
         "R450_DEPENDENCY_MISSING_OR_UNSAFE")
    need(sha256(preferred_bytes).hexdigest() ==
         observed["dependency_sha256"]["R239_filtered.jar"]
         and sha256(alternate_bytes).hexdigest() ==
         observed["dependency_sha256"]["R218.jar"],
         "R450_DEPENDENCIES_CHANGED_DURING_AUDIT")
    preferred, _, _ = r447.archive(preferred_bytes, "dependency")
    alternate, _, _ = r447.archive(alternate_bytes, "dependency")
    numbers, details = aggregate(
        known, generic, literal, sites, original_classes, preferred,
        alternate, original_resources)
    after, _ = r446.observe()
    need(after == observed, "R450_R421_INPUT_CHANGED_DURING_AUDIT")
    r447.read_pinned_original(original)  # exact original SHA again
    return {
        "status": "R450_GENERIC_SIGNATURE_RESOURCE_CALLSITE_UNAPPROVED",
        "original_exact_v309_sha_matched":
            older["exact_original_v309_sha_matched"],
        "original_classfiles": older["original_class_files"],
        "original_resource_files": older["original_resource_files"],
        "reconstructed_java_sources": older["rebuilt_java_sources"],
        "reconstructed_classfiles": older["rebuilt_compiled_class_files"],
        "resource_companion_checked": companion is not None,
        "independently_approved_R421_manifest_present": False,
        "source_compiled_in_this_audit": False,
        "game_client_started": False,
        "player_history_accessed": False,
        "live_asset_loading_tested": False,
        "release_authorized": False,
        "merge_authorized": False,
        **numbers,
    }, {
        "schema": SCHEMA,
        "current_observation_unapproved": True,
        "details": details,
        "historical_R421_manifest_approved": False,
        "runtime_tested": False,
        "release_authorized": False,
        "merge_authorized": False,
    }


def save_private(report: dict) -> str:
    temp, *_ = r446.roots()
    need(scanner.directory(temp), "R450_PRIVATE_TEMP_MISSING")
    raw = (json.dumps(report, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":")) + "\n").encode("ascii")
    need(len(raw) <= MAX_REPORT_BYTES, "R450_PRIVATE_REPORT_TOO_LARGE")
    folder = Path(tempfile.mkdtemp(prefix=PREFIX, dir=str(temp)))
    need(folder.parent == temp and scanner.directory(folder),
         "R450_PRIVATE_QUARANTINE_INVALID")
    output = folder / REPORT_NAME
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_BINARY", 0) |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return folder.name


def run(original: Path, companion: Path | None = None, save: bool = False) -> dict:
    summary, details = inspect(original, companion)
    if save:
        twice, next_details = inspect(original, companion)
        need(twice == summary and next_details == details,
             "R450_INPUT_CHANGED_BEFORE_PRIVATE_OUTPUT")
        summary["private_quarantine_directory_name"] = save_private(details)
        summary["private_worklist_saved"] = True
    else:
        summary["private_worklist_saved"] = False
    return summary


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-v309-jar", type=Path, required=True)
    p.add_argument("--resource-companion-root", type=Path)
    p.add_argument("--save-private-unapproved-worklist", action="store_true")
    args = p.parse_args(argv)
    try:
        print(json.dumps(run(args.original_v309_jar, args.resource_companion_root,
                             args.save_private_unapproved_worklist),
                         sort_keys=True))
        return 0
    except (Refused, r449.Refused, r448.Refused, r447.Refused, r446.Refused,
            scanner.Refused, r440.Refused, OSError, ValueError,
            TypeError, UnicodeError) as error:
        reason = str(error) if isinstance(error, (
            Refused, r449.Refused, r448.Refused, r447.Refused,
            r446.Refused, scanner.Refused, r440.Refused)) else (
            "R450_READ_ONLY_OWNER_INPUT_REFUSED")
        print(json.dumps({
            "status": "R450_GENERIC_RESOURCE_AUDIT_REFUSED",
            "reason": reason[:120],
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
