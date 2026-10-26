"""Independently authored Java9 synthetic menu/config event parity fixtures.

No v311 game binary, reconstructed Java source, game constants or assets.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from spk_recovery.standalone_source_parity import (
    StandaloneSourceParityError, verify_standalone_sources,
)

SOURCES = {
 "rs/syntheticmenu80/WindowShown.java": """package rs.syntheticmenu80;
public final class WindowShown {
 public String name(){return "Window shown";}
 public boolean equals(Object o){return o instanceof WindowShown;}
 public int hashCode(){return 9;}
}
""",
 "rs/syntheticmenu80/StartedSignal.java": """package rs.syntheticmenu80;
public final class StartedSignal {
 public String name(){return "Service started";}
 public boolean equals(Object o){return o instanceof StartedSignal;}
 public int hashCode(){return 21;}
}
""",
 "rs/syntheticmenu80/SettingUpdate.java": """package rs.syntheticmenu80;
public final class SettingUpdate {
 private String area;
 private int number;
 public SettingUpdate(String area,int number){this.area=area;this.number=number;}
 public String area(){return area;}
 public int number(){return number;}
 public void setNumber(int value){number=value;}
 public String toString(){return "Update=" + area + "/" + number;}
}
""",
 "rs/syntheticmenu80/ActionPicker.java": """package rs.syntheticmenu80;
public final class ActionPicker {
 public static final ActionPicker SHARED=new ActionPicker();
 private int first,second,third;
 public void assign(int a,int b,int c){first=a;second=b;third=c;}
 public int select(int i){
  switch(i){case 1:return first;case 2:return second;case 3:return third;default:return 0;}
 }
 public boolean equals(Object x){return x==this;}
 public String toString(){return "ActionPicker("+first+","+second+","+third+")";}
}
""",
 "rs/syntheticmenu80/HoverPicker.java": """package rs.syntheticmenu80;
public final class HoverPicker {
 public static final HoverPicker SHARED=new HoverPicker();
 private String tip;
 public void tooltip(String value){tip=value;}
 public String tooltip(){return tip;}
 public int at(int i){switch(i){case 1:return 7;case 2:return 17;default:return -1;}}
 public String toString(){return "Hover="+tip;}
}
""",
}

PROBE = """import rs.syntheticmenu80.*;
public final class SyntheticMenuTranscript {
 public static void main(String[] args){
  System.out.println("W:"+new WindowShown().name()+":"+new WindowShown().hashCode());
  System.out.println("S:"+new StartedSignal().name()+":"+new StartedSignal().hashCode());
  String[] labels={null,"", "café"};
  for(String label:labels){
   SettingUpdate note=new SettingUpdate(label,-7);
   System.out.println("N0:"+note);
   note.setNumber(25);
   System.out.println("N1:"+note.area()+":"+note.number());
  }
  ActionPicker menu=new ActionPicker();
  for(int step=-2;step<6;step++){
   menu.assign(step,step+1,step+2);
   System.out.println("M:"+step+":"+menu.select(step)+":"+menu.toString());
  }
  HoverPicker hover=new HoverPicker();
  for(String label:labels){
   hover.tooltip(label);
   System.out.println("H:"+hover+":"+hover.tooltip()+":"+hover.at(1)+":"+hover.at(3));
  }
  if(ActionPicker.SHARED==null||HoverPicker.SHARED==null)
   throw new AssertionError("missing toy singletons");
 }
}
"""

def digest(raw: bytes)->str:
    return hashlib.sha256(raw).hexdigest()

def run(command):
    p=subprocess.run(command,capture_output=True,text=True,timeout=60)
    if p.returncode: raise AssertionError(p.stderr[-1600:])
    return p.stdout

@unittest.skipUnless(
    all(shutil.which(name) for name in ("javac","javap","java")),
    "A JDK with --release 9 is required",
)
class SyntheticMenuConfigSourceTests(unittest.TestCase):
    def fixture(self,root:Path):
        src=root/"src"
        for name,text in SOURCES.items():
            path=src/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(text,encoding="utf-8")
        classes=root/"original";classes.mkdir()
        run(["javac","--release","9","-proc:none","-g:none",
             "-classpath",str(root/"empty-classpath"),"-sourcepath",str(root/"empty-sourcepath"),
             "-d",str(classes),*[str(src/name) for name in sorted(SOURCES)]])
        jar=root/"original-synthetic.jar"
        with zipfile.ZipFile(jar,"w") as archive:
            for path in sorted(classes.rglob("*.class")):
                archive.writestr(path.relative_to(classes).as_posix(),path.read_bytes())
        with zipfile.ZipFile(jar) as archive:
            pins={key:digest(archive.read(key)) for key in archive.namelist()}
        self.assertEqual(len(pins),5)
        return src,jar,pins

    def test_closed_five_class_java9_sources_and_19_behavior_lines(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);src,jar,pins=self.fixture(root)
            result=verify_standalone_sources(
                jar,src,root/"rebuilt",
                original_sha256=digest(jar.read_bytes()),class_sha256=pins)
            self.assertTrue(result["all_passed"])
            self.assertEqual(result["total_classes"],5)
            self.assertFalse(result["original_game_binary_on_compile_classpath"])
            probe=root/"SyntheticMenuTranscript.java"
            probe.write_text(PROBE,encoding="utf-8")
            run(["javac","--release","9","-cp",str(jar),"-d",str(root),str(probe)])
            outputs=[]
            for binary in (jar,root/"rebuilt"/"classes"):
                outputs.append(run([
                    "java","-cp",str(root)+os.pathsep+str(binary),
                    "SyntheticMenuTranscript"]))
            self.assertEqual(outputs[0],outputs[1])
            self.assertEqual(len(outputs[0].splitlines()),19)

    def test_altered_menu_switch_is_rejected_by_original_instructions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);src,jar,pins=self.fixture(root)
            file=src/"rs/syntheticmenu80/ActionPicker.java"
            text=file.read_text()
            changed=text.replace("case 2:return second;","case 2:return first;")
            self.assertNotEqual(text,changed)
            file.write_text(changed,encoding="utf-8")
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH",
            ):
                verify_standalone_sources(
                    jar,src,root/"rejected",
                    original_sha256=digest(jar.read_bytes()),class_sha256=pins)

    def test_missing_event_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);src,jar,pins=self.fixture(root)
            (src/"rs/syntheticmenu80/StartedSignal.java").unlink()
            with self.assertRaises(StandaloneSourceParityError):
                verify_standalone_sources(
                    jar,src,root/"rejected",
                    original_sha256=digest(jar.read_bytes()),class_sha256=pins)

    def test_wrong_original_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);src,jar,pins=self.fixture(root)
            with self.assertRaisesRegex(StandaloneSourceParityError,"WRONG_ORIGINAL_JAR"):
                verify_standalone_sources(
                    jar,src,root/"rejected",
                    original_sha256="0"*64,class_sha256=pins)
if __name__=="__main__":
    unittest.main(verbosity=2)
