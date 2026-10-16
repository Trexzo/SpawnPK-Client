"""R213 unrelated Java9 two-method source parity and mutation rejection.

The fixtures are invented from scratch; hosted tests never access
SpawnPK's original client, donor Java files, system commands or game runtime.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
import unittest

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_readable_spellbook_toggle_methods_r213 import (
    R213ReadableSpellbookCodeError,
    audit_two_readable_methods,
    extract_pinned_source_method,
)


class R213SyntheticReadableToggleSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("JDK9-capable javac required")
        cls.tmp=TemporaryDirectory(prefix="r213-invented-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.before=(
            "package invented;\n"
            "import java.util.List;\n"
            "public class Legacy {\n"
            " public static int saved;\n"
            " public static boolean active;\n"
            " public static List<String> values;\n"
            " public static void m(int code){\n"
            "   if(code==12){saved=code;k();}\n"
            "   if(code==13){if(values.contains(\"X\"))"
            "values.remove(\"X\");else values.add(\"X\"); k();}\n"
            "   if(code==14){active=!active;k();}\n"
            " }\n"
            " public static void k(){\n"
            "   if(active) saved=1;else saved=2;\n"
            " }\n"
            "}\n"
        )
        cls.after=(
            "package invented;\n"
            "import java.util.List;\n"
            "public class Readable {\n"
            " public static int previous;\n"
            " public static boolean enabled;\n"
            " public static List<String> categories;\n"
            " public static void method640(int code){\n"
            "   if(code==12){previous=code;method1241();}\n"
            "   if(code==13){if(categories.contains(\"X\"))"
            "categories.remove(\"X\");else categories.add(\"X\");"
            " method1241();}\n"
            "   if(code==14){enabled=!enabled;method1241();}\n"
            " }\n"
            " public static void method1241(){\n"
            "   if(enabled) previous=1;else previous=2;\n"
            " }\n"
            "}\n"
        )
        cls.original=cls.compile_java("before","Legacy",cls.before)
        cls.readable=cls.compile_java("after","Readable",cls.after)
        probe=profile_class_field_accesses(cls.original)
        counts={}
        for m in probe["methods"]:
            if m["name"] in ("m","k"):
                counts[(m["name"],m["descriptor"])]=len(m["instructions"])
        cls.method_pairs=(
            ("m","(I)V","method640",counts[("m","(I)V")],None),
            ("k","()V","method1241",counts[("k","()V")],None),
        )
        cls.total=sum(r[3] for r in cls.method_pairs)
        cls.aliases={
            ("invented/Legacy","saved","I"):
                ("invented/Readable","previous","I"),
            ("invented/Legacy","active","Z"):
                ("invented/Readable","enabled","Z"),
            ("invented/Legacy","values","Ljava/util/List;"):
                ("invented/Readable","categories","Ljava/util/List;"),
            ("invented/Legacy","k","()V"):
                ("invented/Readable","method1241","()V"),
            ("java/util/List","contains","(Ljava/lang/Object;)Z"):
                ("java/util/List","contains","(Ljava/lang/Object;)Z"),
            ("java/util/List","remove","(Ljava/lang/Object;)Z"):
                ("java/util/List","remove","(Ljava/lang/Object;)Z"),
            ("java/util/List","add","(Ljava/lang/Object;)Z"):
                ("java/util/List","add","(Ljava/lang/Object;)Z"),
        }

    @classmethod
    def compile_java(cls,folder,name,java):
        root=cls.root/folder
        src=root/"src/invented"/(name+".java")
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_text(java,encoding="utf-8")
        empty=root/"empty";out=root/"out"
        empty.mkdir();out.mkdir()
        p=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(out),str(src)],
            capture_output=True,text=True,timeout=60,check=False)
        if p.returncode:
            raise AssertionError("Invented source Javac failed: "+p.stderr)
        return (out/"invented"/(name+".class")).read_bytes()

    def compare(self,compiled=None,**changes):
        kw={
            "method_pairs":self.method_pairs,
            "member_aliases":self.aliases,
            "expected_total":self.total,
        }
        kw.update(changes)
        return audit_two_readable_methods(
            self.original,compiled or self.readable,**kw)

    def test_both_readable_method_bodies_match_under_explicit_renames(self):
        report=self.compare()
        self.assertEqual(2,report["selected_original_method_count"])
        self.assertEqual(self.total,report[
            "original_jvm_instructions_matched"])
        self.assertTrue(report[
            "readable_source_semantic_code_parity_verified"])
        self.assertFalse(report[
            "original_parent_full_class_header_verified"])
        self.assertFalse(report["original_game_code_executed"])

    def test_changed_predicate_rejected(self):
        altered=self.compile_java(
            "wrong-predicate","Readable",self.after.replace(
                "if(code==14)","if(code==15)"))
        with self.assertRaises(R213ReadableSpellbookCodeError):
            self.compare(altered)

    def test_changed_toggle_and_array_list_operation_rejected(self):
        altered=self.compile_java(
            "wrong-toggle","Readable",self.after.replace(
                "enabled=!enabled;","enabled=true;"))
        with self.assertRaises(R213ReadableSpellbookCodeError):
            self.compare(altered)
        altered=self.compile_java(
            "wrong-list","Readable",self.after.replace(
                'categories.remove("X")','categories.add("X")'))
        with self.assertRaises(R213ReadableSpellbookCodeError):
            self.compare(altered)

    def test_wrong_symbolic_field_or_method_map_rejected(self):
        for broken in (
            {**self.aliases,
             ("invented/Legacy","active","Z"):
                ("invented/Readable","previous","Z")},
            {**self.aliases,
             ("invented/Legacy","k","()V"):
                ("invented/Readable","method640","()V")},
        ):
            with self.subTest(broken=broken):
                with self.assertRaises(R213ReadableSpellbookCodeError):
                    self.compare(member_aliases=broken)

    def test_wrong_original_instruction_total_and_method_missing(self):
        with self.assertRaises(R213ReadableSpellbookCodeError):
            self.compare(expected_total=self.total+1)
        with self.assertRaises(R213ReadableSpellbookCodeError):
            self.compare(method_pairs=(
                ("m","(I)V","notThere",self.method_pairs[0][3],None),
                self.method_pairs[1]))

    def test_extracted_java_brace_balance_and_uniqueness(self):
        text="public static void method640(int code) {if(code==1){return;}}"
        self.assertIn("if(code==1){return;}",
                      extract_pinned_source_method(text,"method640"))
        with self.assertRaises(R213ReadableSpellbookCodeError):
            extract_pinned_source_method(
                text.replace("method640","renamed"),"method640")
        with self.assertRaises(R213ReadableSpellbookCodeError):
            extract_pinned_source_method(
                text.replace("return;}}","return;}"),"method640")


if __name__=="__main__":
    unittest.main()
