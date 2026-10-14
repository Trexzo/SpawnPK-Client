"""R161: constructor and packet loader with Java-only original game signatures."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_matrix_packet_source_r161 import (
    R161MatrixPacketSourceError, verify_original_packet_loader_java)


@unittest.skipUnless(shutil.which("java") and shutil.which("javac"),
                     "Actual JDK required")
class R161MatrixPacketSourceTests(unittest.TestCase):
    OWNER="ext/Matrix"
    PACKET="rs/Packet"

    def setUp(self):
        scope=tempfile.TemporaryDirectory()
        self.addCleanup(scope.cleanup)
        self.root=Path(scope.name)
        self.original=self.make_original()
        self.java=self.archive("matrix-java.zip", {
            "ext/Matrix.java":self.matrix_java(known_original=False)})
        self.helpers=self.archive("source-scaffolds.zip", {
            "rs/Packet.java":"package rs; public class Packet {"
               "public int readShort(){return 0;}"
               "public float readFloat(){return 0f;}}",
            "ext/Components.java":"package ext;public class Components {"
               "public float x;public Components(){} }",
            "ext/Converter.java":"package ext;public class Converter {"
               "public static float decode(int n){return 0f;}}",
        })
        self.manifest=self.root/"members.json"
        self.members=[("<init>","(Lrs/Packet;Z)V"),
                      ("load","(Lrs/Packet;Z)V"),
                      ("apply","(Lext/Components;)V")]
        self.manifest.write_text(json.dumps([
            {"name":a,"descriptor":b} for a,b in self.members]))
        with ZipFile(self.original) as z:
            raw=z.read("ext/Matrix.class")
        self.original_matrix_sha=hashlib.sha256(raw).hexdigest()
        profile=profile_class_field_accesses(raw)
        self.original_ops=sum(len(m["instructions"]) for m in profile["methods"]
                              if (m["name"],m["descriptor"]) in self.members)

    @staticmethod
    def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @staticmethod
    def matrix_java(*,known_original,wrong_index=False):
        index="1" if wrong_index else "0"
        return (
            "package ext;public class Matrix {public float[] e;"
            "public Matrix(rs.Packet p,boolean flag){"
            "this.e=new float[16];this.load(p,flag);}"
            "void load(rs.Packet p,boolean flag){"
            "if(flag){ext.Components c=new ext.Components();"
            "c.x=ext.Converter.decode(p.readShort());"
            "this.apply(c);}"
            "else{for(int i=0;i<16;++i){this.e[i]=p.readFloat();}}"
            "}"
            "void apply(ext.Components c){this.e["+index+"]=c.x;}"
            + ("public int unused(rs.Packet p){return p.readShort();}"
               if known_original else "")
            + "}")

    def make_original(self):
        classes=self.root/"original-classes";classes.mkdir()
        sources={
            "rs/Packet.java":"package rs;public class Packet {"
                "public int readShort(){return 9;}"
                "public float readFloat(){return 9f;}}",
            "ext/Components.java":"package ext;public class Components {"
                "public float x;public Components(){}"
                "public int unused(){return 2;}}",
            "ext/Converter.java":"package ext;public class Converter {"
                "public static float decode(int x){return x*9f;}}",
            "ext/Matrix.java":self.matrix_java(known_original=True),
        }
        for name,code in sources.items():
            target=self.root/"original-src"/name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(code)
            p=subprocess.run([
                shutil.which("javac"),"--release","9",
                "-proc:none","-g:none","-classpath",str(classes),
                "-d",str(classes),str(target)],capture_output=True)
            self.assertEqual(0,p.returncode,p.stderr.decode(errors="replace"))
        dest=self.root/"original.jar"
        with ZipFile(dest,"w") as archive:
            for path in sorted(classes.rglob("*.class")):
                archive.write(path,path.relative_to(classes).as_posix())
        return dest

    def archive(self,name,sources):
        output=self.root/name
        with ZipFile(output,"w") as z:
            for path,text in sorted(sources.items()):
                z.writestr("src/main/java/"+path,text)
        return output

    def prove(self,source=None,helpers=None,members=None,helper_sha=None):
        source=source or self.java
        helpers=helpers or self.helpers
        members=members or self.manifest
        return verify_original_packet_loader_java(
            self.original,source,helpers,members,
            original_sha256=self.sha(self.original),
            matrix_source_sha256=self.sha(source),
            helper_source_sha256=(helper_sha if helper_sha is not None
                                  else self.sha(helpers)),
            selection_sha256=self.sha(members),
            matrix_owner=self.OWNER,packet_owner=self.PACKET,
            loader_method="load",expected_matrix_sha256=self.original_matrix_sha,
            expected_methods=3,expected_instructions=self.original_ops,
            expected_helper_sources=3,expected_self_calls=2)

    def test_source_only_packet_loader_with_closed_internal_calls(self):
        p=self.prove()
        self.assertEqual(3,p["original_selected_method_count_verified"])
        self.assertEqual(self.original_ops,p["exact_selected_rebuilt_jvm_instruction_count"])
        self.assertEqual(2,p["verified_same_owner_method_edges"])
        self.assertFalse(p["original_packet_and_converter_helper_method_bodies_verified"])
        self.assertFalse(p["original_game_binary_used_for_compiler_dependencies"])
        self.assertFalse(p["complete_matrix_java_source_accepted"])

    def test_wrong_selected_matrix_body_refused(self):
        altered=self.archive("wrong-source.zip",{
            "ext/Matrix.java":self.matrix_java(known_original=False,
                                               wrong_index=True)})
        with self.assertRaises(R161MatrixPacketSourceError):
            self.prove(source=altered)

    def test_missing_packet_source_scaffold_cannot_fallback_to_binary(self):
        changed=self.archive("missing-packet.zip",{
            "ext/Components.java":"package ext;public class Components {public float x;}",
            "ext/Converter.java":"package ext;public class Converter {"
                                 "public static float decode(int x){return 0f;}}"})
        with self.assertRaises(R161MatrixPacketSourceError):
            self.prove(helpers=changed)

    def test_helper_hash_and_missing_loader_member_rejected(self):
        with self.assertRaises(R161MatrixPacketSourceError):
            self.prove(helper_sha="0"*64)
        subset=self.root/"bad-members.json"
        subset.write_text(json.dumps([{"name":"<init>",
                                       "descriptor":"(Lrs/Packet;Z)V"}]))
        with self.assertRaises(R161MatrixPacketSourceError):
            self.prove(members=subset)


if __name__=="__main__":
    unittest.main()
