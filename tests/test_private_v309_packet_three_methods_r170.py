"""R170 synthetic source-only exact JVM Packet short/raw32/float method proofs."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_packet_three_methods_r170 import (
    R170PacketThreeSourceError, verify_original_packet_B_r_s)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "Actual Java 9-compatible JDK required")
class R170PacketThreeMethodTests(unittest.TestCase):
    OWNER="rs/demo/Packet"

    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root=Path(td.name)
        self.original=self._original()
        self.source=self._zip("candidate.zip",self.java_code(original=False))
        with ZipFile(self.original) as jar:
            data=jar.read(self.OWNER+".class")
        self.owner_sha=hashlib.sha256(data).hexdigest()
        profile=profile_class_field_accesses(data)
        self.opcodes=sum(
            len(m["instructions"]) for m in profile["methods"]
            if (m["name"],m["descriptor"]) in
            {("signed16","()I"),("raw32","()I"),("nextFloat","()F")})
        self.raw_count=next(
            len(m["instructions"]) for m in profile["methods"]
            if (m["name"],m["descriptor"])==("raw32","()I"))

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @staticmethod
    def java_code(*,original,wrong_int_shift=False,
                  wrong_float=False,wrong_byte_order=False):
        unsigned16=("7" if wrong_int_shift else "8")
        raw=("this.buffer[this.cursor-1]" if wrong_byte_order
             else "this.buffer[this.cursor-4]")
        float_expr=("return 0f;" if wrong_float else
                    "return Float.intBitsToFloat(this.raw32());")
        return (
            "package rs.demo;public class Packet{"
            "public byte[] buffer;public int cursor;"
            "public int signed16(){"
            "this.cursor+=2;"
            "int n=((this.buffer[this.cursor-2]&255)<<"+unsigned16+")"
            "+(this.buffer[this.cursor-1]&255);"
            "if(n>32767)n-=65536;return n;}"
            "public int raw32(){this.cursor+=4;"
            "return (("+raw+"&255)<<24)"
            "+((this.buffer[this.cursor-3]&255)<<16)"
            "+((this.buffer[this.cursor-2]&255)<<8)"
            "+(this.buffer[this.cursor-1]&255);}"
            "public float nextFloat(){"+float_expr+"}"
            "public int notYetRecovered(){return "+
            ("17" if original else "99")+";}"
            "}")

    def _original(self):
        classes=self.root/"original-classes"
        classes.mkdir()
        source=self.root/"original-src"/(self.OWNER+".java")
        source.parent.mkdir(parents=True)
        source.write_text(self.java_code(original=True),encoding="utf-8")
        result=subprocess.run(
            [shutil.which("javac"),"--release","9","-g:none","-proc:none",
             "-d",str(classes),str(source)],capture_output=True)
        self.assertEqual(0,result.returncode,
                         result.stderr.decode(errors="replace"))
        archive=self.root/"original.jar"
        with ZipFile(archive,"w") as jar:
            jar.write(classes/(self.OWNER+".class"),self.OWNER+".class")
        return archive

    def _zip(self,name,body):
        zpath=self.root/name
        with ZipFile(zpath,"w") as z:
            z.writestr("src/main/java/"+self.OWNER+".java",body)
        return zpath

    def prove(self,source=None,*,source_hash=None,opcode_drift=0):
        source=source or self.source
        return verify_original_packet_B_r_s(
            self.original,source,
            original_sha256=self.sha(self.original),
            private_packet_sha256=source_hash or self.sha(source),
            original_owner=self.OWNER,
            original_class_sha256=self.owner_sha,
            signed_short="signed16",raw_int="raw32",
            float_reader="nextFloat",
            bytes_field="buffer",position_field="cursor",
            expected_instructions=self.opcodes+opcode_drift,
            expected_raw_int_instructions=self.raw_count)

    def test_all_three_original_jvm_method_bodies_and_closed_call(self):
        x=self.prove()
        self.assertEqual(3,x["original_selected_java_method_count"])
        self.assertEqual(self.opcodes,x["selected_original_jvm_instructions_matched"])
        self.assertEqual(self.raw_count,
                         x["original_32bit_reader_jvm_instructions_matched"])
        self.assertTrue(x["selected_java_source_self_call_closed"])
        self.assertFalse(x["complete_original_packet_java_source_accepted"])
        self.assertFalse(x["add_partial_packet_source_to_canonical_client_tree"])
        self.assertFalse(x["original_client_binary_compiler_fallback_used"])

    def test_modified_short_raw_byte_order_or_float_wrapper_rejected(self):
        tests=[
            ("bad-short.zip",dict(wrong_int_shift=True)),
            ("bad-raw32.zip",dict(wrong_byte_order=True)),
            ("bad-float.zip",dict(wrong_float=True))]
        for name,options in tests:
            with self.subTest(name=name):
                mutated=self._zip(name,self.java_code(original=False,**options))
                with self.assertRaises(ValueError):
                    self.prove(mutated)

    def test_strict_sha_and_instruction_counts(self):
        with self.assertRaises(R170PacketThreeSourceError):
            self.prove(source_hash="0"*64)
        with self.assertRaises(ValueError):
            self.prove(opcode_drift=1)

    def test_compiled_source_runtime_byte_order_bits_and_cursor(self):
        java_source=self.root/"java"/(self.OWNER+".java")
        java_source.parent.mkdir(parents=True)
        java_source.write_text(self.java_code(original=False),encoding="utf-8")
        harness=self.root/"java"/"PacketRuntime.java"
        harness.write_text(
            "import rs.demo.Packet;"
            "public class PacketRuntime {"
            "static void yes(boolean b){if(!b)throw new AssertionError();}"
            "public static void main(String[] a){"
            "int[] bits={0,1,-1,0x80000000,0x7f800000,"
            "0x7fc00001,0x3f800000,0x12345678};"
            "for(int v:bits){Packet p=new Packet();"
            "p.buffer=new byte[]{17,(byte)(v>>>24),(byte)(v>>>16),"
            "(byte)(v>>>8),(byte)v,19};p.cursor=1;"
            "yes(p.raw32()==v);yes(p.cursor==5);p.cursor=1;"
            "yes(Float.floatToRawIntBits(p.nextFloat())==v);"
            "yes(p.cursor==5);}"
            "int[] shorts={0,1,32767,32768,65535,0x1234};"
            "for(int v:shorts){Packet p=new Packet();"
            "p.buffer=new byte[]{17,(byte)(v>>>8),(byte)v,19};"
            "p.cursor=1;yes(p.signed16()==(short)v);"
            "yes(p.cursor==3);}"
            "System.out.print(\"R170_SYNTHETIC_RUNTIME_PASS\");}}",
            encoding="utf-8")
        classes=self.root/"runtime-classes"
        classes.mkdir()
        run=subprocess.run([
            shutil.which("javac"),"--release","9","-proc:none",
            "-g:none","-d",str(classes),str(java_source),str(harness)],
            capture_output=True)
        self.assertEqual(0,run.returncode,run.stderr.decode(errors="replace"))
        execute=subprocess.run([
            shutil.which("java"),"-cp",str(classes),"PacketRuntime"],
            capture_output=True,timeout=15)
        self.assertEqual(0,execute.returncode,
                         execute.stderr.decode(errors="replace"))
        self.assertIn("R170_SYNTHETIC_RUNTIME_PASS",
                      execute.stdout.decode())


if __name__=="__main__":
    unittest.main()
