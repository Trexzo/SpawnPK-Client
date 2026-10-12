"""R109: exact 93 store / 8 final / six RHS opcode templates, fail closed."""
from __future__ import annotations

from copy import deepcopy
import unittest

from spk_recovery.private_v309_eight_final_initializer_r109 import (
    OriginalEightFinalInitializerError,
    original_eight_final_write_proof,
)


class OriginalFinalAssignmentShapeTests(unittest.TestCase):
    def setUp(self):
        self.owner = "p/Owner"
        self.enum = "p/Owner$Choice"
        self.fields = []
        self.rows = []
        self.bootstrap = {
            "index": 0,
            "bootstrap_method": {
                "reference_kind": 6,
                "owner": "java/lang/invoke/StringConcatFactory",
                "name": "makeConcatWithConstants",
                "descriptor": "test",
            },
            "arguments": [{"kind": "string", "value": "prefix\x01suffix"}],
        }
        for i in range(85):
            name = "mutable" + str(i)
            self.fields.append({
                "name": name, "descriptor": "Z",
                "access": 9, "constant_value": None,
            })
        for i in range(33):
            self.fields.append({
                "name": "constant" + str(i), "descriptor": "Z",
                "access": 25, "constant_value": 0,
            })
        types = (
            "L" + self.enum + ";", "Ljava/lang/String;",
            "Ljava/lang/String;", "Ljava/lang/String;",
            "Ljava/lang/String;", "[I",
            "Ljava/lang/String;", "Ljava/lang/Integer;",
        )
        for i, typ in enumerate(types):
            self.fields.append({
                "name": "final" + str(i), "descriptor": typ,
                "access": 25, "constant_value": None,
            })

        def ins(op, **kwargs):
            r = {"opcode": op, "offset": len(self.rows),
                 "length": 1, **kwargs}
            self.rows.append(r)
            return r

        def store(i):
            f = self.fields[118 + i]
            return ins("0xb3", owner=self.owner, name=f["name"],
                       descriptor=f["descriptor"])

        def evalue():
            return ins("0xb2", owner=self.enum, name="ALPHA",
                       descriptor="L" + self.enum + ";")

        def concat(index=0):
            return ins("0xba", name="makeConcatWithConstants",
                       descriptor="(Ljava/lang/String;)Ljava/lang/String;",
                       bootstrap_method_attr_index=index)

        def ldc_string(value):
            return ins("0x12", constant_pool_tag=8, constant=value)

        for i in range(85):
            ins("0x03")
            ins("0xb3", owner=self.owner,
                name="mutable" + str(i), descriptor="Z")

        evalue()
        store(0)

        for i in (1, 2):
            evalue()
            evalue()
            branch = ins("0xa6")
            ldc_string("yes")
            go = ins("0xa7")
            alternative = ldc_string("no")
            join = concat()
            branch["branch_target_offset"] = alternative["offset"]
            go["branch_target_offset"] = join["offset"]
            store(i)

        for i in (3, 4):
            evalue()
            ins("0xb8", owner="p/Helper", name="stringFromEnum",
                descriptor="(L" + self.enum + ";)Ljava/lang/String;")
            store(i)

        ins("0x10", int_constant=33)
        ins("0xbc", array_primitive_atype=10)
        store(5)

        ins("0xb8", owner="p/Helper", name="header",
            descriptor="()Ljava/lang/String;")
        concat(1)
        store(6)

        ins("0x12", constant_pool_tag=3, constant=450)
        ins("0xb8", owner="java/lang/Integer", name="valueOf",
            descriptor="(I)Ljava/lang/Integer;")
        store(7)

        for _ in range(10):
            ins("0x00")

        self.assertEqual(len(self.rows), 213)
        self.profile = {
            "internal_name": self.owner, "classfile_major": 53,
            "fields": self.fields,
            "methods": [{
                "name": "<clinit>", "descriptor": "()V",
                "access": 8, "instructions": self.rows,
            }],
            "bootstrap_methods": [
                self.bootstrap,
                {
                    **self.bootstrap,
                    "index": 1,
                    "arguments": [{
                        "kind": "string", "value": "\x01_suffix",
                    }],
                },
            ],
        }

    def proof(self, profile=None):
        return original_eight_final_write_proof(
            profile if profile is not None else self.profile)

    def test_all_eight_private_rhs_classified_without_claiming_java_source(self):
        records, result = self.proof()
        self.assertEqual(len(records), 8)
        self.assertEqual(result["original_nonconstant_static_final_assignments_recovered"], 8)
        self.assertEqual(result["original_owner_static_field_writes"], 93)
        self.assertEqual(result["original_owner_clinit_instruction_count"], 213)
        self.assertEqual(result["original_simple_rhs_sites_without_indy"], 5)
        self.assertEqual(result["original_concat_rhs_sites_with_private_bootstrap"], 3)
        self.assertFalse(result["original_exact_java_source_of_eight_assignments_compiled"])
        self.assertFalse(result["R58_complete_clinit_parity_proven"])
        self.assertEqual(
            result["exact_original_initializer_opcode_and_operand_recipes"],
            {
                "direct_enum_constant": 1,
                "conditional_enum_comparison_concat": 2,
                "enum_to_string_static_helper": 2,
                "fixed_integer_array_allocation": 1,
                "static_string_helper_concat": 1,
                "integer_valueof_constant": 1,
            })
        for record in records:
            self.assertFalse(record["source_java_expression_compiled_and_proven"])

    def test_changed_conditional_branch_target_rejected(self):
        bad = deepcopy(self.profile)
        branch = next(r for r in bad["methods"][0]["instructions"]
                      if r["opcode"] == "0xa6")
        branch["branch_target_offset"] += 1
        with self.assertRaisesRegex(
            OriginalEightFinalInitializerError,
            "CONDITIONAL_STRING_CONCAT_BRANCH_OR_LITERALS_NOT_EXACT",
        ):
            self.proof(bad)

    def test_changed_indy_bootstrap_index_rejected(self):
        bad = deepcopy(self.profile)
        indy = next(r for r in bad["methods"][0]["instructions"]
                    if r["opcode"] == "0xba")
        indy["bootstrap_method_attr_index"] = 200
        with self.assertRaisesRegex(
            OriginalEightFinalInitializerError,
            "EXACT_ORIGINAL_INDY_BOOTSTRAP_NOT_UNIQUE",
        ):
            self.proof(bad)

    def test_arbitrary_bootstrap_must_not_be_accepted_as_string_concat(self):
        bad = deepcopy(self.profile)
        bad["bootstrap_methods"][0]["arguments"][0]["value"] = "missing-marker"
        with self.assertRaisesRegex(
            OriginalEightFinalInitializerError,
            "ORIGINAL_SINGLE_ARGUMENT_STRING_CONCAT_BOOTSTRAP_NOT_EXACT",
        ):
            self.proof(bad)

    def test_conditional_and_helper_indy_must_use_distinct_bootstraps(self):
        bad = deepcopy(self.profile)
        dyn = [r for r in bad["methods"][0]["instructions"]
               if r["opcode"] == "0xba"]
        dyn[-1]["bootstrap_method_attr_index"] = 0
        with self.assertRaisesRegex(
            OriginalEightFinalInitializerError,
            "TWO_CONDITIONAL_ONE_HELPER_CONCAT_BOOTSTRAP_IDS_NOT_EXACT",
        ):
            self.proof(bad)

    def test_boxed_integer_method_identity_must_not_be_guessed(self):
        bad = deepcopy(self.profile)
        method = next(
            row for row in bad["methods"][0]["instructions"]
            if row["opcode"] == "0xb8" and
            row.get("owner") == "java/lang/Integer")
        method["name"] = "parseInt"
        with self.assertRaisesRegex(
            OriginalEightFinalInitializerError,
            "ORIGINAL_BOXED_INTEGER_VALUEOF_RHS_NOT_EXACT",
        ):
            self.proof(bad)

    def test_missing_one_nonconstant_final_store_rejected(self):
        bad = deepcopy(self.profile)
        rows = bad["methods"][0]["instructions"]
        row = next(r for r in rows if r.get("name") == "final0")
        row["name"] = "mutable0"
        with self.assertRaisesRegex(
            OriginalEightFinalInitializerError,
            "ORIGINAL_OWNER_STATIC_FIELD_ASSIGNED_MORE_THAN_ONCE",
        ):
            self.proof(bad)

    def test_invalid_classfile_method_or_field_counts_fail_closed(self):
        bad = deepcopy(self.profile)
        bad["fields"].pop()
        with self.assertRaisesRegex(
            OriginalEightFinalInitializerError,
            "ORIGINAL_OWNER_126_FIELD_INVENTORY_NOT_EXACT",
        ):
            self.proof(bad)
        bad = deepcopy(self.profile)
        bad["methods"][0]["instructions"].pop()
        with self.assertRaisesRegex(
            OriginalEightFinalInitializerError,
            "ORIGINAL_STATIC_INITIALIZER_213_INSTRUCTIONS_REQUIRED",
        ):
            self.proof(bad)

    def test_original_static_final_field_writes_not_duplicated(self):
        bad = deepcopy(self.profile)
        row = bad["methods"][0]["instructions"][1]
        row["name"] = "final1"
        row["descriptor"] = "Ljava/lang/String;"
        with self.assertRaisesRegex(
            OriginalEightFinalInitializerError,
            "ORIGINAL_OWNER_STATIC_FIELD_ASSIGNED_MORE_THAN_ONCE",
        ):
            self.proof(bad)

    def test_rhs_array_must_be_int_newarray_not_byte_array(self):
        bad = deepcopy(self.profile)
        row = next(r for r in bad["methods"][0]["instructions"]
                   if r["opcode"] == "0xbc")
        row["array_primitive_atype"] = 8
        with self.assertRaisesRegex(
            OriginalEightFinalInitializerError,
            "ORIGINAL_INTEGER_ARRAY_ALLOCATION_NOT_EXACT",
        ):
            self.proof(bad)
