"""R217 cross-platform unrelated Java9 source tests; never execute game code.

Java9 compiles synthetic lunar/ancient analogues, checks all bytecode Code
rows, branch/offset/operands, and rejects altered arithmetic, loops, member
identities and SHA-protected provenance. No original proprietary Java/JAR
exists in hosted CI.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
import unittest

from spk_recovery.private_v309_readable_spellbook_layouts_r217 import (
    R217ReadableLayoutError,
    audit_layout_methods,
    extract_existing_method,
    normalize_ancient_compiler_shape,
    verify_pinned_real_readable_layouts,
    METHOD_DETAILS,
)
from spk_recovery.private_v309_readable_spellbook_long_filter_r214 import (
    parse_javap_code,
)


class R217InventedLayoutsJava9(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac") or not shutil.which("javap"):
            raise unittest.SkipTest("JDK9-capable javac/javap required")
        cls.temp=TemporaryDirectory(prefix="spk-r217-unrelated-layouts-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name)
        cls.p_body=(
            "    int[] cells={11,22,33};\n"
            "    for(int index=0;index<cells.length;index++){\n"
            "      System.out.println(cells[index]);\n"
            "    }\n"
        )
        cls.n_body=(
            "    int var6=13;int var7=6;\n"
            "    int var8=var6;int var9=var7;\n"
            "    if(var7>0){var8 += 4;var9 += 2;}\n"
            "    System.out.println(var8+var9);\n"
        )
        cls.original=cls.compile_java("legacy","Legacy",
            "public void p(){\n"+cls.p_body+"}\n"
            "public void n(){\n"+cls.n_body+"}\n")
        cls.readable=cls.compile_java("readable","Readable",
            "public void method1712(){\n"+cls.p_body+"}\n"
            "public void method3532(){\n"+cls.n_body+"}\n")
        cls.expected={}
        cls.total=0
        for readable,old in (("method1712","p"),("method3532","n")):
            rows=parse_javap_code(cls.original,"public void "+old+"();")
            cls.total+=len(rows)
            cls.expected[readable]={
                "original":old,"operations":len(rows),
                "last_offset":rows[-1][0],"aliases":{},
            }

    @classmethod
    def compile_java(cls,label,owner,source):
        base=cls.root/label
        file=base/"src"/"invented"/(owner+".java")
        file.parent.mkdir(parents=True,exist_ok=True)
        file.write_text("package invented;\n"
                        "public class "+owner+" {\n"+source+"}\n")
        out=base/"out";empty=base/"empty"
        out.mkdir();empty.mkdir()
        result=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-implicit:none","-classpath",str(empty),
             "-sourcepath",str(empty),"-d",str(out),str(file)],
            capture_output=True,text=True,timeout=60,check=False)
        if result.returncode:
            raise AssertionError("Invented JDK9 fixture failed: "+
                                 result.stderr)
        return subprocess.run([
            "javap","-p","-c","-classpath",str(out),
            "invented."+owner],
            capture_output=True,text=True,check=True,timeout=25).stdout

    def compare(self,readable=None,**changes):
        settings={"details":self.expected,"expected_total":self.total}
        settings.update(changes)
        return audit_layout_methods(
            self.original,readable or self.readable,**settings)

    def test_all_two_invented_methods_match_offsets_and_operands(self):
        report=self.compare()
        self.assertEqual({"p()","n()"},set(report))
        self.assertEqual(self.total,sum(
            x["matched_original_jvm_instructions"]
            for x in report.values()))
        self.assertTrue(all(x["all_original_offsets_branches_and_operands_match"]
                            for x in report.values()))

    def test_wrong_layout_loop_operand_rejected(self):
        mutation=self.compile_java(
            "changed-loop","Readable",
            "public void method1712(){\n"+
            self.p_body.replace("index<cells.length","index<2")+"}\n"
            "public void method3532(){\n"+self.n_body+"}\n")
        with self.assertRaises(R217ReadableLayoutError):
            self.compare(mutation)

    def test_wrong_ancient_conditional_rejected(self):
        mutation=self.compile_java(
            "changed-conditional","Readable",
            "public void method1712(){\n"+self.p_body+"}\n"
            "public void method3532(){\n"+
            self.n_body.replace("if(var7>0)","if(var7<0)")+"}\n")
        with self.assertRaises(R217ReadableLayoutError):
            self.compare(mutation)

    def test_extra_arithmetic_or_symbolic_alias_rejected(self):
        mutation=self.compile_java(
            "changed-increment","Readable",
            "public void method1712(){\n"+self.p_body+"}\n"
            "public void method3532(){\n"+
            self.n_body.replace("var8 += 4","var8 += 5")+"}\n")
        with self.assertRaises(R217ReadableLayoutError):
            self.compare(mutation)
        altered={k:dict(v) for k,v in self.expected.items()}
        altered["method1712"]["aliases"]={"unused/mapping":"fake"}
        with self.assertRaises(R217ReadableLayoutError):
            self.compare(details=altered)

    def test_exact_two_compiler_normalizations_and_refusal(self):
        original=(
            "public void method3532(){\n"
            " var8 = var6 + 4;\n var9 = var7 + 2;\n}\n"
        )
        normalized=normalize_ancient_compiler_shape(original,pin=False)
        self.assertIn("var8 += 4;",normalized)
        self.assertIn("var9 += 2;",normalized)
        self.assertNotIn("var6 + 4",normalized)
        with self.assertRaises(R217ReadableLayoutError):
            normalize_ancient_compiler_shape(original)
        with self.assertRaises(R217ReadableLayoutError):
            normalize_ancient_compiler_shape(
                original.replace("var6 + 4","var6 + 7"),pin=False)
        with self.assertRaises(R217ReadableLayoutError):
            normalize_ancient_compiler_shape(
                original.replace("var9 = var7 + 2;",""),pin=False)

    def test_pinned_real_readable_source_extraction_and_duplicates(self):
        fixtures={
            "method1712":"public void method1712(){int a=1;}",
            "method3532":"public void method3532(){int b=2;}",
        }
        for name,source in fixtures.items():
            self.assertIn("public void "+name,
                          extract_existing_method(source,name))
            with self.assertRaises(R217ReadableLayoutError):
                extract_existing_method(source+"\n"+source,name)
            with self.assertRaises(R217ReadableLayoutError):
                extract_existing_method(
                    source.replace(name,"unknownMethod"),name)
        self.assertEqual(487,METHOD_DETAILS["method1712"]["operations"])
        self.assertEqual(419,METHOD_DETAILS["method3532"]["operations"])
        self.assertEqual(3,len(METHOD_DETAILS["method1712"]["aliases"]))
        self.assertEqual(8,len(METHOD_DETAILS["method3532"]["aliases"]))

    def test_forged_private_original_binary_rejected(self):
        fake=self.root/"invented-not-client.jar"
        fake.write_bytes(b"no original client")
        with self.assertRaises(R217ReadableLayoutError):
            verify_pinned_real_readable_layouts(fake,fake)


if __name__=="__main__":
    unittest.main()
