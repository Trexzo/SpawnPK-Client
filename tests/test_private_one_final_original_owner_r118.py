"""R118: one final SHA-pinned owner source candidate, all gates fail closed."""
from __future__ import annotations

from contextlib import ExitStack
from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import spk_recovery.private_one_final_original_owner_r118 as gate


def synthetic_owner():
    lengths=[2,2,2,3,4,20,41,213,364,697]
    fields=[
        {"name":"f"+str(i),"descriptor":"Z","access":9}
        for i in range(126)
    ]
    methods=[]
    for i,n in enumerate(lengths):
        rows=[
            {"opcode":"0x00","offset":j,"length":1}
            for j in range(n)]
        if n==213:
            for j in range(93):
                rows[j]={
                    "opcode":"0xb3","offset":j,"length":1,
                    "owner":"p/Owner","name":"f"+str(j),
                    "descriptor":"Z",
                }
        methods.append({
            "name":"<clinit>" if n==213 else "m"+str(i),
            "descriptor":"()V",
            "access":8 if n==213 else 9,
            "instructions":rows,
        })
    return {
        "internal_name":"p/Owner","classfile_major":53,
        "class_access":49,"super_name":"java/lang/Object",
        "fields":fields,"methods":methods,
    }


class OriginalOwnerAllFinalGateR118Tests(unittest.TestCase):
    ORIGINAL=["p/Owner$Owner.class","p/Owner$One.class",
              "p/Owner$Two.class","p/Owner$Three.class"]
    SOURCE=["p/Owner$Surrogate.class","p/Owner$One.class",
            "p/Owner$Two.class","p/Owner$Three.class"]

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.original=self.root/"original.jar"
        self.source=self.root/"source.jar"
        self.final_bytes=None
        self.destination=self.root/"accepted"
        self.make_zip(self.original,self.ORIGINAL,b"original-owner")
        self.make_zip(self.source,self.SOURCE,b"compiled-owner")
        self.old=synthetic_owner()
        self.new=deepcopy(self.old)
        self.final=deepcopy(self.old)
        self.calls=[]

    @staticmethod
    def make_zip(path,nested,owner):
        with ZipFile(path,"w") as z:
            z.writestr("p/Owner.class",owner)
            for name in nested:
                z.writestr(name,("symbolic|"+name).encode("utf-8"))

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def accept(self,pin=None):
        return gate.accept_one_final_v309_source_compiled_owner(
            self.original,self.source,
            "p/Owner.class","Surrogate",self.destination,
            original_sha256=pin or self.sha(self.original),
            candidate_sha256=self.sha(self.source))

    def mock_profiles(self,*,r106=None,r94=None,clinit=None,frontier=None,large=None):
        ctx=ExitStack()
        self.addCleanup(ctx.close)
        def profile(path,entry):
            self.assertEqual(entry,"p/Owner.class")
            if Path(path)==self.original:
                return deepcopy(self.old)
            if Path(path)==self.source:
                return deepcopy(self.new)
            return deepcopy(self.final)
        def repair(a,b,owner,surrogate,out,**kw):
            self.calls.append("R106/R105/R104/R95")
            self.assertEqual(self.sha(b),kw["candidate_sha256"])
            self.assertEqual(self.sha(a),kw["original_sha256"])
            self.assertEqual(owner,"p/Owner.class")
            self.assertEqual(surrogate,"Surrogate")
            out=Path(out);out.mkdir()
            finaljar=out/"all-four-R95-after-StackMap.private.jar"
            self.make_zip(finaljar,self.ORIGINAL,b"final-after-all-four")
            self.final_bytes=finaljar.read_bytes()
            return {
                "original_four_nested_enums_R95_accepted":True,
                "original_case_insensitive_lookup_method_frames_identical":True,
                "candidate_method_code_bytes_preserved":True,
                "original_lookups_method_code_bytes_transferred":False,
                "r95_accepted_candidate_sha256":self.sha(finaljar),
            }
        def check_methods(a,b,owner,other,out,**kw):
            self.calls.append("R94-final")
            self.assertEqual(b.read_bytes(),self.final_bytes)
            self.assertEqual(kw["candidate_sha256"],self.sha(b))
            out.mkdir()
            return {
                "R66_and_R81_parity_passed_all_nine_ordinary_methods":True,
                "original_ordinary_methods_parity_checked":9,
                "original_ordinary_jvm_instruction_operands_compared":1135,
            }
        def check_clinit(original,candidate,alias_rows):
            self.calls.append("R58-final")
            self.assertEqual(len(alias_rows),93)
            self.assertEqual(alias_rows[0]["original"],
                             {"name":"f0","descriptor":"Z"})
            return {
                "identical_normalized_initializer_operand_semantics":True,
                "original_owner_static_writes_in_order":93,
                "original_initializer_instructions":213,
            }
        def check_fields(old,new,left,right):
            self.calls.append("R88-final")
            self.assertEqual(left,set(self.ORIGINAL))
            self.assertEqual(right,set(self.ORIGINAL))
            proof={
                "original_fields":126,"candidate_fields":126,
                "original_methods":10,"candidate_methods":10,
                "original_nested_classes":4,"candidate_nested_classes":4,
            }
            for field in (
                "missing_original_fields","extra_candidate_fields",
                "shared_field_declaration_mismatches",
                "missing_original_methods","extra_candidate_methods",
                "shared_method_declaration_mismatches",
                "missing_original_nested_classes","extra_candidate_nested_classes",
            ):
                proof[field]=0
            for field in (
                "original_candidate_major_equal","original_candidate_super_equal",
                "original_candidate_class_access_equal",
                "original_candidate_class_signature_equal",
                "original_candidate_interface_list_equal",
            ):
                proof[field]=True
            return proof
        for name,fn in (
            ("profile_jar_class",profile),
            ("repair_then_require_r105_r95",r106 or repair),
            ("replay_all_original_methods",r94 or check_methods),
            ("compare_clinit_operand_semantics",clinit or check_clinit),
            ("private_owner_frontier",frontier or check_fields),
            ("exact_original_large_methods_before_or_after",large or (lambda a,b:True)),
        ):
            ctx.enter_context(patch.object(gate,name,fn))

    def test_exact_final_candidate_passes_all_original_owner_gates(self):
        self.mock_profiles()
        proof=self.accept()
        self.assertEqual(self.calls,
                         ["R106/R105/R104/R95","R94-final","R58-final","R88-final"])
        self.assertTrue(proof["R95_original_four_enums_passed"])
        self.assertTrue(proof["R94_original_nine_ordinary_owner_methods_passed"])
        self.assertTrue(proof["R58_original_clinit_operand_semantics_passed"])
        self.assertTrue(proof["R88_original_owner_all_declarations_passed"])
        self.assertFalse(proof["whole_original_client_runtime_equivalence_certified"])
        self.assertEqual(self.sha(self.destination/"candidate.private.jar"),
                         proof["final_all_original_gates_candidate_sha256"])
        self.assertEqual(len(list(self.destination.iterdir())),2)

    def test_wrong_original_sha256_vetoes_before_preimage(self):
        self.mock_profiles()
        with self.assertRaisesRegex(
                gate.OneFinalOriginalOwnerR118Error,
                "SOURCE_JAR_SHA256_PIN_MISMATCH"):
            self.accept(pin="0"*64)
        self.assertEqual(self.calls,[])
        self.assertFalse(self.destination.exists())

    def test_source_missing_one_other_enum_vetoes_before_r106(self):
        self.make_zip(self.source,self.SOURCE[:-1],b"compiled-owner")
        self.mock_profiles()
        with self.assertRaisesRegex(
                gate.OneFinalOriginalOwnerR118Error,
                "EXACT_ONE_SOURCE_INVALID_FOURTH_ENUM_NAME_REQUIRED"):
            self.accept()
        self.assertEqual(self.calls,[])
        self.assertFalse(self.destination.exists())

    def test_missing_original_owner_ordinary_method_blocks_all_rebinding(self):
        self.new["methods"].pop()
        self.mock_profiles()
        with self.assertRaisesRegex(
                gate.OneFinalOriginalOwnerR118Error,
                "126_FIELD_TEN_METHOD_PREIMAGE_REQUIRED"):
            self.accept()
        self.assertEqual(self.calls,[])
        self.assertFalse(self.destination.exists())

    def test_r106_any_failure_cannot_promote(self):
        def deny(*args,**kw):
            raise gate.VerifiedEnumStackMapError("changed stack map")
        self.mock_profiles(r106=deny)
        with self.assertRaisesRegex(
                gate.OneFinalOriginalOwnerR118Error,
                "R106_R105_R104_R95_FOUR_ENUMS_NOT_ACCEPTED"):
            self.accept()
        self.assertFalse(self.destination.exists())

    def test_final_r94_ordinary_method_failure_blocks_publication(self):
        def deny(*args,**kw):
            raise gate.AllOwnerMethodsParityError("loader operand mismatch")
        self.mock_profiles(r94=deny)
        with self.assertRaisesRegex(
                gate.OneFinalOriginalOwnerR118Error,
                "R94_FINAL_NINE_OWNER_METHODS_NOT_ACCEPTED"):
            self.accept()
        self.assertFalse(self.destination.exists())

    def test_final_r58_initializer_mismatch_blocks_publication(self):
        def deny(*args,**kw):
            raise gate.ClinitOperandWitnessError("original writes drift")
        self.mock_profiles(clinit=deny)
        with self.assertRaisesRegex(
                gate.OneFinalOriginalOwnerR118Error,
                "R58_OR_R88_COMPLETE_FINAL_OWNER_JVM_NOT_ACCEPTED"):
            self.accept()
        self.assertFalse(self.destination.exists())

    def test_final_r88_missing_field_blocks_publication(self):
        def wrong(a,b,one,two):
            self.calls.append("R88-final")
            return {"original_fields":126,"candidate_fields":125}
        self.mock_profiles(frontier=wrong)
        with self.assertRaisesRegex(
                gate.OneFinalOriginalOwnerR118Error,
                "R88_FINAL_126_FIELDS_TEN_METHODS_FOUR_ENUMS_NOT_EQUAL"):
            self.accept()
        self.assertFalse(self.destination.exists())

    def test_missing_large_method_stackmap_proof_vetoes_before_r106(self):
        def deny(a,b):
            raise gate.OneFinalOriginalOwnerR118Error("missing original loader state")
        self.mock_profiles(large=deny)
        with self.assertRaisesRegex(
                gate.OneFinalOriginalOwnerR118Error,
                "missing original loader state"):
            self.accept()
        self.assertEqual(self.calls,[])
        self.assertFalse(self.destination.exists())

    def test_loader_uninitialized_reference_resolves_candidate_pc_index(self):
        # javac can widen earlier LDCs, shifting NEW and StackMap bytecode PCs.
        # Both sides must resolve uninitialized NEW from their OWN offset table.
        original_ins=[{"offset":i,"opcode":"0xbb" if i==20 else "0x00"}
                      for i in range(697)]
        candidate_ins=[{"offset":i+(1 if i>=10 else 0),
                        "opcode":"0xbb" if i==20 else "0x00"}
                       for i in range(697)]
        def frames(ins):
            result=[]
            for i in range(30,191):
                row={"bytecode_offset":ins[i]["offset"],
                     "frame_type":255 if i==30 else 251}
                if i==30:
                    row["locals"]=[{"kind":"uninitialized",
                                   "new_offset":ins[20]["offset"]}]
                result.append(row)
            return result
        original_loader={"name":"load","descriptor":"()V","access":9,
                         "stackmap_table_present":True,
                         "instructions":original_ins,
                         "stackmap_frames":frames(original_ins)}
        candidate_loader={"name":"load","descriptor":"()V","access":9,
                          "stackmap_table_present":True,
                          "instructions":candidate_ins,
                          "stackmap_frames":frames(candidate_ins)}
        original={"methods":[original_loader]}
        candidate={"methods":[candidate_loader]}
        operand_proof={
            "original_instructions_with_all_semantic_operands_compared":697,
            "original_explicit_branches":120,
            "original_ordered_typed_exception_entries":44,
            "original_ordered_static_writes":78,
            "all_parsed_JVM_operands_equal_with_private_aliases":True,
        }
        saver_proof={
            "original_saver_R66_R81_all_operands_passed":True,
            "original_saver_jvm_StackMapTable_frames_equal":10,
        }
        with patch.object(gate,"unique_unrecovered",
                          return_value={697:original_loader}), \
             patch.object(gate,"original_saver_method_profile_proof",
                          return_value=saver_proof), \
             patch.object(gate,"compare_all_method_operands",
                          return_value=operand_proof):
            self.assertTrue(gate.exact_original_large_methods_before_or_after(
                original,candidate))
            corrupted=deepcopy(candidate)
            corrupted["methods"][0]["stackmap_frames"][0]["locals"][0][
                "new_offset"]=candidate_ins[21]["offset"]
            with self.assertRaises(gate.LoaderSymbolicFramesR117Error):
                gate.exact_original_large_methods_before_or_after(
                    original,corrupted)

