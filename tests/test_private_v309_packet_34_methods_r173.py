"""R173 synthetic: 12 additional byte writer method compilation tests.

All hosted sources are independent synthetic examples, never the private
original-v309 Packet Java source.
"""
from zipfile import ZipFile
import unittest
from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_packet_34_methods_r173 import (
    WRITERS,verify_packet_34)
from test_private_v309_packet_22_methods_r172 import (
    R172PacketAdditionalMethodsTests)


class R173PacketWriterTests(R172PacketAdditionalMethodsTests):
    @staticmethod
    def java(*,original,wrong_o=False,wrong_y=False,wrong_p=False):
        base=R172PacketAdditionalMethodsTests.java(
            original=original,wrong_o=wrong_o,
            wrong_y=wrong_y,wrong_p=wrong_p)
        # Synthetic, deliberately DIFFERENT body shapes from original Packet.
        body="".join(
            "public void "+name+"(int x){"
            "this.buffer[this.cursor++]=(byte)(x+"+str(index+1)+");}"
            for index,name in enumerate(
                ("b","d","e","f","h","i","j","l","m","n","o","p")))
        return base[:-1]+body+"}"

    def setUp(self):
        super().setUp()
        with ZipFile(self.original) as jar:
            raw=jar.read(self.OWNER+".class")
        profile=profile_class_field_accesses(raw)
        lookup={(m["name"],m["descriptor"]):m for m in profile["methods"]}
        self.writer_count=sum(len(lookup[key]["instructions"])
                              for key in WRITERS)

    def verify34(self,source=None,writer_drift=0,sha=None):
        source=source or self.source
        return verify_packet_34(
            self.original,source,
            original_sha256=self.sha(self.original),
            source_sha256=sha or self.sha(source),
            owner=self.OWNER,class_sha256=self.original_class_sha,
            first_six_kwargs={
                "signed_short":"signed16","raw_int":"raw32",
                "float_reader":"nextFloat",
                "alternate_raw_int":"raw32Second",
                "unsigned_short":"unsigned16","unsigned_byte":"unsigned8",
                "bytes_field":"buffer","cursor_field":"cursor",
                "expected_raw_int_instructions":self.raw_count,
                "expected_unsigned_short_instructions":self.o_count,
                "expected_unsigned_byte_instructions":self.y_count,
                "base_six_instruction_count":self.instructions,
            },
            legacy=self.instructions+self.additional_instructions,
            writes=self.writer_count+writer_drift)

    def test_all_original_selected_byte_writer_code_matches(self):
        report=self.verify34()
        self.assertEqual(34,report["verified_selected_packet_methods"])
        self.assertEqual(12,report["new_original_byte_writer_methods"])
        self.assertEqual(self.instructions+self.additional_instructions+
                         self.writer_count,
                         report["original_jvm_instructions_matched"])
        self.assertFalse(report["full_packet_class_recovered"])

    def test_modified_single_writer_source_refused(self):
        source=self.java(original=False)
        self.assertIn("x+3",source)
        altered=self.zip_source(
            "altered-writer.zip",source.replace("x+3","x+101",1))
        with self.assertRaises(ValueError):
            self.verify34(source=altered)

    def test_wrong_sha_or_original_instruction_count_rejected(self):
        with self.assertRaises(ValueError):
            self.verify34(sha="0"*64)
        with self.assertRaises(ValueError):
            self.verify34(writer_drift=1)


if __name__=="__main__":
    unittest.main()
