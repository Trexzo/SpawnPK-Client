"""R167: synthetic original quaternion source with pool lock, math and equality."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_original_quaternion_source_r167 import (
    verify_original_quaternion_java,verify_and_overlay_quaternion,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("javap"),
                     "Real source compilation required")
class R167OriginalQuaternionSourceTests(unittest.TestCase):
    OWNER="example/Quat"

    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.original=self.compile_original()
        self.candidate=self.source_zip("candidate.zip",self.java())
        self.prior=self.root/"private-prior.zip"
        with ZipFile(self.prior,"w") as z:
            z.writestr("recovered-source/v309/src/rs/Client.java",
                       "package rs;public class Client{}")
        with ZipFile(self.original) as z:
            raw=z.read(self.OWNER+".class")
        self.original_owner_sha=hashlib.sha256(raw).hexdigest()
        p=profile_class_field_accesses(raw)
        self.methods=len(p["methods"])
        self.opcodes=sum(len(m["instructions"]) for m in p["methods"])

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @staticmethod
    def java(*,different_math=False,different_concat=False,different_pool=False):
        op="+" if different_math else "-"
        punct=";" if different_concat else ","
        # Synthetic-only: deliberately not SpawnPK original source.
        acquire="pool[n--]" if different_pool else "pool[--n]"
        return (
            "package example;public final class Quat{"
            "public static Quat[] pool = new Quat[0];"
            "public static int capacity=4;public static int n;"
            "float x,y,z,w;"
            "static {pool=new Quat[4];n=0;new Quat();}"
            "public static Quat acquire(){synchronized(pool){"
            "if(n==0)return new Quat();"
            +acquire+".reset();return pool[n];}}"
            "public void release(){synchronized(pool){"
            "if(n<capacity-1)pool[++n-1]=this;}}"
            "public Quat(){this.reset();}"
            "void set(float a,float b,float c,float d){"
            "x=a;y=b;z=c;w=d;}"
            "public void axis(float a,float b,float c,float radians){"
            "float s=(float)Math.sin((double)(radians*0.5F));"
            "float cos=(float)Math.cos((double)(radians*0.5F));"
            "this.x=a*s;this.y=b*s;this.z=c*s;this.w=cos;}"
            "public final void reset(){x=y=z=0f;w=1f;}"
            "public final void combine(Quat o){"
            "this.set(this.x*o.w+o.x*this.w,"
            "this.y*o.w+this.w*o.y,"
            "this.z*o.w+this.w*o.z,"
            "this.w*o.w"+op+"this.x*o.x);}"
            "public boolean equals(Object o){"
            "if(!(o instanceof Quat))return false;"
            "Quat q=(Quat)o;return q.x==x&&q.y==y&&q.z==z&&q.w==w;}"
            "public int hashCode(){float s=1f;"
            "s=s*31f+x;s=s*31f+y;s=s*31f+z;s=s*31f+w;"
            "return (int)s;}"
            "public String toString(){return \"\"+x+\""+punct+"\"+y"
            "+\""+punct+"\"+z+\""+punct+"\"+w;}"
            "}")

    def compile_original(self):
        java=self.root/"original-src"/(self.OWNER+".java")
        java.parent.mkdir(parents=True)
        java.write_text(self.java(),encoding="utf8")
        out=self.root/"original-classes"
        out.mkdir()
        p=subprocess.run([shutil.which("javac"),"--release","9",
                          "-proc:none","-g:none","-d",str(out),str(java)],
                         capture_output=True)
        self.assertEqual(0,p.returncode,p.stderr.decode(errors="replace"))
        jar=self.root/"original.jar"
        with ZipFile(jar,"w") as z:
            z.write(out/(self.OWNER+".class"),self.OWNER+".class")
        return jar

    def source_zip(self,name,contents):
        path=self.root/name
        with ZipFile(path,"w") as z:
            z.writestr("src/main/java/"+self.OWNER+".java",contents)
        return path

    def verify(self,source=None,sha=None):
        source=source or self.candidate
        return verify_original_quaternion_java(
            self.original,source,
            original_sha256=self.sha(self.original),
            quaternion_source_sha256=sha or self.sha(source),
            owner=self.OWNER,
            original_class_sha256=self.original_owner_sha,
            expected_methods=self.methods,
            expected_fields=7,
            expected_instructions=self.opcodes)

    def test_complete_quaternion_pool_methods_and_string_concat(self):
        p=self.verify()
        self.assertEqual(11,p["original_jvm_method_count"])
        self.assertEqual(7,p["original_field_count"])
        self.assertEqual(self.opcodes,p["original_jvm_instruction_count"])
        self.assertTrue(p["pool_acquire_release_monitor_and_handlers_checked_in_code"])
        self.assertTrue(p["original_string_concat_bootstrap_equal"])
        self.assertFalse(p["complete_client_source_compilation_verified"])

    def test_modified_quaternion_multiply_rejected(self):
        bad=self.source_zip("wrong-multiply.zip",self.java(different_math=True))
        with self.assertRaises(ValueError):
            self.verify(bad)

    def test_modified_pool_index_rejected(self):
        bad=self.source_zip("wrong-pool.zip",self.java(different_pool=True))
        with self.assertRaises(ValueError):
            self.verify(bad)

    def test_changed_concat_bootstrap_rejected(self):
        bad=self.source_zip("wrong-string.zip",self.java(different_concat=True))
        with self.assertRaises(ValueError):
            self.verify(bad)

    def test_private_source_overlay_requires_full_java_proof(self):
        report=verify_and_overlay_quaternion(
            self.original,self.candidate,self.prior,
            self.root/"fresh-private.zip",
            original_sha256=self.sha(self.original),
            quaternion_source_sha256=self.sha(self.candidate),
            prior_canonical_sha256=self.sha(self.prior),
            owner=self.OWNER,
            original_class_sha256=self.original_owner_sha,
            expected_methods=self.methods,expected_fields=7,
            expected_instructions=self.opcodes,
            expected_prior_java=1)
        self.assertEqual(2,report["private_source_overlay"][
            "new_client_java_file_count"])
        self.assertFalse(report["full_original_v309_client_compiled"])
        with ZipFile(self.root/"fresh-private.zip") as z:
            self.assertIn("recovered-source/v309/src/"+self.OWNER+".java",
                          z.namelist())


if __name__=="__main__":
    unittest.main()
