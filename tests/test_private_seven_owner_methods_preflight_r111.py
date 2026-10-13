"""R111: seven original-method JVM shapes and explicit unrecovered stubs."""
from __future__ import annotations

from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

import spk_recovery.private_seven_owner_methods_preflight_r111 as gate


class SevenOriginalOwnerMethodsSourceTests(TestCase):
    def setUp(self):
        self.owner = "p/Owner"
        self.original_nested = "p/Owner$Owner"
        self.source_nested = "p/Owner$Surrogate"
        self.bootstrap = [{
            "index": 0,
            "bootstrap_method": {
                "reference_kind": 6,
                "target_kind": "method",
                "owner": "java/lang/invoke/LambdaMetafactory",
                "name": "metafactory",
                "descriptor": "example",
            },
            "arguments": [
                {"kind": "method_type", "descriptor": "()V"},
                {"kind": "method_handle", "reference_kind": 6,
                 "owner": "p/Owner", "name": "g",
                 "descriptor": "()V"},
                {"kind": "method_type", "descriptor": "()V"},
            ],
        }]

        def method(name, desc, count, *, access=9, callback=False,
                   boolean=False, bool_branch=False):
            ops = ["0x03"] * count
            if callback:
                ops = ["0x12", "0xba", "0xb8", "0xb1"]
            elif bool_branch:
                ops[1], ops[11] = "0x99", "0xa7"
            elif count == 3:
                ops = ["0x2a", "0xb7", "0xb1"]
            elif count == 2 and boolean:
                ops = ["0x03", "0xac"]
            elif count > 2:
                ops[-1] = "0xb1"
            rows = []
            for i, op in enumerate(ops):
                row = {"opcode": op, "offset": i * 3, "length": 3}
                if op in ("0x99", "0xa7"):
                    row["branch_target_offset"] = (
                        (18 if op == "0x99" else 19) * 3)
                if op == "0xb7":
                    row.update({"owner": "java/lang/Object",
                                "name": "<init>", "descriptor": "()V"})
                if op == "0x12":
                    row.update({"constant_pool_tag": 8,
                                "constant": "SaveSettings"})
                if op == "0xba":
                    row.update({"name": "invoke",
                                "descriptor": "()Lp/Callback;",
                                "bootstrap_method_attr_index": 0})
                if op == "0xb8":
                    row.update({"owner": "p/Callbacks", "name": "add",
                                "descriptor": "(Ljava/lang/String;Lp/Callback;)V"})
                rows.append(row)
            return {"name": name, "descriptor": desc,
                    "access": access, "signature": None,
                    "max_stack": 1, "max_locals": 0,
                    "exception_handlers": [], "instructions": rows}

        self.small = [
            method("<init>", "()V", 3, access=1),
            method("a", "()Z", 2, boolean=True),
            method("b", "()Z", 2, boolean=True),
            method("c", "()Z", 2, boolean=True),
            method("a", "(Z)V", 20, bool_branch=True),
            method("d", "()V", 4, callback=True),
            method("e", "()V", 41),
        ]
        self.large364 = method("g", "()V", 364, access=10)
        self.large697 = method("f", "()V", 697)
        self.init = method("<clinit>", "()V", 213, access=8)
        self.original = {
            "internal_name": self.owner,
            "methods": deepcopy(self.small + [
                self.large364, self.large697, self.init]),
            "bootstrap_methods": deepcopy(self.bootstrap),
        }
        placeholder = method("g", "()V", 1, access=10)
        placeholder["instructions"][0]["opcode"] = "0xb1"
        t = "(L" + self.source_nested + ";)Ljava/lang/String;"
        source_helper_a = method("privateAccess1", t, 3)
        source_helper_b = method("privateAccess2", t, 3)
        self.candidate = {
            "internal_name": self.owner,
            "methods": deepcopy(self.small + [
                placeholder, source_helper_a, source_helper_b, self.init]),
            "bootstrap_methods": deepcopy(self.bootstrap),
        }
        self.partial = {
            "original_initializer_writes_in_original_order_compared": 93,
            "original_candidate_jvm_instructions_compared": 213,
            "strict_R58_original_all_operands_certified": False,
        }

    def proof(self, *, original=None, candidate=None, preflight=None):
        with patch.object(
            gate, "compare_original_93write_source_preflight",
            return_value=preflight if preflight is not None else self.partial,
        ) as check:
            result = gate.prove_original_seven_small_methods(
                original or self.original, candidate or self.candidate,
                source_nested_type=self.source_nested,
                original_nested_type=self.original_nested)
        check.assert_called_once()
        return result

    def test_exact_seven_original_method_bodies_and_callback_proof(self):
        r = self.proof()
        self.assertEqual(r["original_small_owner_methods_opcode_verified"], 7)
        self.assertEqual(r["original_small_owner_method_instructions_verified"], 74)
        self.assertEqual(r["original_small_owner_method_opcounts"],
                         [2, 2, 2, 3, 4, 20, 41])
        self.assertEqual(r["original_callback_lambda_bootstrap_semantics_compared"], 1)
        self.assertTrue(r["provisional_original_364_instruction_method_body_is_stub"])
        self.assertTrue(r["provisional_original_697_instruction_method_is_absent"])
        self.assertEqual(r["source_only_provisional_outer_helper_methods"], 2)
        self.assertFalse(r["R94_all_nine_owner_methods_accepted"])

    def test_opcode_drift_in_callback_vetoes(self):
        wrong = deepcopy(self.candidate)
        method = next(x for x in wrong["methods"]
                      if x["name"] == "d")
        method["instructions"][1]["opcode"] = "0xb9"
        with self.assertRaisesRegex(
            gate.SevenOwnerMethodsSourceError,
            "SMALL_ORIGINAL_OWNER_OPCODE_SEQUENCE_DIFFERENT",
        ):
            self.proof(candidate=wrong)

    def test_original_method_set_incomplete_vetoes(self):
        wrong = deepcopy(self.original)
        wrong["methods"] = [m for m in wrong["methods"]
                            if m["name"] != "f"]
        with self.assertRaisesRegex(
            gate.SevenOwnerMethodsSourceError,
            "ORIGINAL_TEN_METHOD_V309_SIGNATURE_SHAPES_CHANGED",
        ):
            self.proof(original=wrong)

    def test_missing_one_small_original_method_vetoes(self):
        wrong = deepcopy(self.candidate)
        wrong["methods"] = [x for x in wrong["methods"]
                            if not (x["name"] == "c"
                                    and x["descriptor"] == "()Z")]
        with self.assertRaisesRegex(
            gate.SevenOwnerMethodsSourceError,
            "SEVEN_ORIGINAL_ORDINARY_OWNER_METHODS_NOT_PRESENT",
        ):
            self.proof(candidate=wrong)

    def test_callback_original_method_handle_change_rejected(self):
        wrong = deepcopy(self.candidate)
        wrong["bootstrap_methods"][0]["arguments"][1]["name"] = "unrelated"
        with self.assertRaisesRegex(
            gate.SevenOwnerMethodsSourceError,
            "ORIGINAL_CALLBACK_LAMBDA_BOOTSTRAP_OR_TARGET_NOT_EXACT",
        ):
            self.proof(candidate=wrong)

    def test_364_original_method_must_be_explicit_nonoriginal_placeholder(self):
        wrong = deepcopy(self.candidate)
        method = next(x for x in wrong["methods"] if x["name"] == "g")
        method["instructions"][0]["opcode"] = "0x03"
        with self.assertRaisesRegex(
            gate.SevenOwnerMethodsSourceError,
            "ORIGINAL_364_METHOD_PLACEHOLDER_OR_MISSING_697_NOT_EXACT",
        ):
            self.proof(candidate=wrong)

    def test_provisional_outer_helper_count_must_be_two(self):
        wrong = deepcopy(self.candidate)
        wrong["methods"] = [m for m in wrong["methods"]
                            if m["name"] != "privateAccess2"]
        with self.assertRaisesRegex(
            gate.SevenOwnerMethodsSourceError,
            "EXACT_TWO_SOURCE_ONLY_PROVISIONAL_PRIVATE_ACCESS_HELPERS_REQUIRED",
        ):
            self.proof(candidate=wrong)

    def test_changed_external_method_call_target_vetoes(self):
        wrong = deepcopy(self.candidate)
        method = next(x for x in wrong["methods"] if x["name"] == "d")
        method["instructions"][2]["name"] = "registerDifferent"
        with self.assertRaisesRegex(
            gate.SevenOwnerMethodsSourceError,
            "SMALL_OWNER_FIELD_OR_METHOD_REFERENCE_DIFFERENT",
        ):
            self.proof(candidate=wrong)

    def test_requires_r110_93_write_source_preflight(self):
        with self.assertRaisesRegex(
            gate.SevenOwnerMethodsSourceError,
            "R110_COMPLETE_ORIGINAL_INITIALIZER_SOURCE_PREFLIGHT_REQUIRED",
        ):
            self.proof(preflight={
                **self.partial,
                "original_initializer_writes_in_original_order_compared": 92,
            })
