"""R168: five original-named synthetic JVM math owners plus one Packet stub.

No SpawnPK proprietary source or original binaries appear in public tests.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_math_source_closure_r168 import (
    OriginalFiveMathSourceR168Error,
    verify_original_five_math_source_bundle,
)


@unittest.skipUnless(shutil.which("javac"), "Java9 capable JDK required")
class R168JointOriginalMathSourceTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.original_math=self.java_sources()
        self.original=self.compile_original()
        self.original_hashes={}
        with ZipFile(self.original) as jar:
            for n in "abcde":
                name="example/"+n
                binary=jar.read(name+".class")
                self.original_hashes[name]=hashlib.sha256(binary).hexdigest()
        self.original_methods=0
        self.original_ops=0
        with ZipFile(self.original) as jar:
            for owner in self.original_hashes:
                profile=profile_class_field_accesses(jar.read(owner+".class"))
                self.original_methods+=len(profile["methods"])
                self.original_ops+=sum(len(m["instructions"])
                                       for m in profile["methods"])
        self.sources=self.archive("math-sources.zip",{
            "example/"+k+".java":v for k,v in self.original_math.items()})
        self.packet=self.archive("packet-stub.zip",{
            "rs/x/e.java":"package rs.x;public class e{"
                "public int B(){return 0;}public float s(){return 0f;}}",
        })

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @staticmethod
    def java_sources():
        return {
            "a":("package example;public class a{float x,y,z;"
                 "public a(){x=y=z=0f;}"
                 "public void rotate(float f){float c=(float)Math.cos(f);"
                 "this.x=this.x*c-this.y*f;}"
                 "public String toString(){return \"\"+x+\",\"+y+\",\"+z;}}"),
            "b":("package example;public class b{"
                 "float[] mat=new float[16];"
                 "public b(){mat[0]=1f;mat[5]=1f;}"
                 "public void load(rs.x.e packet){mat[0]=packet.s();"
                 "mat[1]=(float)packet.B();}"
                 "public void transform(a t){mat[12]=t.x;}"
                 "public int count(){return mat.length;}}"),
            "c":("package example;public final class c{"
                 "static c[] pool=new c[2];static int n;"
                 "float x,y,z,w;"
                 "public c(){w=1f;}"
                 "public static c borrow(){synchronized(pool){"
                 "if(n==0)return new c();return pool[--n];}}"
                 "public void release(){synchronized(pool){"
                 "if(n<2)pool[n++]=this;}}"
                 "public void set(float a,float b){x=a;y=b;}}"),
            "d":("package example;public class d{"
                 "public static final int UNIT=16;"
                 "static float[] table=new float[UNIT];"
                 "static {for(int i=0;i<UNIT;i++)"
                 "table[i]=(float)Math.sin((double)i);}"
                 "public static float read(int i){return table[i&15];}}"),
            "e":("package example;public class e{"
                 "float x,y,z;"
                 "public e(float a,float b,float c){x=a;y=b;z=c;}"
                 "public float magnitude(){return"
                 "(float)Math.sqrt((double)(x*x+y*y+z*z));}}"),
        }

    def compile_original(self):
        root=self.root/"original-source"
        files=[]
        for name,body in self.original_math.items():
            file=root/("example/"+name+".java")
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text(body)
            files.append(file)
        packet=root/"rs/x/e.java"
        packet.parent.mkdir(parents=True,exist_ok=True)
        packet.write_text("package rs.x;public class e{"
                          "public int B(){return 7;}"
                          "public float s(){return 7f;}}")
        files.append(packet)
        compiled=self.root/"original-classes"
        compiled.mkdir()
        p=subprocess.run(
            [shutil.which("javac"),"--release","9","-g:none",
             "-proc:none","-d",str(compiled),*[str(f) for f in files]],
            capture_output=True)
        self.assertEqual(0,p.returncode,p.stderr.decode(errors="replace"))
        archive=self.root/"original.jar"
        with ZipFile(archive,"w") as z:
            for file in sorted(compiled.rglob("*.class")):
                z.write(file,file.relative_to(compiled).as_posix())
        return archive

    def archive(self,name,source):
        path=self.root/name
        with ZipFile(path,"w") as z:
            for entry,contents in sorted(source.items()):
                z.writestr("src/main/java/"+entry,contents)
        return path

    def prove(self,source=None,packet=None,math_sha=None):
        source=source or self.sources
        packet=packet or self.packet
        return verify_original_five_math_source_bundle(
            self.original,source,packet,
            original_sha256=self.sha(self.original),
            math_source_sha256=math_sha or self.sha(source),
            packet_source_sha256=self.sha(packet),
            original_math_owners=self.original_hashes,
            original_packet_owner="rs/x/e",
            expected_original_methods=self.original_methods,
            expected_original_instructions=self.original_ops)

    def test_all_five_compiled_together_with_source_only_packet(self):
        result=self.prove()
        self.assertEqual(5,result["five_original_reconstructed_owner_count"])
        self.assertEqual(self.original_methods,result[
            "verified_original_jvm_method_count"])
        self.assertEqual(self.original_ops,result[
            "verified_original_jvm_instruction_count"])
        self.assertTrue(result["java9_joint_original_source_only_compile_passed"])
        self.assertFalse(result[
            "compiler_only_packet_method_bodies_original_evidenced"])
        self.assertFalse(result["original_game_binary_on_compiler_classpath"])
        self.assertFalse(result["full_original_client_compiled"])

    def test_missing_original_math_file_is_rejected(self):
        altered=self.archive("four-math.zip",{
            "example/"+name+".java":value
            for name,value in self.original_math.items() if name!="e"
        })
        with self.assertRaises(OriginalFiveMathSourceR168Error):
            self.prove(source=altered)

    def test_changed_matrix_jvm_body_is_rejected(self):
        source=self.original_math.copy()
        source["b"]=source["b"].replace(
            "mat[0]=packet.s()", "mat[0]=1.0f")
        altered=self.archive("modified-matrix.zip",{
            "example/"+name+".java":value for name,value in source.items()
        })
        with self.assertRaises(ValueError):
            self.prove(source=altered)

    def test_packet_stub_must_have_original_source_identity(self):
        wrong=self.archive("wrong-packet.zip",{
            "rs/x/Unknown.java":"package rs.x;public class Unknown{}",
        })
        with self.assertRaises(OriginalFiveMathSourceR168Error):
            self.prove(packet=wrong)

    def test_changed_pinned_math_bundle_hash_rejected(self):
        with self.assertRaises(OriginalFiveMathSourceR168Error):
            self.prove(math_sha="0"*64)


if __name__=="__main__":
    unittest.main()
