"""R222 unrelated Java9 source replacement and fail-closed provenance tests.

Original SpawnPK source and JAR are NOT present in hosted CI. Invented
Java fixture validates moving 19 temporary static builders from a fake
Widget to fake WidgetComponent while compiling an actual (invented)
separately supplied Widget + 3 enums and subclass.
"""
import ast
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from spk_recovery import private_v309_spellbook_real_dependencies_r222 as r222


class R222SyntheticDependencySourceClosure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real={
            "Widget":(
                "package rs.interfaces.widgets;"
                "import rs.interfaces.WidgetComponent;"
                "import rs.graphics.HitsplatFont;"
                "public abstract class Widget extends WidgetComponent {"
                "protected HitsplatFont[] fonts;"
                "public Widget(HitsplatFont[] f){this.fonts=f;}"
                "public abstract void register();}"
            ),
            "Class176":"package rs.interfaces.widgets;public enum Class176 {A,B,C;}",
            "Class177":(
                "package rs.interfaces.widgets;public enum Class177 {"
                "A(Class176.A),B(Class176.B);"
                "public final Class176 type;"
                "Class177(Class176 t){this.type=t;}}"
            ),
            "Class178":"package rs.interfaces.widgets;public enum Class178 {A,B,C;}",
        }
        cls.fake={
            "rs/interfaces/widgets/Widget.java":(
                "package rs.interfaces.widgets;"
                "import rs.interfaces.WidgetComponent;"
                "import rs.graphics.HitsplatFont;"
                "public class Widget extends WidgetComponent {"
                "public Widget(HitsplatFont[] f){}"
                " public static WidgetComponent createPanelWidget(int n)"
                "{return null;}"
                + "".join(
                    f" public static void builder{i}(int n){{}}"
                    for i in range(18))
                + " }"
            ),
            "rs/interfaces/WidgetComponent.java":(
                "package rs.interfaces; import rs.graphics.Sprite;"
                " public class WidgetComponent {"
                " public int foo; }"
            ),
            "rs/graphics/HitsplatFont.java":"package rs.graphics;public class HitsplatFont {}",
            "rs/graphics/Sprite.java":"package rs.graphics;public class Sprite {}",
            "rs/interfaces/widgets/Class176.java":"package rs.interfaces.widgets;public enum Class176 {D;}",
            "rs/interfaces/widgets/Class177.java":"package rs.interfaces.widgets;public class Class177 {}",
            "rs/interfaces/widgets/Class178.java":"package rs.interfaces.widgets;public class Class178 {}",
            "rs/interfaces/widgets/Class170.java":"package rs.interfaces.widgets;public class Class170 {}",
            "rs/gui/Launcher.java":"package rs.gui;public class Launcher {}",
            "rs/Client.java":"package rs;public class Client {}",
            "rs/Configuration.java":"package rs;public class Configuration {}",
        }
        assert len(cls.fake)==11
        cls.pins={k:hashlib.sha256(v.encode()).hexdigest()
                  for k,v in cls.real.items()}

    def integrated(self):
        with patch.object(r222,"REPLACEMENTS",self.pins):
            return r222.integrate_actual_readable_dependencies(
                self.fake,self.real)

    def test_four_real_owners_replace_four_not_all_helpers(self):
        result=self.integrated()
        self.assertEqual(11,len(result))
        for owner,text in self.real.items():
            self.assertEqual(
                text,result[f"rs/interfaces/widgets/{owner}.java"])
        self.assertEqual(19,result[
            "rs/interfaces/WidgetComponent.java"].count("public static "))
        self.assertEqual(7,r222.REMAINING_COMPILER_ONLY_OWNERS)
        self.assertEqual(4,len(r222.REPLACEMENTS))

    def test_real_java9_sources_compile_with_inherited_static_builders(self):
        if not shutil.which("javac"):
            self.skipTest("JDK required")
        result=self.integrated()
        result["rs/interfaces/widgets/Class179.java"]=(
            "package rs.interfaces.widgets;"
            "import rs.interfaces.WidgetComponent;"
            "import rs.graphics.HitsplatFont;"
            "public class Class179 extends Widget {"
            "public Class179(HitsplatFont[] fonts){super(fonts);}"
            "public void register(){"
            "WidgetComponent x=createPanelWidget(1);"
            "builder1(1);"
            "if(x!=null){this.foo=1;}}"
            "public Class176 category(){return Class176.A;}"
            "public Class178 mode(){return Class178.B;}"
            "public Class177 group(){return Class177.A;}"
            "}"
        )
        with TemporaryDirectory(prefix="r222-invented-") as tmp:
            root=Path(tmp);src=root/"src";out=root/"classes"
            empty=root/"empty";out.mkdir();empty.mkdir()
            paths=[]
            for relative,data in result.items():
                file=src/relative;file.parent.mkdir(parents=True,exist_ok=True)
                file.write_text(data)
                paths.append(str(file))
            process=subprocess.run(
                ["javac","--release","9","-g:none","-proc:none",
                 "-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(out),*paths],
                capture_output=True,text=True,timeout=60,check=False)
            self.assertEqual(0,process.returncode,process.stderr)
            self.assertEqual(
                {key[:-5]+".class" for key in result},
                {p.relative_to(out).as_posix() for p in out.rglob("*.class")})

    def test_literal_only_helper_dictionary_parsing(self):
        script="H="+repr(self.fake)+"\n"
        self.assertEqual(self.fake,
                         r222.read_fake_template_ast(script.encode()))
        with self.assertRaises(r222.R222DependencyClosureError):
            r222.read_fake_template_ast(
                b"H = {'bad': dangerous_call()}\n")
        with self.assertRaises(r222.R222DependencyClosureError):
            r222.read_fake_template_ast(
                (script+"H="+repr(self.fake)).encode())

    def test_nonmatching_source_or_builder_count_rejected(self):
        wrong={**self.real,"Class176":
               self.real["Class176"].replace("{A,B,C;}","{A,C,B;}")}
        with patch.object(r222,"REPLACEMENTS",self.pins):
            with self.assertRaises(r222.R222DependencyClosureError):
                r222.integrate_actual_readable_dependencies(self.fake,wrong)
        bad=dict(self.fake)
        bad["rs/interfaces/widgets/Widget.java"]=bad[
            "rs/interfaces/widgets/Widget.java"].replace(
                " public static void builder17(int n){}","")
        with patch.object(r222,"REPLACEMENTS",self.pins):
            with self.assertRaises(r222.R222DependencyClosureError):
                r222.integrate_actual_readable_dependencies(bad,self.real)

    def test_private_inputs_are_required_before_any_build(self):
        with TemporaryDirectory(prefix="r222-bad-") as td:
            fake=Path(td)/"not-real-original.jar"
            fake.write_bytes(b"unrelated")
            with self.assertRaises(r222.R222DependencyClosureError):
                r222.verify_private_real_widget_and_enums(fake,fake,fake)


if __name__=="__main__":
    unittest.main()
