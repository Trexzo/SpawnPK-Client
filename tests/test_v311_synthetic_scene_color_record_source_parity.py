"""Independent toy Java9 scene-color/override parity; no original v311 game code."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from spk_recovery.standalone_source_parity import StandaloneSourceParityError, verify_standalone_sources

SOURCES = {
 "rs/synthetic90/PaletteEntry.java": """
package rs.synthetic90;
import java.awt.Color;
import java.awt.Polygon;
public final class PaletteEntry {
 public Polygon shape;
 public Color normal;
 public Color selected;
 public Color overlay = new Color(4,6,8,90);
 public boolean active;
 public PaletteEntry(Polygon shape,Color normal,Color selected){
  this.shape=shape;this.normal=normal;this.selected=selected;
 }
 public Color color(){return active?selected:normal;}
 public Color overlay(){return overlay;}
}
""",
 "rs/synthetic90/NamedStamp.java": """
package rs.synthetic90;
public final class NamedStamp {
 public final String base;
 public final long time;
 public String override;
 public NamedStamp(String base,long time){this.base=base;this.time=time;}
 public String name(){return override==null?base:override;}
}
""",
}

PROBE = """
import rs.synthetic90.*;
import java.awt.Color;
import java.awt.Polygon;
public final class Synthetic90SceneTranscript {
 public static void main(String[] ignored){
  int cases=0;
  for(Color foreground:new Color[]{null,Color.BLACK,Color.GREEN}){
   PaletteEntry scene=new PaletteEntry(new Polygon(new int[]{0,2,3},
     new int[]{5,4,1},3),foreground,Color.BLUE);
   System.out.println("DEFAULT:"+(scene.color()==null?"null":scene.color().getRGB())
       +":"+scene.overlay().getRGB());cases++;
   scene.active=true;
   System.out.println("ACTIVE:"+scene.color().getRGB());cases++;
  }
  for(String name:new String[]{null,"","naïve"}){
   NamedStamp item=new NamedStamp(name,Long.MIN_VALUE);
   System.out.println("FALLBACK:"+String.valueOf(item.name())+":"+item.time);cases++;
   item.override="ready";
   System.out.println("OVERRIDE:"+item.name());cases++;
  }
  if(cases!=12)throw new AssertionError("BAD_CASE_COUNT");
 }
}
"""

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def execute(command):
    result=subprocess.run(command,capture_output=True,text=True,timeout=50)
    if result.returncode:
        raise AssertionError(result.stderr[-1200:])
    return result.stdout

@unittest.skipUnless(all(shutil.which(x) for x in ("java","javac","javap")), "JDK9+ required")
class SyntheticSceneRecordParityTests(unittest.TestCase):
    def fixture(self,root:Path):
        source=root/"src"
        for relative,body in SOURCES.items():
            f=source/relative;f.parent.mkdir(parents=True,exist_ok=True)
            f.write_text(body,encoding="utf-8")
        compiled=root/"original";compiled.mkdir()
        execute(["javac","--release","9","-proc:none","-g:none",
            "-classpath",str(root/"empty-classpath"),"-sourcepath",str(root/"empty-sourcepath"),
            "-d",str(compiled),*[str(source/x) for x in sorted(SOURCES)]])
        jar=root/"toy-original.jar"
        with zipfile.ZipFile(jar,"w") as out:
            for f in sorted(compiled.rglob("*.class")):
                out.writestr(f.relative_to(compiled).as_posix(),f.read_bytes())
        with zipfile.ZipFile(jar) as z:
            pins={name:digest(z.read(name)) for name in z.namelist()}
        self.assertEqual(len(pins),2)
        return source,jar,pins

    def test_two_source_closed_classes_and_original_vs_rebuilt_behavior(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source,jar,pins=self.fixture(root)
            report=verify_standalone_sources(jar,source,root/"rebuilt",
                original_sha256=digest(jar.read_bytes()),class_sha256=pins)
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"],2)
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            probe=root/"Synthetic90SceneTranscript.java"
            probe.write_text(PROBE,encoding="utf-8")
            execute(["javac","--release","9","-cp",str(jar),"-d",str(root),str(probe)])
            results=[]
            for cp in (jar,root/"rebuilt"/"classes"):
                results.append(execute(["java","-Djava.awt.headless=true",
                    "-cp",str(root)+os.pathsep+str(cp),"Synthetic90SceneTranscript"]))
            self.assertEqual(results[0],results[1])
            self.assertEqual(len(results[0].splitlines()),12)

    def test_selected_color_instruction_mutation_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source,jar,pins=self.fixture(root)
            path=source/"rs/synthetic90/PaletteEntry.java"
            old=path.read_text()
            changed=old.replace("active?selected:normal","active?overlay:normal")
            self.assertNotEqual(old,changed)
            path.write_text(changed,encoding="utf-8")
            with self.assertRaisesRegex(StandaloneSourceParityError,
                "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH"):
                verify_standalone_sources(jar,source,root/"refused",
                    original_sha256=digest(jar.read_bytes()),class_sha256=pins)

    def test_missing_source_and_bad_original_pin_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source,jar,pins=self.fixture(root)
            with self.assertRaisesRegex(StandaloneSourceParityError,"WRONG_ORIGINAL_JAR"):
                verify_standalone_sources(jar,source,root/"badpin",
                    original_sha256="0"*64,class_sha256=pins)
            (source/"rs/synthetic90/NamedStamp.java").unlink()
            with self.assertRaises(StandaloneSourceParityError):
                verify_standalone_sources(jar,source,root/"missing",
                    original_sha256=digest(jar.read_bytes()),class_sha256=pins)

if __name__=="__main__":
    unittest.main(verbosity=2)
