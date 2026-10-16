"""R219 invented Java9 regression tests, NOT original game Java.

No original client binaries/source included on hosted CI. The synthetic
original/readable class builds verify strict offset, instruction, control-
flow and symbolic matching while rejecting mutations and fake SHA inputs.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
import unittest

from spk_recovery.private_v309_readable_spellbook_final_methods_r219 import (
    R219OriginalReadableMethodsError,
    METHODS,
    audit_real_method_pair,
    extract_existing_method,
    verify_pinned_final_two_parent_methods,
)
from spk_recovery.private_v309_readable_spellbook_long_filter_r214 import (
    parse_javap_code,
)


class R219SyntheticRemainingSpellbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac") or not shutil.which("javap"):
            raise unittest.SkipTest("JDK9-capable javac and javap required")
        cls.tmp=TemporaryDirectory(prefix="r219-invented-java-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.source_a=(
            " int[] vals={2,3,5};\n"
            " for(int i=0;i<vals.length;i++){\n"
            "  System.out.println(vals[i]);\n"
            " }\n"
        )
        cls.source_m=(
            " int[] cells={4,7,9};\n"
            " int total=0;\n"
            " for(int v:cells)total+=v;\n"
            " System.out.println(total);\n"
        )
        cls.original=cls.compiled(
            "legacy","Legacy",
            "public void a(){"+cls.source_a+"}\n"
            "public void m(){"+cls.source_m+"}\n")
        cls.readable=cls.compiled(
            "readable","Readable",
            "public void register(){"+cls.source_a+"}\n"
            "public void method2352(){"+cls.source_m+"}\n")
        cls.expected={}
        for readable,original in (("register","a"),("method2352","m")):
            ops=parse_javap_code(
                cls.original,"public void "+original+"();")
            cls.expected[readable]={
                "original":original,"ops":len(ops),
                "last":ops[-1][0],"aliases":{},
            }

    @classmethod
    def compiled(cls,label,name,body):
        root=cls.root/label
        source=root/"src"/"invented"/(name+".java")
        source.parent.mkdir(parents=True,exist_ok=True)
        source.write_text(
            "package invented;\npublic class "+name+"{\n"+body+"}\n")
        out=root/"classes";empty=root/"empty"
        out.mkdir();empty.mkdir()
        result=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-implicit:none","-classpath",str(empty),
             "-sourcepath",str(empty),"-d",str(out),str(source)],
            capture_output=True,text=True,check=False,timeout=60)
        if result.returncode:
            raise AssertionError("Synthetic Javac failed: "+result.stderr)
        return subprocess.run(
            ["javap","-p","-c","-classpath",str(out),
             "invented."+name],
            capture_output=True,text=True,check=True,timeout=30).stdout

    def compare(self,selected,candidate=None,**changes):
        options={"selected_method":selected,
                 "expected":self.expected}
        options.update(changes)
        return audit_real_method_pair(
            self.original,candidate or self.readable,**options)

    def test_both_original_to_readable_code_bodies_match(self):
        for name in ("register","method2352"):
            with self.subTest(name=name):
                proof=self.compare(name)
                self.assertEqual(
                    self.expected[name]["ops"],
                    proof["original_jvm_instructions_verified"])
                self.assertTrue(proof[
                    "all_instruction_offsets_branches_and_symbolic_operands_match"])
                self.assertFalse(proof[
                    "actual_existing_readable_java_source_modified"])

    def test_changed_classic_array_initialization_rejected(self):
        mutant=self.compiled(
            "array-changed","Readable",
            "public void register(){"+self.source_a+"}\n"
            "public void method2352(){"+
            self.source_m.replace("{4,7,9}","{4,7,10}")+"}\n")
        with self.assertRaises(R219OriginalReadableMethodsError):
            self.compare("method2352",mutant)

    def test_changed_registration_loop_limit_rejected(self):
        mutant=self.compiled(
            "registration-changed","Readable",
            "public void register(){"+
            self.source_a.replace("i<vals.length","i<2")+"}\n"
            "public void method2352(){"+self.source_m+"}\n")
        with self.assertRaises(R219OriginalReadableMethodsError):
            self.compare("register",mutant)

    def test_wrong_member_map_and_expected_count_rejected(self):
        altered={x:dict(y) for x,y in self.expected.items()}
        altered["register"]["aliases"]={"unseen":"unexpected"}
        with self.assertRaises(R219OriginalReadableMethodsError):
            self.compare("register",expected=altered)
        altered={x:dict(y) for x,y in self.expected.items()}
        altered["method2352"]["ops"]+=1
        with self.assertRaises(R219OriginalReadableMethodsError):
            self.compare("method2352",expected=altered)

    def test_existing_readable_source_extraction_rejects_duplicates(self):
        examples={
            "register":"public void register(){int x=10;}",
            "method2352":"public void method2352(){int z=3;}",
        }
        for name,body in examples.items():
            with self.subTest(name=name):
                self.assertIn(name,extract_existing_method(body,name))
                with self.assertRaises(R219OriginalReadableMethodsError):
                    extract_existing_method(body+"\n"+body,name)
                with self.assertRaises(R219OriginalReadableMethodsError):
                    extract_existing_method(
                        body.replace(name,"different"),name)
        self.assertEqual(438,METHODS["register"]["ops"])
        self.assertEqual(1580,METHODS["method2352"]["ops"])
        self.assertEqual(21,len(METHODS["register"]["aliases"]))
        self.assertEqual(23,len(METHODS["method2352"]["aliases"]))

    def test_forged_original_binary_sha_pin_rejected(self):
        fake=self.root/"fake-client.jar"
        fake.write_bytes(b"not original v309")
        with self.assertRaises(R219OriginalReadableMethodsError):
            verify_pinned_final_two_parent_methods(fake,fake)


if __name__=="__main__":
    unittest.main()
