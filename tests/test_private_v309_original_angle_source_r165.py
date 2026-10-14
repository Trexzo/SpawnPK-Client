"""R165 original static-final constants are evidence, not just JVM method Code."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile
from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_original_angle_source_r165 import (
    R165OriginalAngleError,verify_original_angle_java,
    verified_private_source_tree_overlay)


@unittest.skipUnless(shutil.which("javac") and shutil.which("javap"),
                     "Real Java compiler required")
class R165OriginalAngleSourceTests(unittest.TestCase):
    OWNER="example/Angle"

    def setUp(self):
        home=tempfile.TemporaryDirectory()
        self.addCleanup(home.cleanup)
        self.root=Path(home.name)
        self.original=self.compile_original()
        self.source=self.source_zip("source.zip",self.sample())
        self.baseline=self.root/"baseline.zip"
        with ZipFile(self.baseline,"w") as z:
            z.writestr("recovered-source/v309/src/example/Root.java",
                       "package example;public class Root{}")
        with ZipFile(self.original) as z:
            raw=z.read(self.OWNER+".class")
        self.owner_sha=hashlib.sha256(raw).hexdigest()
        profile=profile_class_field_accesses(raw)
        self.method_count=len(profile["methods"])
        self.opcode_count=sum(len(m["instructions"]) for m in profile["methods"])

    @staticmethod
    def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @staticmethod
    def sample(*,different_unused_constant=False,wrong_math=False):
        constant="12" if different_unused_constant else "11"
        expression="x + 1" if wrong_math else "(x & 15)"
        return ("package example;public class Angle {"
                "public static final double A = 6.25D;"
                "public static final int B = "+constant+";"
                "public static final int C = 15;"
                "static final int[] lookup = new int[16];"
                "Angle(){throw new Error();}"
                "public static int transform(int x){return "+expression+";}"
                "public static int combine(int x,int y){return x+y;}"
                "public static int read(int x){return lookup[x&15];}"
                "static {for(int i=0;i<16;i++){lookup[i]=(int)"
                "(16.0D*Math.sin(i*0.5D));}}"
                "}")

    def compile_original(self):
        source=self.root/"orig"/(self.OWNER+".java")
        source.parent.mkdir(parents=True)
        source.write_text(self.sample())
        classes=self.root/"classes"
        classes.mkdir()
        p=subprocess.run([shutil.which("javac"),"--release","9",
            "-proc:none","-g:none","-d",str(classes),str(source)],
            capture_output=True)
        self.assertEqual(0,p.returncode,p.stderr.decode(errors="replace"))
        target=self.root/"original.jar"
        with ZipFile(target,"w") as z:
            z.write(classes/(self.OWNER+".class"),self.OWNER+".class")
        return target

    def source_zip(self,name,content):
        target=self.root/name
        with ZipFile(target,"w") as z:
            z.writestr("src/main/java/"+self.OWNER+".java",content)
        return target

    def verify(self,source=None):
        source=source or self.source
        return verify_original_angle_java(
            self.original,source,
            original_sha256=self.sha(self.original),
            angle_source_sha256=self.sha(source),
            original_owner=self.OWNER,
            class_sha256=self.owner_sha,
            expected_methods=self.method_count,
            expected_fields=4,
            expected_instructions=self.opcode_count)

    def test_exact_constant_values_and_all_original_method_code(self):
        result=self.verify()
        self.assertTrue(result["all_original_static_final_constants_equal"])
        self.assertEqual(self.method_count,result["verified_original_jvm_method_count"])
        self.assertEqual(self.opcode_count,result["verified_original_jvm_instruction_count"])
        self.assertFalse(result["original_binary_used_as_compiler_dependency"])
        self.assertFalse(result["complete_client_compiled"])

    def test_changed_unused_constant_vetoes_even_with_same_method_code(self):
        candidate=self.source_zip("wrong-constant.zip",
            self.sample(different_unused_constant=True))
        with self.assertRaises(R165OriginalAngleError):
            self.verify(candidate)

    def test_changed_math_rejected(self):
        candidate=self.source_zip("wrong-math.zip",
            self.sample(wrong_math=True))
        with self.assertRaises(ValueError):
            self.verify(candidate)

    def test_verified_source_overlay_preserves_prior_files(self):
        result=verified_private_source_tree_overlay(
            self.original,self.source,self.baseline,
            self.root/"new-tree.zip",
            angle_source_sha256=self.sha(self.source),
            previous_tree_sha256=self.sha(self.baseline),
            original_sha256=self.sha(self.original),
            original_owner=self.OWNER,
            original_class_sha256=self.owner_sha,
            expected_methods=self.method_count,
            expected_fields=4,
            expected_instructions=self.opcode_count,
            expected_prior_java=1)
        self.assertEqual(2,result["private_source_tree"]["new_client_java_file_count"])
        with ZipFile(self.root/"new-tree.zip") as z:
            self.assertIn("recovered-source/v309/src/example/Root.java",z.namelist())
            self.assertIn("recovered-source/v309/src/example/Angle.java",z.namelist())


if __name__=="__main__":
    unittest.main()
