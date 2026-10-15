"""R175 synthetic original Java 49-method source parity and call-closure tests."""
from zipfile import ZipFile
import unittest
from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_packet_49_methods_r175 import (
    NEW,verify_packet_49)
from test_private_v309_packet_43_methods_r174 import (
    R174PacketEndianReaderTests)


class R175PacketAdditionalReaderTests(R174PacketEndianReaderTests):
    @staticmethod
    def java(*,original,wrong_o=False,wrong_y=False,wrong_p=False):
        base=R174PacketEndianReaderTests.java(
            original=original,wrong_o=wrong_o,wrong_y=wrong_y,wrong_p=wrong_p)
        extra=(
            "public int l(){return this.buffer[this.cursor]&15;}"
            "public int m(){return this.cursor+101;}"
            "public int q(){return this.cursor*7;}"
            "public int u(){return this.buffer[this.cursor++]&127;}"
            "public int x(){return this.cursor-2;}"
            "public int t(){if(this.cursor<2)return this.unsigned8();"
            "return this.unsigned16();}"
        )
        return base[:-1]+extra+"}"

    def setUp(self):
        super().setUp()
        with ZipFile(self.original) as z:
            raw=z.read(self.OWNER+".class")
        profile=profile_class_field_accesses(raw)
        index={(m["name"],m["descriptor"]):m for m in profile["methods"]}
        self.new_count=sum(len(index[k]["instructions"]) for k in NEW)

    def verify49(self,source=None,source_hash=None,count_delta=0):
        source=source or self.source
        return verify_packet_49(
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
            old_count=self.instructions+self.additional_instructions+
                      self.writer_count+self.endian_count,
            new_count=self.new_count+count_delta,
            first_six=self.instructions,self_call_edges=3)

    def test_49_selected_packet_java_method_bodies_match(self):
        r=self.verify49()
        self.assertEqual(49,r["private_v309_packet_selected_method_count"])
        self.assertEqual(6,r["new_exact_original_method_bodies"])
        self.assertEqual(3,r["same_original_self_call_edges_closed"])
        self.assertFalse(r["complete_original_packet_restored"])
        self.assertFalse(r["original_binary_compiler_fallback_used"])

    def test_changed_new_method_expression_refused(self):
        source=self.java(original=False)
        self.assertIn("this.cursor*7",source)
        altered=self.zip_source(
            "changed-extra-reader.zip",
            source.replace("this.cursor*7","this.cursor*9"))
        with self.assertRaises(ValueError):
            self.verify49(source=altered)

    def test_changed_sha_and_opcode_count_refused(self):
        with self.assertRaises(ValueError):
            self.verify49(source_hash="0"*64)
        with self.assertRaises(ValueError):
            self.verify49(count_delta=1)


if __name__=="__main__":
    unittest.main()
