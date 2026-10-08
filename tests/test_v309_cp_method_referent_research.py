from __future__ import annotations

import copy
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.v309_cp_method_referent_research import (
    V309CpMethodWitnessError,
    _method_semantics,
    compare_cp_method_profiles,
)


def _instruction(opcode, length, offset, **fields):
    return {"opcode": opcode, "mnemonic": "synthetic", "length": length,
            "offset": offset, **fields}


def _test_method(*, constant="private-value", cp_slot=12, owner="p/Old",
                 name="run", extra=None):
    instructions = [
        _instruction("0x12", 2, 0, constant=constant, constant_pool_index=cp_slot),
        _instruction("0xb8", 3, 2, owner=owner, name="call",
                     descriptor="(Ljava/lang/String;)V"),
        _instruction("0xb1", 1, 5),
    ]
    if extra is not None:
        instructions = extra
    return {
        "name": name, "access": 1, "descriptor": "()V",
        "code_length": sum(x["length"] for x in instructions),
        "instructions": instructions, "exception_handlers": [],
    }


def _profile(owner, *, method=None, methods=None, bootstrap=None):
    return {"internal_name": owner, "methods": (
        methods if methods is not None else [method or _test_method(owner=owner)]
    ), "bootstrap_methods": [] if bootstrap is None else bootstrap}


class CpMethodReferentTests(unittest.TestCase):
    def compare(self, old=None, new=None):
        return compare_cp_method_profiles(
            _profile("p/Old") if old is None else old,
            _profile("p/New", method=_test_method(owner="p/New", cp_slot=99))
            if new is None else new,
            old_owner="p/Old", new_owner="p/New",
        )

    def test_changed_constant_pool_slots_same_meaning_pass_research_only(self):
        result = self.compare()
        self.assertEqual(result["unique_cp_semantic_method_matches"], 1)
        self.assertEqual(result["ambiguous_duplicate_semantic_shapes"], 0)
        self.assertEqual(result["accepted_class_identifications"], 0)
        self.assertEqual(result["accepted_member_identifications"], 0)

    def test_equal_cp_slot_changed_literal_must_not_match(self):
        result = self.compare(new=_profile(
            "p/New", method=_test_method(owner="p/New", cp_slot=12,
                                         constant="different-secret"),
        ))
        self.assertEqual(result["unique_cp_semantic_method_matches"], 0)

    def test_changed_member_target_meaning_must_not_match(self):
        new = _profile("p/New", method=_test_method(owner="p/Other", cp_slot=12))
        self.assertEqual(self.compare(new=new)["unique_cp_semantic_method_matches"], 0)

    def test_duplicate_fingerprint_not_promoted_to_unique(self):
        old = _profile("p/Old", methods=[
            _test_method(name="alpha"), _test_method(name="beta")
        ])
        result = self.compare(old=old)
        self.assertEqual(result["unique_cp_semantic_method_matches"], 0)
        self.assertEqual(result["ambiguous_duplicate_semantic_shapes"], 1)

    def test_source_profile_with_unsupported_method_handle_ldc_refused(self):
        bad = _profile("p/Old", method=_test_method(extra=[
            _instruction("0x12", 2, 0, constant_pool_index=17),  # unresolved handle
            _instruction("0xb8", 3, 2, owner="p/Old", name="call",
                         descriptor="()V"),
            _instruction("0xb1", 1, 5),
        ]))
        result = self.compare(old=bad)
        self.assertEqual(result["old_unsupported"], 1)
        self.assertEqual(result["unique_cp_semantic_method_matches"], 0)

    def test_switch_or_multiarray_unsupported_not_compared(self):
        for op in ("0xaa", "0xab", "0xc5"):
            bad = _profile("p/Old", method=_test_method(extra=[
                _instruction(op, 2, 0),
                _instruction("0xb8", 3, 2, owner="p/Old", name="call",
                             descriptor="()V"),
                _instruction("0xb1", 1, 5),
            ]))
            with self.subTest(op=op):
                self.assertEqual(self.compare(old=bad)["old_unsupported"], 1)

    def test_different_exception_handlers_are_not_equal(self):
        new = _profile("p/New", method=_test_method(owner="p/New", cp_slot=32))
        new["methods"][0]["exception_handlers"] = [
            {"start_pc": 0, "end_pc": 5, "handler_pc": 5,
             "catch_type": "java/lang/Exception"}
        ]
        self.assertEqual(self.compare(new=new)["unique_cp_semantic_method_matches"], 0)

    def test_missing_or_ambiguous_invokedynamic_bootstrap_refuses(self):
        m = _test_method(extra=[
            _instruction("0xba", 5, 0, bootstrap_method_attr_index=2,
                         name="run", descriptor="()Ljava/lang/Runnable;"),
            _instruction("0xb1", 1, 5),
        ])
        old = _profile("p/Old", method=m)
        self.assertEqual(self.compare(old=old)["old_unsupported"], 1)
        old["bootstrap_methods"] = [
            {"index": 2, "bootstrap_method": {
                "reference_kind": 6, "target_kind": "method",
                "owner": "java/lang/invoke/LambdaMetafactory",
                "name": "metafactory",
                "descriptor": "()V",
            }, "arguments": [{"kind": "constant_pool_entry", "tag": 17}]}
        ]
        self.assertEqual(self.compare(old=old)["old_unsupported"], 1)

    def test_bootstrap_cp_index_permutation_resolves_real_referents(self):
        def indy_profile(owner, index, method_name="helper"):
            handle = {"reference_kind": 6, "target_kind": "method",
                      "owner": owner, "name": method_name, "descriptor": "()V"}
            method = _test_method(extra=[
                _instruction("0xba", 5, 0, bootstrap_method_attr_index=index,
                             name="run", descriptor="()Ljava/lang/Runnable;"),
                _instruction("0xb1", 1, 5),
            ])
            bootstrap = [{
                "index": index,
                "bootstrap_method": {
                    "reference_kind": 6, "target_kind": "method",
                    "owner": "java/lang/invoke/LambdaMetafactory",
                    "name": "metafactory", "descriptor": "()V",
                    "reference_index": 44 + index,
                },
                "arguments": [{"kind": "method_handle",
                               "constant_pool_index": 26 + index,
                               "method_handle": handle}],
            }]
            return _profile(owner, method=method, bootstrap=bootstrap)
        old = indy_profile("p/Old", 0)
        new = indy_profile("p/New", 3)
        self.assertEqual(self.compare(old=old, new=new)["unique_cp_semantic_method_matches"], 1)
        new["bootstrap_methods"][0]["arguments"][0]["method_handle"]["name"] = "different"
        self.assertEqual(self.compare(old=old, new=new)["unique_cp_semantic_method_matches"], 0)

    def test_zero_cp_reference_methods_are_excluded(self):
        simple = _test_method(extra=[_instruction("0xb1", 1, 0)])
        result = self.compare(
            old=_profile("p/Old", method=simple),
            new=_profile("p/New", method=simple),
        )
        self.assertEqual(result["old_without_cp_references"], 1)
        self.assertEqual(result["unique_cp_semantic_method_matches"], 0)


@unittest.skipUnless(shutil.which("javac"), "javac required for actual constant-pool proof")
class RealJavaCpShiftTests(unittest.TestCase):
    def test_javac_cp_shift_keeps_exact_referent_semantics(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            fixtures = [
                ("old", "public class Worker {\n"
                        "  public static void extra(){System.out.println(\"unrelated\");}\n"
                        "  public static void run(){System.out.println(\"stable\");}\n"
                        "}\n"),
                ("new", "public class Worker {\n"
                        "  public static void run(){System.out.println(\"stable\");}\n"
                        "}\n"),
            ]
            profiles = []
            for name, source in fixtures:
                directory = root / name
                directory.mkdir()
                file = directory / "Worker.java"
                file.write_text(source, encoding="utf-8")
                run = subprocess.run(
                    ["javac", "--release", "11", "-proc:none", "-d",
                     str(directory), str(file)], capture_output=True, text=True,
                )
                self.assertEqual(run.returncode, 0, run.stderr)
                profiles.append(profile_class_field_accesses(
                    (directory / "Worker.class").read_bytes()
                ))
            first = next(m for m in profiles[0]["methods"] if m["name"] == "run")
            second = next(m for m in profiles[1]["methods"] if m["name"] == "run")
            first_cp = [x["constant_pool_index"] for x in first["instructions"]
                        if x["opcode"] == "0x12"]
            second_cp = [x["constant_pool_index"] for x in second["instructions"]
                         if x["opcode"] == "0x12"]
            self.assertEqual(len(first_cp), 1)
            self.assertEqual(len(second_cp), 1)
            self.assertNotEqual(first_cp, second_cp)
            a, refs_a = _method_semantics(
                first, profiles[0]["bootstrap_methods"],
                old_owner="Worker", new_owner="Worker",
            )
            b, refs_b = _method_semantics(
                second, profiles[1]["bootstrap_methods"],
                old_owner="Worker", new_owner="Worker",
            )
            self.assertEqual(a, b)
            self.assertGreaterEqual(refs_a, 2)
            self.assertEqual(refs_a, refs_b)


if __name__ == "__main__":
    unittest.main()
