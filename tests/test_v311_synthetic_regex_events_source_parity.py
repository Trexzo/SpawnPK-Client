"""Synthetic-only Java9 event/regex source parity and guarded failure tests.

All Java fixture classes are independently authored toy classes, not
decompiled or reconstructed SpawnPK game Java. No original client binary.
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
from spk_recovery.source_dependency_closure import (
    SourceClosureError, require_selected_source_closure,
)

SOURCES = {
 "rs/synthetic72/WordMatcher.java": """
package rs.synthetic72;
import java.util.regex.Pattern;
public final class WordMatcher {
 public static boolean accepts(String phrase,String word){
  return Pattern.compile(Pattern.quote(word),Pattern.CASE_INSENSITIVE)
     .matcher(phrase).find();
 }
}
""",
 "rs/synthetic72/FocusFlag.java": """
package rs.synthetic72;
public final class FocusFlag {
 private boolean value;
 public FocusFlag(boolean initial){value=initial;}
 public boolean enabled(){return value;}
 public void toggle(){value=!value;}
 public String toString(){return "Flag=" + value;}
}
""",
 "rs/synthetic72/AlertReceipt.java": """
package rs.synthetic72;
public final class AlertReceipt {
 private final String message;
 private final FocusFlag flag;
 public AlertReceipt(String message,FocusFlag flag){
  this.message=message;
  this.flag=flag;
 }
 public boolean isVisible(){return flag.enabled() && WordMatcher.accepts(message,"ok");}
 public String render(){return message + ":" + flag.toString();}
}
""",
}

PROBE = """
import rs.synthetic72.*;
public final class ToyEventTextProbe {
 public static void main(String[] ignored) {
  String[] texts={"OK","ok event","warning","", "Är OK"};
  String[] queries={"ok","warn","a.*"};
  int count=0;
  for(String text:texts)for(String query:queries){
   System.out.println("SEARCH:"+text+":"+query+":"+WordMatcher.accepts(text,query));
   count++;
  }
  for(boolean initial:new boolean[]{false,true}){
   FocusFlag flag=new FocusFlag(initial);
   System.out.println("FLAG:"+flag.enabled()+":"+flag);
   flag.toggle();
   System.out.println("TOGGLE:"+flag.enabled()+":"+flag);
   count+=2;
  }
  for(String text:new String[]{"ok","skip"}){
   FocusFlag flag=new FocusFlag(true);
   AlertReceipt record=new AlertReceipt(text,flag);
   System.out.println("RECEIPT:"+record.isVisible()+":"+record.render());
   count++;
  }
  if(count!=21)throw new AssertionError("BAD_TOY_CASE_COUNT");
 }
}
"""

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def launch(argv):
    process=subprocess.run(argv,capture_output=True,text=True,timeout=55)
    if process.returncode:
        raise AssertionError(process.stderr[-1800:])
    return process.stdout

@unittest.skipUnless(
    all(shutil.which(name) for name in ("javac","javap","java")),
    "Requires Java9-capable JDK",
)
class SyntheticEventRegexSourceParity(unittest.TestCase):
    def fixture(self,root:Path):
        src=root/"source"
        for name,body in SOURCES.items():
            file=src/name
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text(body,encoding="utf-8")
        compiled=root/"original-classes"
        compiled.mkdir()
        launch([
            "javac","--release","9","-proc:none","-g:none",
            "-classpath",str(root/"empty-cp"),
            "-sourcepath",str(root/"empty-src"),
            "-d",str(compiled),*[str(src/name) for name in sorted(SOURCES)]
        ])
        jar=root/"toy-original.jar"
        with zipfile.ZipFile(jar,"w") as archive:
            for file in sorted(compiled.rglob("*.class")):
                archive.writestr(file.relative_to(compiled).as_posix(),file.read_bytes())
        with zipfile.ZipFile(jar) as archive:
            pins={name:digest(archive.read(name)) for name in archive.namelist()}
        self.assertEqual(len(pins),3)
        return src,jar,pins

    def test_three_class_parity_and_21_case_behavior(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            src,jar,pins=self.fixture(root)
            report=verify_standalone_sources(
                jar,src,root/"rebuilt",
                original_sha256=digest(jar.read_bytes()),class_sha256=pins
            )
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"],3)
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            self.assertGreaterEqual(
                report["explicit_original_project_dependency_closure"]["source_project_dependency_edges"],2)
            probe=root/"ToyEventTextProbe.java"
            probe.write_text(PROBE,encoding="utf-8")
            launch(["javac","--release","9","-cp",str(jar),
                    "-d",str(root),str(probe)])
            outputs=[]
            for binary in (jar,root/"rebuilt"/"classes"):
                outputs.append(launch([
                    "java","-cp",str(root)+os.pathsep+str(binary),"ToyEventTextProbe"
                ]))
            self.assertEqual(outputs[0],outputs[1])
            self.assertEqual(len(outputs[0].splitlines()),21)

    def test_missing_dependency_class_refused_before_compilation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            _,jar,_=self.fixture(root)
            with zipfile.ZipFile(jar) as archive:
                with self.assertRaisesRegex(
                    SourceClosureError,"PROJECT_SOURCE_DEPENDENCY_OUTSIDE_SELECTION",
                ):
                    require_selected_source_closure(archive,{
                        "rs/synthetic72/AlertReceipt.class",
                        "rs/synthetic72/WordMatcher.class",
                    })

    def test_changed_event_state_refused_on_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            src,jar,pins=self.fixture(root)
            target=src/"rs/synthetic72/FocusFlag.java"
            target.write_text(target.read_text(encoding="utf-8").replace(
                "value=!value;", "value=true;"),encoding="utf-8")
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH",
            ):
                verify_standalone_sources(
                    jar,src,root/"bad",
                    original_sha256=digest(jar.read_bytes()),class_sha256=pins,
                )

    def test_wrong_input_jar_sha_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            src,jar,pins=self.fixture(root)
            with self.assertRaisesRegex(
                StandaloneSourceParityError,"WRONG_ORIGINAL_JAR",
            ):
                verify_standalone_sources(
                    jar,src,root/"bad",
                    original_sha256="0"*64,class_sha256=pins,
                )

if __name__=="__main__":
    unittest.main(verbosity=2)
