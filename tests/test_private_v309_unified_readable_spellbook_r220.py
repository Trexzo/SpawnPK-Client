"""R220 synthetic JDK9 / JVM instruction semantics tests.

No original client JAR or original-derived source in hosted CI. Tests
exercise real JDK9 compiled unrelated Java and exact synthetic JVM
disassemblies to ensure ldc_w byte-width normalization, branch ordinal
matching, member alias SHA pins and five-edit source constraints fail closed.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

from spk_recovery.private_v309_unified_readable_spellbook_r220 import (
    R220UnifiedSpellbookError,
    METHOD_SPECS,
    audit_single_class_method_code,
    reconstruct_only_pinned_compiler_shape,
    verify_pinned_single_compiled_class,
)

SHA_EMPTY=hashlib.sha256(b"{}").hexdigest()
SHA_RENAME=hashlib.sha256(json.dumps(
    {"Method a:()V":"Method renamed:()V"},
    sort_keys=True,separators=(",",":")).encode()).hexdigest()


class R220InventedUnifiedClassSemantics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac") or not shutil.which("javap"):
            raise unittest.SkipTest("JDK javac/javap required")
        cls.tmp=TemporaryDirectory(prefix="spk-r220-invented-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        body=(
            "package unrelated;\n"
            "public class Sample {\n"
            " public static int[] vals={3,5};\n"
            " public void register(){\n"
            "  for(int k=0;k<vals.length;k++)System.out.println(vals[k]);\n"
            " }\n"
            "}\n"
        )
        src=cls.root/"src/unrelated/Sample.java"
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_text(body)
        out=cls.root/"classes"
        empty=cls.root/"empty"
        out.mkdir();empty.mkdir()
        p=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-implicit:none","-classpath",str(empty),
             "-sourcepath",str(empty),"-d",str(out),str(src)],
            capture_output=True,text=True,check=False,timeout=60)
        if p.returncode:
            raise AssertionError(p.stderr)
        cls.javap=subprocess.run(
            ["javap","-p","-c","-classpath",str(out),
             "unrelated.Sample"],
            capture_output=True,text=True,check=True,timeout=30).stdout

    def test_actual_javac_method_semantics_compare_with_self(self):
        from spk_recovery.private_v309_readable_spellbook_long_filter_r214 import (
            parse_javap_code,
        )
        row=parse_javap_code(self.javap,"public void register();")
        branch=sum(x[1].startswith("if") or x[1].startswith("goto")
                   for x in row)
        spec=(("public void register();","public void register();",
               len(row),0,branch,0,SHA_EMPTY),)
        result=audit_single_class_method_code(
            self.javap,self.javap,methods=spec,
            require_full_inventory=False)
        self.assertEqual(len(row),result["verified_original_jvm_instructions"])
        self.assertEqual(0,result["only_ldc_to_ldc_w_opcode_changes"])
        self.assertTrue(result[
            "full_class_original_jvm_code_equivalent_under_verified_renames"])

    def test_ldc_to_ldc_w_and_branch_target_index_allowed(self):
        before=(
            "public void a();\n"
            "    Code:\n"
            "       0: ldc           #3 // String moon\n"
            "       2: goto          6\n"
            "       5: iconst_0\n"
            "       6: return\n"
        )
        after=(
            "public void method();\n"
            "    Code:\n"
            "       0: ldc_w         #300 // String moon\n"
            "       3: goto          7\n"
            "       6: iconst_0\n"
            "       7: return\n"
        )
        spec=(("public void a();","public void method();",
               4,1,1,0,SHA_EMPTY),)
        report=audit_single_class_method_code(
            before,after,methods=spec,require_full_inventory=False)
        self.assertEqual(1,report["only_ldc_to_ldc_w_opcode_changes"])

    def test_branch_target_wrong_index_is_rejected(self):
        before=(
            "public void a();\n    Code:\n"
            "       0: ldc           #3 // String moon\n"
            "       2: goto          6\n"
            "       5: iconst_0\n"
            "       6: return\n"
        )
        after=(
            "public void method();\n    Code:\n"
            "       0: ldc_w         #300 // String moon\n"
            "       3: goto          6\n"
            "       6: iconst_0\n"
            "       7: return\n"
        )
        spec=(("public void a();","public void method();",
               4,1,1,0,SHA_EMPTY),)
        with self.assertRaises(R220UnifiedSpellbookError):
            audit_single_class_method_code(
                before,after,methods=spec,require_full_inventory=False)

    def test_symbolic_member_mapping_digest_is_required(self):
        original=(
            "public void a();\n    Code:\n"
            "       0: invokestatic  #12 // Method a:()V\n"
            "       3: return\n"
        )
        new=(
            "public void renamed();\n    Code:\n"
            "       0: invokestatic  #200 // Method renamed:()V\n"
            "       3: return\n"
        )
        good=(("public void a();","public void renamed();",
               2,0,0,1,SHA_RENAME),)
        result=audit_single_class_method_code(
            original,new,methods=good,require_full_inventory=False)
        self.assertEqual(1,result["verified_member_aliases_across_methods"])
        bad=(("public void a();","public void renamed();",
              2,0,0,1,SHA_EMPTY),)
        with self.assertRaises(R220UnifiedSpellbookError):
            audit_single_class_method_code(
                original,new,methods=bad,require_full_inventory=False)

    def test_non_symbolic_operand_change_and_other_opcode_rejected(self):
        src=("public void a();\n    Code:\n"
             "       0: bipush        5\n       2: return\n")
        changed=src.replace("bipush        5","bipush        6")
        spec=(("public void a();","public void a();",
               2,0,0,0,SHA_EMPTY),)
        with self.assertRaises(R220UnifiedSpellbookError):
            audit_single_class_method_code(
                src,changed,methods=spec,require_full_inventory=False)
        changed=src.replace("bipush","sipush")
        with self.assertRaises(R220UnifiedSpellbookError):
            audit_single_class_method_code(
                src,changed,methods=spec,require_full_inventory=False)

    def test_actual_full_fourteen_method_manifest_has_correct_totals(self):
        self.assertEqual(14,len(METHOD_SPECS))
        self.assertEqual(4314,sum(x[2] for x in METHOD_SPECS))
        self.assertEqual(178,sum(x[3] for x in METHOD_SPECS))
        self.assertEqual(125,sum(x[5] for x in METHOD_SPECS))
        self.assertEqual(14,len({x[0] for x in METHOD_SPECS}))
        self.assertEqual(14,len({x[1] for x in METHOD_SPECS}))

    def test_unpinned_source_cannot_be_silently_normalized(self):
        with self.assertRaises((R220UnifiedSpellbookError,ValueError)):
            reconstruct_only_pinned_compiler_shape(
                "class Invention{}",enforce_sha=True)
        with self.assertRaises((R220UnifiedSpellbookError,ValueError)):
            reconstruct_only_pinned_compiler_shape(
                "public static void method2689(Class178 x){}",
                enforce_sha=False)

    def test_original_source_and_binary_shas_fail_closed(self):
        fake=self.root/"unrelated-not-v309.jar"
        fake.write_bytes(b"not client")
        with self.assertRaises(R220UnifiedSpellbookError):
            verify_pinned_single_compiled_class(
                fake,fake,fake,fake)


if __name__=="__main__":
    unittest.main()
