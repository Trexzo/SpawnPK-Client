"""R164 source-only complete vector method/field parity and no-overwrite tests."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_original_vector_source_r164 import (
    R164OriginalVectorError, verify_original_vector_java,
    private_vector_source_overlay)


@unittest.skipUnless(shutil.which("javac"), "A real JDK is required")
class R164OriginalVectorTests(unittest.TestCase):
    OWNER="example/Point3"

    def setUp(self):
        hold=tempfile.TemporaryDirectory()
        self.addCleanup(hold.cleanup)
        self.root=Path(hold.name)
        self.original_code=self.java_code()
        self.original=self.make_original()
        self.candidate=self.java_zip("private-source.zip",self.original_code)
        self.overlay_base=self.root/"source-base.zip"
        with ZipFile(self.overlay_base,"w") as out:
            out.writestr("recovered-source/v309/src/rs/Client.java",
                         "package rs;public class Client{}")
        with ZipFile(self.original) as z:
            original=z.read(self.OWNER+".class")
        self.original_sha=hashlib.sha256(original).hexdigest()
        p=profile_class_field_accesses(original)
        self.methods=len(p["methods"])
        self.instructions=sum(len(m["instructions"]) for m in p["methods"])

    @staticmethod
    def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @staticmethod
    def java_code(*,wrong_length=False,wrong_field=False):
        op="+" if wrong_length else "*"
        field="public float x" if wrong_field else "float x"
        return ("package example;public class Point3{"
                +field+";float y;float z;"
                "Point3(float a,float b,float c){x=a;y=b;z=c;}"
                "static void used(int unused){}"
                "float length(){return (float)Math.sqrt((double)"
                "(x"+op+"x+y*y+z*z));}"
                "public String toString(){return x+\", \"+y+\", \"+z;}"
                "static {new Point3(0f,0f,0f);used(17);}"
                "}")

    def make_original(self):
        path=self.root/"original-src"/(self.OWNER+".java")
        path.parent.mkdir(parents=True)
        path.write_text(self.original_code,encoding="utf8")
        classes=self.root/"classes"
        classes.mkdir()
        p=subprocess.run([shutil.which("javac"),"--release","9",
            "-proc:none","-g:none","-d",str(classes),str(path)],
            capture_output=True)
        self.assertEqual(0,p.returncode,p.stderr.decode(errors="replace"))
        target=self.root/"synthetic-original.jar"
        with ZipFile(target,"w") as z:
            z.write(classes/(self.OWNER+".class"),self.OWNER+".class")
        return target

    def java_zip(self,name,code):
        dest=self.root/name
        with ZipFile(dest,"w") as z:
            z.writestr("src/main/java/"+self.OWNER+".java",code)
        return dest

    def verify(self,source=None,source_hash=None):
        source=source or self.candidate
        return verify_original_vector_java(
            self.original,source,
            original_sha256=self.sha(self.original),
            vector_source_sha256=source_hash or self.sha(source),
            original_owner=self.OWNER,
            original_class_sha256=self.original_sha,
            expected_methods=self.methods,expected_fields=3,
            expected_instructions=self.instructions)

    def test_all_original_methods_fields_and_jvm_instructions(self):
        result=self.verify()
        self.assertEqual(self.methods,result["full_original_vector_method_count"])
        self.assertEqual(3,result["full_original_vector_field_count"])
        self.assertEqual(self.instructions,
                         result["original_recompiled_jvm_instruction_count"])
        self.assertTrue(result["original_recompiled_method_code_equal"])
        self.assertTrue(result["no_original_binary_compiler_fallback"])
        self.assertFalse(result["full_original_v309_client_compiles"])
        self.assertFalse(result["private_java_source_publication_authorized"])

    def test_mutated_vector_arithmetic_or_field_is_rejected(self):
        for name,body in [
            ("wrong-math.zip",self.java_code(wrong_length=True)),
            ("wrong-field.zip",self.java_code(wrong_field=True))]:
            with self.subTest(name=name):
                bad=self.java_zip(name,body)
                with self.assertRaises(ValueError):
                    self.verify(source=bad)

    def test_sha_mismatch_rejected(self):
        with self.assertRaises(R164OriginalVectorError):
            self.verify(source_hash="0"*64)

    def test_original_one_class_source_overlay_only(self):
        output=self.root/"overlay.zip"
        result=private_vector_source_overlay(
            self.overlay_base,self.candidate,output,
            baseline_sha256=self.sha(self.overlay_base),
            vector_source_sha256=self.sha(self.candidate),
            expected_original_files=1,
            expected_vector_source_rel=self.OWNER+".java")
        self.assertEqual(2,result["new_client_java_file_count"])
        self.assertFalse(result["source_only_unverified_helpers_added"])
        with ZipFile(output) as z:
            self.assertEqual(2,len(z.namelist()))
            self.assertIn("recovered-source/v309/src/"+self.OWNER+".java",
                          z.namelist())

    def test_source_overwrite_or_baseline_hash_rejected(self):
        collision=self.root/"owner-conflict.zip"
        with ZipFile(collision,"w") as z:
            z.writestr("recovered-source/v309/src/"+self.OWNER+".java",
                       "class Other {}")
        with self.assertRaises(R164OriginalVectorError):
            private_vector_source_overlay(
                collision,self.candidate,self.root/"no-output.zip",
                baseline_sha256=self.sha(collision),
                vector_source_sha256=self.sha(self.candidate),
                expected_original_files=1,
                expected_vector_source_rel=self.OWNER+".java")
        with self.assertRaises(R164OriginalVectorError):
            private_vector_source_overlay(
                self.overlay_base,self.candidate,self.root/"no-output.zip",
                baseline_sha256="0"*64,
                vector_source_sha256=self.sha(self.candidate),
                expected_original_files=1,
                expected_vector_source_rel=self.OWNER+".java")


if __name__=="__main__":
    unittest.main()
