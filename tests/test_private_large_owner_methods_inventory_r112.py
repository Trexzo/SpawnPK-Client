"""R112 strict private original 364/697-method frontier tests."""
from __future__ import annotations
from copy import deepcopy
import unittest
from spk_recovery.private_large_owner_methods_inventory_r112 import (
    TwoLargeOwnerMethodInventoryError, unique_unrecovered, method_inventory,
)


def instruction(op, offset, **kwargs):
    return {"opcode":op,"offset":offset,**kwargs}


def method(count, name):
    rows=[instruction("0x00",i) for i in range(count-1)]
    rows.append(instruction("0xb1",count-1))
    return {"name":name,"descriptor":"()V","access":9,
            "instructions":rows,"exception_handlers":[],
            "max_stack":2,"max_locals":2}


class OriginalTwoLargeMethodsR112Tests(unittest.TestCase):
    def setUp(self):
        counts=(2,2,2,3,4,20,41,213,364,697)
        self.profile={
            "classfile_major":53,
            "fields":[{"name":"f"+str(i)} for i in range(126)],
            "methods":[method(n,"m"+str(i)) for i,n in enumerate(counts)]
        }
        for m in self.profile["methods"]:
            if len(m["instructions"])==364:
                m["instructions"][0]=instruction(
                    "0xb2",0,owner="p/Owner",name="flag",descriptor="Z")
                m["instructions"][1]=instruction(
                    "0xba",1,name="makeConcatWithConstants",
                    descriptor="(I)Ljava/lang/String;",
                    bootstrap_method_attr_index=3)
                m["instructions"][2]=instruction(
                    "0xa7",2,branch_target_offset=5)
            if len(m["instructions"])==697:
                m["instructions"][0]=instruction(
                    "0xb8",0,owner="p/Helper",name="run",descriptor="()V")
                m["instructions"][1]=instruction(
                    "0xb3",1,owner="p/Owner",name="flag",descriptor="Z")
                m["instructions"][2]=instruction(
                    "0x9a",2,branch_target_offset=5)

    def test_two_exact_original_length_frontiers_and_private_symbols(self):
        found=unique_unrecovered(self.profile)
        self.assertEqual(set(found),{364,697})
        small,_=method_inventory(found[364])
        big,_=method_inventory(found[697])
        self.assertEqual(small["method_jvm_instructions"],364)
        self.assertEqual(big["method_jvm_instructions"],697)
        self.assertEqual(small["invokedynamic_sites"],1)
        self.assertEqual(big["field_write_sites"],1)
        self.assertEqual(small["explicit_branch_sites"],1)
        self.assertEqual(big["explicit_branch_sites"],1)
        self.assertEqual(len(small["private_operand_map_sha256"]),64)

    def test_changed_owner_field_inventory_is_vetoed(self):
        bad=deepcopy(self.profile)
        bad["fields"].pop()
        with self.assertRaisesRegex(
                TwoLargeOwnerMethodInventoryError,
                "126FIELD_TENMETHOD_OWNER_REQUIRED"):
            unique_unrecovered(bad)

    def test_changed_large_method_instruction_count_vetoed(self):
        bad=deepcopy(self.profile)
        bad["methods"][-1]["instructions"].pop()
        with self.assertRaisesRegex(
                TwoLargeOwnerMethodInventoryError,
                "INSTRUCTION_DISTRIBUTION_CHANGED"):
            unique_unrecovered(bad)

    def test_branch_target_must_resolve_to_instruction(self):
        bad=deepcopy(self.profile)
        m=unique_unrecovered(bad)[697]
        m["instructions"][2]["branch_target_offset"]=999
        with self.assertRaisesRegex(
                TwoLargeOwnerMethodInventoryError,
                "BRANCH_TARGET_UNRESOLVED"):
            method_inventory(m)

    def test_invokedynamic_missing_original_bootstrap_index_vetoed(self):
        bad=deepcopy(self.profile)
        m=unique_unrecovered(bad)[364]
        del m["instructions"][1]["bootstrap_method_attr_index"]
        with self.assertRaisesRegex(
                TwoLargeOwnerMethodInventoryError,
                "INVOKEDYNAMIC_UNRESOLVED"):
            method_inventory(m)

    def test_unresolved_private_member_reference_vetoed(self):
        bad=deepcopy(self.profile)
        m=unique_unrecovered(bad)[697]
        del m["instructions"][0]["descriptor"]
        with self.assertRaisesRegex(
                TwoLargeOwnerMethodInventoryError,
                "MEMBER_OPERANDS_UNRESOLVED"):
            method_inventory(m)

    def test_missing_original_return_vetoed(self):
        bad=deepcopy(self.profile)
        m=unique_unrecovered(bad)[364]
        m["instructions"][-1]["opcode"]="0x00"
        with self.assertRaisesRegex(
                TwoLargeOwnerMethodInventoryError,
                "STACK_LOCAL_OR_RETURN_MISSING"):
            method_inventory(m)
