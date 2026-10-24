"""Synthetic-only Java9 bitfield/tint source parity and negative regressions.

This fixture is independently authored toy Java. It contains no proprietary
reconstructed original-v311 Java code, original client or vendor classfiles.
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
    StandaloneSourceParityError,
    verify_standalone_sources,
)

TOY = """package rs.synthetic106;
public final class ToyTint {
 public static final int MAX_TONE=73;
 private ToyTint(){}
 public static int clamp(int x){
  if(x<=0||x>=MAX_TONE)return 0;
  return x;
 }
 public static int mix(int color,int tone,int opacity){
  int effective=clamp(tone);
  int strength=Math.max(0,Math.min(100,opacity));
  if(effective==0||strength==0)return color;
  int src=color&255;
  int target=(src+effective*3)&255;
  return (color&~255)|((src*(100-strength)+target*strength+50)/100);
 }
 public static String mode(int x){
  switch(x){
   case 0:return "base";
   case 1:return "tint";
   case 2:return "soft";
   case 3:return "strong";
   default:return "other";
  }
 }
}
"""
PROBE = """import rs.synthetic106.ToyTint;
public final class Toy106Probe {
 public static void main(String[] ignored){
  int count=0;
  int[] colors={Integer.MIN_VALUE,-1,0,1,0xabcdef,0xffffff,Integer.MAX_VALUE};
  int[] tones={Integer.MIN_VALUE,-1,0,1,17,72,73,74,Integer.MAX_VALUE};
  int[] strengths={-5,0,1,17,50,99,100,101};
  for(int tone:tones){
   System.out.println("CLAMP:"+tone+":"+ToyTint.clamp(tone));count++;
  }
  for(int color:colors)for(int tone:tones)for(int strength:strengths){
   System.out.println("MIX:"+color+":"+tone+":"+strength+":"+
    ToyTint.mix(color,tone,strength));count++;
  }
  for(int mode=-1;mode<=5;mode++){
   System.out.println("MODE:"+mode+":"+ToyTint.mode(mode));count++;
  }
  if(count!=520)throw new AssertionError("WRONG_CASE_COUNT_"+count);
  System.out.println("CASES="+count);
 }
}
"""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def execute(argv):
    task = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    if task.returncode:
        raise AssertionError(task.stderr[-2000:])
    return task.stdout


@unittest.skipUnless(
    all(shutil.which(cmd) for cmd in ("java", "javac", "javap")),
    "Java9-capable JDK required",
)
class ToyColorSourceParity106(unittest.TestCase):
    def make_fixture(self, root: Path):
        source = root / "sources/rs/synthetic106/ToyTint.java"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(TOY, encoding="utf-8")
        built = root / "original"
        built.mkdir()
        execute(["javac", "--release", "9", "-proc:none", "-g:none",
                 "-classpath", str(root / "empty-cp"),
                 "-sourcepath", str(root / "empty-sp"),
                 "-d", str(built), str(source)])
        archive = root / "toy-original.jar"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("rs/synthetic106/ToyTint.class",
                       (built / "rs/synthetic106/ToyTint.class").read_bytes())
        with zipfile.ZipFile(archive) as z:
            pinned = {"rs/synthetic106/ToyTint.class":
                      sha(z.read("rs/synthetic106/ToyTint.class"))}
        return archive, root / "sources", pinned

    def test_exact_source_parity_and_520_toy_values(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar, sources, pins = self.make_fixture(root)
            report = verify_standalone_sources(
                jar, sources, root / "recompiled",
                original_sha256=sha(jar.read_bytes()), class_sha256=pins)
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"], 1)
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            self.assertTrue(report["explicit_original_project_dependency_closure"][
                "explicit_project_class_closure"])
            probe = root / "Toy106Probe.java"
            probe.write_text(PROBE, encoding="utf-8")
            execute(["javac", "--release", "9", "-cp", str(jar),
                     "-d", str(root), str(probe)])
            transcripts = [
                execute(["java", "-cp", str(root) + os.pathsep + str(cp),
                         "Toy106Probe"])
                for cp in (jar, root / "recompiled/classes")
            ]
            self.assertEqual(transcripts[0], transcripts[1])
            self.assertEqual(len(transcripts[0].splitlines()), 521)
            self.assertTrue(transcripts[0].endswith("CASES=520\n"))

    def test_color_math_changed_without_jvm_parity_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar, sources, pins = self.make_fixture(root)
            source = sources / "rs/synthetic106/ToyTint.java"
            before = source.read_text()
            after = before.replace("src+effective*3", "src+effective*2")
            self.assertNotEqual(after, before)
            source.write_text(after)
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH",
            ):
                verify_standalone_sources(
                    jar, sources, root / "rejected",
                    original_sha256=sha(jar.read_bytes()), class_sha256=pins)

    def test_missing_source_and_wrong_original_authority_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar, sources, pins = self.make_fixture(root)
            with self.assertRaisesRegex(
                StandaloneSourceParityError, "WRONG_ORIGINAL_JAR"
            ):
                verify_standalone_sources(
                    jar, sources, root / "wrong",
                    original_sha256="0" * 64, class_sha256=pins)
            (sources / "rs/synthetic106/ToyTint.java").unlink()
            with self.assertRaises(StandaloneSourceParityError):
                verify_standalone_sources(
                    jar, sources, root / "missing",
                    original_sha256=sha(jar.read_bytes()), class_sha256=pins)


if __name__ == "__main__":
    unittest.main(verbosity=2)
