"""Synthetic-only v311 renderer-buffer source-parity regression.

Independent toy java.nio classes. No game JAR, original source or client binary.
"""
from __future__ import annotations

import hashlib
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
    "rs/syntheticbuffers/FloatPool.java": r"""
package rs.syntheticbuffers;
import java.nio.*;
public final class FloatPool {
 private FloatBuffer data=ByteBuffer.allocateDirect(32).order(ByteOrder.nativeOrder()).asFloatBuffer();
 public void put(float x){data.put(x);}
 public void reserve(int needed){
  int capacity=data.capacity();
  int position=data.position();
  if(capacity-position<needed){
   do {capacity*=2;}while(capacity-position<needed);
   FloatBuffer larger=ByteBuffer.allocateDirect(capacity*4).order(ByteOrder.nativeOrder()).asFloatBuffer();
   data.flip();larger.put(data);data=larger;
  }
 }
 public void reset(){data.clear();}
 public FloatBuffer buffer(){return data;}
}
""",
    "rs/syntheticbuffers/IntPool.java": r"""
package rs.syntheticbuffers;
import java.nio.*;
public final class IntPool {
 private IntBuffer data=ByteBuffer.allocateDirect(32).order(ByteOrder.nativeOrder()).asIntBuffer();
 public void put(int x){data.put(x);}
 public void reserve(int needed){
  int capacity=data.capacity();
  int position=data.position();
  if(capacity-position<needed){
   do {capacity*=2;}while(capacity-position<needed);
   IntBuffer larger=ByteBuffer.allocateDirect(capacity*4).order(ByteOrder.nativeOrder()).asIntBuffer();
   data.flip();larger.put(data);data=larger;
  }
 }
 public void reset(){data.clear();}
 public IntBuffer buffer(){return data;}
}
""",
}

PROBE = r"""
import rs.syntheticbuffers.*;
import java.util.*;
public final class SyntheticBufferTranscript {
 public static void main(String[] args){
  FloatPool fp=new FloatPool();
  fp.put(2.25f);fp.put(-3.5f);
  System.out.println("F0:"+fp.buffer().position()+":"+fp.buffer().capacity());
  fp.reserve(9);
  System.out.println("F1:"+fp.buffer().get(0)+":"+fp.buffer().get(1)+":"+fp.buffer().capacity());
  fp.reset();
  System.out.println("F2:"+fp.buffer().position()+":"+fp.buffer().limit());
  IntPool ip=new IntPool();
  ip.put(101);ip.put(-7);
  ip.reserve(12);
  System.out.println("I0:"+ip.buffer().get(0)+":"+ip.buffer().get(1)+":"+ip.buffer().capacity());
  ip.reserve(32);
  System.out.println("I1:"+ip.buffer().capacity()+":"+ip.buffer().position());
  ip.reset();
  System.out.println("I2:"+ip.buffer().position()+":"+ip.buffer().limit());
 }
}
"""

def digest(data: bytes):
    return hashlib.sha256(data).hexdigest()

@unittest.skipUnless(
    all(shutil.which(name) for name in ("javac", "javap", "java")),
    "JDK9+ required",
)
class SyntheticBufferSourceTests(unittest.TestCase):
    def fixture(self, root: Path):
        sources=root/"sources"
        for name,body in SOURCES.items():
            destination=sources/name
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_text(body,encoding="utf-8")
        compiled=root/"original-build"
        compiled.mkdir()
        run=subprocess.run([
            "javac","--release","9","-proc:none","-g:none",
            "-classpath",str(root/"empty-classpath"),
            "-sourcepath",str(root/"empty-sourcepath"),
            "-d",str(compiled),
            *[str(sources/name) for name in sorted(SOURCES)],
        ],capture_output=True,text=True,timeout=45)
        self.assertEqual(run.returncode,0,run.stderr)
        archive=root/"synthetic-original.jar"
        with zipfile.ZipFile(archive,"w") as z:
            for f in sorted(compiled.rglob("*.class")):
                z.writestr(f.relative_to(compiled).as_posix(),f.read_bytes())
        with zipfile.ZipFile(archive) as z:
            pins={name:digest(z.read(name)) for name in z.namelist()}
        self.assertEqual(len(pins),2)
        return sources,archive,pins

    def test_two_complete_sources_and_six_original_vs_rebuilt_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            sources,jar,pins=self.fixture(root)
            report=verify_standalone_sources(
                jar,sources,root/"rebuilt",
                original_sha256=digest(jar.read_bytes()),class_sha256=pins,
            )
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"],2)
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            self.assertEqual(
                report["explicit_original_project_dependency_closure"][
                    "source_project_dependency_edges"],0,
            )
            probe=root/"SyntheticBufferTranscript.java"
            probe.write_text(PROBE,encoding="utf-8")
            build=subprocess.run([
                "javac","--release","9","-cp",str(jar),
                "-d",str(root),str(probe),
            ],capture_output=True,text=True,timeout=45)
            self.assertEqual(build.returncode,0,build.stderr)
            outputs=[]
            for cp in (jar,root/"rebuilt"/"classes"):
                result=subprocess.run([
                    "java","-cp",str(root)+__import__("os").pathsep+str(cp),
                    "SyntheticBufferTranscript",
                ],capture_output=True,text=True,timeout=45)
                self.assertEqual(result.returncode,0,result.stderr)
                outputs.append(result.stdout)
            self.assertEqual(outputs[0],outputs[1])
            self.assertEqual(len(outputs[0].splitlines()),6)

    def test_changed_synthetic_growth_fails_exact_instruction_parity(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            sources,jar,pins=self.fixture(root)
            changed=sources/"rs/syntheticbuffers/IntPool.java"
            changed.write_text(changed.read_text().replace(
                "capacity*=2;","capacity*=3;"),encoding="utf-8")
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH",
            ):
                verify_standalone_sources(
                    jar,sources,root/"bad",
                    original_sha256=digest(jar.read_bytes()),class_sha256=pins,
                )
            self.assertFalse((root/"bad"/"SOURCE-REBUILD-VERIFY.json").exists())

    def test_wrong_synthetic_original_jar_pin_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            sources,jar,pins=self.fixture(root)
            with self.assertRaises(StandaloneSourceParityError):
                verify_standalone_sources(
                    jar,sources,root/"bad",
                    original_sha256="0"*64,class_sha256=pins,
                )
            self.assertFalse((root/"bad"/"SOURCE-REBUILD-VERIFY.json").exists())

    def test_missing_source_cannot_be_accepted_as_complete_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            sources,jar,pins=self.fixture(root)
            (sources/"rs/syntheticbuffers/FloatPool.java").unlink()
            with self.assertRaises(StandaloneSourceParityError):
                verify_standalone_sources(
                    jar,sources,root/"bad",
                    original_sha256=digest(jar.read_bytes()),class_sha256=pins,
                )
            self.assertFalse((root/"bad"/"SOURCE-REBUILD-VERIFY.json").exists())

if __name__=="__main__":
    unittest.main(verbosity=2)
