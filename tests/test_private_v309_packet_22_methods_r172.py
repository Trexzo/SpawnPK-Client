"""R172 synthetic: add cursor and buffer Java methods to R171 Packet fixture.

Only generated/synthetic original classes enter hosted CI. All real-v309
source and JAR bytes stay private.
"""
import hashlib
from pathlib import Path
from zipfile import ZipFile
import unittest

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_packet_22_methods_r172 import (
    EXTRA, verify_packet_22,
)
from test_private_v309_packet_six_readers_r171 import R171SixPacketReadMethodsTests


class R172PacketAdditionalMethodsTests(R171SixPacketReadMethodsTests):
    @staticmethod
    def java(*,original,wrong_o=False,wrong_y=False,wrong_p=False):
        base=R171SixPacketReadMethodsTests.java(
            original=original,wrong_o=wrong_o,
            wrong_y=wrong_y,wrong_p=wrong_p)
        # Distinct synthetic semantics and constant values. The original
        # SpawnPK source expressions are never placed in this test.
        extra=(
            "public int bitCursor;public int marked;"
            "public int h(){int x=this.cursor;return x;}"
            "public void i(){this.cursor=0;}"
            "public int j(){return 42;}"
            "public int k(){return -17;}"
            "public byte z(){return this.buffer[this.cursor++];}"
            "public void J(){this.bitCursor=this.cursor*8;}"
            "public void K(){this.cursor=this.bitCursor/8;}"
            "public int Z(){return this.cursor;}"
            "public int aa(){return this.cursor+1;}"
            "public int ab(){return this.marked;}"
            "public byte[] ac(){return this.buffer;}"
            "public int N(){return this.buffer[this.cursor++]+5;}"
            "public int O(){return this.buffer[this.cursor++]^3;}"
            "public int P(){return 0x7f&this.buffer[this.cursor++];}"
            "public byte Q(){return (byte)(this.buffer[this.cursor++]+1);}"
            "public byte R(){return (byte)(this.buffer[this.cursor++]-1);}"
        )
        return base[:-1]+extra+"}"

    def setUp(self):
        super().setUp()
        with ZipFile(self.original) as z:
            raw=z.read(self.OWNER+".class")
        profile=profile_class_field_accesses(raw)
        index={(m["name"],m["descriptor"]):m for m in profile["methods"]}
        self.additional_instructions=sum(
            len(index[identity]["instructions"]) for identity in EXTRA)

    def verify22(self,source=None,extra_delta=0,sha=None):
        source=source or self.source
        return verify_packet_22(
            self.original,source,
            original_sha256=self.sha(self.original),
            source_sha256=sha or self.sha(source),
            owner=self.OWNER,class_sha256=self.original_class_sha,
            first_six_kwargs={
                "signed_short":"signed16","raw_int":"raw32",
                "float_reader":"nextFloat",
                "alternate_raw_int":"raw32Second",
                "unsigned_short":"unsigned16",
                "unsigned_byte":"unsigned8",
                "bytes_field":"buffer","cursor_field":"cursor",
                "expected_raw_int_instructions":self.raw_count,
                "expected_unsigned_short_instructions":self.o_count,
                "expected_unsigned_byte_instructions":self.y_count,
            },
            expected_legacy=self.instructions,
            expected_extra=self.additional_instructions+extra_delta)

    def test_22_selected_original_source_methods_recompile(self):
        report=self.verify22()
        self.assertEqual(22,report["verified_original_method_bodies"])
        self.assertEqual(self.instructions+self.additional_instructions,
                         report["verified_original_jvm_instructions"])
        self.assertFalse(report["complete_packet_recovered"])
        self.assertFalse(report["canonical_source_tree_modified"])
        self.assertFalse(report["original_class_binary_used_as_dependency"])

    def test_modified_new_method_code_rejected(self):
        body=self.java(original=False)
        self.assertIn("return 42;",body)
        candidate=self.zip_source(
            "changed-cursor-source.zip",body.replace("return 42;","return 41;"))
        with self.assertRaises(ValueError):
            self.verify22(source=candidate)

    def test_changed_jvm_instruction_count_or_zip_hash_rejected(self):
        with self.assertRaises(ValueError):
            self.verify22(extra_delta=1)
        with self.assertRaises(ValueError):
            self.verify22(sha="0"*64)


if __name__=="__main__":
    unittest.main()
