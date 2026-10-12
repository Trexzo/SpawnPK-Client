"""R94: real javac9 ten-method fixture and per-member source mutation gates."""
import copy
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile
from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.private_all_owner_methods_parity import (
    AllOwnerMethodsParityError,prove_all_original_nonclinit_methods,
)

@unittest.skipUnless(shutil.which("javac"),"javac required")
class AllOwnerMethodParityTests(unittest.TestCase):
    def fixture(self):
        tmp=tempfile.TemporaryDirectory()
        root=Path(tmp.name);src=root/"src";out=root/"classes"
        files={
          "p/Owner.java":(
            'package p; public final class Owner {'
            'public static int[] array = new int[2];'
            'public static boolean flag;'
            'private static void save(){}'
            'public static void load(){System.out.println("load");}'
            'public static void register(){p.Registrar.add("save",Owner::save);}'
            'public static boolean first(){return false;}'
            'public static boolean second(){return false;}'
            'public static boolean delegate(){return first();}'
            'public static void toggle(boolean value){if(value){flag=true;}else{flag=false;}}'
            'public static void write(){array[0]=1;array[1]=2;}'
            '}'),
          "p/Action.java":(
            'package p; @FunctionalInterface public interface Action {void invoke();}'),
          "p/Registrar.java":(
            'package p; public final class Registrar {'
            'public static void add(String name,Action fn){} }')
        }
        for path,data in files.items():
            f=src/path;f.parent.mkdir(parents=True,exist_ok=True)
            f.write_text(data,encoding="utf-8")
        out.mkdir()
        run=subprocess.run(["javac","--release","9","-g:none","-proc:none",
                            "-d",str(out)]+[str(src/x) for x in files],
                           capture_output=True,text=True)
        if run.returncode:raise AssertionError(run.stderr)
        jar=root/"test.jar"
        with ZipFile(jar,"w") as z:
            for f in out.rglob("*.class"):
                z.write(f,f.relative_to(out).as_posix())
        profile=profile_jar_class(jar,"p/Owner.class")
        return tmp,profile
    def test_all_nine_original_ordinary_members_identity(self):
        tmp,original=self.fixture()
        try:
            report=prove_all_original_nonclinit_methods(
                original,copy.deepcopy(original))
            self.assertEqual(report["original_owner_total_method_declarations"],10)
            self.assertEqual(report["original_ordinary_methods_parity_checked"],9)
            self.assertTrue(report["R66_and_R81_parity_passed_all_nine_ordinary_methods"])
            self.assertFalse(report["whole_client_runtime_equivalence_certified"])
        finally:tmp.cleanup()
    def test_only_lambda_bootstrap_target_or_string_mutation_rejects(self):
        tmp,original=self.fixture()
        try:
            forged=copy.deepcopy(original)
            method=next(m for m in forged["methods"]
                        if m["name"]=="register")
            method["instructions"][0]["constant"]="tampered"
            with self.assertRaisesRegex(AllOwnerMethodsParityError,
                                        "R66_R81_ORIGINAL_OWNER"):
                prove_all_original_nonclinit_methods(original,forged)
            forged=copy.deepcopy(original)
            forged["bootstrap_methods"][0]["arguments"][1][
                "method_handle"]["name"]="invented"
            with self.assertRaisesRegex(AllOwnerMethodsParityError,
                                        "R66_R81_ORIGINAL_OWNER"):
                prove_all_original_nonclinit_methods(original,forged)
        finally:tmp.cleanup()
    def test_missing_original_member_or_changed_boolean_veto(self):
        tmp,original=self.fixture()
        try:
            forged=copy.deepcopy(original)
            forged["methods"]=[m for m in forged["methods"]
                               if m["name"]!="delegate"]
            with self.assertRaisesRegex(AllOwnerMethodsParityError,
                                        "TEN_METHOD_DECLARATIONS_NOT_EXACT"):
                prove_all_original_nonclinit_methods(original,forged)
            forged=copy.deepcopy(original)
            next(m for m in forged["methods"] if m["name"]=="first")[
                "instructions"][0]["opcode"]="0x04"
            with self.assertRaisesRegex(AllOwnerMethodsParityError,
                                        "R66_R81_ORIGINAL_OWNER"):
                prove_all_original_nonclinit_methods(original,forged)
        finally:tmp.cleanup()

if __name__=="__main__":
    unittest.main()
