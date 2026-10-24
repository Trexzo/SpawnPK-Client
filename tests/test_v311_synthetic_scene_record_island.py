"""Novel JDK-only scene record source island parity tests, without game code."""
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
 "rs/synthetic64/GridBuckets.java": """package rs.synthetic64;
public final class GridBuckets {
 private int[] content;
 public GridBuckets(int cells){content=new int[cells*5];}
 public GridBuckets write(int cell,int channel,int value){content[cell*5+channel]=value;return this;}
 public int read(int cell,int channel){return content[cell*5+channel];}
 public void increment(int cell,int channel,int delta){content[cell*5+channel]+=delta;}
}""",
 "rs/synthetic64/TimedValue.java": """package rs.synthetic64;
public final class TimedValue {
 private long timestamp;private int state;
 public TimedValue(int start){state=start;}
 public void update(int next,long tick){state=next;timestamp=tick;}
 public long timestamp(){return timestamp;}
 public int state(){return state;}
}""",
 "rs/synthetic64/RecordShelf.java": """package rs.synthetic64;
public final class RecordShelf {
 private GridBuckets buckets;private TimedValue current;
 public RecordShelf(int size){buckets=new GridBuckets(size);current=new TimedValue(0);}
 public void put(int index,int value){buckets.write(index,2,value);current.update(value,index);}
 public int get(int index){return buckets.read(index,2);}
 public long tick(){return current.timestamp();}
}""",
}

PROBE = """import rs.synthetic64.*;
public final class SyntheticSceneRecords {
 public static void main(String[] unused) {
  GridBuckets slots=new GridBuckets(3);
  slots.write(1,3,101);slots.increment(1,3,-22);
  System.out.println("GRID:"+slots.read(1,3));
  RecordShelf shelf=new RecordShelf(4);
  for(int i=0;i<4;i++){
   shelf.put(i,7*i-2);
   System.out.println("SHELF:"+i+":"+shelf.get(i)+":"+shelf.tick());
  }
  TimedValue v=new TimedValue(-3);
  v.update(Integer.MAX_VALUE,Long.MIN_VALUE);
  System.out.println("STATE:"+v.state()+":"+v.timestamp());
  try{slots.read(4,0);System.out.println("NO_ERROR");}
  catch(Throwable t){System.out.println("ERROR:"+t.getClass().getName());}
 }
}
"""

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

@unittest.skipUnless(all(shutil.which(x) for x in ("javac","javap","java")), "JDK9+ required")
class SyntheticThreeSceneRecords(unittest.TestCase):
    def fixture(self,root:Path):
        src=root/"src"
        for name,code in SOURCES.items():
            path=src/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(code,encoding="utf-8")
        output=root/"original";output.mkdir()
        result=subprocess.run([
            "javac","--release","9","-proc:none","-g:none",
            "-classpath",str(root/"empty-classpath"),
            "-sourcepath",str(root/"empty-sourcepath"),
            "-d",str(output),*[str(src/name) for name in sorted(SOURCES)]
        ],capture_output=True,text=True,timeout=45)
        self.assertEqual(result.returncode,0,result.stderr)
        jar=root/"synthetic-original.jar"
        with zipfile.ZipFile(jar,"w") as archive:
            for path in sorted(output.rglob("*.class")):
                archive.writestr(path.relative_to(output).as_posix(),path.read_bytes())
        with zipfile.ZipFile(jar) as archive:
            hashes={entry:sha(archive.read(entry)) for entry in archive.namelist()}
        self.assertEqual(len(hashes),3)
        return src,jar,hashes

    def test_three_source_closure_and_equal_seven_line_behaviors(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src,jar,hashes=self.fixture(root)
            report=verify_standalone_sources(
                jar,src,root/"rebuilt",
                original_sha256=sha(jar.read_bytes()),class_sha256=hashes)
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"],3)
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            self.assertGreaterEqual(report["explicit_original_project_dependency_closure"]["source_project_dependency_edges"],2)
            probe=root/"SyntheticSceneRecords.java"
            probe.write_text(PROBE,encoding="utf-8")
            built=subprocess.run(["javac","--release","9","-cp",str(jar),
                                  "-d",str(root),str(probe)],
                                 capture_output=True,text=True,timeout=45)
            self.assertEqual(built.returncode,0,built.stderr)
            actual=[]
            for cp in (jar,root/"rebuilt"/"classes"):
                result=subprocess.run(["java","-cp",str(root)+os.pathsep+str(cp),
                                       "SyntheticSceneRecords"],
                                      capture_output=True,text=True,timeout=45)
                self.assertEqual(result.returncode,0,result.stderr)
                actual.append(result.stdout)
            self.assertEqual(actual[0],actual[1])
            self.assertEqual(len(actual[0].splitlines()),7)

    def test_modified_stride_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src,jar,hashes=self.fixture(root)
            path=src/"rs/synthetic64/GridBuckets.java"
            path.write_text(path.read_text().replace("cell*5+channel","cell*6+channel"),encoding="utf-8")
            with self.assertRaisesRegex(StandaloneSourceParityError,"ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH"):
                verify_standalone_sources(jar,src,root/"rejected",
                    original_sha256=sha(jar.read_bytes()),class_sha256=hashes)

    def test_missing_class_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src,jar,hashes=self.fixture(root)
            (src/"rs/synthetic64/GridBuckets.java").unlink()
            with self.assertRaises(StandaloneSourceParityError):
                verify_standalone_sources(jar,src,root/"rejected",
                    original_sha256=sha(jar.read_bytes()),class_sha256=hashes)

    def test_wrong_jar_sha_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src,jar,hashes=self.fixture(root)
            with self.assertRaisesRegex(StandaloneSourceParityError,"WRONG_ORIGINAL_JAR"):
                verify_standalone_sources(jar,src,root/"rejected",
                    original_sha256="0"*64,class_sha256=hashes)

if __name__=="__main__":
    unittest.main(verbosity=2)
