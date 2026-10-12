"""R85 synthetic exact-ordinal partition, overlap and missing-gap vetoes."""
import copy
import unittest
from spk_recovery.private_save_method_candidate import (
    SaveWriterSourceError, partition_original_save_method,
)


def synthetic():
    rows=[{"offset":i,"length":1,"opcode":"0x00"} for i in range(364)]
    # Only 47 site regions and the original explicit two-op newline gap
    # matter for this partition-level synthetic test.
    for index,offset in ((20,44),(152,380),(153,381),(154,384),(336,871)):
        rows[index]["offset"]=offset
    # Keep offsets strictly increasing after the critical landmarks.
    for left,right in ((0,20),(20,152),(154,336),(336,364)):
        start=rows[left]["offset"]
        end=rows[right]["offset"] if right<len(rows) else 929
        for i in range(left+1,right):
            rows[i]["offset"]=start+(i-left)*(end-start)//(right-left)
    rows[152]["opcode"]="0x2b"
    rows[153].update(opcode="0xb6",owner="java/io/BufferedWriter",
                     name="newLine",descriptor="()V")
    # This test uses 47 abstract site windows, one starting after the gap.
    spans=[(20,26),(26,32),(32,38),(38,44)]
    cursor=44
    while len(spans)<20:
        spans.append((cursor,cursor+6))
        cursor+=6
    # Last pre-gap site ends at 152.
    spans.append((cursor,152))
    spans.append((154,160))
    cursor=160
    # Twenty-four seven-op blocks and one eight-op closing block:
    # all 25 sites have room for at least one actual writer instruction.
    for _ in range(24):
        spans.append((cursor,cursor+7))
        cursor+=7
    spans.append((cursor,336))
    assert len(spans)==47
    simple,special=[],[]
    for i,(a,b) in enumerate(spans):
        rows[a]["opcode"]="0x2b"
        rows[a+1].update(opcode="0xb6",owner="java/io/BufferedWriter",
                         name="write",descriptor="(Ljava/lang/String;)V")
        if i<42:
            simple.append({"original_JVM_start_offset":rows[a]["offset"],
                           "original_JVM_end_next_offset":rows[b]["offset"],
                           "private_java_source_fragment":"writer.write(value);\n"})
        else:
            special.append({"original_start_offset":rows[a]["offset"],
                            "original_end_offset":rows[b]["offset"],
                            "private_java_source_fragment":"writer.write(value);\n"})
    # Offset ordinal map must be globally injective for this witness.
    assert len({r["offset"] for r in rows})==364
    return rows,simple,special


class SaveMethodPartitionTests(unittest.TestCase):
    def test_expected_full_364_ordinal_source_partition(self):
        rows,reg,special=synthetic()
        result=partition_original_save_method(rows,reg,special)
        self.assertEqual(result["original_total_jvm_instructions"],364)
        self.assertEqual(result["original_writer_and_separator_JVM_instructions"],316)
        self.assertEqual(result["original_standalone_array_separator_instruction_count"],2)
        self.assertEqual(result["original_write_calls_accounted_for"],47)
        self.assertFalse(result["whole_364_op_candidate_compiled_against_original_dependencies"]
                         if "whole_364_op_candidate_compiled_against_original_dependencies" in result
                         else result["complete_original_method_compiled"])

    def test_missing_separate_newline_fails(self):
        rows,reg,special=synthetic()
        rows[153]["name"]="write"
        with self.assertRaisesRegex(SaveWriterSourceError,"UNEXPLAINED_ORIGINAL_SAVE_JVM_GAP"):
            partition_original_save_method(rows,reg,special)

    def test_duplicate_source_site_fails(self):
        rows,reg,special=synthetic()
        special[0]["original_start_offset"]=reg[-1]["original_JVM_start_offset"]
        with self.assertRaisesRegex(SaveWriterSourceError,"SOURCE_OVERLAP"):
            partition_original_save_method(rows,reg,special)

if __name__=="__main__":
    unittest.main()
