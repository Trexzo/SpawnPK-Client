"""R195 unrelated seven-method Java9 class with one fake signature dependency."""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile,ZIP_DEFLATED

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_windows_identifier_source_r195 import (
    R195OriginalWindowsIdentifierError,
    verify_pinned_original_windows_identifier_source,
)
from spk_recovery.private_v309_four_owner_javac_frontier_r192 import (
    build_private_four_owner_overlay,
    compare_pinned_private_four_owner_javac,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class R195SyntheticSevenMethodsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("Java compiler required")
        cls.tmp=TemporaryDirectory(prefix="r195-invented-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.owner="invented/W"
        cls.helper_owner="invented/S"
        cls.original_source=(
            "package invented;\n"
            "public class W {\n"
            " private static final int c=7;\n"
            " private static final int d=10;\n"
            " public static String a;\n"
            " public static boolean b;\n"
            " public W(){}\n"
            " public static String a(){\n"
            "  if(b)return a;\n"
            "  a=String.valueOf(S.a(\"seed\"));\n"
            "  b=true;\n"
            "  return null;\n"
            " }\n"
            " private static int a(String txt,int count){\n"
            "  if(count<=0)return 0;\n"
            "  return txt.length()+count;\n"
            " }\n"
            " private static String a(S other){return other.toString();}\n"
            " private static String b(S other){\n"
            "  try{return other.toString();}\n"
            "  catch(RuntimeException ex){return null;}\n"
            " }\n"
            " public static java.util.Date a(String txt) throws Exception {\n"
            "  return new java.text.SimpleDateFormat(\"yyyy\").parse(txt);\n"
            " }\n"
            " static{a=null;b=false;}\n"
            "}\n"
        )
        cls.helper_source=(
            "package invented;\n"
            "public class S {\n"
            " public static boolean a(String text){return text==null;}\n"
            "}\n"
        )
        cls.java_zip=cls.pack(
            "invented-windows-java.zip",cls.owner,cls.original_source)
        cls.helper_zip=cls.pack(
            "compiler-only-helper.zip",cls.helper_owner,cls.helper_source)
        src=cls.root/"src"
        files=[]
        for owner,text in ((cls.owner,cls.original_source),
                           (cls.helper_owner,cls.helper_source)):
            path=src/(owner+".java")
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(text,encoding="utf-8")
            files.append(str(path))
        out=cls.root/"classes"
        empty=cls.root/"empty"
        out.mkdir();empty.mkdir()
        result=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(out),*files],
            capture_output=True,text=True,timeout=60,check=False)
        if result.returncode:
            raise AssertionError("synthetic original class Java9 build failed")
        data=(out/(cls.owner+".class")).read_bytes()
        cls.class_sha=hashlib.sha256(data).hexdigest()
        cls.jar=cls.root/"invented-original.jar"
        with ZipFile(cls.jar,"w",ZIP_DEFLATED) as f:
            f.writestr(cls.owner+".class",data)
        profile=profile_class_field_accesses(data)
        cls.total=sum(len(x["instructions"]) for x in profile["methods"])

    @classmethod
    def pack(cls,name,owner,java):
        p=cls.root/name
        with ZipFile(p,"w",ZIP_DEFLATED) as archive:
            archive.writestr("client/src/main/java/"+owner+".java",java)
        return p

    def verify(self,source=None,helper=None,**kwargs):
        source=source or self.java_zip
        helper=helper or self.helper_zip
        args={
            "original_sha256":sha(self.jar),
            "source_sha256":sha(source),
            "compiler_only_signature_sha256":sha(helper),
            "original_owner":self.owner,
            "original_class_sha256":self.class_sha,
            "helper_owner":self.helper_owner,
            "expected_methods":7,
            "expected_instructions":self.total,
            "expected_fields":4,
        }
        args.update(kwargs)
        return verify_pinned_original_windows_identifier_source(
            self.jar,source,helper,**args)

    def test_all_seven_methods_and_four_fields_match(self):
        result=self.verify()
        self.assertEqual(7,result["original_methods_compiled_and_matched"])
        self.assertEqual(self.total,result["original_jvm_instructions_matched"])
        self.assertTrue(result[
            "original_field_header_and_method_abi_matched"])
        self.assertFalse(result[
            "compiler_only_signature_source_is_original"])
        self.assertFalse(result[
            "original_systeminfo_or_powershell_command_executed"])
        self.assertFalse(result["complete_client_compiled"])

    def test_modified_independent_jvm_method_rejected(self):
        altered=self.pack("changed-branch.zip",self.owner,
                          self.original_source.replace(
                              "if(count<=0)","if(count<0)"))
        with self.assertRaises(R195OriginalWindowsIdentifierError):
            self.verify(source=altered)

    def test_wrong_owner_digest_and_instruction_count_rejected(self):
        for params in (
            {"original_sha256":"0"*64},
            {"source_sha256":"0"*64},
            {"compiler_only_signature_sha256":"0"*64},
            {"original_class_sha256":"0"*64},
            {"expected_methods":8},
            {"expected_instructions":self.total+1},
            {"original_owner":"invented/X"},
            {"helper_owner":"invented/Y"},
            {"expected_fields":5},
        ):
            with self.subTest(params=params):
                with self.assertRaises(R195OriginalWindowsIdentifierError):
                    self.verify(**params)

    def test_missing_or_unrecognized_helper_owner_rejected(self):
        fake=self.pack(
            "fake-helper-wrong-name.zip",
            "invented/Wrong",self.helper_source)
        with self.assertRaises(R195OriginalWindowsIdentifierError):
            self.verify(helper=fake)

    def test_private_java_overlay_keeps_original_bytes(self):
        baseline=self.root/"baseline.zip"
        with ZipFile(baseline,"w",ZIP_DEFLATED) as z:
            z.writestr("recovered-source/v309/src/invented/Keep.java",
                        "package invented; public class Keep {}")
        candidate=self.root/"overlay.zip"
        manifest=build_private_four_owner_overlay(
            baseline,[self.java_zip],candidate,
            baseline_sha256=sha(baseline),
            source_identities=((self.owner+".java",sha(self.java_zip)),),
            expected_baseline_java=1)
        self.assertEqual(1,manifest[
            "baseline_java_files_exactly_preserved"])
        with ZipFile(candidate) as z:
            self.assertEqual(b"package invented; public class Keep {}",
                             z.read("recovered-source/v309/src/invented/Keep.java"))
        report=compare_pinned_private_four_owner_javac(
            baseline,candidate,
            original_sha256=sha(baseline),
            candidate_sha256=sha(candidate),
            expected_original_count=1,expected_added_count=1)
        self.assertFalse(report["original_jar_on_compiler_classpath"])
        self.assertGreater(report["candidate"]["total_compiler_errors"],0)


if __name__=="__main__":
    unittest.main()
