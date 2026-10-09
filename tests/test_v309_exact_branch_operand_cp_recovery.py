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
    _instruction_semantics,
    _method_semantics,
    compare_cp_method_profiles,
)


def _fixture(owner: str, branch_opcode: str = "0xc6", target: int = 8):
    # LDC; conditional jump; CP invoke; return. JVM offsets: 0,2,5,8.
    rows = [
        {"opcode": "0x12", "mnemonic": "ldc", "offset": 0, "length": 2,
         "constant_pool_tag": 8, "constant": "same-cp-string"},
        {"opcode": branch_opcode, "mnemonic": "opcode_" + branch_opcode[2:],
         "offset": 2, "length": 3, "branch_target_offset": target},
        {"opcode": "0xb8", "mnemonic": "invokestatic", "offset": 5, "length": 3,
         "member_constant_pool_tag": 10, "owner": owner, "name": "helper",
         "descriptor": "()V"},
        {"opcode": "0xb1", "mnemonic": "return", "offset": 8, "length": 1},
    ]
    return {"internal_name": owner, "bootstrap_methods": [],
            "methods": [{"name": "ordinary", "access": 1,
                         "descriptor": "()V", "code_length": 9,
                         "instructions": rows, "exception_handlers": []}]}


class ExactJvmBranchMethodTests(unittest.TestCase):
    def test_conditional_ifnull_branch_with_cp_refs_is_not_discarded(self):
        old = _fixture("p/Old")
        new = _fixture("p/New")
        result = compare_cp_method_profiles(
            old, new, old_owner="p/Old", new_owner="p/New")
        self.assertEqual(result["old_eligible"], 1)
        self.assertEqual(result["new_eligible"], 1)
        self.assertEqual(result["unique_cp_semantic_method_matches"], 1)
        self.assertEqual(result["accepted_class_identifications"], 0)
        self.assertEqual(result["accepted_member_identifications"], 0)

    def test_branch_opcodes_and_destinations_are_exact_fingerprint_parts(self):
        baseline = _fixture("p/Old")
        first, cp_sites = _method_semantics(
            baseline["methods"][0], [], old_owner="p/Old", new_owner="SELF")
        self.assertEqual(cp_sites, 2)
        for opcode, target in (("0xc7", 8), ("0xc6", 5), ("0x99", 8)):
            other = _fixture("p/Old", branch_opcode=opcode, target=target)
            with self.subTest(opcode=opcode, target=target):
                second, cp_count = _method_semantics(
                    other["methods"][0], [], old_owner="p/Old", new_owner="SELF")
                self.assertEqual(cp_count, 2)
                self.assertNotEqual(first, second)

    def test_branch_to_middle_or_end_of_code_is_rejected(self):
        for target in (6, 9, -1):
            with self.subTest(target=target):
                m = _fixture("p/Old", target=target)["methods"][0]
                with self.assertRaises(V309CpMethodWitnessError):
                    _method_semantics(m, [], old_owner="p/Old", new_owner="SELF")

    def test_bad_branch_width_missing_target_and_unknown_multibyte_refused(self):
        good = _fixture("p/Old")["methods"][0]["instructions"][1]
        invalid = [
            dict(good, length=2),
            dict(good, branch_target_offset=2 + 32768),
            dict(good, branch_target_offset=2 - 32769),
            {k: v for k, v in good.items() if k != "branch_target_offset"},
            dict(good, opcode="0xfa", mnemonic="opcode_fa"),
            dict(good, opcode="0xa8", mnemonic="jsr"),
        ]
        for row in invalid:
            with self.subTest(row=row):
                with self.assertRaises(V309CpMethodWitnessError):
                    _instruction_semantics(row, [], old_owner="p/Old", new_owner="SELF")

    def test_goto_w_exact_32bit_target_is_supported_and_checked(self):
        instructions = [
            {"opcode": "0xc8", "mnemonic": "opcode_c8", "length": 5,
             "offset": 0, "branch_target_offset": 5},
            {"opcode": "0xb1", "mnemonic": "return", "length": 1, "offset": 5},
        ]
        method = {"name": "go", "access": 1, "descriptor": "()V",
                  "code_length": 6, "instructions": instructions,
                  "exception_handlers": []}
        sig, cp_sites = _method_semantics(method, [], old_owner="p/Old",
                                          new_owner="SELF")
        self.assertEqual(cp_sites, 0)
        self.assertEqual(len(sig[3]), 2)
        modified = copy.deepcopy(method)
        modified["instructions"][0]["branch_target_offset"] = 4
        with self.assertRaises(V309CpMethodWitnessError):
            _method_semantics(modified, [], old_owner="p/Old", new_owner="SELF")
        modified["instructions"][0]["branch_target_offset"] = 1 << 31
        with self.assertRaises(V309CpMethodWitnessError):
            _method_semantics(modified, [], old_owner="p/Old", new_owner="SELF")


@unittest.skipUnless(shutil.which("javac"), "javac required for JVM branch parity")
class RealJavaBranchTests(unittest.TestCase):
    def test_real_javac_conditional_branches_with_cp_referents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            java = root / "BranchWitness.java"
            java.write_text(
                "public final class BranchWitness {\n"
                " public static String object(Object o) {\n"
                "  if (o == null) return String.valueOf(o);\n"
                "  return o.toString();\n"
                " }\n"
                " public static int number(int n) {\n"
                "  if (n != 0) return Integer.valueOf(n).intValue();\n"
                "  return Integer.valueOf(4).intValue();\n"
                " }\n"
                "}\n",
                encoding="utf-8",
            )
            compile_result = subprocess.run(
                ["javac", "--release", "11", "-proc:none", "-d", str(root),
                 str(java)], capture_output=True, text=True)
            self.assertEqual(compile_result.returncode, 0,
                             compile_result.stderr)
            profile = profile_class_field_accesses(
                (root / "BranchWitness.class").read_bytes())
            self.assertEqual(profile["internal_name"], "BranchWitness")
            methods = {m["name"]: m for m in profile["methods"]}
            for name in ("object", "number"):
                with self.subTest(name=name):
                    method = methods[name]
                    self.assertTrue(any(
                        i["opcode"] in {"0x99", "0x9a", "0xc6", "0xc7"}
                        for i in method["instructions"]))
                    signature, count = _method_semantics(
                        method, profile["bootstrap_methods"],
                        old_owner="BranchWitness", new_owner="SELF",
                    )
                    self.assertGreaterEqual(count, 1)
                    self.assertEqual(len(signature[3]),
                                     len(method["instructions"]))


if __name__ == "__main__":
    unittest.main()
