"""R110: fail-closed original 213-op/93-write pre-R105 source preflight."""
from __future__ import annotations

from copy import deepcopy
import unittest

from spk_recovery.private_original_93write_initializer_source_preflight_r110 import (
    OriginalInitializerSourcePreflightError,
    compare_original_93write_source_preflight,
)


class CompleteInitializerPreimageShapeTests(unittest.TestCase):
    ORIG = "p/Owner$Owner"
    SOURCE = "p/Owner$Surrogate"

    def setUp(self):
        own = "p/Owner"
        fields = []
        for i in range(85):
            fields.append({"name": f"m{i}", "descriptor": "Z",
                           "access": 9, "signature": None,
                           "constant_value": None})
        for i in range(8):
            fields.append({"name": f"f{i}",
                           "descriptor": "L" + self.ORIG + ";"
                           if i == 0 else "Ljava/lang/String;",
                           "access": 25, "signature": None,
                           "constant_value": None})
        for i in range(33):
            fields.append({"name": f"c{i}", "descriptor": "Z",
                           "access": 25, "signature": None,
                           "constant_value": 1 if i % 2 else 0})
        self.assertEqual(len(fields), 126)
        self.fields = fields
        rows = []
        for i in range(2):
            rows.append({"opcode": "0x12", "constant_pool_tag": 3,
                         "constant": 1000 + i})
        for i in range(3):
            rows.append({"opcode": "0xba",
                         "name": "makeConcatWithConstants",
                         "descriptor": "(Ljava/lang/String;)Ljava/lang/String;",
                         "bootstrap_method_attr_index": 0})
        for i in range(14):
            rows.append({"opcode": "0xb2"})
        for i in range(4):
            rows.append({"opcode": "0xb8"})
        for op in ("0xa6", "0xa6", "0xa6", "0x9a",
                   "0xa7", "0xa7", "0xa7", "0xa7"):
            rows.append({"opcode": op})
        while len(rows) < 119:
            rows.append({"opcode": "0x03"})
        for i in range(85):
            rows.append({"opcode": "0xb3", "owner": own,
                         "name": f"m{i}", "descriptor": "Z"})
        for i in range(8):
            rows.append({"opcode": "0xb3", "owner": own,
                         "name": f"f{i}", "descriptor":
                         "L" + self.ORIG + ";" if i == 0 else
                         "Ljava/lang/String;"})
        rows.append({"opcode": "0xb1"})
        self.assertEqual(len(rows), 213)
        for i, row in enumerate(rows):
            row["offset"], row["length"] = i * 3, 3
            if row["opcode"] in ("0xa6", "0x9a", "0xa7"):
                row["branch_target_offset"] = rows[-1].get(
                    "offset", 212 * 3)
        self.bootstrap = [{
            "index": 0,
            "bootstrap_method": {
                "reference_kind": 6, "target_kind": "method",
                "owner": "java/lang/invoke/StringConcatFactory",
                "name": "makeConcatWithConstants",
                "descriptor": "(LOOKUP)CALLSITE",
            },
            "arguments": [{"kind": "string", "value": "p\u0001s"}],
        }]
        self.original = {
            "internal_name": own, "classfile_major": 53,
            "super_name": "java/lang/Object", "class_access": 33,
            "fields": fields,
            "methods": [{
                "name": "<clinit>", "descriptor": "()V", "access": 8,
                "max_stack": 2, "max_locals": 0,
                "exception_handlers": [], "instructions": rows,
            }],
            "bootstrap_methods": self.bootstrap,
        }
        self.candidate = deepcopy(self.original)
        self.candidate["fields"][85]["descriptor"] = (
            "L" + self.SOURCE + ";")
        self.candidate["methods"][0]["instructions"][211]["descriptor"] = (
            "Ljava/lang/String;")  # last final f7 unchanged
        self.candidate["methods"][0]["instructions"][204]["descriptor"] = (
            "L" + self.SOURCE + ";")  # first final f0
        for i in range(2):
            self.candidate["methods"][0]["instructions"][i]["opcode"] = "0x13"

    def proof(self, original=None, candidate=None):
        return compare_original_93write_source_preflight(
            original or self.original, candidate or self.candidate,
            candidate_nested_type=self.SOURCE,
            original_nested_type=self.ORIG)

    def test_126_fields_93_ordered_writes_213_ops_two_ldc_widths(self):
        p = self.proof()
        self.assertEqual(p["original_owner_fields_compared"], 126)
        self.assertEqual(p["original_compile_time_field_values_compared"], 33)
        self.assertEqual(p["original_initializer_writes_in_original_order_compared"], 93)
        self.assertEqual(p["original_mutable_field_write_targets_compared"], 85)
        self.assertEqual(p["original_nonconstant_final_write_targets_compared"], 8)
        self.assertEqual(p["original_candidate_jvm_instructions_compared"], 213)
        self.assertEqual(p["original_source_ldc_to_ldc_w_width_differences"], 2)
        self.assertEqual(p["original_StringConcatFactory_recipes_compared"], 3)
        self.assertFalse(p["strict_R58_original_all_operands_certified"])
        self.assertFalse(p["R107_complete_original_owner_accepted"])

    def test_changed_final_field_target_rejected(self):
        candidate = deepcopy(self.candidate)
        candidate["methods"][0]["instructions"][211]["name"] = "f6"
        with self.assertRaisesRegex(
            OriginalInitializerSourcePreflightError,
            "SAME_ORIGINAL_FIELD_WRITTEN_MORE_THAN_ONCE"):
            self.proof(candidate=candidate)

    def test_missing_one_original_field_write_rejected(self):
        candidate = deepcopy(self.candidate)
        candidate["methods"][0]["instructions"][119]["opcode"] = "0x00"
        with self.assertRaisesRegex(
            OriginalInitializerSourcePreflightError,
            "CLINIT_OPCODE_NOT_A_NARROW_TO_WIDE_LDC"):
            self.proof(candidate=candidate)

    def test_unexpected_opcode_mutation_not_accepted_as_ldc_width(self):
        candidate = deepcopy(self.candidate)
        candidate["methods"][0]["instructions"][2]["opcode"] = "0xbb"
        with self.assertRaisesRegex(
            OriginalInitializerSourcePreflightError,
            "CLINIT_OPCODE_NOT_A_NARROW_TO_WIDE_LDC"):
            self.proof(candidate=candidate)

    def test_initializer_branch_target_drift_rejected(self):
        candidate = deepcopy(self.candidate)
        row = next(r for r in candidate["methods"][0]["instructions"]
                   if r["opcode"] == "0xa6")
        row["branch_target_offset"] = 211 * 3
        with self.assertRaisesRegex(
            OriginalInitializerSourcePreflightError,
            "CLINIT_BRANCH_TARGET_ORDINALS_NOT_EXACT"):
            self.proof(candidate=candidate)

    def test_constantvalue_drift_rejected(self):
        candidate = deepcopy(self.candidate)
        candidate["fields"][-1]["constant_value"] = 7
        with self.assertRaisesRegex(
            OriginalInitializerSourcePreflightError,
            "ORIGINAL_126_FIELD_DECLARATIONS_DIFFER"):
            self.proof(candidate=candidate)

    def test_original_bootstrap_recipe_drift_rejected(self):
        candidate = deepcopy(self.candidate)
        candidate["bootstrap_methods"][0]["arguments"][0]["value"] = "different\u0001recipe"
        with self.assertRaisesRegex(
            OriginalInitializerSourcePreflightError,
            "ORIGINAL_CLINIT_THREE_BOOTSTRAP_RECIPES_NOT_EQUAL"):
            self.proof(candidate=candidate)

    def test_source_nested_field_identity_not_arbitrary(self):
        candidate = deepcopy(self.candidate)
        candidate["fields"][85]["descriptor"] = "Lp/Owner$Unexpected;"
        with self.assertRaisesRegex(
            OriginalInitializerSourcePreflightError,
            "ORIGINAL_126_FIELD_DECLARATIONS_DIFFER"):
            self.proof(candidate=candidate)

    def test_java_stack_local_shape_is_original(self):
        candidate = deepcopy(self.candidate)
        candidate["methods"][0]["max_stack"] = 3
        with self.assertRaisesRegex(
            OriginalInitializerSourcePreflightError,
            "ORIGINAL_CLINIT_STACK_LOCAL_OR_HANDLERS_CHANGED"):
            self.proof(candidate=candidate)
