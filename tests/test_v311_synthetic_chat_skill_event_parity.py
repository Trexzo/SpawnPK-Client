"""Novel synthetic Java9 chat-event source parity, not original client code."""
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
"rs/syntheticevents75/TextReceipt.java": """
package rs.syntheticevents75;
public class TextReceipt {
 private String content;
 public TextReceipt(String content){this.content=content;}
 public String getContent(){return content;}
 public void setContent(String content){this.content=content;}
 public boolean equals(Object value){
  if(value==this)return true;
  if(!(value instanceof TextReceipt))return false;
  TextReceipt other=(TextReceipt)value;
  String left=this.getContent(),right=other.getContent();
  return left==null?right==null:left.equals(right);
 }
 public int hashCode(){return content==null?17:content.hashCode();}
 public String toString(){return "TextReceipt(" + getContent() + ")";}
}
""",
"rs/syntheticevents75/DirectReceipt.java": """
package rs.syntheticevents75;
public class DirectReceipt {
 private final String author;
 private final TextReceipt message;
 public DirectReceipt(String author,TextReceipt message){this.author=author;this.message=message;}
 public String getAuthor(){return author;}
 public boolean hasText(){return message!=null && message.getContent()!=null;}
 public String toString(){return author + ":" + String.valueOf(message);}
}
""",
"rs/syntheticevents75/LevelSignal.java": """
package rs.syntheticevents75;
public class LevelSignal {
 private int level;
 private double score;
 public LevelSignal(int level,double score){this.level=level;this.score=score;}
 public int level(){return level;}
 public double score(){return score;}
 public void update(double value){score=value;}
 public boolean equals(Object rhs){
  if(!(rhs instanceof LevelSignal))return false;
  LevelSignal other=(LevelSignal)rhs;
  return level==other.level && Double.compare(score,other.score)==0;
 }
 public int hashCode(){
  long bits=Double.doubleToLongBits(score);
  return level*31+(int)(bits^(bits>>>32));
 }
 public String toString(){return "LevelSignal(" + level + "," + score + ")";}
}
"""
}
PROBE = """
import rs.syntheticevents75.*;
public class SyntheticEventTranscript {
 public static void main(String[] args){
  String[] texts={null,"","hi","snow"};
  for(String text:texts){
   TextReceipt a=new TextReceipt(text), b=new TextReceipt(text);
   System.out.println("T:"+a+":"+a.equals(b)+":"+a.hashCode());
   System.out.println("D:"+new DirectReceipt("From",a).toString());
  }
  double[] values={-0.0d,0.0d,Double.NaN,Double.POSITIVE_INFINITY,3.5d};
  for(double value:values){
   LevelSignal a=new LevelSignal(-7,value);
   LevelSignal b=new LevelSignal(-7,value);
   System.out.println("L:"+a+":"+a.equals(b)+":"+a.hashCode());
  }
 }
}
"""
def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def call(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=60)
    if p.returncode:raise AssertionError(p.stderr[-1200:])
    return p.stdout

@unittest.skipUnless(all(shutil.which(x) for x in ("javac","javap","java")), "JDK9 required")
class SyntheticR75Events(unittest.TestCase):
    def fixture(self, root: Path):
        src=root/"src"
        for name,body in SOURCES.items():
            f=src/name
            f.parent.mkdir(parents=True,exist_ok=True)
            f.write_text(body,encoding="utf-8")
        out=root/"original"
        out.mkdir()
        call(["javac","--release","9","-proc:none","-g:none",
              "-classpath",str(root/"empty-cp"),"-sourcepath",str(root/"empty-src"),
              "-d",str(out),*[str(src/name) for name in sorted(SOURCES)]])
        jar=root/"synthetic-original.jar"
        with zipfile.ZipFile(jar,"w") as z:
            for f in sorted(out.rglob("*.class")):
                z.writestr(f.relative_to(out).as_posix(),f.read_bytes())
        with zipfile.ZipFile(jar) as z:
            pins={k:digest(z.read(k)) for k in z.namelist()}
        self.assertEqual(len(pins),3)
        return src,jar,pins

    def test_three_source_closure_and_original_vs_rebuilt_behaviors(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            src,jar,pins=self.fixture(root)
            r=verify_standalone_sources(jar,src,root/"rebuilt",
                original_sha256=digest(jar.read_bytes()),class_sha256=pins)
            self.assertTrue(r["all_passed"])
            self.assertEqual(r["total_classes"],3)
            self.assertFalse(r["original_game_binary_on_compile_classpath"])
            self.assertGreaterEqual(
                r["explicit_original_project_dependency_closure"]["source_project_dependency_edges"],1)
            probe=root/"SyntheticEventTranscript.java"
            probe.write_text(PROBE,encoding="utf-8")
            call(["javac","--release","9","-cp",str(jar),"-d",str(root),str(probe)])
            transcripts=[]
            for cp in (jar,root/"rebuilt"/"classes"):
                transcripts.append(call(["java","-cp",str(root)+os.pathsep+str(cp),
                                         "SyntheticEventTranscript"]))
            self.assertEqual(transcripts[0],transcripts[1])
            self.assertEqual(len(transcripts[0].splitlines()),13)

    def test_changed_skill_hash_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);src,jar,pins=self.fixture(root)
            f=src/"rs/syntheticevents75/LevelSignal.java"
            f.write_text(f.read_text().replace("level*31+","level*37+"),encoding="utf-8")
            with self.assertRaisesRegex(StandaloneSourceParityError,
                   "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH"):
                verify_standalone_sources(jar,src,root/"rejected",
                    original_sha256=digest(jar.read_bytes()),class_sha256=pins)

    def test_missing_source_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);src,jar,pins=self.fixture(root)
            (src/"rs/syntheticevents75/TextReceipt.java").unlink()
            with self.assertRaises(StandaloneSourceParityError):
                verify_standalone_sources(jar,src,root/"rejected",
                    original_sha256=digest(jar.read_bytes()),class_sha256=pins)

    def test_wrong_original_hash_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);src,jar,pins=self.fixture(root)
            with self.assertRaisesRegex(StandaloneSourceParityError,"WRONG_ORIGINAL_JAR"):
                verify_standalone_sources(jar,src,root/"rejected",
                    original_sha256="0"*64,class_sha256=pins)

if __name__=="__main__":
    unittest.main(verbosity=2)
