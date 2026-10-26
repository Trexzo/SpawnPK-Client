"""JDK-only coordinate and display-constant source-parity regression.

Every Java source here is an independently authored synthetic fixture.
No original game JAR, game classfile, or reconstructed v311 source is included.
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
    "rs/synthetic69/Coordinates.java": """
package rs.synthetic69;
public class Coordinates {
 private final int x,y;
 public Coordinates(int x,int y){this.x=x;this.y=y;}
 public int x(){return x;}
 public int y(){return y;}
 public double difference(Coordinates other){
  return Math.hypot((double)(x-other.x),(double)(y-other.y));
 }
 public int hashCode(){int result=7;result=31*result+x;result=31*result+y;return result;}
 public boolean equals(Object other){
  if(this==other)return true;
  if(other==null || getClass()!=other.getClass())return false;
  Coordinates rhs=(Coordinates)other;
  return x==rhs.x && y==rhs.y;
 }
 public String toString(){return "Coordinate(" + x + "," + y + ")";}
}
""",
    "rs/synthetic69/DisplayDefaults.java": """
package rs.synthetic69;
import java.awt.Dimension;
public class DisplayDefaults {
 public static final int WIDTH=960;
 public static final int HEIGHT=540;
 public static final float SCALE=0.75f;
 public static final Dimension SIZE=new Dimension(WIDTH,HEIGHT);
}
""",
}
PROBE = """
import rs.synthetic69.*;
public final class SyntheticCoordinatesProbe {
 public static void main(String[] args) {
  int[] values={Integer.MIN_VALUE,-7,0,12,Integer.MAX_VALUE};
  for(int x:values)for(int y:values){
   Coordinates a=new Coordinates(x,y);
   Coordinates b=new Coordinates(y,x);
   System.out.println("P:"+a+":"+a.hashCode()+":"+a.equals(b)+":"+
                      Double.doubleToRawLongBits(a.difference(b)));
  }
  System.out.println("SIZE:"+DisplayDefaults.SIZE.width+":"+DisplayDefaults.SIZE.height);
  System.out.println("SCALE:"+Float.floatToRawIntBits(DisplayDefaults.SCALE));
 }
}
"""

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def execute(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise AssertionError(result.stderr[-1200:])
    return result.stdout

@unittest.skipUnless(
    all(shutil.which(name) for name in ("javac", "javap", "java")),
    "Java 9 compiler, javap and Java runtime are required",
)
class SyntheticCoordinatesAndConstantsTests(unittest.TestCase):
    def fixture(self, root: Path):
        sources = root / "source"
        for name, body in SOURCES.items():
            path = sources / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        compiled = root / "original-classes"
        compiled.mkdir()
        execute([
            "javac", "--release", "9", "-proc:none", "-g:none",
            "-classpath", str(root / "empty-classpath"),
            "-sourcepath", str(root / "empty-sourcepath"),
            "-d", str(compiled),
            *[str(sources / name) for name in sorted(SOURCES)],
        ])
        original = root / "synthetic-original.jar"
        with zipfile.ZipFile(original, "w") as z:
            for path in sorted(compiled.rglob("*.class")):
                z.writestr(path.relative_to(compiled).as_posix(), path.read_bytes())
        with zipfile.ZipFile(original) as z:
            hashes = {name: digest(z.read(name)) for name in z.namelist()}
        self.assertEqual(len(hashes), 2)
        return sources, original, hashes

    def test_two_java9_classes_original_parity_and_27_runtime_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, original, hashes = self.fixture(root)
            report = verify_standalone_sources(
                original, source, root / "rebuilt",
                original_sha256=digest(original.read_bytes()),
                class_sha256=hashes,
            )
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"], 2)
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            probe = root / "SyntheticCoordinatesProbe.java"
            probe.write_text(PROBE, encoding="utf-8")
            execute(["javac", "--release", "9", "-cp", str(original), "-d", str(root), str(probe)])
            results = []
            for cp in (original, root / "rebuilt" / "classes"):
                results.append(execute([
                    "java", "-cp", str(root) + os.pathsep + str(cp),
                    "SyntheticCoordinatesProbe",
                ]))
            self.assertEqual(results[0], results[1])
            self.assertEqual(len(results[0].splitlines()), 27)
            original_constants = execute([
                "javap", "-p", "-constants", "-classpath", str(original),
                "rs.synthetic69.DisplayDefaults",
            ])
            rebuilt_constants = execute([
                "javap", "-p", "-constants", "-classpath",
                str(root / "rebuilt" / "classes"), "rs.synthetic69.DisplayDefaults",
            ])
            self.assertEqual(original_constants, rebuilt_constants)

    def test_changed_coordinate_math_fails_symbolic_parity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, original, hashes = self.fixture(root)
            path = source / "rs/synthetic69/Coordinates.java"
            path.write_text(path.read_text().replace("31*result+y", "29*result+y"),
                            encoding="utf-8")
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH",
            ):
                verify_standalone_sources(
                    original, source, root / "refused",
                    original_sha256=digest(original.read_bytes()),
                    class_sha256=hashes,
                )

    def test_display_constant_value_must_be_checked_separately(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, original, hashes = self.fixture(root)
            constant = source / "rs/synthetic69/DisplayDefaults.java"
            constant.write_text(constant.read_text().replace("WIDTH=960", "WIDTH=961"),
                                encoding="utf-8")
            changed = root / "changed"
            changed.mkdir()
            execute([
                "javac", "--release", "9", "-proc:none", "-g:none",
                "-classpath", str(root / "empty-cp"),
                "-sourcepath", str(root / "empty-sp"),
                "-d", str(changed), str(constant),
            ])
            original_constants = execute([
                "javap", "-p", "-constants", "-classpath", str(original),
                "rs.synthetic69.DisplayDefaults",
            ])
            changed_constants = execute([
                "javap", "-p", "-constants", "-classpath", str(changed),
                "rs.synthetic69.DisplayDefaults",
            ])
            self.assertNotEqual(original_constants, changed_constants)

    def test_missing_original_source_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, original, hashes = self.fixture(root)
            (source / "rs/synthetic69/Coordinates.java").unlink()
            with self.assertRaises(StandaloneSourceParityError):
                verify_standalone_sources(
                    original, source, root / "refused",
                    original_sha256=digest(original.read_bytes()),
                    class_sha256=hashes,
                )

if __name__ == "__main__":
    unittest.main(verbosity=2)
