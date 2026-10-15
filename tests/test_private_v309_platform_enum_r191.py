"""R191 invented Java9 platform enum cross-build semantic parity tests.

Real OS detection is never executed: these tests compile Java9 classfiles
and read their JVM Code. No SpawnPK binary or original derived source in CI.
"""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

from spk_recovery.private_v309_platform_enum_r191 import (
    R191PlatformEnumSourceError,
    audit_original_platform_enum_java,
)


class R191SyntheticPlatformEnumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("Java compiler is required")
        cls.tmp=TemporaryDirectory(prefix="r191-fake-platform-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.start=(
            "package invented;\n"
            "public enum O { Windows, MacOS, Linux, Other;\n"
        )
        cls.detector=(
            " private static final O e;\n"
            " static {\n"
            "  String os=System.getProperty(\"os.name\",\"generic\")"
            ".toLowerCase();\n"
            "  if(os.contains(\"mac\")||os.contains(\"darwin\"))e=MacOS;\n"
            "  else if(os.contains(\"win\"))e=Windows;\n"
            "  else if(os.contains(\"nux\"))e=Linux;\n"
            "  else e=Other;\n"
            " }\n"
            " public static O a(){ return e; }\n"
            "}\n"
        )
        cls.aliases=(
            " public static final O a=Windows;\n"
            " public static final O b=MacOS;\n"
            " public static final O c=Linux;\n"
            " public static final O d=Other;\n"
        )
        cls.original=cls.compile_java(
            "original",cls.start+cls.detector)
        cls.candidate=cls.compile_java(
            "reconstructed",cls.start+cls.aliases+cls.detector)

    @classmethod
    def compile_java(cls,folder,java):
        root=cls.root/folder
        path=root/"source/invented/O.java"
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(java,encoding="utf-8")
        classes=root/"classes"
        empty=root/"empty"
        classes.mkdir();empty.mkdir()
        p=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(classes),str(path)],
            capture_output=True,text=True,check=False,timeout=60)
        if p.returncode:
            raise AssertionError("synthetic source did not compile: "+p.stderr)
        return (classes/"invented/O.class").read_bytes()

    def audit(self,candidate=None,**kwargs):
        options={
            "original_owner":"invented/O",
            "original_class_sha256":
                hashlib.sha256(self.original).hexdigest(),
            "original_field_map":{
                "Windows":"Windows","MacOS":"MacOS",
                "Linux":"Linux","Other":"Other",
                "e":"e","$VALUES":"$VALUES"},
            "original_array_method_map":{"$values":"$values"},
        }
        options.update(kwargs)
        return audit_original_platform_enum_java(
            self.original,candidate or self.candidate,**options)

    def test_all_six_semantic_java_methods_and_os_detection(self):
        result=self.audit()
        self.assertTrue(result[
            "all_six_original_enum_methods_semantically_matched"])
        self.assertEqual(["Windows","MacOS","Linux","Other"],
                         result["original_os_labels_in_order"])
        self.assertTrue(result[
            "original_os_detection_branches_and_literal_checks_match"])
        self.assertTrue(result[
            "original_enum_obfuscated_field_aliases_preserved"])
        self.assertTrue(result[
            "four_extra_alias_fields_in_source_generated_class"])
        self.assertFalse(result["original_game_executed"])
        self.assertFalse(result["full_original_client_compiled"])

    def test_wrong_enum_constant_order_rejected(self):
        wrong=self.compile_java(
            "wrong-order",
            self.start.replace(
                "Windows, MacOS, Linux, Other",
                "MacOS, Windows, Linux, Other")+
            self.aliases+self.detector)
        with self.assertRaises(R191PlatformEnumSourceError):
            self.audit(wrong)

    def test_wrong_platform_detection_branch_rejected(self):
        wrong=self.compile_java(
            "wrong-branch",
            self.start+self.aliases+self.detector.replace(
                'contains(\"nux\")','contains(\"nix\")'))
        with self.assertRaises(R191PlatformEnumSourceError):
            self.audit(wrong)

    def test_changed_alias_rejected(self):
        wrong=self.compile_java(
            "wrong-alias",
            self.start+self.aliases.replace("a=Windows;","a=Other;")+
            self.detector)
        with self.assertRaises(R191PlatformEnumSourceError):
            self.audit(wrong)

    def test_missing_alias_rejected(self):
        wrong=self.compile_java(
            "missing-alias",
            self.start+self.aliases.replace(
                " public static final O c=Linux;\n","")+
            self.detector)
        with self.assertRaises(R191PlatformEnumSourceError):
            self.audit(wrong)

    def test_changed_os_property_name_rejected(self):
        wrong=self.compile_java(
            "wrong-property",
            self.start+self.aliases+self.detector.replace(
                '"os.name"','"java.vendor"'))
        with self.assertRaises(R191PlatformEnumSourceError):
            self.audit(wrong)

    def test_wrong_exact_original_sha_and_owner_rejected(self):
        for args in (
            {"original_class_sha256":"0"*64},
            {"original_owner":"invented/P"},
        ):
            with self.subTest(args=args):
                with self.assertRaises(R191PlatformEnumSourceError):
                    self.audit(**args)


if __name__=="__main__":
    unittest.main()
