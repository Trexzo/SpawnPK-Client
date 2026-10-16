"""R214 unrelated Java9 invented class comparison and adversarial tests.

The actual original v309 client JAR / source are NOT present in hosted CI.
These tests ensure the reported 243-instruction private acceptance cannot
follow solely from a method-name list or an unchecked opcode count.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
import unittest

from spk_recovery.private_v309_readable_spellbook_long_filter_r214 import (
    R214OriginalReadableFilterError,
    SYMBOL_ALIASES,
    ORIGINAL_METHOD_BODY_SHA256,
    COMPILER_NORMALIZED_BODY_SHA256,
    compare_full_original_readable_code,
    extract_actual_donor_method,
    normalize_existing_method_for_original_javac,
    parse_javap_code,
    verify_pinned_v309_readable_long_filter_method,
)


class R214InventedLongMethodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac") or not shutil.which("javap"):
            raise unittest.SkipTest("JDK9 javac/javap required")
        cls.tmp=TemporaryDirectory(prefix="r214-independent-invented-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.donor=(
            "   public static void method2689(Category var0) {\n"
            "      if (field3646) {\n"
            "         if (var0 == Category.UTILITY) {\n"
            "            ArrayList var2 = new ArrayList();\n"
            "            ArrayList var3 = new ArrayList();\n"
            "            if (var2.size() > 2) {\n"
            "               var3.add(10);\n"
            "            }\n"
            "         }\n"
            "      }\n"
            "   }"
        )
        cls.normalized=normalize_existing_method_for_original_javac(
            cls.donor,require_pin=False)
        cls.common=(
            "package invented;\n"
            "import java.util.*;\n"
            "public class Example {\n"
            " public static boolean field3646;\n"
        )
        cls.enum="package invented; public enum Category {UTILITY, OTHER;}"
        cls.old=cls.build("old",cls.common+cls.normalized+"\n}\n")
        cls.new=cls.build("new",cls.common+cls.normalized+"\n}\n")
        cls.a=cls.javap("old")
        cls.b=cls.javap("new")
        cls.title="public static void method2689(invented.Category);"
        cls.rows=parse_javap_code(cls.a,cls.title)

    @classmethod
    def build(cls,folder,source):
        root=cls.root/folder
        src=root/"src/invented/Example.java"
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_text(source,encoding="utf-8")
        cat=root/"src/invented/Category.java"
        cat.write_text(cls.enum,encoding="utf-8")
        out=root/"classes";empty=root/"empty"
        out.mkdir();empty.mkdir()
        result=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-implicit:none","-classpath",str(empty),
             "-sourcepath",str(empty),"-d",str(out),str(src),str(cat)],
            capture_output=True,text=True,timeout=60,check=False)
        if result.returncode:
            raise AssertionError("Invented Java9 source compilation failed: "+
                                 result.stderr)
        return out

    @classmethod
    def javap(cls,folder):
        out=cls.root/folder/"classes"
        return subprocess.run(
            ["javap","-p","-c","-classpath",str(out),
             "invented.Example"],
            capture_output=True,text=True,check=True,timeout=30).stdout

    def proof(self,old=None,new=None,**params):
        return compare_full_original_readable_code(
            old or self.a,new or self.b,
            original_title=self.title,
            readable_title=self.title,
            aliases={},
            expected_instructions=len(self.rows),
            expected_last_offset=self.rows[-1][0],
            **params,
        )

    def test_one_guard_and_two_list_decl_normalization(self):
        self.assertIn("if (!field3646) return;",self.normalized)
        self.assertIn("List var2 = new ArrayList();",self.normalized)
        self.assertIn("List var3 = new ArrayList();",self.normalized)
        self.assertNotIn("if (field3646) {",self.normalized)
        self.assertNotIn("ArrayList var2 =",self.normalized)
        result=self.proof()
        self.assertTrue(result[
            "matched_original_byte_offsets_opcodes_and_operands"])
        self.assertTrue(result["all_branch_target_addresses_equal"])

    def test_changed_conditional_branch_rejected(self):
        body=self.normalized.replace(
            "if (var0 == Category.UTILITY)",
            "if (var0 != Category.UTILITY)")
        self.build("wrong-conditional",self.common+body+"\n}\n")
        with self.assertRaises(R214OriginalReadableFilterError):
            self.proof(new=self.javap("wrong-conditional"))

    def test_untyped_arraylist_virtual_invocation_rejected(self):
        body=self.normalized.replace(
            "List var3 = new ArrayList();",
            "ArrayList var3 = new ArrayList();")
        self.build("arraylist-drift",self.common+body+"\n}\n")
        with self.assertRaises(R214OriginalReadableFilterError):
            self.proof(new=self.javap("arraylist-drift"))

    def test_wrong_method_invocation_or_edited_literal_rejected(self):
        body=self.normalized.replace(
            "var3.add(10)","var3.clear()")
        self.build("wrong-invoke",self.common+body+"\n}\n")
        with self.assertRaises(R214OriginalReadableFilterError):
            self.proof(new=self.javap("wrong-invoke"))

    def test_unknown_symbolic_alias_is_rejected(self):
        with self.assertRaises(R214OriginalReadableFilterError):
            compare_full_original_readable_code(
                self.a,self.b,
                original_title=self.title,readable_title=self.title,
                aliases={"not/used/symbol":"missing"},
                expected_instructions=len(self.rows),
                expected_last_offset=self.rows[-1][0])
        self.assertEqual(16,len(SYMBOL_ALIASES))

    def test_compiler_normalization_rejects_arbitrary_nonpinned_method(self):
        with self.assertRaises(R214OriginalReadableFilterError):
            normalize_existing_method_for_original_javac(self.donor)
        for corrupted in (
            self.donor.replace("field3646","differentFlag"),
            self.donor.replace("ArrayList var3","List var3"),
            self.donor.replace("if (field3646) {","while (field3646) {"),
            self.donor[:-1],
        ):
            with self.subTest(mutant=corrupted[-45:]):
                with self.assertRaises(R214OriginalReadableFilterError):
                    normalize_existing_method_for_original_javac(
                        corrupted,require_pin=False)
        self.assertEqual(64,len(ORIGINAL_METHOD_BODY_SHA256))
        self.assertEqual(64,len(COMPILER_NORMALIZED_BODY_SHA256))

    def test_missing_or_duplicated_source_method_rejected(self):
        content="class A {\n"+self.donor+"\n}\n"
        self.assertEqual(self.donor,
                         extract_actual_donor_method(content))
        with self.assertRaises(R214OriginalReadableFilterError):
            extract_actual_donor_method(content+self.donor)
        with self.assertRaises(R214OriginalReadableFilterError):
            extract_actual_donor_method(
                content.replace("method2689","changedName"))

    def test_private_original_binary_hash_guard_rejects_forged_jar(self):
        fake=self.root/"unrelated.jar"
        fake.write_bytes(b"not original SpawnPK")
        with self.assertRaises(R214OriginalReadableFilterError):
            verify_pinned_v309_readable_long_filter_method(
                fake,fake)


if __name__=="__main__":
    unittest.main()
