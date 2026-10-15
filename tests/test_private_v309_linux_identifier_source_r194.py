"""R194 synthetic Linux-like Java method shape, no system command execution."""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile,ZIP_DEFLATED

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_linux_identifier_source_r194 import (
    R194OriginalLinuxIdentifierError,
    verify_pinned_original_linux_identifier_source,
)
from spk_recovery.private_v309_macos_serial_source_r193 import (
    R193OriginalMacOSSerialSourceError,
)
from spk_recovery.private_v309_four_owner_javac_frontier_r192 import (
    R192PrivateSourceFrontierError,
    build_private_four_owner_overlay,
    compare_pinned_private_four_owner_javac,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class R194SyntheticLinuxIdentifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("JDK required")
        cls.temp=TemporaryDirectory(prefix="r194-invented-source-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name)
        cls.owner="invented/A"
        cls.src=(
            "package invented;\n"
            "public class A {\n"
            " private static String a;\n"
            " public A(){}\n"
            " public static final String a(){\n"
            "  if(a==null)b();\n"
            "  if(a==null)c();\n"
            "  return a;\n"
            " }\n"
            " private static java.io.BufferedReader a(String source){\n"
            "  return new java.io.BufferedReader(\n"
            "   new java.io.StringReader(source));\n"
            " }\n"
            " private static void b(){\n"
            "  java.io.BufferedReader r=null;\n"
            "  try{r=a(\"ALPHA\");a=r.readLine();}\n"
            "  catch(java.io.IOException e){return;}\n"
            "  finally{if(r!=null)try{r.close();}\n"
            "   catch(java.io.IOException ignored){}}\n"
            " }\n"
            " private static void c(){\n"
            "  java.io.BufferedReader r=null;\n"
            "  try{r=a(\"BETA\");a=r.readLine();}\n"
            "  catch(java.io.IOException e){}\n"
            "  finally{if(r!=null)try{r.close();}\n"
            "   catch(java.io.IOException ignored){}}\n"
            " }\n"
            " static{a=null;}\n"
            "}\n"
        )
        src=cls.root/"source/invented/A.java"
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_text(cls.src,encoding="utf-8")
        out=cls.root/"out"
        empty=cls.root/"empty"
        out.mkdir();empty.mkdir()
        proc=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(out),str(src)],
            capture_output=True,text=True,timeout=60,check=False)
        if proc.returncode:
            raise AssertionError("unrelated Java9 fixture compilation failed")
        blob=(out/(cls.owner+".class")).read_bytes()
        cls.class_sha=hashlib.sha256(blob).hexdigest()
        cls.jar=cls.root/"fake-original.jar"
        with ZipFile(cls.jar,"w",ZIP_DEFLATED) as z:
            z.writestr(cls.owner+".class",blob)
        cls.source_zip=cls.pack("unrelated-six-methods.zip",cls.src)
        profile=profile_class_field_accesses(blob)
        cls.instruction_total=sum(
            len(m["instructions"]) for m in profile["methods"])

    @classmethod
    def pack(cls,name,java):
        path=cls.root/name
        with ZipFile(path,"w",ZIP_DEFLATED) as z:
            z.writestr("client/src/main/java/"+cls.owner+".java",java)
        return path

    def verify(self,source=None,**extras):
        source=source or self.source_zip
        args={
            "original_sha256":sha(self.jar),
            "source_sha256":sha(source),
            "original_owner":self.owner,
            "original_class_sha256":self.class_sha,
            "expected_methods":6,
            "expected_instructions":self.instruction_total,
            "expected_fields":1,
        }
        args.update(extras)
        return verify_pinned_original_linux_identifier_source(
            self.jar,source,**args)

    def test_all_six_original_unrelated_java_methods_match(self):
        result=self.verify()
        self.assertEqual(6,result["full_original_method_count_compiled"])
        self.assertEqual(self.instruction_total,
                         result["full_original_jvm_instructions_matched"])
        self.assertTrue(result[
            "full_dmidecode_and_lshal_source_methods_recovered"])
        self.assertFalse(result["original_shell_commands_executed"])
        self.assertFalse(result["whole_v309_client_compiles"])

    def test_mutated_discovery_method_rejected(self):
        bad=self.pack(
            "mutated-linux-branch.zip",
            self.src.replace('a(\"ALPHA\")','a(\"GAMMA\")'))
        with self.assertRaises(R193OriginalMacOSSerialSourceError):
            self.verify(source=bad)

    def test_original_digest_counts_and_source_owner_rejected(self):
        for changes in (
            {"original_sha256":"0"*64},
            {"source_sha256":"0"*64},
            {"original_class_sha256":"0"*64},
            {"original_owner":"invented/B"},
            {"expected_methods":5},
            {"expected_fields":2},
            {"expected_instructions":self.instruction_total+1},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(R193OriginalMacOSSerialSourceError):
                    self.verify(**changes)

    def test_overlay_does_not_modify_original_java_bytes(self):
        baseline=self.root/"baseline.zip"
        with ZipFile(baseline,"w",ZIP_DEFLATED) as z:
            z.writestr(
                "recovered-source/v309/src/invented/Keep.java",
                "package invented; public class Keep {}")
        overlay=self.root/"merged.zip"
        report=build_private_four_owner_overlay(
            baseline,[self.source_zip],overlay,
            baseline_sha256=sha(baseline),
            source_identities=((self.owner+".java",sha(self.source_zip)),),
            expected_baseline_java=1)
        self.assertEqual(1,report["baseline_java_files_exactly_preserved"])
        with ZipFile(overlay) as z:
            self.assertEqual(2,len(z.namelist()))
            self.assertEqual(
                b"package invented; public class Keep {}",
                z.read("recovered-source/v309/src/invented/Keep.java"))
        measured=compare_pinned_private_four_owner_javac(
            baseline,overlay,original_sha256=sha(baseline),
            candidate_sha256=sha(overlay),
            expected_original_count=1,expected_added_count=1)
        self.assertEqual(0,measured["compilation_error_delta"])
        self.assertFalse(measured["original_jar_on_compiler_classpath"])


if __name__=="__main__":
    unittest.main()
