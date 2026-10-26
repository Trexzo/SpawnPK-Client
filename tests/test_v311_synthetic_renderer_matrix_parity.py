"""JDK-only synthetic matrix source-parity regression.

The classes and constants are independently authored toy examples, not
original v311 game bytecode, source, data, classfiles or assets.
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

SOURCES = {
    "rs/syntheticmath/AnglePair.java": """
package rs.syntheticmath;
public final class AnglePair {
 private AnglePair() {}
 public static float[] lookup(float theta) {
  return new float[]{(float)Math.cos((double)theta),(float)Math.sin((double)theta)};
 }
}
""",
    "rs/syntheticmath/Matrix2.java": """
package rs.syntheticmath;
public final class Matrix2 {
 private Matrix2() {}
 public static float[] rotation(float theta) {
  float[] pair=AnglePair.lookup(theta);
  return new float[]{pair[0],-pair[1],pair[1],pair[0]};
 }
 public static void combine(float[] out,float[] in) {
  float a=out[0],b=out[1],c=out[2],d=out[3];
  out[0]=a*in[0]+b*in[2];
  out[1]=a*in[1]+b*in[3];
  out[2]=c*in[0]+d*in[2];
  out[3]=c*in[1]+d*in[3];
 }
}
""",
}

PROBE = """
import java.util.*; import rs.syntheticmath.*;
public class SyntheticMathTranscript {
 static String bits(float[] data) {
  int[] result=new int[data.length];
  for(int i=0;i<data.length;i++)result[i]=Float.floatToRawIntBits(data[i]);
  return Arrays.toString(result);
 }
 public static void main(String[] ignored) {
  for(float theta:new float[]{0f,-0f,0.125f,-0.75f,3.1415927f,Float.NaN}) {
   float[] first=Matrix2.rotation(theta);
   float[] other=Matrix2.rotation(0.35f);
   System.out.println("FIRST:"+bits(first));
   Matrix2.combine(first,other);
   System.out.println("MULT:"+bits(first));
  }
  float[] same=Matrix2.rotation(0.55f);
  Matrix2.combine(same,same);
  System.out.println("ALIAS:"+bits(same));
  try { Matrix2.combine(new float[2],new float[4]);System.out.println("NO_ERROR"); }
  catch(Throwable t){System.out.println("ERR:"+t.getClass().getName());}
 }
}
"""

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

@unittest.skipUnless(
    all(shutil.which(x) for x in ("javac", "java", "javap")),
    "JDK9+ required",
)
class SyntheticMatrixSourceParityTests(unittest.TestCase):
    def fixture(self, root: Path):
        source = root / "src"
        for name, body in SOURCES.items():
            item = source / name
            item.parent.mkdir(parents=True, exist_ok=True)
            item.write_text(body, encoding="utf-8")
        output = root / "original"
        output.mkdir()
        built = subprocess.run([
            "javac", "--release", "9", "-proc:none", "-g:none",
            "-encoding", "UTF-8",
            "-classpath", str(root / "empty-classpath"),
            "-sourcepath", str(root / "empty-sourcepath"),
            "-d", str(output),
            *[str(source / name) for name in sorted(SOURCES)],
        ], capture_output=True, text=True, timeout=45)
        self.assertEqual(built.returncode, 0, built.stderr)
        jar = root / "synthetic-original.jar"
        with zipfile.ZipFile(jar, "w") as z:
            for item in sorted(output.rglob("*.class")):
                z.writestr(item.relative_to(output).as_posix(), item.read_bytes())
        with zipfile.ZipFile(jar) as z:
            pins = {name: sha(z.read(name)) for name in z.namelist()}
        self.assertEqual(len(pins), 2)
        return source, jar, pins

    def test_dependency_closed_two_source_build_and_matrix_behaviors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, jar, pins = self.fixture(root)
            report = verify_standalone_sources(
                jar, source, root / "rebuilt",
                original_sha256=sha(jar.read_bytes()), class_sha256=pins,
            )
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"], 2)
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            self.assertGreaterEqual(
                report["explicit_original_project_dependency_closure"][
                    "source_project_dependency_edges"], 1,
            )
            probe = root / "SyntheticMathTranscript.java"
            probe.write_text(PROBE, encoding="utf-8")
            compiled = subprocess.run([
                "javac", "--release", "9", "-cp", str(jar),
                "-d", str(root), str(probe),
            ], capture_output=True, text=True, timeout=45)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            transcripts = []
            for cp in (jar, root / "rebuilt" / "classes"):
                trial = subprocess.run([
                    "java", "-cp", str(root) + os.pathsep + str(cp),
                    "SyntheticMathTranscript",
                ], capture_output=True, text=True, timeout=45)
                self.assertEqual(trial.returncode, 0, trial.stderr)
                transcripts.append(trial.stdout)
            self.assertEqual(transcripts[0], transcripts[1])
            self.assertEqual(len(transcripts[0].splitlines()), 14)

    def test_wrong_matrix_sign_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, jar, pins = self.fixture(root)
            matrix = source / "rs/syntheticmath/Matrix2.java"
            before = matrix.read_text(encoding="utf-8")
            matrix.write_text(before.replace("pair[0],-pair[1]", "pair[0],pair[1]"),
                              encoding="utf-8")
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH",
            ):
                verify_standalone_sources(
                    jar, source, root / "rejected",
                    original_sha256=sha(jar.read_bytes()), class_sha256=pins,
                )

    def test_missing_angle_dependency_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, jar, pins = self.fixture(root)
            (source / "rs/syntheticmath/AnglePair.java").unlink()
            with self.assertRaises(StandaloneSourceParityError):
                verify_standalone_sources(
                    jar, source, root / "rejected",
                    original_sha256=sha(jar.read_bytes()), class_sha256=pins,
                )

    def test_wrong_original_pin_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, jar, pins = self.fixture(root)
            with self.assertRaisesRegex(
                StandaloneSourceParityError, "WRONG_ORIGINAL_JAR",
            ):
                verify_standalone_sources(
                    jar, source, root / "rejected",
                    original_sha256="0"*64, class_sha256=pins,
                )

if __name__ == "__main__":
    unittest.main(verbosity=2)
