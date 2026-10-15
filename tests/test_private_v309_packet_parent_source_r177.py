"""R177 synthetic exact-superclass field, method and linked-node source tests."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from subprocess import run
from shutil import which
import unittest
from spk_recovery.private_v309_packet_parent_source_r177 import (
    verify_original_packet_parents,overlay_verified_parent_java)


@unittest.skipUnless(which("javac") and which("java"),"Java JDK required")
class PacketParentsR177(unittest.TestCase):
    def setUp(self):
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.java={
            "rs/t.java":("package rs; public class t {"
                         "public long c;public t d,e;"
                         "public final void b(){"
                         "if(this.e==null){}else{"
                         "this.e.d=this.d;this.d.e=this.e;"
                         "this.d=null;this.e=null;}}}"),
            "rs/a.java":("package rs;public class a extends t{"
                         "public a a,b;"
                         "public final void a(){"
                         "if(this.b==null){}else{"
                         "this.b.a=this.a;this.a.b=this.b;"
                         "this.a=null;this.b=null;}}}"),
        }
        self.jar=self.create_original()
        self.source=self.archive("two-source.zip",self.java)
        self.digests={}
        with ZipFile(self.jar) as z:
            for owner in ("rs/t","rs/a"):
                self.digests[owner]=hashlib.sha256(
                    z.read(owner+".class")).hexdigest()

    @staticmethod
    def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

    def archive(self,name,sources):
        path=self.root/name
        with ZipFile(path,"w") as z:
            for item,body in sorted(sources.items()):
                z.writestr("src/main/java/"+item,body)
        return path

    def create_original(self):
        src=self.root/"original-src";out=self.root/"original-class"
        out.mkdir()
        filenames=[]
        for name,body in self.java.items():
            file=src/name
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text(body)
            filenames.append(file)
        p=run([which("javac"),"--release","9","-proc:none","-g:none",
               "-d",str(out),*[str(x) for x in filenames]],
              capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr.decode(errors="replace"))
        jar=self.root/"synthetic-original.jar"
        with ZipFile(jar,"w") as z:
            for owner in ("rs/t","rs/a"):
                z.write(out/(owner+".class"),owner+".class")
        return jar

    def verify(self,source=None,sha=None):
        source=source or self.source
        return verify_original_packet_parents(
            self.jar,source,original_sha256=self.sha(self.jar),
            source_sha256=sha or self.sha(source),
            original_class_shas=self.digests)

    def test_two_classes_full_source_and_linked_list_abi(self):
        result=self.verify()
        self.assertEqual(2,result["complete_original_parent_classes_source_built"])
        self.assertEqual(4,result["all_original_parent_method_bodies_matched"])
        self.assertEqual(48,result["matched_original_jvm_instructions"])
        self.assertTrue(result["original_superchain_and_field_abi_verified"])
        self.assertFalse(result["original_packet_rs_x_e_complete"])

    def test_mutated_link_pointer_or_sha_is_rejected(self):
        altered=dict(self.java)
        altered["rs/a.java"]=altered["rs/a.java"].replace(
            "this.a.b=this.b;","this.a.b=this.a;")
        with self.assertRaises(ValueError):
            self.verify(self.archive("mutation.zip",altered))
        with self.assertRaises(ValueError):
            self.verify(sha="0"*64)

    def test_private_source_overlay_preserves_all_previous_files(self):
        base=self.archive("base.zip",{
            "rs/Client.java":"package rs;public class Client{}"})
        canonical=self.root/"canonical.zip"
        # Baseline fixture uses the actual canonical relative root.
        with ZipFile(canonical,"w") as z:
            z.writestr("recovered-source/v309/src/rs/Client.java",
                       "package rs;public class Client{}")
        dest=self.root/"new-tree.zip"
        p=overlay_verified_parent_java(
            canonical,self.source,dest,
            baseline_sha256=self.sha(canonical),
            parents_sha256=self.sha(self.source),expected_original_java=1)
        self.assertEqual(3,p["source_files"])
        self.assertFalse(p["partial_packet_installed"])
        with ZipFile(dest) as z:
            self.assertEqual(3,len(z.namelist()))
            self.assertIn("recovered-source/v309/src/rs/t.java",z.namelist())
            self.assertIn("recovered-source/v309/src/rs/a.java",z.namelist())

    def test_overlay_existing_original_owner_not_overwritten(self):
        collision=self.root/"collision.zip"
        with ZipFile(collision,"w") as z:
            z.writestr("recovered-source/v309/src/rs/t.java",
                       "package rs;public class t{}")
        with self.assertRaises(ValueError):
            overlay_verified_parent_java(
                collision,self.source,self.root/"refuse.zip",
                baseline_sha256=self.sha(collision),
                parents_sha256=self.sha(self.source),expected_original_java=1)


if __name__=="__main__":
    unittest.main()
