"""R193 uses unrelated synthetic Java9 fixtures, not original game code."""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile,ZIP_DEFLATED

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_macos_serial_source_r193 import (
    R193OriginalMacOSSerialSourceError,
    verify_pinned_original_macos_serial_java,
)
from spk_recovery.private_v309_four_owner_javac_frontier_r192 import (
    build_private_four_owner_overlay,
    compare_pinned_private_four_owner_javac,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class R193SyntheticOriginalMacOSSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("JDK required")
        cls.tmp=TemporaryDirectory(prefix="r193-synthetic-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.owner="invented/B"
        cls.body=(
            "package invented;\n"
            "public class B {\n"
            " private static String a;\n"
            " public B(){}\n"
            " public static final String a(){\n"
            "  if(a!=null)return a;\n"
            "  try{a=String.valueOf(4);}catch(RuntimeException ex){\n"
            "   return null;\n"
            "  }\n"
            "  return a;\n"
            " }\n"
            " static{a=null;}\n"
            "}\n"
        )
        src=cls.root/"src/invented/B.java"
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_text(cls.body,encoding="utf-8")
        dest=cls.root/"classes"
        empty=cls.root/"empty"
        dest.mkdir();empty.mkdir()
        p=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(dest),str(src)],
            capture_output=True,text=True,timeout=60,check=False)
        if p.returncode:
            raise AssertionError("invented Java9 fixture failed to compile")
        data=(dest/(cls.owner+".class")).read_bytes()
        cls.cls_sha=hashlib.sha256(data).hexdigest()
        cls.binary_zip=cls.root/"invented-class.jar"
        with ZipFile(cls.binary_zip,"w",ZIP_DEFLATED) as z:
            z.writestr(cls.owner+".class",data)
        cls.source_zip=cls.make_java_zip("invented-source.zip",cls.body)
        profile=profile_class_field_accesses(data)
        cls.count=sum(len(method["instructions"])
                      for method in profile["methods"])

    @classmethod
    def make_java_zip(cls,name,body):
        dest=cls.root/name
        with ZipFile(dest,"w",ZIP_DEFLATED) as z:
            z.writestr("client/src/main/java/"+cls.owner+".java",body)
        return dest

    def verify(self,source=None,**changes):
        source=source or self.source_zip
        args={
            "original_sha256":sha(self.binary_zip),
            "source_sha256":sha(source),
            "original_owner":self.owner,
            "original_class_sha256":self.cls_sha,
            "expected_methods":3,
            "expected_instructions":self.count,
            "expected_fields":1,
        }
        args.update(changes)
        return verify_pinned_original_macos_serial_java(
            self.binary_zip,source,**args)

    def test_all_methods_and_field_abi_original_bytecode_match(self):
        report=self.verify()
        self.assertEqual(3,report["full_original_method_count_compiled"])
        self.assertEqual(self.count,report["full_original_jvm_instructions_matched"])
        self.assertTrue(report["original_field_abi_and_class_header_match"])
        self.assertTrue(report["source_only_javac_no_binary_fallback"])
        self.assertFalse(report["original_system_profiler_or_game_code_executed"])
        self.assertFalse(report["whole_v309_client_compiles"])

    def test_changed_real_method_bytecode_rejected(self):
        changed=self.make_java_zip(
            "changed-operation.zip",
            self.body.replace("String.valueOf(4)","String.valueOf(5)"))
        with self.assertRaises(R193OriginalMacOSSerialSourceError):
            self.verify(changed)

    def test_wrong_input_shas_class_counts_and_owner_rejected(self):
        for args in (
            {"original_sha256":"0"*64},
            {"source_sha256":"0"*64},
            {"original_class_sha256":"0"*64},
            {"original_owner":"invented/C"},
            {"expected_methods":4},
            {"expected_fields":2},
            {"expected_instructions":self.count+1},
        ):
            with self.subTest(args=args):
                with self.assertRaises(R193OriginalMacOSSerialSourceError):
                    self.verify(**args)

    def test_private_overlay_preserves_all_prior_source_bytes(self):
        original=self.root/"one-baseline.zip"
        with ZipFile(original,"w",ZIP_DEFLATED) as z:
            z.writestr(
                "recovered-source/v309/src/invented/A.java",
                b"package invented; class A {static int n(){return 1;}}")
        overlay=self.root/"new-overlay.zip"
        result=build_private_four_owner_overlay(
            original,[self.source_zip],overlay,
            baseline_sha256=sha(original),
            source_identities=((self.owner+".java",sha(self.source_zip)),),
            expected_baseline_java=1)
        self.assertEqual(1,result["baseline_java_files_exactly_preserved"])
        self.assertEqual(1,result["added_independently_evidenced_java_files"])
        with ZipFile(overlay) as z:
            self.assertIn(
                "recovered-source/v309/src/invented/B.java",z.namelist())
            self.assertIn(
                "return 1",z.read(
                    "recovered-source/v309/src/invented/A.java").decode())

    def test_actual_javac_frontier_with_unrelated_source(self):
        baseline=self.root/"baseline-frontier.zip"
        with ZipFile(baseline,"w",ZIP_DEFLATED) as z:
            z.writestr(
                "recovered-source/v309/src/invented/A.java",
                "package invented; public class A {static int a(){return 1;}}")
        output=self.root/"candidate-frontier.zip"
        build_private_four_owner_overlay(
            baseline,[self.source_zip],output,
            baseline_sha256=sha(baseline),
            source_identities=((self.owner+".java",sha(self.source_zip)),),
            expected_baseline_java=1)
        measured=compare_pinned_private_four_owner_javac(
            baseline,output,
            original_sha256=sha(baseline),
            candidate_sha256=sha(output),
            expected_original_count=1,expected_added_count=1)
        self.assertEqual(0,measured["baseline"]["total_compiler_errors"])
        self.assertEqual(0,measured["candidate"]["total_compiler_errors"])
        self.assertEqual(0,measured["compilation_error_delta"])
        self.assertFalse(measured["original_jar_on_compiler_classpath"])


if __name__=="__main__":
    unittest.main()
