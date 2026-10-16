"""R226 regression tests: 12 original packet-base method proof contracts.

Synthetic disassembly never contains proprietary client bytes. CI must
reject changes in member operands, instruction offsets, opcodes, original
method inventory, dependency fingerprints and original JAR provenance.
"""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from spk_recovery.private_v309_real_packet_base_closure_r226 import (
    ALIASES,CONCRETE_METHODS,EXPECTED_ORIGINAL_INSTRUCTIONS,
    ORIGINAL_CLASS_SHA256,REAL_JAVA,
    R226RealPacketClosureError,
    compare_packet_base_jvm,build_real_packet_closure,parse_code,
)


def fake_disassemblies():
    original=[]
    readable=[]
    symbols=iter(ALIASES.items())
    used=0
    for old_header,new_header,nops in CONCRETE_METHODS:
        a=[old_header,"    Code:"]
        b=[new_header,"    Code:"]
        for index in range(nops):
            if index==nops-1:
                opcode="return"
                operand=""
                newoperand=""
            elif used<len(ALIASES):
                operand,newoperand=next(symbols)
                opcode="getfield" if operand.startswith("Field ") else "invokevirtual"
                used+=1
            else:
                opcode="nop"
                operand=newoperand=""
            a.append(f"       {index}: {opcode}"+
                     (f" // {operand}" if operand else ""))
            b.append(f"       {index}: {opcode}"+
                     (f" // {newoperand}" if newoperand else ""))
        original.extend(a+[""])
        readable.extend(b+[""])
    if used!=len(ALIASES):
        raise AssertionError("Synthetic aliases were not all consumed")
    return "\n".join(original),"\n".join(readable)


class R226InventedOriginalPacketBaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old,cls.new=fake_disassemblies()

    def test_all_twelve_concrete_method_bodies_and_all_aliases(self):
        result=compare_packet_base_jvm(self.old,self.new)
        self.assertEqual(12,result[
            "original_concrete_method_bodies_verified"])
        self.assertEqual(52,result[
            "original_concrete_JVM_instructions_verified"])
        self.assertEqual(12,result[
            "explicit_member_aliases_verified"])
        self.assertTrue(result[
            "original_JVM_offsets_opcodes_and_operands_match"])

    def test_wrong_member_symbol_rejected(self):
        changed=self.new.replace(
            "Field packet:Lrs/io/Packet;",
            "Field stolen:Lrs/io/Packet;",1)
        with self.assertRaises(R226RealPacketClosureError):
            compare_packet_base_jvm(self.old,changed)

    def test_wrong_opcode_or_offset_rejected(self):
        with self.assertRaises(R226RealPacketClosureError):
            compare_packet_base_jvm(self.old,self.new.replace(
                ": nop",": pop",1))
        changed=self.new.replace("       0:","       81:",1)
        with self.assertRaises(R226RealPacketClosureError):
            compare_packet_base_jvm(self.old,changed)

    def test_method_omission_and_duplicate_rejected(self):
        original=self.old.replace(CONCRETE_METHODS[0][0],
                                  "public unrelated();",1)
        with self.assertRaises(R226RealPacketClosureError):
            compare_packet_base_jvm(original,self.new)
        with self.assertRaises(R226RealPacketClosureError):
            compare_packet_base_jvm(
                self.old+"\n"+self.old,self.new)

    def test_unapproved_alias_and_changed_instruction_count_rejected(self):
        with self.assertRaises(R226RealPacketClosureError):
            compare_packet_base_jvm(
                self.old,self.new,aliases={
                    **ALIASES,
                    "Field hidden:I":"Field hiddenNew:I",
                })
        with self.assertRaises(R226RealPacketClosureError):
            compare_packet_base_jvm(
                self.old,self.new,
                expected_total=EXPECTED_ORIGINAL_INSTRUCTIONS+1)

    def test_forged_original_binary_or_tree_rejected(self):
        with TemporaryDirectory() as tmp:
            f=Path(tmp)/"fake.jar"
            f.write_bytes(b"not the pinned original client")
            with self.assertRaises(R226RealPacketClosureError):
                build_real_packet_closure(f,f,f)

    def test_unique_original_source_pins_and_binary_hashes(self):
        self.assertEqual(6,len(REAL_JAVA))
        self.assertEqual(6,len(set(REAL_JAVA)))
        self.assertEqual(64,len(ORIGINAL_CLASS_SHA256))
        self.assertTrue(all(len(sha)==64 for sha in REAL_JAVA.values()))


if __name__=="__main__":
    unittest.main()
