"""R176: independently compiled synthetic 61-method Packet source checks."""
import unittest
from zipfile import ZipFile
from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_packet_61_methods_r176 import (
    verify_packet_61, ADDED)
from test_private_v309_packet_49_methods_r175 import (
    R175PacketAdditionalReaderTests)


class R176PacketBufferStringTests(R175PacketAdditionalReaderTests):
    @staticmethod
    def java(*,original,wrong_o=False,wrong_y=False,wrong_p=False):
        base=R175PacketAdditionalReaderTests.java(
            original=original,wrong_o=wrong_o,
            wrong_y=wrong_y,wrong_p=wrong_p)
        # Synthetic test methods, not copied from the original client.
        more=(
            "public int g(){return this.cursor+123;}"
            "public long E(){long x=this.D()&4294967295L;"
            "long y=this.D()&4294967295L;return (x<<32)+y;}"
            "public String w(){return \"hello\"+this.cursor;}"
            "public String F(){return \"world\"+this.cursor;}"
            "public void G(){this.cursor++;}"
            "public void I(){this.cursor+=2;}"
            "public byte[] H(){return new byte[]{1,2,3};}"
            "public void a(byte[] x,int count,int offset){"
            "for(int i=offset;i<offset+count;i++)this.buffer[this.cursor++]=x[i];}"
            "public void a(int length,int offset,byte[] dst){"
            "for(int i=offset;i<offset+length;i++)dst[i]=this.buffer[this.cursor++];}"
            "public void a(int start,byte[] src,int length){"
            "for(int i=start+length-1;i>=start;i--)this.buffer[this.cursor++]=src[i];}"
            "public void b(int len,int start,byte[] dst){"
            "for(int i=start;i<start+len;i++)dst[i]=this.buffer[this.cursor++];}"
            "public final void b(byte[] dst,int start,int count){"
            "for(int i=start;i<count+start;i++)dst[i]=this.buffer[this.cursor++];}"
        )
        return base[:-1]+more+"}"

    def setUp(self):
        super().setUp()
        with ZipFile(self.original) as z:
            raw=z.read(self.OWNER+".class")
        index={(m["name"],m["descriptor"]):m
               for m in profile_class_field_accesses(raw)["methods"]}
        self.additional_count=sum(
            len(index[x]["instructions"]) for x in ADDED)

    def verify61(self,source=None,sha=None,count_delta=0):
        source=source or self.source
        return verify_packet_61(
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
            legacy=(self.instructions+self.additional_instructions+
                    self.writer_count+self.endian_count+self.new_count),
            new_count=self.additional_count+count_delta,
            first_six=self.instructions,
            prior_endian=self.endian_count,
            prior_twenty_two=self.instructions+self.additional_instructions,
            prior_six_new_instructions=self.new_count,
            expected_calls=5)

    def test_61_original_member_bodies_match_source_only_java(self):
        report=self.verify61()
        self.assertEqual(61,report["selected_packet_method_bodies"])
        self.assertEqual(12,report["new_original_methods"])
        self.assertEqual(5,report["selected_original_self_calls_closed"])
        self.assertFalse(report["original_packet_class_complete"])
        self.assertFalse(report["original_binary_compiler_fallback"])

    def test_new_method_mutation_rejected(self):
        original=self.java(original=False)
        self.assertIn("this.cursor+123",original)
        mutated=self.zip_source(
            "wrong-buffer-read.zip",
            original.replace("this.cursor+123","this.cursor+124"))
        with self.assertRaises(ValueError):
            self.verify61(source=mutated)

    def test_source_hash_and_count_guards(self):
        with self.assertRaises(ValueError):
            self.verify61(sha="0"*64)
        with self.assertRaises(ValueError):
            self.verify61(count_delta=1)


if __name__=="__main__":
    unittest.main()
