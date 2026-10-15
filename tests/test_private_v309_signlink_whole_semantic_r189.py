"""R189 source-only synthetic constant-pool width normalization regressions.

Two invented, non-SpawnPK Java9 source orders compile to the SAME JVM
operations and exception control-flow, with ldc→ldc_w and changed byte
offsets. Negative cases prove no constant, branch, exception type, field or
method inventory mutation is normalized away. No original game binary here.
"""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_signlink_whole_semantic_r189 import (
    R189SignlinkWholeSourceSemanticError,
    audit_original_owner_semantic_classfiles,
)


class R189SyntheticConstantPoolSemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("JDK required")
        cls.tmp=TemporaryDirectory(prefix="r189-invented-cp-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.header=(
            "package synthetic;\n"
            "public class N {\n"
            "  private static int v;\n"
        )
        cls.focus=(
            "  public static String focus(){\n"
            "    try {\n"
            "      if(v<0)throw new IllegalArgumentException(\"NEGATIVE\");\n"
            "      return \"FOCUS\";\n"
            "    }catch(IllegalArgumentException ex){\n"
            "      return \"FALLBACK\";\n"
            "    }\n"
            "  }\n"
        )
        cls.fillers="".join(
            "  public static void x%03d(){v=1;}\n" % x
            for x in range(125))
        cls.original=cls.compile_java("synthetic-old",
            cls.header+cls.focus+cls.fillers+"}\n")
        cls.rebuilt=cls.compile_java("synthetic-reordered",
            cls.header+cls.fillers+cls.focus+"}\n")
        profile_old=profile_class_field_accesses(cls.original)
        profile_new=profile_class_field_accesses(cls.rebuilt)
        cls.method_count=len(profile_old["methods"])
        cls.instruction_count=sum(
            len(m["instructions"]) for m in profile_old["methods"])
        cls.widenings=sum(
            1 for old,new in zip(
                sorted(profile_old["methods"],
                       key=lambda m:(m["name"],m["descriptor"])),
                sorted(profile_new["methods"],
                       key=lambda m:(m["name"],m["descriptor"])))
            for a,b in zip(old["instructions"],new["instructions"])
            if a["opcode"]=="0x12" and b["opcode"]=="0x13")
        if cls.widenings<1:
            raise AssertionError(
                "Unrelated Java9 fixture did not induce ldc width change")

    @classmethod
    def compile_java(cls,directory,source):
        root=cls.root/directory
        src=root/"src/synthetic/N.java"
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_text(source,encoding="utf-8")
        out=root/"classes"
        empty=root/"empty"
        out.mkdir()
        empty.mkdir()
        p=subprocess.run([
            "javac","--release","9","-g:none","-proc:none","-implicit:none",
            "-classpath",str(empty),"-sourcepath",str(empty),
            "-d",str(out),str(src)],
            capture_output=True,text=True,timeout=90,check=False)
        if p.returncode:
            raise AssertionError("Synthetic compilation failed: "+p.stderr)
        return (out/"synthetic/N.class").read_bytes()

    def verify(self,binary=None,**changes):
        binary=binary or self.rebuilt
        args={
            "expected_total_methods":self.method_count,
            "expected_total_instructions":self.instruction_count,
            "expected_ldc_widenings":self.widenings,
            "expected_owner":"synthetic/N",
            "expected_original_class_sha256":
                hashlib.sha256(self.original).hexdigest(),
        }
        args.update(changes)
        return audit_original_owner_semantic_classfiles(
            self.original,binary,**args)

    def test_all_methods_cp_resolved_semantically_equivalent(self):
        output=self.verify()
        self.assertEqual(self.method_count,
                         output["methods_semantically_recompiled_in_one_java_class"])
        self.assertEqual(self.instruction_count,
                         output["resolved_original_jvm_instructions_compared"])
        self.assertEqual(self.widenings,
                         output["only_ldc_to_ldc_w_opcode_encoding_differences"])
        self.assertTrue(output["all_method_signatures_flags_and_core_semantics_match"])
        self.assertTrue(output["all_declared_field_abi_and_constant_values_match"])
        self.assertFalse(output["all_original_byte_offsets_and_classfile_bytes_identical"])
        self.assertFalse(output[
            "stackmap_semantic_equivalence_or_jvm_verifier_acceptance_proved"])
        self.assertFalse(output["original_runtime_validated"])
        self.assertFalse(output["complete_original_client_compiled"])

    def test_changed_literal_cannot_hide_behind_ldc_width(self):
        mutated=self.compile_java("synthetic-changed-string",
            self.header+self.fillers+
            self.focus.replace('"FOCUS"','"CHANGED"')+"}\n")
        with self.assertRaises(R189SignlinkWholeSourceSemanticError):
            self.verify(mutated)

    def test_changed_branch_is_rejected(self):
        mutated=self.compile_java("synthetic-changed-condition",
            self.header+self.fillers+
            self.focus.replace("if(v<0)","if(v<=0)")+"}\n")
        with self.assertRaises(R189SignlinkWholeSourceSemanticError):
            self.verify(mutated)

    def test_changed_exception_handler_catch_type_is_rejected(self):
        mutated=self.compile_java("synthetic-changed-catch",
            self.header+self.fillers+
            self.focus.replace(
                "catch(IllegalArgumentException ex)",
                "catch(RuntimeException ex)")+"}\n")
        with self.assertRaises(R189SignlinkWholeSourceSemanticError):
            self.verify(mutated)

    def test_changed_field_modifiers_are_rejected(self):
        mutated=self.compile_java("synthetic-public-field",
            self.header.replace("private static int v",
                                "public static int v")+
            self.fillers+self.focus+"}\n")
        with self.assertRaises(R189SignlinkWholeSourceSemanticError):
            self.verify(mutated)

    def test_missing_method_fails_even_if_other_code_equivalent(self):
        mutated=self.compile_java("synthetic-missing-method",
            self.header+self.fillers.replace(
                "  public static void x024(){v=1;}\n","")+
            self.focus+"}\n")
        with self.assertRaises(R189SignlinkWholeSourceSemanticError):
            self.verify(mutated)

    def test_wrong_original_digest_and_expected_ldc_count_rejected(self):
        for opts in (
            {"expected_original_class_sha256":"0"*64},
            {"expected_ldc_widenings":self.widenings+1},
            {"expected_total_instructions":self.instruction_count+1},
            {"expected_total_methods":self.method_count+1},
        ):
            with self.subTest(opts=opts):
                with self.assertRaises(R189SignlinkWholeSourceSemanticError):
                    self.verify(**opts)


if __name__=="__main__":
    unittest.main()
