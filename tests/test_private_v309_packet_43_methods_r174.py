"""R174: original-method coverage test with independent synthetic JVM owners.

Build 43 selected methods from Java 9 twice and compare original method
Code. All source samples here are generic, not SpawnPK original Java.
"""
from zipfile import ZipFile
import unittest

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_packet_43_methods_r174 import (
    READERS, verify_packet_43)
from test_private_v309_packet_34_methods_r173 import (
    R173PacketWriterTests)


class R174PacketEndianReaderTests(R173PacketWriterTests):
    @staticmethod
    def java(*,original,wrong_o=False,wrong_y=False,wrong_p=False):
        base=R173PacketWriterTests.java(
            original=original,wrong_o=wrong_o,
            wrong_y=wrong_y,wrong_p=wrong_p)
        extra=(
            "public int S(){return this.cursor+this.buffer[this.cursor];}"
            "public int T(){return (this.buffer[this.cursor]&255)+128;}"
            "public int U(){return (this.buffer[this.cursor++]&255)<<8;}"
            "public int V(){return this.cursor*3;}"
            "public int W(){return this.buffer[this.cursor++]&255;}"
            "public int X(){return this.cursor+1;}"
            "public int Y(){return this.cursor-1;}"
            "public int C(){return this.buffer[this.cursor]&31;}"
            "public int D(){return this.buffer[this.cursor]&63;}"
        )
        return base[:-1]+extra+"}"

    def setUp(self):
        super().setUp()
        with ZipFile(self.original) as z:
            raw=z.read(self.OWNER+".class")
        p=profile_class_field_accesses(raw)
        lookup={(m["name"],m["descriptor"]):m for m in p["methods"]}
        self.endian_count=sum(
            len(lookup[key]["instructions"]) for key in READERS)

    def verify43(self,source=None,expected_delta=0,source_hash=None):
        source=source or self.source
        return verify_packet_43(
            self.original,source,
            original_sha256=self.sha(self.original),
            source_sha256=source_hash or self.sha(source),
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
            previous_count=self.instructions+self.additional_instructions+
                           self.writer_count,
            new_count=self.endian_count+expected_delta,
            previous_22_count=self.instructions+self.additional_instructions,
            initial_six=self.instructions)

    def test_all_43_original_selected_methods_recompiled(self):
        r=self.verify43()
        self.assertEqual(43,r["selected_original_java_method_count"])
        self.assertEqual(9,r["new_original_reader_method_count"])
        self.assertEqual(self.endian_count,
                         r["new_matching_original_jvm_instructions"])
        self.assertFalse(r["original_packet_class_complete"])
        self.assertFalse(r["canonical_client_source_tree_modified"])
        self.assertFalse(r["derived_source_publication_authorized"])

    def test_endian_method_mutation_is_refused(self):
        body=self.java(original=False)
        self.assertIn("return this.cursor*3;",body)
        bad=self.zip_source("mutated-endian.zip",
            body.replace("return this.cursor*3;",
                         "return this.cursor*5;"))
        with self.assertRaises(ValueError):
            self.verify43(source=bad)

    def test_changed_source_hash_and_expected_opcode_count_refused(self):
        with self.assertRaises(ValueError):
            self.verify43(source_hash="0"*64)
        with self.assertRaises(ValueError):
            self.verify43(expected_delta=1)


if __name__=="__main__":
    unittest.main()
