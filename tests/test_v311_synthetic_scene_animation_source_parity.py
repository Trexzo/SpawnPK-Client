"""Synthetic Java 9 source-island proof for small animation/scene helpers.

All Java fixtures are independently authored toy code. No original game
binary, recovered source, game constants, account data or other assets.
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
 "rs/synthetic93/SlidingCount.java": """package rs.synthetic93;
public final class SlidingCount {
 private int lower,upper,value;
 public SlidingCount(int lower,int upper){
  this.lower=lower;this.upper=upper;value=lower;
 }
 public int value(){return value;}
 public void advance(){value++;if(value>upper)value=lower;}
}
""",
 "rs/synthetic93/LabelRecord.java": """package rs.synthetic93;
public final class LabelRecord {
 private String text;
 private int width,height;
 public LabelRecord(String text){this.text=text;width=150;height=96;}
 public String text(){return text;}
 public int area(){return width*height;}
}
""",
 "rs/synthetic93/MutableNumber.java": """package rs.synthetic93;
public final class MutableNumber {
 private int value;
 public MutableNumber(int first){value=first;}
 public void set(int next){value=next;}
 public int get(){return value;}
}
""",
 "rs/synthetic93/DashboardSnapshot.java": """package rs.synthetic93;
public final class DashboardSnapshot {
 private final SlidingCount counter;
 private final LabelRecord label;
 private final MutableNumber number;
 public DashboardSnapshot(String text,int lo,int hi){
  counter=new SlidingCount(lo,hi);
  label=new LabelRecord(text);
  number=new MutableNumber(lo);
 }
 public void advance(){counter.advance();number.set(counter.value());}
 public String render(){return label.text()+":"+number.get()+":"+label.area();}
}
""",
}

PROBE = """
import rs.synthetic93.*;
public final class Synthetic93Transcript {
 public static void main(String[] unused){
  for(int n:new int[]{-1,0,3,Integer.MAX_VALUE}){
   SlidingCount counter=new SlidingCount(n,n+2);
   for(int i=0;i<3;i++){
    counter.advance();
    System.out.println("C:"+n+":"+i+":"+counter.value());
   }
  }
  for(String label:new String[]{"", "panel", "älg"}){
   DashboardSnapshot snapshot=new DashboardSnapshot(label,0,2);
   System.out.println("D0:"+snapshot.render());
   snapshot.advance();
   System.out.println("D1:"+snapshot.render());
  }
 }
}
"""

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(argv):
    process = subprocess.run(argv, capture_output=True, text=True, timeout=55)
    if process.returncode:
        raise AssertionError(process.stderr[-1500:])
    return process.stdout


@unittest.skipUnless(
    all(shutil.which(executable) for executable in ("javac", "javap", "java")),
    "JDK9+ tools required",
)
class Synthetic93SceneSourceTests(unittest.TestCase):
    def fixture(self, root: Path):
        sources = root / "src"
        for name, body in SOURCES.items():
            target = sources / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        classes = root / "toy-original"
        classes.mkdir()
        run([
            "javac", "--release", "9", "-proc:none", "-g:none",
            "-classpath", str(root / "empty-cp"),
            "-sourcepath", str(root / "empty-sp"),
            "-d", str(classes),
            *[str(sources / n) for n in sorted(SOURCES)],
        ])
        jar = root / "toy-original.jar"
        with zipfile.ZipFile(jar, "w") as z:
            for class_file in sorted(classes.rglob("*.class")):
                z.writestr(
                    class_file.relative_to(classes).as_posix(),
                    class_file.read_bytes(),
                )
        with zipfile.ZipFile(jar) as z:
            pins = {name: sha(z.read(name)) for name in z.namelist()}
        self.assertEqual(len(pins), 4)
        return sources, jar, pins

    def test_closed_four_source_classes_and_18_behavior_cases(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            src, jar, pins = self.fixture(root)
            report = verify_standalone_sources(
                jar, src, root / "rebuilt",
                original_sha256=sha(jar.read_bytes()), class_sha256=pins,
            )
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"], 4)
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            self.assertGreaterEqual(
                report["explicit_original_project_dependency_closure"][
                    "source_project_dependency_edges"
                ], 3,
            )
            probe = root / "Synthetic93Transcript.java"
            probe.write_text(PROBE, encoding="utf-8")
            run([
                "javac", "--release", "9", "-cp", str(jar),
                "-d", str(root), str(probe),
            ])
            outputs = []
            for cp in (jar, root / "rebuilt" / "classes"):
                outputs.append(run([
                    "java", "-cp", str(root) + os.pathsep + str(cp),
                    "Synthetic93Transcript",
                ]))
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(len(outputs[0].splitlines()), 18)

    def test_changed_counter_opcode_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            src, jar, pins = self.fixture(root)
            target = src / "rs/synthetic93/SlidingCount.java"
            original = target.read_text()
            changed = original.replace("value++;", "value+=2;")
            self.assertNotEqual(original, changed)
            target.write_text(changed, encoding="utf-8")
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH",
            ):
                verify_standalone_sources(
                    jar, src, root / "refused",
                    original_sha256=sha(jar.read_bytes()), class_sha256=pins,
                )

    def test_missing_dependency_source_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            src, jar, pins = self.fixture(root)
            (src / "rs/synthetic93/MutableNumber.java").unlink()
            with self.assertRaises(StandaloneSourceParityError):
                verify_standalone_sources(
                    jar, src, root / "refused",
                    original_sha256=sha(jar.read_bytes()), class_sha256=pins,
                )

    def test_wrong_jar_authority_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            src, jar, pins = self.fixture(root)
            with self.assertRaisesRegex(
                StandaloneSourceParityError, "WRONG_ORIGINAL_JAR",
            ):
                verify_standalone_sources(
                    jar, src, root / "refused",
                    original_sha256="0" * 64, class_sha256=pins,
                )

if __name__ == "__main__":
    unittest.main(verbosity=2)
