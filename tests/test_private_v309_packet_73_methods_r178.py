"""R178 synthetic complete-original-source-only Packet parent and partial class proof."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_packet_73_methods_r178 import (
    R178OriginalPacketSourceError, verify_original_packet_73)


@unittest.skipUnless(shutil.which("javac"), "JDK required")
class R178OriginalPacketWithRealParentsTests(unittest.TestCase):
    OWNER="rs/x/e"
    PARENTS={
        "rs/t.java":("package rs; public class t {"
                     "public long identity;public t next;"
                     "public t(){} public void unlink(){this.next=null;}}"),
        "rs/a.java":("package rs;public class a extends t {"
                     "public int position;public a(){}"
                     "public void resetNode(){this.position=0;}}"),
    }
    REAL_HELPER=("package rs.q;public class a {"
                 "public int compute(){return 42;}}")
    STUB_HELPER="package rs.q;public class a {}"

    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.original=self.original_jar()
        self.parents=self.archive("parent-source.zip",self.PARENTS)
        self.source=self.archive("packet-source.zip",{
            "rs/x/e.java":self.packet_java(original=False)})
        self.stub=self.archive("helper-source.zip",{
            "rs/q/a.java":self.STUB_HELPER})
        with ZipFile(self.original) as z:
            self.packet_class_sha=hashlib.sha256(
                z.read("rs/x/e.class")).hexdigest()
            self.parent_class_shas={
                n:hashlib.sha256(z.read(n+".class")).hexdigest()
                for n in ("rs/t","rs/a")}
        profile=profile_class_field_accesses(
            self.original_class_bytes())
        selected={(m["name"],m["descriptor"]) for m in profile["methods"]}-
                 {("notRestored","()I"),("<clinit>","()V")}
        self.selected_inst=sum(len(m["instructions"])
            for m in profile["methods"]
            if (m["name"],m["descriptor"]) in selected)
        self.parent_inst=0
        for owner in ("rs/t","rs/a"):
            p=profile_class_field_accesses(self.original_class_bytes(owner))
            self.parent_inst+=sum(len(m["instructions"])
                                  for m in p["methods"])

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @staticmethod
    def packet_java(*,original,mutated=False):
        return ("package rs.x;public class e extends rs.a {"
                "public rs.q.a helper;public byte[] bytes;public int position;"
                "public e(){super();}"
                "public e(byte[] b){super();this.bytes=b;this.position=0;}"
                "public int getPosition(){return this.position"+(
                  "+1" if mutated else "")+";}"
                "public void setPosition(int x){this.position=x;}"
                + ("public static int STATIC_VALUE;"
                   "static {STATIC_VALUE=19;}"
                   "public int notRestored(){return 8;}"
                   if original else "")
                + "}")

    def archive(self,name,files):
        out=self.root/name
        with ZipFile(out,"w") as z:
            for path,body in sorted(files.items()):
                z.writestr("src/main/java/"+path,body)
        return out

    def original_jar(self):
        files={**self.PARENTS,
               "rs/x/e.java":self.packet_java(original=True),
               "rs/q/a.java":self.REAL_HELPER}
        cls=self.root/"original-classes";cls.mkdir()
        paths=[]
        for rel,body in files.items():
            p=self.root/"orig"/rel
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(body,encoding="utf-8")
            paths.append(p)
        result=subprocess.run(
            [shutil.which("javac"),"--release","9",
             "-proc:none","-g:none","-d",str(cls),
             *[str(p) for p in paths]],
            capture_output=True)
        self.assertEqual(0,result.returncode,
                         result.stderr.decode(errors="replace"))
        jar=self.root/"original.jar"
        with ZipFile(jar,"w") as z:
            for file in sorted(cls.rglob("*.class")):
                z.write(file,file.relative_to(cls).as_posix())
        return jar

    def original_class_bytes(self,owner=None):
        with ZipFile(self.original) as z:
            return z.read((owner or self.OWNER)+".class")

    def verify(self,source=None,source_sha=None,chosen_count=None):
        source=source or self.source
        return verify_original_packet_73(
            self.original,source,self.parents,self.stub,
            original_sha256=self.sha(self.original),
            packet_source_sha256=source_sha or self.sha(source),
            parent_source_sha256=self.sha(self.parents),
            signature_source_sha256=self.sha(self.stub),
            original_owner=self.OWNER,
            original_class_sha256=self.packet_class_sha,
            original_parent_class_shas=self.parent_class_shas,
            selected_method_count=chosen_count or 4,
            selected_instructions=self.selected_inst,
            original_total_noninitializer_methods=5,
            expected_parent_instructions=self.parent_inst,
            remaining_original_methods={
                ("notRestored","()I"),("<clinit>","()V")})

    def test_four_complete_source_methods_and_two_verified_parents(self):
        report=self.verify()
        self.assertEqual(4,report["selected_original_packet_method_count"])
        self.assertEqual(self.selected_inst,
                         report["matching_selected_original_jvm_instructions"])
        self.assertEqual(2,report["original_packet_parent_classes_java_verified"])
        self.assertEqual(1,report["remaining_unverified_original_method_count"])
        self.assertFalse(report["original_rs_q_a_helper_body_proven"])
        self.assertFalse(report["original_binary_compiler_fallback_used"])
        self.assertFalse(report["full_original_packet_class_recovered"])

    def test_changed_method_and_original_hash_rejected(self):
        mutant=self.archive("changed-packet.zip",{
            "rs/x/e.java":self.packet_java(original=False,mutated=True)})
        with self.assertRaises(ValueError):
            self.verify(source=mutant)
        with self.assertRaises(R178OriginalPacketSourceError):
            self.verify(source_sha="0"*64)

    def test_incorrect_selected_method_count_rejected(self):
        with self.assertRaises(R178OriginalPacketSourceError):
            self.verify(chosen_count=5)


if __name__=="__main__":
    unittest.main()
