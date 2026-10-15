"""R171: synthetic javac-to-original JVM Packet six-method parity and vetoes."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_packet_six_readers_r171 import (
    R171SixPacketMethodsError,
    verify_original_packet_six_readers,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "JDK required for original Packet Java proof")
class R171SixPacketReadMethodsTests(unittest.TestCase):
    OWNER="rs/demo/Packet"

    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root=Path(td.name)
        self.original=self.build_original()
        self.source=self.zip_source("candidate.zip",self.java(original=False))
        with ZipFile(self.original) as z:
            data=z.read(self.OWNER+".class")
        self.original_class_sha=hashlib.sha256(data).hexdigest()
        profile=profile_class_field_accesses(data)
        self.instructions=sum(
            len(m["instructions"]) for m in profile["methods"]
            if (m["name"],m["descriptor"]) in {
                ("signed16","()I"),("raw32","()I"),("nextFloat","()F"),
                ("raw32Second","()I"),("unsigned16","()I"),
                ("unsigned8","()I")})
        self.raw_count=self.length(profile,"raw32")
        self.o_count=self.length(profile,"unsigned16")
        self.y_count=self.length(profile,"unsigned8")

    @staticmethod
    def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

    @staticmethod
    def length(profile,name):
        return next(len(m["instructions"]) for m in profile["methods"]
                    if m["name"]==name and m["descriptor"]=="()I")

    @staticmethod
    def java(*,original,wrong_o=False,wrong_y=False,wrong_p=False):
        o_shift="7" if wrong_o else "8"
        y_source=("this.buffer[this.cursor++]"
                  if wrong_y else "this.buffer[this.cursor++] & 255")
        p_last=("this.buffer[this.cursor-2]"
                if wrong_p else "this.buffer[this.cursor-1]")
        return (
            "package rs.demo;public class Packet{"
            "public byte[] buffer;public int cursor;"
            "public int signed16(){this.cursor+=2;"
            "int n=((this.buffer[this.cursor-2]&255)<<8)"
            "+(this.buffer[this.cursor-1]&255);"
            "if(n>32767)n-=65536;return n;}"
            "public int raw32(){this.cursor+=4;"
            "return ((this.buffer[this.cursor-4]&255)<<24)"
            "+((this.buffer[this.cursor-3]&255)<<16)"
            "+((this.buffer[this.cursor-2]&255)<<8)"
            "+(this.buffer[this.cursor-1]&255);}"
            "public float nextFloat(){return Float.intBitsToFloat(this.raw32());}"
            "public int raw32Second(){this.cursor+=4;"
            "return ((this.buffer[this.cursor-4]&255)<<24)"
            "+((this.buffer[this.cursor-3]&255)<<16)"
            "+((this.buffer[this.cursor-2]&255)<<8)"
            "+("+p_last+"&255);}"
            "public int unsigned16(){this.cursor+=2;"
            "return ((this.buffer[this.cursor-2]&255)<<"+o_shift+")"
            "+(this.buffer[this.cursor-1]&255);}"
            "public int unsigned8(){return "+y_source+";}"
            "public int unverified(){return "+
            ("7" if original else "42")+";}"
            "}")

    def build_original(self):
        classes=self.root/"original-classes";classes.mkdir()
        source=self.root/"original-src"/(self.OWNER+".java")
        source.parent.mkdir(parents=True)
        source.write_text(self.java(original=True))
        p=subprocess.run(
            [shutil.which("javac"),"--release","9","-proc:none","-g:none",
             "-d",str(classes),str(source)],capture_output=True)
        self.assertEqual(0,p.returncode,p.stderr.decode(errors="replace"))
        jar=self.root/"original.jar"
        with ZipFile(jar,"w") as z:
            z.write(classes/(self.OWNER+".class"),self.OWNER+".class")
        return jar

    def zip_source(self,name,text):
        file=self.root/name
        with ZipFile(file,"w") as archive:
            archive.writestr("src/main/java/"+self.OWNER+".java",text)
        return file

    def proof(self,source=None,sha=None,extra=0):
        source=source or self.source
        return verify_original_packet_six_readers(
            self.original,source,
            original_sha256=self.sha(self.original),
            private_source_sha256=sha or self.sha(source),
            original_owner=self.OWNER,
            original_class_sha256=self.original_class_sha,
            signed_short="signed16",raw_int="raw32",
            float_reader="nextFloat",alternate_raw_int="raw32Second",
            unsigned_short="unsigned16",unsigned_byte="unsigned8",
            bytes_field="buffer",cursor_field="cursor",
            expected_instructions=self.instructions+extra,
            expected_raw_int_instructions=self.raw_count,
            expected_unsigned_short_instructions=self.o_count,
            expected_unsigned_byte_instructions=self.y_count)

    def test_all_six_readers_exact_with_unselected_different_source(self):
        r=self.proof()
        self.assertEqual(6,r["exact_original_method_bodies_verified"])
        self.assertEqual(self.instructions,r["exact_original_jvm_instructions_matched"])
        self.assertTrue(r["both_original_32bit_reader_bodies_verified"])
        self.assertTrue(r["float_reader_calls_verified_original_32bit_source"])
        self.assertFalse(r["entire_original_packet_class_java_recovered"])
        self.assertFalse(r["partial_packet_added_to_canonical_source_tree"])

    def test_unsigned_shift_cursor_mask_or_second_raw_int_mutation_refused(self):
        for name,kw in [
            ("wrong-16.zip",{"wrong_o":True}),
            ("wrong-8.zip",{"wrong_y":True}),
            ("wrong-raw.zip",{"wrong_p":True})]:
            with self.subTest(name=name):
                file=self.zip_source(name,self.java(original=False,**kw))
                with self.assertRaises(ValueError):
                    self.proof(file)

    def test_pinned_original_and_method_count_guards(self):
        with self.assertRaises(R171SixPacketMethodsError):
            self.proof(sha="0"*64)
        with self.assertRaises(ValueError):
            self.proof(extra=1)

    def test_source_only_unsigned_readers_and_cursor(self):
        classes=self.root/"runtime-classes";classes.mkdir()
        source=self.root/"runtime-src"/(self.OWNER+".java")
        source.parent.mkdir(parents=True)
        source.write_text(self.java(original=False))
        harness=self.root/"runtime-src"/"PacketRuntime.java"
        harness.write_text(
            "import rs.demo.Packet;"
            "public final class PacketRuntime{"
            "static void ok(boolean x){if(!x)throw new AssertionError();}"
            "public static void main(String[] x){"
            "for(int n:new int[]{0,1,0x12345678,-1,0x80000000}){"
            "byte[] b={99,(byte)(n>>>24),(byte)(n>>>16),"
            "(byte)(n>>>8),(byte)n,77};"
            "Packet p=new Packet();p.buffer=b;p.cursor=1;"
            "ok(p.raw32Second()==n);ok(p.cursor==5);}"
            "for(int n:new int[]{0,1,32767,32768,65535}){"
            "byte[] b={99,(byte)(n>>>8),(byte)n,77};"
            "Packet p=new Packet();p.buffer=b;p.cursor=1;"
            "ok(p.unsigned16()==n);ok(p.cursor==3);}"
            "for(int n:new int[]{0,1,127,128,255}){"
            "Packet p=new Packet();p.buffer=new byte[]{99,(byte)n,77};"
            "p.cursor=1;ok(p.unsigned8()==n);ok(p.cursor==2);}"
            "System.out.print(\"R171_SYNTHETIC_RUNTIME_PASS\");}}")
        p=subprocess.run(
            [shutil.which("javac"),"--release","9","-proc:none",
             "-g:none","-d",str(classes),str(source),str(harness)],
            capture_output=True)
        self.assertEqual(0,p.returncode,p.stderr.decode(errors="replace"))
        result=subprocess.run(
            [shutil.which("java"),"-cp",str(classes),"PacketRuntime"],
            capture_output=True,timeout=15)
        self.assertEqual(0,result.returncode,
                         result.stderr.decode(errors="replace"))
        self.assertIn("R171_SYNTHETIC_RUNTIME_PASS",
                      result.stdout.decode())


if __name__=="__main__":
    unittest.main()
