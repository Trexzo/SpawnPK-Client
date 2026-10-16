"""R215 independently invented Java9 constructor + default initializer tests.

The hosted fixtures contain no original SpawnPK source or JAR. They compile
a tiny unrelated Java class, remap its displayed javap member labels, and
confirm that exact 4+13 instruction comparison fails on semantic changes.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
import unittest

from spk_recovery.private_v309_readable_spellbook_constructor_initializer_r215 import (
    R215OriginalReadableInitializerError,
    audit_constructor_and_initializer,
    extract_exact_readable_constructor,
    extract_original_static_initializer_declarations,
    verify_pinned_original_readable_constructor_clinit,
)
from spk_recovery.private_v309_readable_spellbook_long_filter_r214 import (
    R214OriginalReadableFilterError,
)


class R215SyntheticReadableConstructorAndDefaults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac") or not shutil.which("javap"):
            raise unittest.SkipTest("JDK javac/javap unavailable")
        cls.tmp=TemporaryDirectory(prefix="r215-invented-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.body=(
            "package invented;\n"
            "import java.util.*;\n"
            "public class Readable extends Parent {\n"
            " public static int field3645 = 0;\n"
            " public static boolean field3646 = true;\n"
            " public static boolean field3647 = true;\n"
            " public static final List<Type> field3648 = new ArrayList();\n"
            " private static int field3656 = -1;\n"
            " public Readable(Font[] var1) { super(var1); }\n"
            "}\n"
        )
        cls.javap_text=cls.compile_java("baseline",cls.body)
        cls.good_readable=cls.rename_readable(cls.javap_text)
        cls.good_original=cls.rename_original(cls.good_readable)

    @classmethod
    def compile_java(cls,folder,source):
        root=cls.root/folder
        data={
            "invented/Readable.java":source,
            "invented/Parent.java":(
                "package invented; public class Parent {"
                "public Parent(Font[] f){} }"),
            "invented/Font.java":"package invented; public class Font {}",
            "invented/Type.java":"package invented; public enum Type {A;}",
        }
        paths=[]
        for name,java in data.items():
            p=root/"src"/name
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(java,encoding="utf-8")
            paths.append(str(p))
        output=root/"classes"
        empty=root/"empty"
        output.mkdir();empty.mkdir()
        built=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-implicit:none","-classpath",str(empty),
             "-sourcepath",str(empty),"-d",str(output),*paths],
            capture_output=True,text=True,timeout=60,check=False)
        if built.returncode:
            raise AssertionError("Invented Java9 source failed: "+built.stderr)
        return subprocess.run(
            ["javap","-p","-c","-classpath",str(output),
             "invented.Readable"],
            capture_output=True,text=True,check=True,timeout=30).stdout

    @staticmethod
    def rename_readable(text):
        return text.replace(
            "public invented.Readable(invented.Font[]);",
            "public rs.interfaces.widgets.Class179(rs.graphics.HitsplatFont[]);"
        ).replace(
            'Method invented/Parent."<init>":([Linvented/Font;)V',
            'Method rs/interfaces/widgets/Widget."<init>":([Lrs/graphics/HitsplatFont;)V'
        )

    @staticmethod
    def rename_original(text):
        return (
            text.replace(
                "public rs.interfaces.widgets.Class179(rs.graphics.HitsplatFont[]);",
                "public rs.n.c.ap(rs.l.K[]);"
            ).replace(
                'Method rs/interfaces/widgets/Widget."<init>":([Lrs/graphics/HitsplatFont;)V',
                'Method rs/n/c."<init>":([Lrs/l/K;)V'
            ).replace("Field field3645:I","Field c:I")
             .replace("Field field3646:Z","Field d:Z")
             .replace("Field field3647:Z","Field e:Z")
             .replace("Field field3648:Ljava/util/List;",
                      "Field f:Ljava/util/List;")
             .replace("Field field3656:I","Field bQ:I")
        )

    def test_real_javac_fixture_exact_four_and_thirteen_operations(self):
        result=audit_constructor_and_initializer(
            self.good_original,self.good_readable)
        self.assertEqual(4,result[
            "original_constructor_jvm_instructions_matched"])
        self.assertEqual(13,result[
            "original_static_initializer_jvm_instructions_matched"])
        self.assertEqual(17,result["total_original_jvm_instructions_matched"])
        self.assertTrue(result[
            "five_original_runtime_default_assignments_matched"])
        self.assertFalse(result["full_original_spelled_class_abi_accepted"])

    def test_changed_initial_boolean_rejected(self):
        invalid=self.compile_java(
            "changed-default",self.body.replace(
                "field3647 = true;","field3647 = false;"))
        with self.assertRaises(R215OriginalReadableInitializerError):
            audit_constructor_and_initializer(
                self.good_original,self.rename_readable(invalid))

    def test_changed_static_field_order_rejected(self):
        original=(
            " public static boolean field3646 = true;\n"
            " public static boolean field3647 = true;"
        )
        reversed_lines=(
            " public static boolean field3647 = true;\n"
            " public static boolean field3646 = true;"
        )
        changed=self.compile_java(
            "changed-default-order",self.body.replace(original,reversed_lines))
        with self.assertRaises(R215OriginalReadableInitializerError):
            audit_constructor_and_initializer(
                self.good_original,self.rename_readable(changed))

    def test_constructor_super_descriptor_rejected(self):
        changed=self.good_readable.replace(
            'Method rs/interfaces/widgets/Widget."<init>":([Lrs/graphics/HitsplatFont;)V',
            'Method invented/Wrong."<init>":([Lrs/graphics/HitsplatFont;)V')
        with self.assertRaises(R215OriginalReadableInitializerError):
            audit_constructor_and_initializer(self.good_original,changed)

    def test_donor_constructor_and_initializer_source_extraction(self):
        src=self.body.replace("Readable","Class179").replace(
            "Font[] var1","HitsplatFont[] var1").replace(
            "List<Type>","List<Class176>")
        constructor=extract_exact_readable_constructor(src)
        self.assertIn("super(var1);",constructor)
        fields=extract_original_static_initializer_declarations(src)
        self.assertEqual(5,len(fields))
        self.assertEqual([
            "field3645","field3646","field3647","field3648","field3656"],
            [item.split("=")[0].split()[-1].strip() for item in fields])

    def test_missing_field_initializer_is_rejected(self):
        with self.assertRaises(R215OriginalReadableInitializerError):
            extract_original_static_initializer_declarations(
                self.body.replace("field3656 = -1;","field3656 = 0;"))
        with self.assertRaises(R215OriginalReadableInitializerError):
            extract_original_static_initializer_declarations(
                self.body.replace("field3648 = new ArrayList();",
                                  "field3648 = null;"))

    def test_duplicate_or_missing_readable_constructor_rejected(self):
        src=self.body.replace("Readable","Class179").replace(
            "Font[] var1","HitsplatFont[] var1").replace(
            "List<Type>","List<Class176>")
        with self.assertRaises(R215OriginalReadableInitializerError):
            extract_exact_readable_constructor(src+
                " public Class179(HitsplatFont[] var1) {super(var1);}")
        with self.assertRaises(R215OriginalReadableInitializerError):
            extract_exact_readable_constructor(src.replace(
                "public Class179(","public Other("))

    def test_private_sha_gate_rejects_forged_original_binary(self):
        with TemporaryDirectory() as tmp:
            fake=Path(tmp)/"unrelated.jar"
            fake.write_bytes(b"not a client JAR")
            with self.assertRaises(R215OriginalReadableInitializerError):
                verify_pinned_original_readable_constructor_clinit(fake,fake)


if __name__=="__main__":
    unittest.main()
