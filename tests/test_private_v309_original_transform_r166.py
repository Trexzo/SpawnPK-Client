"""R166: source-only eight-method synthetic transform, original Code and concat recipe."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_original_transform_source_r166 import (
    R166OriginalTransformError, verify_original_transform_java,
    verify_and_overlay_transform,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("javap"),
                     "Java9-capable JDK required")
class R166OriginalTransformTests(unittest.TestCase):
    OWNER="example/Transform3"

    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.orig=self.original()
        self.src=self.source_archive("candidate.zip",self.java())
        self.baseline=self.root/"old-source.zip"
        with ZipFile(self.baseline,"w") as z:
            z.writestr("recovered-source/v309/src/rs/Client.java",
                       "package rs;public class Client{}")
        with ZipFile(self.orig) as z:
            raw=z.read(self.OWNER+".class")
        self.sha_class=hashlib.sha256(raw).hexdigest()
        self.profile=profile_class_field_accesses(raw)
        self.instructions=sum(len(m["instructions"]) for m in
                              self.profile["methods"])

    @staticmethod
    def sha(p):
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()

    @staticmethod
    def java(*,changed_math=False,changed_recipe=False,changed_flags=False):
        operator="+" if changed_math else "-"
        delimiter=";" if changed_recipe else ","
        visibility="public " if changed_flags else ""
        return (
            "package example;" + visibility + "class Transform3 {"
            "float a,b,c,d,e,f,g,h,i,j,k,l;"
            "public static final Transform3 m = new Transform3();"
            "Transform3(){this.reset();}"
            "void reset(){a=b=c=d=0.0f;e=1.0f;f=g=0.0f;"
            "h=1.0f;i=j=k=l=0.0f;}"
            "void rx(float v){float s=(float)Math.sin((double)v);"
            "float c=(float)Math.cos((double)v);"
            "float old=b;this.b=c*old"+operator+"s*this.c;"
            "this.c=s*old+c*this.c;}"
            "void ry(float v){float s=(float)Math.sin((double)v);"
            "float c=(float)Math.cos((double)v);"
            "float old=a;this.a=c*old+s*this.g;"
            "this.g=c*this.g-s*old;}"
            "void rz(float v){float s=(float)Math.sin((double)v);"
            "float c=(float)Math.cos((double)v);"
            "float old=h;this.h=c*old-s*this.a;"
            "this.a=c*this.a+s*old;}"
            "void move(float dx,float dy,float dz){"
            "this.j+=dx;this.k+=dy;this.l+=dz;}"
            "public String toString(){return \"\"+h+\""+delimiter+"\"+a"
            "+\""+delimiter+"\"+g+\""+delimiter+"\"+j;}"
            "}")

    def original(self):
        source=self.root/"original-src"/(self.OWNER+".java")
        source.parent.mkdir(parents=True)
        source.write_text(self.java(),encoding="utf8")
        classes=self.root/"classes"
        classes.mkdir()
        p=subprocess.run(
            [shutil.which("javac"),"--release","9",
             "-g:none","-proc:none","-d",str(classes),str(source)],
            capture_output=True)
        self.assertEqual(0,p.returncode,
                         p.stderr.decode(errors="replace"))
        archive=self.root/"original.jar"
        with ZipFile(archive,"w") as z:
            z.write(classes/(self.OWNER+".class"),self.OWNER+".class")
        return archive

    def source_archive(self,name,source):
        archive=self.root/name
        with ZipFile(archive,"w") as z:
            z.writestr("src/main/java/"+self.OWNER+".java",source)
        return archive

    def prove(self,candidate=None,sha_override=None):
        candidate=candidate or self.src
        return verify_original_transform_java(
            self.orig,candidate,
            original_sha256=self.sha(self.orig),
            transform_source_sha256=sha_override or self.sha(candidate),
            owner=self.OWNER,
            original_class_sha256=self.sha_class,
            expected_methods=8,
            expected_fields=13,
            expected_instructions=self.instructions)

    def test_all_eight_original_methods_fields_and_string_concat(self):
        report=self.prove()
        self.assertEqual(8,report["verified_all_original_method_count"])
        self.assertEqual(13,report["verified_transform_field_count"])
        self.assertEqual(self.instructions,
                         report["verified_all_original_jvm_instructions"])
        self.assertTrue(report[
            "original_string_concatenation_bootstrap_recipe_equal"])
        self.assertFalse(report["original_external_binary_compiler_fallback"])
        self.assertFalse(report["whole_original_v309_client_compiles"])

    def test_changed_float_formula_fails(self):
        bad=self.source_archive("wrong-math.zip",
                                self.java(changed_math=True))
        with self.assertRaises(ValueError):
            self.prove(bad)

    def test_changed_concat_recipe_fails_despite_same_method_opcodes(self):
        bad=self.source_archive("wrong-concat.zip",
                                self.java(changed_recipe=True))
        with self.assertRaises(ValueError):
            self.prove(bad)

    def test_original_class_modifier_change_is_rejected(self):
        bad=self.source_archive("wrong-flags.zip",
                                self.java(changed_flags=True))
        with self.assertRaises(R166OriginalTransformError):
            self.prove(bad)

    def test_sha_mismatch_and_no_overwrite(self):
        with self.assertRaises(ValueError):
            self.prove(sha_override="0"*64)
        proof=verify_and_overlay_transform(
            self.orig,self.src,self.baseline,self.root/"complete.zip",
            java_sha256=self.sha(self.src),
            previous_tree_sha256=self.sha(self.baseline),
            original_sha256=self.sha(self.orig),
            owner=self.OWNER,
            original_class_sha256=self.sha_class,
            expected_methods=8,
            expected_fields=13,
            expected_instructions=self.instructions,
            expected_previous_sources=1)
        self.assertEqual(2,proof[
            "private_canonical_source_overlay"]["new_client_java_file_count"])
        with ZipFile(self.root/"complete.zip") as z:
            self.assertEqual(2,len(z.namelist()))
            self.assertIn("recovered-source/v309/src/"+self.OWNER+".java",
                          z.namelist())


if __name__=="__main__":
    unittest.main()
