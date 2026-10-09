from __future__ import annotations

import copy
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

from spk_recovery.bytecode_profile import (
    BytecodeProfileError, _decoded_instructions, _instruction_length,
    profile_class_field_accesses,
)
from spk_recovery.v309_cp_method_referent_research import (
    V309CpMethodWitnessError, _instruction_semantics, _method_semantics,
)


def opcode_method(profile, name):
    return next(m for m in profile["methods"] if m["name"] == name)


@unittest.skipUnless(shutil.which("javac"), "javac needed for real classfile operand parity")
class RealJavaSwitchArraySemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            return
        cls.tempdir = tempfile.TemporaryDirectory()
        root = Path(cls.tempdir.name)
        source = root / "JvmSwitchArrayFixture.java"
        source.write_text(
            "public final class JvmSwitchArrayFixture {\n"
            " public static int dense(int x) { switch (x) {\n"
            "  case 0: return 11; case 1: return 22;\n"
            "  case 2: return 33; default: return -1; } }\n"
            " public static int sparse(int x) { switch (x) {\n"
            "  case -17: return 11; case 60: return 22;\n"
            "  case 1001: return 33; default: return -1; } }\n"
            " public static int[] primitive(int n) { return new int[n]; }\n"
            " public static long[] primitiveOther(int n) { return new long[n]; }\n"
            " public static int[][] multi(int a,int b) { return new int[a][b]; }\n"
            "}\n", encoding="utf-8",
        )
        result = subprocess.run(
            ["javac", "--release", "11", "-proc:none", "-d", str(root), str(source)],
            text=True, capture_output=True,
        )
        if result.returncode:
            raise AssertionError("javac Java11 real operand fixture failed: " + result.stderr)
        cls.profile = profile_class_field_accesses(
            (root / "JvmSwitchArrayFixture.class").read_bytes()
        )

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "tempdir"):
            cls.tempdir.cleanup()

    def signature(self, method):
        return _method_semantics(
            method, self.profile["bootstrap_methods"],
            old_owner="JvmSwitchArrayFixture",
            new_owner="JvmSwitchArrayFixture",
        )

    def test_real_javac_decodes_both_switch_types_all_arms(self):
        dense = opcode_method(self.profile, "dense")
        sparse = opcode_method(self.profile, "sparse")
        tables = next(r for r in dense["instructions"] if r["opcode"] == "0xaa")
        lookup = next(r for r in sparse["instructions"] if r["opcode"] == "0xab")
        self.assertEqual((tables["switch_low"], tables["switch_high"]), (0, 2))
        self.assertEqual(len(tables["switch_targets"]), 3)
        self.assertEqual([k for k, _ in lookup["switch_pairs"]], [-17, 60, 1001])
        for method in (dense, sparse):
            sig, cp_sites = self.signature(method)
            self.assertGreater(len(sig[3]), 2)
            self.assertEqual(cp_sites, 0)  # CP-free switches never vote for identity.

    def test_real_javac_primitive_array_exact_atype(self):
        ints = opcode_method(self.profile, "primitive")
        longs = opcode_method(self.profile, "primitiveOther")
        irow = next(r for r in ints["instructions"] if r["opcode"] == "0xbc")
        lrow = next(r for r in longs["instructions"] if r["opcode"] == "0xbc")
        self.assertEqual(irow["array_primitive_atype"], 10)
        self.assertEqual(lrow["array_primitive_atype"], 11)
        first, refs = self.signature(ints)
        self.assertEqual(refs, 0)
        changed = copy.deepcopy(ints)
        next(r for r in changed["instructions"] if r["opcode"] == "0xbc")[
            "array_primitive_atype"] = 11
        different, _ = self.signature(changed)
        self.assertNotEqual(first, different)

    def test_real_javac_multidimensional_array_cp_and_dimensions(self):
        original = opcode_method(self.profile, "multi")
        multi = next(r for r in original["instructions"] if r["opcode"] == "0xc5")
        self.assertEqual(multi["type"], "[[I")
        self.assertEqual(multi["array_dimensions"], 2)
        fingerprint, cp_sites = self.signature(original)
        self.assertEqual(cp_sites, 1)
        changed = copy.deepcopy(original)
        next(r for r in changed["instructions"] if r["opcode"] == "0xc5")[
            "array_dimensions"] = 1
        amended, _ = self.signature(changed)
        self.assertNotEqual(fingerprint, amended)
        next(r for r in changed["instructions"] if r["opcode"] == "0xc5")[
            "array_dimensions"] = 3
        with self.assertRaises(V309CpMethodWitnessError):
            self.signature(changed)

    def test_changed_switch_destination_changes_full_fingerprint(self):
        original = opcode_method(self.profile, "dense")
        before, _ = self.signature(original)
        altered = copy.deepcopy(original)
        table = next(r for r in altered["instructions"] if r["opcode"] == "0xaa")
        self.assertNotEqual(table["switch_targets"][0], table["switch_targets"][1])
        table["switch_targets"][0] = table["switch_targets"][1]
        after, _ = self.signature(altered)
        self.assertNotEqual(before, after)

    def test_switch_target_to_middle_of_instruction_is_rejected(self):
        altered = copy.deepcopy(opcode_method(self.profile, "sparse"))
        look = next(r for r in altered["instructions"] if r["opcode"] == "0xab")
        look["switch_pairs"][0] = (
            look["switch_pairs"][0][0], altered["code_length"],
        )
        with self.assertRaises(V309CpMethodWitnessError):
            self.signature(altered)


class SyntheticArraySwitchNegativeTests(unittest.TestCase):
    def test_newarray_rejects_invalid_primitive_atype(self):
        for atype in (0, 3, 12, 255):
            with self.subTest(atype=atype):
                with self.assertRaises(BytecodeProfileError):
                    _decoded_instructions(bytes((0xBC, atype, 0xB1)), [None])
        with self.assertRaises(V309CpMethodWitnessError):
            _instruction_semantics(
                {"opcode": "0xbc", "mnemonic": "newarray", "length": 2,
                 "array_primitive_atype": 12},
                [], old_owner="a/A", new_owner="b/B",
            )

    def test_tableswitch_reversed_bounds_and_truncated_arm_table_fail(self):
        invalid = b"\xaa\x00\x00\x00" + struct.pack(">iii", 0, 3, 2)
        with self.assertRaises(BytecodeProfileError):
            _instruction_length(invalid, 0)
        missing_arms = b"\xaa\x00\x00\x00" + struct.pack(">iii", 0, 0, 3)
        with self.assertRaises(BytecodeProfileError):
            _instruction_length(missing_arms, 0)

    def test_lookupswitch_negative_or_truncated_pairs_fail(self):
        negative = b"\xab\x00\x00\x00" + struct.pack(">ii", 0, -1)
        with self.assertRaises(BytecodeProfileError):
            _instruction_length(negative, 0)
        missing = b"\xab\x00\x00\x00" + struct.pack(">ii", 0, 2)
        with self.assertRaises(BytecodeProfileError):
            _instruction_length(missing, 0)

    def test_switch_padding_must_be_zero_and_matching_case_keys_sorted(self):
        nonzero = (
            b"\xaa\x01\x00\x00" + struct.pack(">iii", 0, 0, 0)
            + struct.pack(">i", 0) + b"\xb1"
        )
        with self.assertRaises(BytecodeProfileError):
            _decoded_instructions(nonzero, [None])
        duplicated = (
            b"\xab\x00\x00\x00" + struct.pack(">ii", 0, 2)
            + struct.pack(">ii", 1, 0)
            + struct.pack(">ii", 1, 0) + b"\xb1"
        )
        with self.assertRaises(BytecodeProfileError):
            _decoded_instructions(duplicated, [None])

    def test_multidimensional_array_rejects_nonarray_cp_owner_or_bad_rank(self):
        from spk_recovery.bytecode_profile import BytecodeProfileError
        # A resolved CONSTANT_Class reference is required by the decoder.
        cp = [None, (1, "java/lang/String"), (7, 1)]
        raw = b"\xc5\x00\x02\x01\xb1"
        with self.assertRaises(BytecodeProfileError):
            _decoded_instructions(raw, cp)
        for dims in (0, 3):
            cp2 = [None, (1, "[[I"), (7, 1)]
            with self.subTest(dimensions=dims), self.assertRaises(BytecodeProfileError):
                _decoded_instructions(b"\xc5\x00\x02" + bytes((dims,)) + b"\xb1", cp2)

    def test_legacy_jsr_is_not_equated_to_supported_branch_code(self):
        for opcode, length in (("0xa8", 3), ("0xa9", 2), ("0xc9", 5)):
            with self.subTest(opcode=opcode):
                with self.assertRaises(V309CpMethodWitnessError):
                    _instruction_semantics(
                        {"opcode": opcode, "length": length, "mnemonic": "legacy"},
                        [], old_owner="a/A", new_owner="b/B",
                    )


if __name__ == "__main__":
    unittest.main()
