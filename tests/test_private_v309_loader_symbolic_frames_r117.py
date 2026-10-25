"""R117: original 161-frame ordinal-aware symbolic re-encoding, no Code copying."""
from __future__ import annotations

from copy import deepcopy
import unittest

from spk_recovery.bytecode_profile import _stackmap_table
from spk_recovery.private_v309_loader_symbolic_frames_r117 import (
    LoaderSymbolicFramesR117Error,
    category, frames_at_ordinals, semantic_frame,
    encode_original_states_at_candidate_pcs, require_original_states_at_candidate_pcs,
)


class Original161FrameMetadataTests(unittest.TestCase):
    def setUp(self):
        class_names = [
            "java/io/File", "java/util/Properties",
            "java/io/FileInputStream", "java/lang/Exception",
        ]
        self.cp = [None]
        for name in class_names:
            index=len(self.cp)
            self.cp.extend([(1,name),(7,index)])
        self.old_rows=[
            {"offset": i*4,"opcode":"0x00","length":1}
            for i in range(697)
        ]
        self.new_rows=[
            {"offset": i*5,"opcode":"0x00","length":1}
            for i in range(697)
        ]
        orig=[
            {"frame_type": 3,"bytecode_offset":i*4}
            for i in range(161)
        ]
        compiled=[
            {"frame_type":4,"bytecode_offset":i*5}
            for i in range(161)
        ]
        top={"kind":"top"}
        integer={"kind":"integer"}
        def obj(name):
            return {"kind":"object","class":name}
        original_exception=obj("java/lang/Exception")
        orig[1]={"frame_type":255,"bytecode_offset":4,
                 "locals":[top,obj("java/util/Properties")],
                 "stack":[original_exception]}
        compiled[1]={
            "frame_type":255,"bytecode_offset":5,
            "locals":[obj("java/io/File"),obj("java/util/Properties"),
                      obj("java/io/FileInputStream")],
            "stack":[original_exception],
        }
        orig[23]={"frame_type":253,"bytecode_offset":23*4,
                  "appended_locals":[top,integer]}
        compiled[23]={
            "frame_type":252,"bytecode_offset":23*5,
            "appended_locals":[integer]}
        orig[25]={"frame_type":249,"bytecode_offset":25*4,
                  "chopped_locals":2}
        compiled[25]={"frame_type":250,"bytecode_offset":25*5,
                      "chopped_locals":1}
        orig[156]={"frame_type":249,"bytecode_offset":156*4,
                   "chopped_locals":2}
        compiled[156]={"frame_type":251,"bytecode_offset":156*5}
        orig[158]={"frame_type":251,"bytecode_offset":158*4}
        compiled[158]={"frame_type":248,"bytecode_offset":158*5,
                       "chopped_locals":3}
        self.orig={
            "stackmap_table_present":True,
            "instructions":self.old_rows,
            "stackmap_frames":orig,
        }
        self.source={
            "stackmap_table_present":True,
            "instructions":self.new_rows,
            "stackmap_frames":compiled,
        }

    def test_reencode_full_original_161_symbolic_frames_at_new_instruction_pcs(self):
        encoded,report=encode_original_states_at_candidate_pcs(
            self.orig,self.source,self.cp)
        parsed=_stackmap_table(
            encoded,self.cp,code=b"\x00"*(697*5),
            instructions=self.new_rows)
        self.assertEqual(len(parsed),161)
        old_ord,old_map=frames_at_ordinals(self.orig)
        new_ord,new_map=frames_at_ordinals({
            **self.source,"stackmap_frames":parsed})
        self.assertEqual(old_ord,new_ord)
        for original,candidate in zip(
                self.orig["stackmap_frames"],parsed):
            self.assertEqual(
                semantic_frame(original,old_map,self.new_rows),
                semantic_frame(candidate,old_map,self.new_rows))
        self.assertTrue(report["original_loader_161_frame_ordinals_aligned"])
        self.assertEqual(report[
            "original_loader_preimage_frame_category_differences"],4)
        self.assertEqual(report[
            "original_loader_preimage_explicit_locals_differences"],2)

    def test_misaligned_canonical_frame_is_a_hard_veto(self):
        changed=deepcopy(self.source)
        changed["stackmap_frames"][3]["bytecode_offset"]+=1
        with self.assertRaisesRegex(
                LoaderSymbolicFramesR117Error,
                "JVM_FRAME_OFFSET_NOT_AT_INSTRUCTION_BOUNDARY"):
            encode_original_states_at_candidate_pcs(
                self.orig,changed,self.cp)

    def test_changed_original_local_payload_frontier_rejected(self):
        changed=deepcopy(self.source)
        changed["stackmap_frames"][1]["locals"]=deepcopy(
            self.orig["stackmap_frames"][1]["locals"])
        with self.assertRaisesRegex(
            LoaderSymbolicFramesR117Error,
                "EXPECTED_ORIGINAL_SOURCE_LOADER_FRAME_FRONTIER_CHANGED"):
            encode_original_states_at_candidate_pcs(
                self.orig,changed,self.cp)

    def test_wrong_preimage_frame_category_must_fail_closed(self):
        changed=deepcopy(self.source)
        changed["stackmap_frames"][25]["frame_type"]=249
        changed["stackmap_frames"][25]["chopped_locals"]=2
        with self.assertRaisesRegex(
                LoaderSymbolicFramesR117Error,
                "EXPECTED_ORIGINAL_SOURCE_LOADER_FRAME_FRONTIER_CHANGED"):
            encode_original_states_at_candidate_pcs(
                self.orig,changed,self.cp)

    def test_missing_candidate_original_verification_class_vetoes(self):
        cp=self.cp[:]
        cp[2]=(7,3)  # java/util/Properties instead of java/io/File
        cp[3]=(1,"java/util/Properties")
        with self.assertRaisesRegex(
                LoaderSymbolicFramesR117Error,
                "ORIGINAL_FRAME_CLASS_NOT_IN_CANDIDATE_POOL"):
            # Remove java/io/Exception instead with a valid CP row string.
            cp=self.cp[:]
            cp[7]=(1,"some/private/OtherException")
            encode_original_states_at_candidate_pcs(
                self.orig,self.source,cp)

    def test_missing_original_frame_count_is_rejected(self):
        changed=deepcopy(self.orig)
        changed["stackmap_frames"].pop()
        with self.assertRaisesRegex(
                LoaderSymbolicFramesR117Error,
                "EXACT_697_LOADER_AND_161_FRAMES_REQUIRED"):
            encode_original_states_at_candidate_pcs(
                changed,self.source,self.cp)

    def test_nonstandard_bytecode_uninitialized_new_target_must_remap(self):
        f={"kind":"uninitialized","new_offset":20}
        original={"frame_type":247,"bytecode_offset":24,"stack":[f]}
        old_index={20:5}
        candidate=[{"offset":i*5,"opcode":"0xbb" if i==5 else "0x00"}
                   for i in range(697)]
        self.assertEqual(
            semantic_frame(original,old_index,candidate)[3],
            [{"kind":"uninitialized","new_offset":25}])

    def test_repaired_original_states_use_candidate_new_offsets(self):
        # 697 instructions; javac widening shifts PC offsets, not ordinal identities.
        old_rows=[{"offset":i*4,"opcode":"0xbb" if i==20 else "0x00"}
                  for i in range(697)]
        new_rows=[{"offset":i*5,"opcode":"0xbb" if i==20 else "0x00"}
                  for i in range(697)]
        def method(rows):
            frames=[]
            for ordinal in range(30,191):
                record={"bytecode_offset":rows[ordinal]["offset"],
                        "frame_type":255 if ordinal==30 else 251}
                if ordinal==30:
                    record["locals"]=[{"kind":"uninitialized",
                                      "new_offset":rows[20]["offset"]}]
                frames.append(record)
            return {"instructions":rows,"stackmap_table_present":True,
                    "stackmap_frames":frames}
        original,candidate=method(old_rows),method(new_rows)
        self.assertTrue(require_original_states_at_candidate_pcs(original,candidate))
        # This was the R117 bug: using original offsets on both sides.
        _,original_index=frames_at_ordinals(original)
        with self.assertRaises(LoaderSymbolicFramesR117Error):
            semantic_frame(candidate["stackmap_frames"][0],
                           original_index,candidate["instructions"])
        damaged=deepcopy(candidate)
        damaged["stackmap_frames"][0]["locals"][0]["new_offset"]=new_rows[21]["offset"]
        with self.assertRaisesRegex(
                LoaderSymbolicFramesR117Error,
                "CANDIDATE_UNINITIALIZED_NEW_OPCODE_CHANGED"):
            require_original_states_at_candidate_pcs(original,damaged)

