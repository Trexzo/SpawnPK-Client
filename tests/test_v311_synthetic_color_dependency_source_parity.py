"""Independent toy Java9 color/bit-packing parity and fail-closed tests.

No v311 original game binary, decompiled source, recovered proprietary Java,
authentic constants, game classfiles or account information are included.
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

SOURCE = """
package rs.synthetic88;
import java.awt.Color;
public final class HueSampler {
 public static final int MASK_X=31;
 public static final int MASK_Y=15;
 public static final int MASK_Z=127;
 private HueSampler(){}
 public static short encode(int x,int y,int z){
  return (short)(((x & 31)<<11)|((y & 15)<<7)|(z & 127));
 }
 public static String describe(short packed){
  return "color("+(((int)packed>>11)&31)+","+(((int)packed>>7)&15)+")";
 }
 public static float sampleHue(int rgb){
  float[] values=Color.RGBtoHSB((rgb>>>16)&255,(rgb>>>8)&255,rgb&255,null);
  return values[0];
 }
}
"""

PROBE = """
import rs.synthetic88.HueSampler;
public class Synthetic88ColorProbe {
 public static void main(String[] args){
  int[] samples={Integer.MIN_VALUE,-1,0,1,7,127,0x123456,0xffffff,0xFF0000};
  for(int color:samples){
   short packed=HueSampler.encode(color,color>>>3,color^77);
   System.out.println("C:"+color+":"+packed+":"+
    HueSampler.describe(packed)+":"+
    Float.floatToRawIntBits(HueSampler.sampleHue(color)));
  }
 }
}
"""

def sha(blob:bytes)->str:
    return hashlib.sha256(blob).hexdigest()

def run(args):
    result=subprocess.run(args,capture_output=True,text=True,timeout=50)
    if result.returncode:
        raise AssertionError(result.stderr[-1800:])
    return result.stdout

@unittest.skipUnless(
    all(shutil.which(tool) for tool in ("javac","javap","java")),
    "Java 9-capable JDK required",
)
class Synthetic88ColorParity(unittest.TestCase):
    def fixture(self,root:Path):
        source=root/"source"/"rs/synthetic88/HueSampler.java"
        source.parent.mkdir(parents=True)
        source.write_text(SOURCE,encoding="utf-8")
        classes=root/"original-classes"
        classes.mkdir()
        run(["javac","--release","9","-proc:none","-g:none",
             "-classpath",str(root/"empty-cp"),
             "-sourcepath",str(root/"empty-src"),
             "-d",str(classes),str(source)])
        jar=root/"synthetic-original.jar"
        with zipfile.ZipFile(jar,"w") as archive:
            archive.writestr("rs/synthetic88/HueSampler.class",
                (classes/"rs/synthetic88/HueSampler.class").read_bytes())
        with zipfile.ZipFile(jar) as archive:
            pin=sha(archive.read("rs/synthetic88/HueSampler.class"))
        return source,jar,{"rs/synthetic88/HueSampler.class":pin}

    def test_exact_java9_bytecode_constant_values_and_nine_behaviors(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source,jar,pins=self.fixture(root)
            report=verify_standalone_sources(
                jar,root/"source",root/"rebuilt",
                original_sha256=sha(jar.read_bytes()),class_sha256=pins)
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"],1)
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            name="rs.synthetic88.HueSampler"
            original_constants=run(["javap","-p","-constants","-classpath",str(jar),name])
            rebuilt_constants=run(["javap","-p","-constants",
                                   "-classpath",str(root/"rebuilt"/"classes"),name])
            self.assertEqual(original_constants,rebuilt_constants)
            probe=root/"Synthetic88ColorProbe.java"
            probe.write_text(PROBE,encoding="utf-8")
            run(["javac","--release","9","-cp",str(jar),"-d",str(root),str(probe)])
            outputs=[]
            for cp in (jar,root/"rebuilt"/"classes"):
                outputs.append(run(["java","-Djava.awt.headless=true",
                    "-cp",str(root)+os.pathsep+str(cp),"Synthetic88ColorProbe"]))
            self.assertEqual(outputs[0],outputs[1])
            self.assertEqual(len(outputs[0].splitlines()),9)

    def test_changed_packing_instruction_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source,jar,pins=self.fixture(root)
            changed=source.read_text().replace("(x & 31)","(x & 30)")
            self.assertNotEqual(changed,source.read_text())
            source.write_text(changed,encoding="utf-8")
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH"):
                verify_standalone_sources(
                    jar,root/"source",root/"rejected",
                    original_sha256=sha(jar.read_bytes()),class_sha256=pins)

    def test_missing_source_and_wrong_authority_are_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source,jar,pins=self.fixture(root)
            with self.assertRaisesRegex(StandaloneSourceParityError,"WRONG_ORIGINAL_JAR"):
                verify_standalone_sources(
                    jar,root/"source",root/"bad",
                    original_sha256="0"*64,class_sha256=pins)
            source.unlink()
            with self.assertRaises(StandaloneSourceParityError):
                verify_standalone_sources(
                    jar,root/"source",root/"missing",
                    original_sha256=sha(jar.read_bytes()),class_sha256=pins)

if __name__=="__main__":
    unittest.main(verbosity=2)
