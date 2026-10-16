"""R216 unrelated invented Java9 UI-panel fixture and negative regression tests.

No SpawnPK JAR or original Java is used by hosted CI. Test Java methods
are compiled, disassembled, compared and discarded without execution.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
import unittest

from spk_recovery.private_v309_readable_spellbook_filter_panel_r216 import (
    R216ReadablePanelError,
    METHOD_SHA256,
    extract_panel_method,
    audit_panel_code,
    verify_private_original_panel,
)
from spk_recovery.private_v309_readable_spellbook_long_filter_r214 import (
    parse_javap_code,
)


class R216InventedPanelSourceProof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac") or not shutil.which("javap"):
            raise unittest.SkipTest("JDK required")
        cls.tmp=TemporaryDirectory(prefix="r216-invented-panel-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.method=(
            "  public void method1592() {\n"
            "    WidgetComponent panel=createPanelWidget(123);\n"
            "    panel.allocateChildren(2);\n"
            "    createDirectSpriteTextButton(124,\"icon\",\"filter\");\n"
            "    createOverlayTextOptionWidget(125,\"test\",this.fonts,0,10);\n"
            "    panel.setChild(0,124,12,22);\n"
            "    panel.setChild(1,125,30,31);\n"
            "  }\n"
        )
        cls.parent=(
            "package toy;\n"
            "public class WidgetComponent {\n"
            "  public void allocateChildren(int x){}\n"
            "  public void setChild(int a,int b,int c,int d){}\n"
            "  public static WidgetComponent createPanelWidget(int x)"
            " {return null;}\n"
            "  public static void createDirectSpriteTextButton("
            "int a,String b,String c){}\n"
            "  public static void createOverlayTextOptionWidget("
            "int a,String b,Font[] c,int d,int e){}\n"
            "}\n"
        )
        cls.source=(
            "package toy;\n"
            "public class Readable extends WidgetComponent {\n"
            "  protected Font[] fonts;\n"
            +cls.method+
            "}\n"
        )
        cls.out=cls.compile("base",cls.source,cls.parent)
        cls.original_javap=cls.inspect(cls.out)
        cls.rows=parse_javap_code(
            cls.original_javap,"public void method1592();")

    @classmethod
    def compile(cls,tag,source,parent):
        root=cls.root/tag
        data={
            "toy/Readable.java":source,
            "toy/WidgetComponent.java":parent,
            "toy/Font.java":"package toy;public class Font{}",
        }
        files=[]
        for path,body in data.items():
            dest=root/"src"/path
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(body)
            files.append(str(dest))
        out=root/"out";empty=root/"empty"
        out.mkdir();empty.mkdir()
        result=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(out),*files],
            capture_output=True,text=True,timeout=60,check=False)
        if result.returncode:
            raise AssertionError(result.stderr)
        return out

    @classmethod
    def inspect(cls,out):
        return subprocess.run([
            "javap","-p","-c","-classpath",str(out),
            "toy.Readable"],capture_output=True,text=True,
            check=True,timeout=25).stdout

    def compare(self,new,**changes):
        options={
            "original_title":"public void method1592();",
            "readable_title":"public void method1592();",
            "aliases":{},
            "expected_instructions":len(self.rows),
            "last_offset":self.rows[-1][0],
        }
        options.update(changes)
        return audit_panel_code(self.original_javap,new,**options)

    def test_original_and_rebuilt_invented_panel_match(self):
        result=self.compare(self.original_javap)
        self.assertEqual(len(self.rows),result["matched_jvm_instructions"])
        self.assertTrue(result[
            "all_original_code_offsets_branches_equal"])
        self.assertFalse(result["donor_java_method_modified"])
        self.assertFalse(result["game_executed"])

    def test_changed_panel_child_coordinates_rejected(self):
        altered=self.compile(
            "changed-child",self.source.replace(
                "panel.setChild(0,124,12,22)",
                "panel.setChild(0,124,12,23)"),self.parent)
        with self.assertRaises(R216ReadablePanelError):
            self.compare(self.inspect(altered))

    def test_wrong_factory_return_type_and_spurious_pop_rejected(self):
        # Returning a value from a call used as a statement emits a POP
        # and must NOT be silently accepted as an equivalent source ABI.
        altered=self.compile(
            "return-type-drift",self.source,
            self.parent.replace(
                "public static void createDirectSpriteTextButton("
                "int a,String b,String c){}",
                "public static WidgetComponent createDirectSpriteTextButton("
                "int a,String b,String c){return null;}"))
        with self.assertRaises(R216ReadablePanelError):
            self.compare(self.inspect(altered))

    def test_wrong_source_call_order_rejected(self):
        changed=self.source.replace(
            "panel.setChild(0,124,12,22);\n"
            "    panel.setChild(1,125,30,31);",
            "panel.setChild(1,125,30,31);\n"
            "    panel.setChild(0,124,12,22);")
        altered=self.compile("order-drift",changed,self.parent)
        with self.assertRaises(R216ReadablePanelError):
            self.compare(self.inspect(altered))

    def test_unexpected_alias_and_count_rejected(self):
        with self.assertRaises(R216ReadablePanelError):
            self.compare(self.original_javap,
                         aliases={"unseen":"other"})
        with self.assertRaises(R216ReadablePanelError):
            self.compare(self.original_javap,
                         expected_instructions=len(self.rows)+1)

    def test_verbatim_source_method_extraction(self):
        raw="class A {\n"+self.method+"}\n"
        self.assertEqual(self.method,extract_panel_method(raw))
        with self.assertRaises(R216ReadablePanelError):
            extract_panel_method(raw+self.method)
        with self.assertRaises(R216ReadablePanelError):
            extract_panel_method(raw.replace(
                "method1592","anotherMethod"))
        self.assertEqual(64,len(METHOD_SHA256))

    def test_private_fingerprint_gate_rejects_forged_binary(self):
        fake=self.root/"fake-original.jar"
        fake.write_bytes(b"unrelated")
        with self.assertRaises(R216ReadablePanelError):
            verify_private_original_panel(fake,fake)


if __name__=="__main__":
    unittest.main()
