"""R218 synthetic-only Java9 source/JVM regression tests.

Tests use invented toy source, JDK9 compilation and javap. The actual
original SpawnPK JAR and decompiled source are NEVER present in hosted CI.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
import unittest

from spk_recovery.private_v309_readable_lunar_spells_r218 import (
    R218ReadableLunarSpellError,
    ALIASES,
    UNMODIFIED_METHOD_SHA256,
    audit_original_lunar_spells,
    extract_real_lunar_spells_method,
    verify_pinned_real_readable_lunar_spells,
)
from spk_recovery.private_v309_readable_spellbook_long_filter_r214 import (
    parse_javap_code,
)


class R218InventedLunarDefinitionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac") or not shutil.which("javap"):
            raise unittest.SkipTest("Java9 compiler and javap required")
        cls.temp=TemporaryDirectory(prefix="r218-invented-java-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name)
        cls.original_source=(
            "public void o(){\n"
            " p();\n"
            " for(int k=0;k<4;k++){\n"
            "  System.out.println(\"Moon\"+k);\n"
            " }\n"
            "}\n"
            "public void p(){}\n"
        )
        cls.readable_source=(
            "public void method892(){\n"
            " method1712();\n"
            " for(int k=0;k<4;k++){\n"
            "  System.out.println(\"Moon\"+k);\n"
            " }\n"
            "}\n"
            "public void method1712(){}\n"
        )
        cls.before=cls.compile_and_inspect(
            "legacy","Legacy",cls.original_source)
        cls.after=cls.compile_and_inspect(
            "readable","Readable",cls.readable_source)
        rows=parse_javap_code(cls.before,"public void o();")
        cls.count=len(rows)
        cls.last_offset=rows[-1][0]
        cls.symbols={"Method p:()V":"Method method1712:()V"}

    @classmethod
    def compile_and_inspect(cls,tag,name,source):
        root=cls.root/tag
        src=root/"src"/"toy"/(name+".java")
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_text("package toy;\n"
                       "public class "+name+" {\n"+source+"}\n")
        out=root/"out";empty=root/"empty"
        out.mkdir();empty.mkdir()
        built=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-implicit:none","-classpath",str(empty),
             "-sourcepath",str(empty),"-d",str(out),str(src)],
            capture_output=True,text=True,timeout=60,check=False)
        if built.returncode:
            raise AssertionError("Invented Java9 source failed: "+built.stderr)
        return subprocess.run([
            "javap","-p","-c","-classpath",str(out),"toy."+name],
            capture_output=True,text=True,timeout=30,check=True).stdout

    def compare(self,rebuilt=None,**changes):
        kwargs={
            "original_title":"public void o();",
            "readable_title":"public void method892();",
            "aliases":self.symbols,
            "expected_instructions":self.count,
            "expected_last_offset":self.last_offset,
        }
        kwargs.update(changes)
        return audit_original_lunar_spells(
            self.before,rebuilt or self.after,**kwargs)

    def test_invented_original_to_readable_method_code_matches(self):
        result=self.compare()
        self.assertEqual(self.count,
                         result["matched_original_jvm_instructions"])
        self.assertEqual(1,
                         result["distinct_original_to_readable_aliases_exercised"])
        self.assertTrue(result[
            "exact_offsets_opcodes_operands_and_branch_targets"])
        self.assertFalse(result["existing_readable_method_source_edited"])
        self.assertFalse(result["original_game_code_executed"])

    def test_changed_iteration_limit_rejected(self):
        mutant=self.compile_and_inspect(
            "limit-change","Readable",
            self.readable_source.replace("k<4","k<5"))
        with self.assertRaises(R218ReadableLunarSpellError):
            self.compare(mutant)

    def test_changed_call_target_rejected(self):
        mutant=self.compile_and_inspect(
            "invocation-change","Readable",
            self.readable_source.replace(
                "method1712();","other();")+"public void other(){}\n")
        with self.assertRaises(R218ReadableLunarSpellError):
            self.compare(mutant)

    def test_bad_symbolic_alias_and_instruction_count_rejected(self):
        with self.assertRaises(R218ReadableLunarSpellError):
            self.compare(aliases={"Method p:()V":"Method wrong:()V"})
        with self.assertRaises(R218ReadableLunarSpellError):
            self.compare(aliases={})
        with self.assertRaises(R218ReadableLunarSpellError):
            self.compare(expected_instructions=self.count+1)

    def test_real_source_extraction_and_method_uniqueness(self):
        data="class A{\n public void method892(){int x=1;}\n}"
        text=extract_real_lunar_spells_method(data)
        self.assertIn("method892()",text)
        with self.assertRaises(R218ReadableLunarSpellError):
            extract_real_lunar_spells_method(data+data)
        with self.assertRaises(R218ReadableLunarSpellError):
            extract_real_lunar_spells_method(
                data.replace("method892","methodOther"))
        self.assertEqual(8,len(ALIASES))
        self.assertEqual(64,len(UNMODIFIED_METHOD_SHA256))

    def test_private_binary_pin_rejects_unrelated_file(self):
        fake=self.root/"not-original.jar"
        fake.write_bytes(b"NOT ORIGINAL")
        with self.assertRaises(R218ReadableLunarSpellError):
            verify_pinned_real_readable_lunar_spells(fake,fake)


if __name__=="__main__":
    unittest.main()
