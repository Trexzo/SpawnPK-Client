"""R223 independent synthetic Java9 source-closure regression suite.

Real game binaries and original-derived Java are NEVER included in Actions.
Hosted fixture mirrors Class170/168/169 and both mode enums using invented
methods, and requires proper isolation of eight NONORIGINAL declarations.
"""
from hashlib import sha256
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from spk_recovery import private_v309_gambling_source_closure_r223 as r223


def digest(text):
    return sha256(text.encode("utf-8")).hexdigest()


class R223InventedRealSources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actual={
            "rs/interfaces/widgets/Class170.java":(
                "package rs.interfaces.widgets;"
                "import rs.interfaces.WidgetComponent;"
                "import rs.graphics.HitsplatFont;"
                "public class Class170 extends Widget {"
                "public static boolean field3530;"
                "public static final rs.scriptpacket.Class260 packet=new Class168();"
                "public static final rs.graphics.hud.Overlay overlay=new Class169();"
                "public Class170(HitsplatFont[] f){super(f);}"
                "public void register(){createArchiveSpriteButton("
                "1,2,3,4,5,\"sample\",6,7,\"close\");}"
                "}"
            ),
            "rs/interfaces/widgets/Class168.java":(
                "package rs.interfaces.widgets;"
                "public class Class168 extends rs.scriptpacket.Class260 {"
                "public void handlePacket(){int x=method2463();"
                "Class170.field3530=(x>0);}}"
            ),
            "rs/interfaces/widgets/Class169.java":(
                "package rs.interfaces.widgets;"
                "import rs.Client;"
                "import rs.graphics.hud.Class69;"
                "public class Class169 extends rs.graphics.hud.Overlay {"
                "public void method1484(){}"
                "public boolean method3175(Client c){return Class170.field3530;}"
                "public void method1640(Client c,Class69 mode){}"
                "public void method904(){}"
                "}"
            ),
            "rs/graphics/hud/Class69.java":(
                "package rs.graphics.hud;"
                "public enum Class69 {A,B;}"
            ),
            "rs/pkg39/Class53.java":(
                "package rs.pkg39;"
                "public enum Class53 {A,B,C;}"
            ),
        }
        cls.pins={key:digest(value) for key,value in cls.actual.items()}
        cls.baseline={
            "rs/interfaces/widgets/Class179.java":(
                "package rs.interfaces.widgets;"
                "import rs.graphics.HitsplatFont;"
                "public class Class179 extends Widget {"
                "public Class179(HitsplatFont[] f){super(f);}"
                "public void register(){Class170 c=new Class170(this.fonts);}"
                "}"
            ),
            "rs/interfaces/widgets/Widget.java":(
                "package rs.interfaces.widgets;"
                "import rs.graphics.HitsplatFont;"
                "import rs.interfaces.WidgetComponent;"
                "public abstract class Widget extends WidgetComponent {"
                "protected HitsplatFont[] fonts;"
                "public Widget(HitsplatFont[] f){fonts=f;}"
                "public abstract void register();}"
            ),
            "rs/interfaces/widgets/Class176.java":(
                "package rs.interfaces.widgets;public enum Class176 {A;}"
            ),
            "rs/interfaces/widgets/Class177.java":(
                "package rs.interfaces.widgets;public enum Class177 {A;}"
            ),
            "rs/interfaces/widgets/Class178.java":(
                "package rs.interfaces.widgets;public enum Class178 {A;}"
            ),
            "rs/interfaces/widgets/Class170.java":(
                "package rs.interfaces.widgets;public class Class170 {}"
            ),
            "rs/interfaces/WidgetComponent.java":(
                "package rs.interfaces; import rs.graphics.Sprite;"
                " import rs.graphics.HitsplatFont;"
                " public class WidgetComponent {"
                " public int scrollHeight,height,width,mouseOverLayer;"
                " public void setChild(int a,int b,int c,int d){}"
                " }"
            ),
            "rs/graphics/Sprite.java":(
                "package rs.graphics;public class Sprite {"
                "public Sprite(String p){} }"
            ),
            "rs/graphics/HitsplatFont.java":(
                "package rs.graphics;public class HitsplatFont {}"
            ),
            "rs/Client.java":(
                "package rs;public class Client {"
                "public static int[] tabInterfaceIds;}"
            ),
            "rs/Configuration.java":(
                "package rs;public class Configuration {"
                "public static void saveSettings(){} }"
            ),
            "rs/gui/Launcher.java":(
                "package rs.gui;public class Launcher {}"
            ),
        }
        assert len(cls.baseline)==12

    def integrated(self,actual=None,base=None):
        with patch.object(r223,"ADDITIONAL_REAL",self.pins):
            return r223.augment_fake_only_sources(
                self.baseline if base is None else base,
                self.actual if actual is None else actual)

    def test_five_genuine_fixture_java_owners_eight_fake_stubs(self):
        sources=self.integrated()
        self.assertEqual(18,len(sources))
        self.assertEqual(9,r223.ALL_REAL_COUNT)
        self.assertEqual(8,r223.NONORIGINAL_SUPPORT_COUNT)
        for name,java in self.actual.items():
            self.assertEqual(java,sources[name])
        for name,java in r223.TEMPORARY_API_CLASSES.items():
            self.assertEqual(java,sources[name])
        self.assertIn("createArchiveSpriteButton",
                      sources["rs/interfaces/WidgetComponent.java"])
        self.assertNotIn("createArchiveSpriteButton",
                         sources["rs/interfaces/widgets/Widget.java"])

    def test_java9_compiles_18_invented_source_files(self):
        if not shutil.which("javac"):
            self.skipTest("JDK required")
        source=self.integrated()
        with TemporaryDirectory(prefix="spk-r223-synthetic-") as td:
            root=Path(td);src=root/"src";out=root/"classes";empty=root/"empty"
            out.mkdir();empty.mkdir()
            paths=[]
            for filename,content in source.items():
                f=src/filename
                f.parent.mkdir(parents=True,exist_ok=True)
                f.write_text(content,encoding="utf-8")
                paths.append(str(f))
            built=subprocess.run(
                ["javac","--release","9","-g:none","-proc:none",
                 "-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(out),*paths],
                capture_output=True,text=True,timeout=90,check=False)
            self.assertEqual(0,built.returncode,built.stderr)
            self.assertEqual(
                {name[:-5]+".class" for name in source},
                {f.relative_to(out).as_posix() for f in out.rglob("*.class")})

    def test_modified_real_source_or_fake_owner_rejected(self):
        bad=dict(self.actual)
        bad["rs/interfaces/widgets/Class170.java"]+="// altered"
        with self.assertRaises(r223.R223ReadableDependencyClosureError):
            self.integrated(actual=bad)
        incomplete=dict(self.actual)
        del incomplete["rs/pkg39/Class53.java"]
        with self.assertRaises(r223.R223ReadableDependencyClosureError):
            self.integrated(actual=incomplete)
        old=dict(self.baseline)
        old["rs/interfaces/WidgetComponent.java"]=old[
            "rs/interfaces/WidgetComponent.java"].replace(
                "mouseOverLayer","mouseOverOther")
        with self.assertRaises(r223.R223ReadableDependencyClosureError):
            self.integrated(base=old)

    def test_wrong_source_inventory_rejected(self):
        incomplete=dict(self.baseline)
        del incomplete["rs/interfaces/widgets/Class170.java"]
        with self.assertRaises(r223.R223ReadableDependencyClosureError):
            self.integrated(base=incomplete)
        duplicate=dict(self.baseline)
        duplicate["rs/pkg39/Class53.java"]="fake previously"
        with self.assertRaises(r223.R223ReadableDependencyClosureError):
            self.integrated(base=duplicate)

    def test_exact_private_input_digests_required(self):
        with TemporaryDirectory() as td:
            fake=Path(td)/"fake-client.jar"
            fake.write_bytes(b"not original")
            with self.assertRaises(r223.R223ReadableDependencyClosureError):
                r223.verify_private_r223_source_closure(fake,fake,fake)


if __name__=="__main__":
    unittest.main()
