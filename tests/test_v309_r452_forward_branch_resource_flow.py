"""R452 public synthetic acyclic Java 11 CFG resource argument tests.

Invented bytecode, fake owner-TEMP source/class/JAR trees only. No real
SpawnPK private source/assets/history/client or server is accessed in CI.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r451_straightline_resource_arguments as r451_fixture
from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r452 import forward_branch_resource_operands as flow
from tools.r452 import audit_forward_branch_resource as r452

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT/"tools/r452/audit_forward_branch_resource.py"


def refs(index: int):
    return r451_fixture.method_ref(index)


def literal(index: int):
    return r451_fixture.literal(index)


def resource(name: str):
    return r451_fixture.resource_filter(name)


def inspect_code(code: bytes, *, stack: int=3, locals: int=2, exceptions: int=0):
    return flow.analyze_method(
        code, stack, locals, exceptions, literal, refs, resource)


def diamond(first: int=1, second: int=1) -> bytes:
    """Forward conditional diamond converging on one resource call.

    pc 0 aload_0; pc 1 iconst_0; pc 2 ifeq -> 10;
    pc 5 ldc first; pc 7 goto -> 12; pc 10 ldc second;
    pc 12 invokevirtual resource; pc 15 pop; pc16 return.
    """
    return (b"\x2a\x03\x99\x00\x08\x12"+bytes([first])+
            b"\xa7\x00\x05\x12"+bytes([second])+
            b"\xb6\x00\x08\x57\xb1")


def invent_branch_in_first_method(original: bytes) -> bytes:
    """Change invented R450 Code attribute, never actual client class bytes."""
    # Fabricated fixture: first Code payload has max_stack=2, max_locals=1,
    # code_length=8; source file reports exactly two getResource calls.
    begin = b"\x00\x00\x00\x14\x00\x02\x00\x01\x00\x00\x00\x08"
    marker = original.find(begin)
    if marker < 0:
        raise AssertionError("fabricated R450 classfile Code segment missing")
    old_code = original[marker+len(begin):marker+len(begin)+8]
    if (len(old_code) != 8 or old_code[0:2] != b"\x2a\x12"
            or old_code[3] != 0xb6 or old_code[-2:] != b"\x57\xb1"):
        raise AssertionError("fabricated Code was unexpectedly changed")
    first_idx = old_code[2]
    method_ref_id = old_code[4:6]
    branch_code = (b"\x2a\x03\x99\x00\x08\x12"+bytes([first_idx])+
                   b"\xa7\x00\x05\x12"+bytes([first_idx])+
                   b"\xb6"+method_ref_id+b"\x57\xb1")
    assert len(branch_code) == 17
    # The Code attribute adds 9 extra bytes (8->17).
    newer = (b"\x00\x00\x00\x1d\x00\x02\x00\x01\x00\x00\x00\x11" +
             branch_code + b"\x00\x00\x00\x00")
    old = begin + old_code + b"\x00\x00\x00\x00"
    return original[:marker]+original[marker:].replace(old,newer,1)


class R452PureAcyclicFlow(unittest.TestCase):
    def test_01_same_literal_both_forward_paths_are_attributed(self):
        result = inspect_code(diamond())
        self.assertEqual(result.resource_call_sites,1)
        self.assertEqual(result.attributed,((12,"images/logo.png"),))
        self.assertEqual(result.ambiguous_resource_call_sites,0)
        self.assertEqual(result.branch_instructions,2)
        self.assertGreaterEqual(result.states_explored,8)

    def test_02_two_different_literal_paths_are_ambiguous_not_both_claimed(self):
        result=inspect_code(diamond(1,2))
        self.assertEqual(result.resource_call_sites,1)
        self.assertEqual(result.attributed,())
        self.assertEqual(result.ambiguous_resource_call_sites,1)

    def test_03_missing_literal_on_one_path_cannot_be_attributed(self):
        # Same length as ldc if we use aconst_null followed by nop.
        code=diamond(1,1).replace(b"\x12\x01\xb6",b"\x01\x00\xb6",1)
        result=inspect_code(code)
        self.assertEqual(result.attributed,())
        self.assertEqual(result.ambiguous_resource_call_sites,1)

    def test_04_single_branch_path_with_call_is_conditionally_attributed(self):
        # Predicate then branch past call to return; call is not guaranteed
        # to execute but the argument is known *when call site is reached*.
        code=(b"\x2a\x03\x99\x00\x08\x12\x01"
              b"\xb6\x00\x08\x57\xb1")
        # ifeq from pc2 to pc10 -> pop; but receiver remains on stack.
        # Path with skipped invoke reaches pop of receiver then return.
        result=inspect_code(code)
        self.assertEqual(result.attributed,((7,"images/logo.png"),))
        self.assertEqual(result.resource_call_sites,1)

    def test_05_forward_goto_bypass_is_allowed_when_all_paths_terminate(self):
        code=b"\xa7\x00\x04\x00\xb1"  # goto pc4, skip nop
        result=inspect_code(code,max_stack=0)
        self.assertIsNotNone(result)
        self.assertEqual(result.attributed,())
        self.assertEqual(result.branch_instructions,1)

    def test_06_backward_goto_loop_excluded_not_approximated(self):
        self.assertIsNone(inspect_code(b"\x00\xa7\xff\xff"))

    def test_07_zero_offset_branch_excluded(self):
        self.assertIsNone(inspect_code(b"\xa7\x00\x00\xb1"))

    def test_08_branch_target_into_operand_refused(self):
        with self.assertRaisesRegex(
                flow.Refused,"R452_FORWARD_BRANCH_MISALIGNED"):
            inspect_code(b"\xa7\x00\x02\xb1")

    def test_09_branch_target_past_end_refused(self):
        with self.assertRaisesRegex(
                flow.Refused,"R452_FORWARD_BRANCH_MISALIGNED"):
            inspect_code(b"\xa7\x00\x09\xb1")

    def test_10_unsupported_switch_is_excluded(self):
        self.assertIsNone(inspect_code(
            b"\xaa\x00\x00\x00"+b"\x00"*4+b"\x00"*4+
            b"\x00"*4+b"\x00"*4+b"\xb1"))

    def test_11_unsupported_exception_handlers_excluded(self):
        self.assertIsNone(inspect_code(diamond(),exceptions=1))

    def test_12_unsupported_instruction_refuses_whole_method(self):
        code=b"\x2a\x12\x01\xb2\x00\x0c\xb6\x00\x08\x57\xb1"
        self.assertIsNone(inspect_code(code))

    def test_13_unmodeled_category_two_values_excluded(self):
        self.assertIsNone(inspect_code(b"\x09\x57\xb1"))

    def test_14_invalid_instruction_stream_refuses(self):
        with self.assertRaisesRegex(
                flow.Refused,"R452_INVALID_JVM_INSTRUCTION_BOUNDARIES"):
            inspect_code(b"\x12")

    def test_15_stack_underflow_excludes_method(self):
        self.assertIsNone(inspect_code(b"\x57\xb1"))

    def test_16_excessive_stack_excludes_without_false_argument(self):
        self.assertIsNone(inspect_code(diamond(),stack=1))

    def test_17_static_resource_call_tracks_argument_across_forward_goto(self):
        code=b"\xa7\x00\x04\x00\x12\x01\xb8\x00\x09\x57\xb1"
        result=inspect_code(code,max_stack=1)
        self.assertEqual(result.attributed,((6,"images/logo.png"),))

    def test_18_stored_string_local_shared_across_forward_paths(self):
        code=(b"\x12\x01\x4c"      # save literal in local 1
              b"\x2a\x03\x99\x00\x03"  # ifeq pc5+3->pc8
              b"\x2b\xb6\x00\x08\x57\xb1")
        result=inspect_code(code,stack=2,locals=2)
        self.assertEqual(result.attributed,((9,"images/logo.png"),))

    def test_19_string_local_overwrite_on_branch_causes_ambiguity(self):
        # Branch destinations from explicit positions: 0 ldc,2 astore_1,
        # 3 aload_0,4 iconst_0,5 ifeq->13,8 aconst_null,9 astore_1,
        # 10 goto->13,13 aload_1,14 invokevirtual,17 pop,18 return.
        code=(b"\x12\x01\x4c\x2a\x03\x99\x00\x08"
              b"\x01\x4c\xa7\x00\x03"
              b"\x2b\xb6\x00\x08\x57\xb1")
        result=inspect_code(code,stack=2)
        self.assertEqual(result.attributed,())
        self.assertEqual(result.ambiguous_resource_call_sites,1)

    def test_20_forward_branch_budget_limits_path_explosion(self):
        with patch.object(flow,"MAX_STATES",4):
            self.assertIsNone(inspect_code(diamond()))

    def test_21_branch_budget_refuses_excessive CFG_nodes(self):
        with patch.object(flow,"MAX_BRANCHES",1):
            self.assertIsNone(inspect_code(diamond()))

    def test_22_unknown_string_argument_not_promoted(self):
        code=(b"\x2a\x01\xb6\x00\x08\x57\xb1")
        result=inspect_code(code)
        self.assertEqual(result.resource_call_sites,1)
        self.assertEqual(result.attributed,())
        self.assertEqual(result.ambiguous_resource_call_sites,1)

    def test_23_multiple_terminal_paths_counted_conservatively(self):
        # Fallthrough and conditional destination both return.
        code=b"\x03\x99\x00\x04\xb1\xb1"
        result=inspect_code(code,max_stack=1)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.terminal_paths,1)

    def test_24_malformed_method_without_return_excluded(self):
        self.assertIsNone(inspect_code(b"\x2a\x57"))

    def test_25_pure_aggregate_de_duplicates_and_compares_R451(self):
        evidence={
            "rs/A.class":[("load()V",12,"images/logo.png")],
            "rs/B.class":[("load()V",7,"textures/missing.png")],
        }
        stats={
            k:{"methods_seen":1,"methods_modeled":1,"methods_skipped":0,
               "branch_methods_modeled":1,"resource_call_sites":1,
               "ambiguous_sites":0,"states_explored":12}
            for k in evidence
        }
        prior={"owner_private_resource_argument_worklist":{
            "modeled_static_literal_call_arguments":[{
                "possible_resource_path":"images/logo.png",
                "rebuilt_method_referencers":["rs/A.class#load()V"]}]}}
        report,private=r452.aggregate(
            evidence,stats,{"images/logo.png"},
            prior["owner_private_resource_argument_worklist"])
        self.assertEqual(report["new_class_method_resource_candidates_beyond_R451"],1)
        self.assertEqual(report["class_method_resource_candidates_also_seen_by_R451"],1)
        self.assertEqual(report["all_path_literal_candidate_names_in_original_v309"],1)
        self.assertFalse(private["historical_R421_source_class_custody_approved"])

    def test_26_counter_mismatch_refused(self):
        with self.assertRaisesRegex(r452.Refused,"R452_COUNTER_INVARIANT_FAILED"):
            r452.aggregate(
                {"rs/A.class":[]},
                {"rs/A.class":{"methods_seen":1,"methods_modeled":0,
                               "methods_skipped":0,"branch_methods_modeled":0,
                               "resource_call_sites":0,"ambiguous_sites":0,
                               "states_explored":0}},
                set(),{"modeled_static_literal_call_arguments":[]})


class R452FakeOwnerPipeline(unittest.TestCase):
    def setUp(self):
        r451_fixture.R451OwnerFakeIsolatedPipeline.setUp(self)
        self.described=invent_branch_in_first_method(self.described)
        self.store_class.write_bytes(self.described)
        p=patch.object(r425,"PINNED_R421_STORE_CLASS",
                       sha256(self.described).hexdigest())
        p.start()
        self.addCleanup(p.stop)

    def outputs(self):
        return sorted(self.temp.glob(r452.PREFIX+"*"))

    def test_27_owner_fake_branch_class_produces_incremental_worklist(self):
        result,private=r452.inspect(self.original_jar)
        self.assertEqual(result["status"],
                         "R452_ACYCLIC_JAVA_RESOURCE_ARGUMENT_EVIDENCE_UNAPPROVED")
        self.assertEqual(result["original_class_count"],5)
        self.assertEqual(result["original_resource_count"],2)
        self.assertEqual(result["R421_java_sources"],2)
        self.assertEqual(result["R421_compiled_classes"],2)
        self.assertEqual(result["forward_branch_methods_fully_modeled"],1)
        self.assertEqual(result["all_path_consensus_resource_call_site_candidates"],2)
        self.assertEqual(result["new_class_method_resource_candidates_beyond_R451"],1)
        self.assertEqual(result["class_method_resource_candidates_also_seen_by_R451"],1)
        self.assertFalse(result["runnable_client_proven"])
        self.assertFalse(result["release_authorized"])
        self.assertEqual(private["schema"],r452.SCHEMA)

    def test_28_readonly_default_outputs_aggregate_without_private_names(self):
        result=r452.run(self.original_jar)
        self.assertFalse(result["private_report_created"])
        self.assertEqual(self.outputs(),[])
        payload=json.dumps(result)
        for secret in ("rs/plugins/loottracker/LootHistoryStore.class",
                       "images/logo.png","textures/missing.png",
                       str(self.temp),r425.PINNED_R421_STORE_SHA):
            self.assertNotIn(secret,payload)

    def test_29_explicit_private_quarantine_contains_names_not_bytes(self):
        result=r452.run(self.original_jar,private=True)
        self.assertTrue(result["private_report_created"])
        self.assertEqual(len(self.outputs()),1)
        obj=json.loads((self.outputs()[0]/r452.NAME).read_text("ascii"))
        self.assertEqual(obj["schema"],r452.SCHEMA)
        self.assertFalse(obj["historical_R421_manifest_approved"])
        self.assertFalse(obj["release_authorized"])
        signals=obj["details"]["new_class_method_resource_signals_beyond_R451"]
        self.assertEqual(len(signals),1)
        self.assertEqual(signals[0]["possible_resource_name"],"images/logo.png")

    def test_30_private_output_never_overwrites_previous_report(self):
        a=r452.run(self.original_jar,private=True)
        prior=self.outputs()[0]/r452.NAME
        before=prior.read_bytes()
        b=r452.run(self.original_jar,private=True)
        self.assertEqual(len(self.outputs()),2)
        self.assertNotEqual(a["private_output_directory"],
                            b["private_output_directory"])
        self.assertEqual(before,prior.read_bytes())

    def test_31_original_JAR_sha_mismatch_fails_closed(self):
        self.original_jar.write_bytes(b"invalid SHA wrong JAR")
        with self.assertRaises(r452.r447.Refused):
            r452.inspect(self.original_jar)

    def test_32_class_bytes_modified_after_snapshot_refuse(self):
        snapshot,_=r452.r446.observe()
        bridge=self.compiled/"rs/Bridge.class"
        bridge.write_bytes(b"unsafe")
        with self.assertRaisesRegex(
                r452.Refused,"R452_COMPILED_MEMBER_CHANGED_DURING_SCAN"):
            r452.observed_cfg(snapshot)

    def test_33_unrelated_source_mutation_before_private_worklist_refused(self):
        base=r452.inspect
        count=[0]
        def altered(*args,**kwargs):
            r=base(*args,**kwargs)
            count[0]+=1
            if count[0]==1:
                source=self.source/"rs/Bridge.java"
                source.write_bytes(source.read_bytes()+b" source mutation")
            return r
        with patch.object(r452,"inspect",side_effect=altered):
            with self.assertRaisesRegex(
                    r452.Refused,"R452_INPUTS_CHANGED_BEFORE_PRIVATE_REPORT"):
                r452.run(self.original_jar,private=True)
        self.assertEqual(self.outputs(),[])

    def test_34_private_report_size_budget(self):
        with patch.object(r452,"MAX_PRIVATE",40):
            with self.assertRaisesRegex(
                    r452.Refused,"R452_PRIVATE_REPORT_BUDGET"):
                r452.run(self.original_jar,private=True)
        self.assertEqual(self.outputs(),[])

    def test_35_public_cli_missing_original_refuses_without_path_leak(self):
        missing=self.temp/"real-original-missing.jar"
        p=subprocess.run([sys.executable,"-B",str(CLI),
                          "--original-v309-jar",str(missing)],
                         capture_output=True,text=True,check=False,timeout=15)
        self.assertEqual(p.returncode,2,p.stderr)
        result=json.loads(p.stdout)
        self.assertEqual(result["status"],"R452_ACYCLIC_RESOURCE_AUDIT_REFUSED")
        self.assertNotIn(str(missing),p.stdout)
        self.assertFalse(result["release_authorized"])

    def test_36_no_source_history_or_release_claims(self):
        report=r452.run(self.original_jar)
        for flag in ("owner_game_client_launched",
                     "actual_private_source_executed",
                     "historical_R421_manifest_approved",
                     "full_client_reconstruction_verified",
                     "runnable_client_proven","resource_packaging_verified",
                     "persistent_game_history_accessed","build_authorized",
                     "merge_authorized","release_authorized"):
            self.assertFalse(report[flag])


if __name__=="__main__":
    unittest.main()
