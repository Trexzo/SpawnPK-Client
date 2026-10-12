"""R81 strict whole-method JVM operands: identity and mutation vetoes."""
import copy
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.whole_method_operand_parity import (
    WholeMethodOperandError, compare_all_method_operands,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class StrictOriginalOperandTests(unittest.TestCase):
    @staticmethod
    def compiled_fixture(path: Path) -> dict:
        src = path/"p"/"Fixture.java"
        out = path/"classes"
        src.parent.mkdir(parents=True, exist_ok=True)
        out.mkdir(parents=True, exist_ok=True)
        src.write_text(
            'package p; public class Fixture {'
            'public static int value;'
            'public static String text;'
            'public static void restore() {'
            ' try {'
            '   String local="value-key";'
            '   if(local.length()>2) value=Integer.valueOf("42").intValue();'
            '   text = "val=" + value;'
            ' } catch (Exception ignored) {}'
            ' }'
            '}', encoding="utf-8")
        cmd = ["javac","--release","9","-g:none","-proc:none",
               "-d",str(out),str(src)]
        run = subprocess.run(cmd, capture_output=True, text=True)
        if run.returncode:
            raise RuntimeError(run.stdout+run.stderr)
        jar = path/"original.jar"
        with ZipFile(jar,"w") as z:
            z.write(out/"p"/"Fixture.class","p/Fixture.class")
        return profile_jar_class(jar,"p/Fixture.class")

    @staticmethod
    def aliases():
        return [
            {"original":{"name":"value","descriptor":"I"},
             "candidate":{"name":"value","descriptor":"I"}},
            {"original":{"name":"text","descriptor":"Ljava/lang/String;"},
             "candidate":{"name":"text","descriptor":"Ljava/lang/String;"}},
        ]

    def compare(self, source, target, aliases=None):
        return compare_all_method_operands(
            source,"restore","()V",target,"restore","()V",
            self.aliases() if aliases is None else aliases, [], [])

    def test_exact_fixture_and_invokedynamic_semantics(self):
        with tempfile.TemporaryDirectory() as tmp:
            original=self.compiled_fixture(Path(tmp))
            report=self.compare(original,copy.deepcopy(original))
            self.assertTrue(report["all_parsed_JVM_operands_equal_with_private_aliases"])
            self.assertTrue(report["original_invokedynamic_bootstrap_semantics_equal"])
            self.assertFalse(report["runtime_equivalence_certified"])
            self.assertFalse(report["all_original_helper_method_bodies_equivalent"])

    def test_changed_original_String_literal_fails_even_if_R66_shape_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            original=self.compiled_fixture(Path(tmp))
            candidate=copy.deepcopy(original)
            method=next(m for m in candidate["methods"] if m["name"]=="restore")
            literal=next(x for x in method["instructions"]
                         if x.get("constant") == "value-key")
            literal["constant"]="forged-key"
            with self.assertRaisesRegex(WholeMethodOperandError,
                                        "JVM_OPERAND_SEMANTIC_MISMATCH"):
                self.compare(original,candidate)

    def test_changed_original_local_index_and_bootstrap_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            original=self.compiled_fixture(Path(tmp))
            candidate=copy.deepcopy(original)
            method=next(m for m in candidate["methods"] if m["name"]=="restore")
            local=next(x for x in method["instructions"] if "local_index" in x)
            local["local_index"]+=1
            with self.assertRaisesRegex(WholeMethodOperandError,
                                        "JVM_OPERAND_SEMANTIC_MISMATCH"):
                self.compare(original,candidate)
            candidate=copy.deepcopy(original)
            self.assertTrue(candidate["bootstrap_methods"])
            candidate["bootstrap_methods"][0]["bootstrap_method"]["name"]="forged"
            with self.assertRaisesRegex(WholeMethodOperandError,
                                        "JVM_OPERAND_SEMANTIC_MISMATCH"):
                self.compare(original,candidate)

    def test_modified_read_field_member_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            original=self.compiled_fixture(Path(tmp))
            candidate=copy.deepcopy(original)
            method=next(m for m in candidate["methods"] if m["name"]=="restore")
            read=next(x for x in method["instructions"] if x.get("opcode")=="0xb2")
            read["name"]="forged_read"
            with self.assertRaisesRegex(WholeMethodOperandError,
                                        "JVM_OPERAND_SEMANTIC_MISMATCH"):
                self.compare(original,candidate)

    def test_R66_structural_veto_precedes_operand_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            original=self.compiled_fixture(Path(tmp))
            candidate=copy.deepcopy(original)
            method=next(m for m in candidate["methods"] if m["name"]=="restore")
            method["instructions"][0]["opcode"]="0xb1"
            with self.assertRaisesRegex(WholeMethodOperandError,
                                        "R66_WHOLE_METHOD_STRUCTURAL_PARITY_FAILED"):
                self.compare(original,candidate)


if __name__=="__main__":
    unittest.main()
