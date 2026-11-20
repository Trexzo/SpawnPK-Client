"""R450 fabricated Java11 generic-signature and adjacent resource-callsite tests.

No SpawnPK client, private Java, assets, history or journal in hosted CI.
Uses exact invented owner TEMP source/class/dependency/JAR layout from R449.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r449_descriptor_resource_gaps as fixture
from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r450 import audit_generic_signatures_resource_calls as r450

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r450/audit_generic_signatures_resource_calls.py"


def invented_class(
    *,
    field_signature="Ljava/util/List<Lrs/SigOnly;>;",
    method_signature="<T:Lrs/SigBound;>(Lrs/SigMissing;)Lrs/SigOriginal;",
    class_signature="<X:Lrs/SigOnly;>Ljava/lang/Object;",
    resource="images/logo.png",
    adjacent=True,
    call="getResource",
    method_owner="java/lang/Class",
    altered_opcode=None,
) -> bytes:
    """Invented classfile with Signature attributes and Code instruction bytes."""
    cp: list[bytes] = []

    def utf(s: str) -> int:
        raw = s.encode("utf-8")
        index = len(cp) + 1
        cp.append(b"\x01" + len(raw).to_bytes(2, "big") + raw)
        return index

    def cls(s: str) -> int:
        name = utf(s)
        i = len(cp) + 1
        cp.append(b"\x07" + name.to_bytes(2, "big"))
        return i

    def name_and_type(name: str, descriptor: str) -> int:
        ni, di = utf(name), utf(descriptor)
        i = len(cp) + 1
        cp.append(b"\x0c" + ni.to_bytes(2, "big") + di.to_bytes(2, "big"))
        return i

    own = cls("rs/plugins/loottracker/LootHistoryStore")
    superclass = cls("java/lang/Object")
    loader = cls(method_owner)
    field_name = utf("genericField")
    field_desc = utf("Ljava/util/List;")
    method_name = utf("inventedMethod")
    method_desc = utf("()V")
    signature_tag, code_tag = utf("Signature"), utf("Code")
    class_sig_idx = utf(class_signature)
    field_sig_idx = utf(field_signature)
    method_sig_idx = utf(method_signature)
    res_idx = utf(resource)
    string_const = len(cp) + 1
    cp.append(b"\x08" + res_idx.to_bytes(2, "big"))
    desc = ("(Ljava/lang/String;)Ljava/io/InputStream;"
            if call.endswith("AsStream") else
            "(Ljava/lang/String;)Ljava/net/URL;")
    nt = name_and_type(call, desc)
    method_ref = len(cp) + 1
    cp.append(b"\x0a" + loader.to_bytes(2, "big")
              + nt.to_bytes(2, "big"))
    assert string_const < 256

    def attribute(label: int, body: bytes) -> bytes:
        return (label.to_bytes(2, "big") +
                len(body).to_bytes(4, "big") + body)

    def signature_attribute(idx: int) -> bytes:
        return attribute(signature_tag, idx.to_bytes(2, "big"))

    code = b"\x12" + bytes([string_const])
    if not adjacent:
        code += b"\x00"  # nop separates literal and invocation
    code += (bytes([altered_opcode]) if altered_opcode is not None
             else b"\xb6")
    code += method_ref.to_bytes(2, "big")
    code += b"\xb1"  # return, not executed in a test
    code_attr = (
        b"\x00\x04" + b"\x00\x01" +
        len(code).to_bytes(4, "big") + code +
        b"\x00\x00" + b"\x00\x00"
    )
    header = (b"\xca\xfe\xba\xbe\x00\x00\x00\x37" +
              (len(cp) + 1).to_bytes(2, "big") + b"".join(cp))
    fields = (b"\x00\x01" +
              b"\x00\x02" + field_name.to_bytes(2, "big") +
              field_desc.to_bytes(2, "big") + b"\x00\x01" +
              signature_attribute(field_sig_idx))
    methods = (
        b"\x00\x01" + b"\x00\x01" + method_name.to_bytes(2, "big") +
        method_desc.to_bytes(2, "big") + b"\x00\x02" +
        signature_attribute(method_sig_idx) +
        attribute(code_tag, code_attr))
    return (header + b"\x00\x21" + own.to_bytes(2, "big") +
            superclass.to_bytes(2, "big") + b"\x00\x00" +
            fields + methods + b"\x00\x01" +
            signature_attribute(class_sig_idx))


class R450GenericResourceCallsites(unittest.TestCase):
    def setUp(self):
        fixture.R449DescriptorResourceRegression.setUp(self)
        self.original_entries.pop("rs/Candidate.class", None)
        self.original_entries["rs/SigOriginal.class"] = b"invented original class"
        self.original_jar.write_bytes(fixture.r448_test_fixture.fake_zip(
            self.original_entries))
        old_store = invented_class()
        self.store_class.write_bytes(old_store)
        for obj, key, val in (
            (r425, "PINNED_R421_STORE_CLASS",
             sha256(old_store).hexdigest()),
            (r450.r447, "ORIGINAL_SHA",
             sha256(self.original_jar.read_bytes()).hexdigest()),
        ):
            change = patch.object(obj, key, val)
            change.start()
            self.addCleanup(change.stop)

    def private_outputs(self):
        return sorted(self.temp.glob(r450.PREFIX + "*"))

    def test_01_field_generic_signature_has_only_nested_class_types(self):
        parsed = r450.generic_signature_types(
            "Ljava/util/Map<Ljava/lang/String;Ljava/util/List<Lrs/SigOnly;>;>;",
            "field")
        self.assertEqual(parsed, {
            "java/util/Map.class", "java/lang/String.class",
            "java/util/List.class", "rs/SigOnly.class"})

    def test_02_class_signature_type_variable_bounds(self):
        parsed = r450.generic_signature_types(
            "<T:Lrs/SigBound;:Ljava/io/Serializable;>"
            "Ljava/lang/Object;Lrs/Interface<Lrs/Item;>;", "class")
        self.assertEqual(parsed, {
            "rs/SigBound.class", "java/io/Serializable.class",
            "java/lang/Object.class", "rs/Interface.class", "rs/Item.class"})

    def test_03_generic_method_wildcards_and_array_arguments(self):
        parsed = r450.generic_signature_types(
            "(Ljava/util/List<+Lrs/Wild;>;[Lrs/Array;)V", "method")
        self.assertEqual(parsed, {"java/util/List.class",
                                  "rs/Wild.class", "rs/Array.class"})

    def test_04_method_signature_return_and_throws(self):
        actual = r450.generic_signature_types(
            "<T:Lrs/Bound;>([Lrs/Array;TT;)Lrs/Result;"
            "^Ljava/io/IOException;^TT;", "method")
        self.assertEqual(actual, {"rs/Bound.class", "rs/Array.class",
                                  "rs/Result.class", "java/io/IOException.class"})

    def test_05_inner_generic_class_separator_mapping(self):
        classes = r450.generic_signature_types(
            "Ljava/util/Map<TK;TV;>.Entry<Lrs/SigOnly;>;", "field")
        self.assertEqual(classes, {
            "java/util/Map.class", "java/util/Map$Entry.class",
            "rs/SigOnly.class"})

    def test_06_invalid_generic_signatures_fail_closed(self):
        for value, kind in (
            ("", "field"), ("Lrs/Missing", "field"),
            ("Lrs/Foo<>;", "field"),
            ("Lrs/Foo<+>;", "field"),
            ("(Lrs/Type;)X", "method"),
            ("<T:Lrs/Foo;>", "class"),
            ("(Lrs/Foo;)V^I", "method"),
            ("L../Escape;", "field"),
            ("T;", "field"),
            ("[V", "field"),
            ("Ljava/util/List<Lrs/Thing;>;unrelated", "field"),
        ):
            with self.subTest(sig=value):
                with self.assertRaises(r450.Refused):
                    r450.generic_signature_types(value, kind)

    def test_07_fabricated_real_java11_class_metadata_parsed(self):
        refs, literals, pairs = r450.class_evidence(self.store_class.read_bytes())
        self.assertEqual(refs, {
            "java/util/List.class", "rs/SigOnly.class",
            "rs/SigBound.class", "rs/SigMissing.class",
            "rs/SigOriginal.class", "java/lang/Object.class"})
        self.assertEqual(literals, {"images/logo.png"})
        self.assertEqual(
            pairs, [("images/logo.png", "java/lang/Class", "getResource")])

    def test_08_no_adjacent_callsite_if_nop_between(self):
        data = invented_class(adjacent=False)
        _, literals, pairs = r450.class_evidence(data)
        self.assertEqual(literals, {"images/logo.png"})
        self.assertEqual(pairs, [])

    def test_09_similar_name_unknown_loader_not_credited(self):
        data = invented_class(method_owner="rs/NotActuallyClass")
        self.assertEqual(r450.class_evidence(data)[2], [])

    def test_10_method_name_without_matching_descriptor_not_credited(self):
        data = invented_class(call="getResourceAsStream",
                              method_owner="rs/NotClass")
        self.assertEqual(r450.class_evidence(data)[2], [])

    def test_11_resource_candidate_not_named_in_original(self):
        data = invented_class(resource="images/not-in-original.png")
        refs, literals, pairs = r450.class_evidence(data)
        self.assertIn("images/not-in-original.png", literals)
        self.assertEqual(len(pairs), 1)
        self.assertIn("rs/SigOnly.class", refs)

    def test_12_bytecode_instruction_stream_decodes_simple_and_wide(self):
        seq = r450.decode_instructions(
            b"\x12\x01\xb6\x00\x02\xc4\x15\x00\xff\xb1")
        self.assertEqual([(op, operand) for _, op, operand in seq],
                         [(0x12, 1), (0xb6, 2), (0xc4, None), (0xb1, None)])

    def test_13_truncated_or_reserved_instruction_fails_closed(self):
        for code in (b"\x12", b"\xb6\x01", b"\xc4",
                     b"\xc4\x12\x00\x01", b"\xca",
                     b"\xaa\x00\x00"):
            with self.subTest(code=code):
                with self.assertRaises(r450.Refused):
                    r450.decode_instructions(code)

    def test_14_tableswitch_and_lookupswitch_boundaries(self):
        table = (b"\xaa" + b"\x00"*3 + b"\x00"*4 +
                 (0).to_bytes(4, "big", signed=True) +
                 (0).to_bytes(4, "big", signed=True) + b"\x00"*4)
        lookup = (b"\xab" + b"\x00"*3 + b"\x00"*4 +
                  (1).to_bytes(4, "big") + b"\x00"*8)
        self.assertEqual(len(r450.decode_instructions(table)), 1)
        self.assertEqual(len(r450.decode_instructions(lookup)), 1)

    def test_15_reject_invalid_or_truncated_classfile(self):
        for binary in (b"", self.store_class.read_bytes()[:-1],
                       self.store_class.read_bytes()+b"tail"):
            with self.subTest(binary_len=len(binary)):
                with self.assertRaises(r450.Refused):
                    r450.class_evidence(binary)

    def test_16_original_and_reconstructed_aggregate_counts(self):
        report, detail = r450.inspect(self.original_jar)
        self.assertEqual(report["status"],
                         "R450_GENERIC_SIGNATURE_RESOURCE_CALLSITE_UNAPPROVED")
        self.assertEqual(report["parsed_reconstructed_classfiles"], 2)
        self.assertEqual(report["reconstructed_java_sources"], 2)
        self.assertEqual(report["reconstructed_classfiles"], 2)
        self.assertEqual(report["unique_resource_paths_with_adjacent_loader_instructions"], 1)
        self.assertEqual(report["adjacent_resource_loader_instruction_sites"], 1)
        self.assertEqual(report["adjacent_loader_resource_paths_present_in_original_v309"], 1)
        self.assertEqual(report["incremental_unresolved_generic_targets_in_original_v309"], 1)
        self.assertFalse(report["runtime_resource_load_proven"])
        self.assertFalse(report["release_authorized"])
        self.assertEqual(detail["schema"], r450.SCHEMA)

    def test_17_private_names_not_printed_without_explicit_optin(self):
        result = r450.run(self.original_jar)
        self.assertFalse(result["private_worklist_saved"])
        self.assertEqual(self.private_outputs(), [])
        text = json.dumps(result)
        for name in ("rs/SigOnly.class", "rs/SigOriginal.class",
                     "images/logo.png", "java/lang/Class", str(self.temp)):
            self.assertNotIn(name, text)

    def test_18_private_report_contains_only_names_not_code(self):
        result = r450.run(self.original_jar, save=True)
        self.assertTrue(result["private_worklist_saved"])
        self.assertEqual(len(self.private_outputs()), 1)
        raw = (self.private_outputs()[0] / r450.REPORT_NAME).read_bytes()
        details = json.loads(raw)
        self.assertEqual(details["schema"], r450.SCHEMA)
        sites = details["details"]["adjacent_string_to_resource_loader_candidates"]
        self.assertEqual(sites[0]["resource_path"], "images/logo.png")
        self.assertFalse(sites[0]["resource_load_executed"])
        self.assertFalse(details["release_authorized"])
        self.assertNotIn(b"\xca\xfe\xba\xbe", raw)

    def test_19_private_report_never_overwrites_existing_report(self):
        first = r450.run(self.original_jar, save=True)
        path = self.private_outputs()[0] / r450.REPORT_NAME
        old = path.read_bytes()
        second = r450.run(self.original_jar, save=True)
        self.assertEqual(len(self.private_outputs()), 2)
        self.assertNotEqual(first["private_quarantine_directory_name"],
                            second["private_quarantine_directory_name"])
        self.assertEqual(path.read_bytes(), old)

    def test_20_wrong_original_sha_fails_closed(self):
        self.original_jar.write_bytes(b"not the pinned original")
        with self.assertRaises(r450.r447.Refused):
            r450.inspect(self.original_jar)

    def test_21_changed_compiled_class_sha_fails_closed(self):
        observed, _ = r450.r446.observe()
        bridge = self.compiled / "rs/Bridge.class"
        bridge.write_bytes(fixture.r448_test_fixture.fake_java11_class(
            "rs/Bridge", ("rs/changed",)))
        with self.assertRaisesRegex(
                r450.Refused, "R450_R421_COMPILED_MEMBER_CHANGED"):
            r450.observed_evidence(observed)

    def test_22_low_private_report_cap_refuses_before_write(self):
        with patch.object(r450, "MAX_REPORT_BYTES", 150):
            with self.assertRaisesRegex(r450.Refused,
                                        "R450_PRIVATE_REPORT_TOO_LARGE"):
                r450.run(self.original_jar, save=True)
        self.assertEqual(self.private_outputs(), [])

    def test_23_mutation_between_observations_no_private_output(self):
        original = r450.inspect
        calls = [0]
        def change(*args, **kwargs):
            result = original(*args, **kwargs)
            calls[0] += 1
            if calls[0] == 1:
                self.original_jar.write_bytes(b"replaced between scans")
            return result
        with patch.object(r450, "inspect", side_effect=change):
            with self.assertRaises(r450.r447.Refused):
                r450.run(self.original_jar, save=True)
        self.assertEqual(self.private_outputs(), [])

    def test_24_class_graph_mismatch_rejected(self):
        with self.assertRaisesRegex(
                r450.Refused, "R450_CLASS_GRAPH_KEYS_MISMATCH"):
            r450.aggregate({"rs/A.class": set()},
                           {"rs/B.class": set()},
                           {"rs/A.class": set()},
                           {"rs/A.class": []}, set(), set(), set(), set())

    def test_25_valid_empty_resource_graph_not_claimed_as_runtime(self):
        report, worklist = r450.aggregate(
            {"rs/A.class": set()}, {"rs/A.class": {"rs/SigOnly.class"}},
            {"rs/A.class": set()}, {"rs/A.class": []},
            {"rs/SigOnly.class"}, set(), set(), set())
        self.assertEqual(report["incremental_unresolved_generic_class_targets"], 1)
        self.assertEqual(report["adjacent_resource_loader_instruction_sites"], 0)
        self.assertFalse(report["runtime_resource_load_proven"])
        self.assertEqual(
            worklist["incremental_unresolved_generic_targets"][0]["class_name"],
            "rs/SigOnly.class")

    def test_26_default_cli_no_real_owner_inputs_exits_without_paths(self):
        missing = self.temp / "never-existed-original.jar"
        run = subprocess.run([
            sys.executable, "-B", str(CLI),
            "--original-v309-jar", str(missing)
        ], text=True, capture_output=True, timeout=15, check=False)
        self.assertEqual(run.returncode, 2)
        result = json.loads(run.stdout)
        self.assertEqual(result["status"], "R450_GENERIC_RESOURCE_AUDIT_REFUSED")
        self.assertFalse(result["release_authorized"])
        self.assertNotIn(str(missing), run.stdout)

    def test_27_owner_private_output_never_grants_release(self):
        summary, private = r450.inspect(self.original_jar)
        for key in ("release_authorized", "merge_authorized",
                    "source_compiled_in_this_audit", "game_client_started",
                    "player_history_accessed",
                    "independently_approved_R421_manifest_present"):
            self.assertFalse(summary[key])
        self.assertFalse(private["historical_R421_manifest_approved"])


if __name__ == "__main__":
    unittest.main()
