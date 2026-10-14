"""R162 synthetic full original matrix JVM source equivalence, no game binaries."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_complete_matrix_java_r162 import (
    CompleteMatrixJavaR162Error, verify_complete_original_matrix_java)


@unittest.skipUnless(shutil.which("javac"), "Real JDK required")
class R162AllMatrixMethodSourceTest(unittest.TestCase):
    OWNER="ext/Matrix"
    PACKET="rs/Packet"
    IDS=[
        ("<init>","()V"),
        ("<init>","(Lrs/Packet;Z)V"),
        ("a","(Lrs/Packet;Z)V"),
        ("init","()V"),
        ("sum","()I"),
        ("<clinit>","()V"),
    ]

    def setUp(self):
        holder=tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root=Path(holder.name)
        self.original=self._original()
        self.candidate=self._archive("matrix-source.zip",
                      {"ext/Matrix.java":self.matrix_source(original=False)})
        self.helpers=self._archive("source-only-helper.zip",{
            "rs/Packet.java":"package rs;public class Packet {"
                "public int readShort(){return 0;}"
                "public float readFloat(){return 0f;}}",
            "ext/Converter.java":"package ext;public class Converter {"
                "public static float decode(int x){return 0f;}}",
        })
        self.selection=self.root/"selection.json"
        self.selection.write_text(json.dumps([
            {"name":n,"descriptor":d} for n,d in self.IDS]))
        with ZipFile(self.original) as zip_:
            raw=zip_.read("ext/Matrix.class")
        self.original_owner_sha=hashlib.sha256(raw).hexdigest()
        profile=profile_class_field_accesses(raw)
        self.original_instruction_count=sum(
            len(m["instructions"]) for m in profile["methods"]
            if (m["name"],m["descriptor"]) in self.IDS)

    @staticmethod
    def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

    @staticmethod
    def matrix_source(*,original,wrong_body=False,wrong_field=False):
        field="float[] e;" if wrong_field else "public float[] e;"
        val="9.0F" if wrong_body else "1.0F"
        return ("package ext;public final class Matrix {"
            "public static final Matrix ID;static Matrix[] cache;static int ptr;"
            +field+
            "static {cache=new Matrix[2];ptr=0;ID=new Matrix();}"
            "public Matrix(){this.e=new float[4];this.init();}"
            "public Matrix(rs.Packet p,boolean raw){"
            "this.e=new float[4];this.a(p,raw);}"
            "private void init(){this.e[0]="+val+";}"
            "void a(rs.Packet p,boolean raw){"
            "if(raw){this.e[0]=p.readFloat();}"
            "else{this.e[0]=ext.Converter.decode(p.readShort());}}"
            "public int sum(){return (int)this.e[0];}"
            + ("public int extraOriginal(rs.Packet p){return p.readShort();}"
               if original else "")
            + "}")

    def _original(self):
        classes=self.root/"original-classes";classes.mkdir()
        sources={
            "rs/Packet.java":"package rs;public class Packet {"
               "public int readShort(){return 7;}"
               "public float readFloat(){return 7f;}}",
            "ext/Converter.java":"package ext;public class Converter {"
               "public static float decode(int x){return x+1f;}}",
            "ext/Matrix.java":self.matrix_source(original=False),
        }
        for name,body in sources.items():
            path=self.root/"original-src"/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(body)
            res=subprocess.run(
                [shutil.which("javac"),"--release","9","-proc:none",
                 "-g:none","-classpath",str(classes),"-d",str(classes),
                 str(path)],capture_output=True)
            self.assertEqual(0,res.returncode,res.stderr.decode(errors="replace"))
        jar=self.root/"original.jar"
        with ZipFile(jar,"w") as output:
            for p in sorted(classes.rglob("*.class")):
                output.write(p,p.relative_to(classes).as_posix())
        return jar

    def _archive(self,name,sources):
        dest=self.root/name
        with ZipFile(dest,"w") as output:
            for path,body in sorted(sources.items()):
                output.writestr("src/main/java/"+path,body)
        return dest

    def verify(self,source=None,helpers=None,selection=None,helper_sha=None):
        source=source or self.candidate
        helpers=helpers or self.helpers
        selection=selection or self.selection
        return verify_complete_original_matrix_java(
            self.original,source,helpers,selection,
            original_sha256=self.sha(self.original),
            matrix_source_sha256=self.sha(source),
            helper_source_sha256=helper_sha or self.sha(helpers),
            selection_sha256=self.sha(selection),
            matrix_owner=self.OWNER,packet_owner=self.PACKET,
            expected_matrix_sha256=self.original_owner_sha,
            expected_members=6,
            expected_instructions=self.original_instruction_count,
            expected_helper_classes=2,
            expected_self_calls=3)

    def test_full_source_class_fields_methods_and_closure(self):
        result=self.verify()
        self.assertEqual(6,result["original_matrix_method_count"])
        self.assertEqual(self.original_instruction_count,
                         result["original_recompiled_jvm_instruction_count"])
        self.assertTrue(result["original_matrix_field_abi_exact"])
        self.assertEqual(3,result["original_self_call_edges_closed"])
        self.assertFalse(result["packet_and_external_helper_bodies_proven_original"])
        self.assertFalse(result["complete_original_client_java_compilation_passed"])

    def test_changed_one_method_or_field_rejected(self):
        bad=self._archive("bad-code.zip",{
            "ext/Matrix.java":self.matrix_source(original=False,wrong_body=True)})
        with self.assertRaises(ValueError):
            self.verify(source=bad)
        field=self._archive("bad-field.zip",{
            "ext/Matrix.java":self.matrix_source(original=False,wrong_field=True)})
        with self.assertRaises(CompleteMatrixJavaR162Error):
            self.verify(source=field)

    def test_missing_class_initializer_refused(self):
        wrong=self.root/"missing-init.json"
        wrong.write_text(json.dumps([
            {"name":n,"descriptor":d} for n,d in self.IDS if n!="<clinit>"]))
        with self.assertRaises(CompleteMatrixJavaR162Error):
            self.verify(selection=wrong)

    def test_wrong_source_helper_sha_fails_closed(self):
        with self.assertRaises(CompleteMatrixJavaR162Error):
            self.verify(helper_sha="0"*64)


if __name__=="__main__":
    unittest.main()
