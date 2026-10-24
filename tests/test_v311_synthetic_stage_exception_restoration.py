"""Unrelated toy Java9 bytecode witness, no original v311 source or binaries."""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from spk_recovery.checked_exception_identity import strip_exact_exception_attribute

FAILURE = "package toy; public class StageFailure extends Exception {public StageFailure(String s){super(s);}}"
PROGRAM = """package toy;
public final class Program {
  public int build(int input) throws StageFailure {
    if (input < 0) throw new StageFailure("negative");
    return input * 3;
  }
}
"""
PROBE = """import toy.Program;
public class StageProbe {
  public static void main(String[] ignored) throws Exception {
    Program p=new Program();
    for(int value: new int[]{-1,0,1,7,42}) {
      try{System.out.println("V:"+value+":"+p.build(value));}
      catch(Exception e){System.out.println("E:"+value+":"+e.getClass().getName()+":"+e.getMessage());}
    }
  }
}
"""


def run(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=45)
    if p.returncode:
        raise AssertionError(p.stderr[-1500:])
    return p.stdout


@unittest.skipUnless(all(shutil.which(x) for x in ("javac","javap","java")), "JDK9+ required")
class SyntheticStageExceptionIdentityTests(unittest.TestCase):
    def fixtures(self,root):
        src=root/"src/toy";src.mkdir(parents=True)
        (src/"StageFailure.java").write_text(FAILURE)
        (src/"Program.java").write_text(PROGRAM)
        original=root/"original";original.mkdir()
        run(["javac","--release","9","-proc:none","-g:none","-d",str(original),
             str(src/"StageFailure.java"),str(src/"Program.java")])
        raw=(original/"toy/Program.class").read_bytes()
        return original,raw

    def test_exact_declaration_removal_preserves_all_toy_executable_jvm_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); original, raw=self.fixtures(root)
            new=strip_exact_exception_attribute(raw, method="build", descriptor="(I)I", exception="toy/StageFailure")
            self.assertNotEqual(raw,new)
            rebuilt=root/"rebuilt/toy";rebuilt.mkdir(parents=True)
            (rebuilt/"Program.class").write_bytes(new)
            (rebuilt/"StageFailure.class").write_bytes((original/"toy/StageFailure.class").read_bytes())
            before=run(["javap","-c","-s","-p","-classpath",str(original),"toy.Program"])
            after=run(["javap","-c","-s","-p","-classpath",str(root/"rebuilt"),"toy.Program"])
            self.assertEqual(before.replace(" throws toy.StageFailure", ""),after)
            probe=root/"StageProbe.java";probe.write_text(PROBE)
            run(["javac","--release","9","-cp",str(original),"-d",str(root),str(probe)])
            outputs=[]
            for cp in (original,root/"rebuilt"):
                outputs.append(run(["java","-cp",str(root)+os.pathsep+str(cp),"StageProbe"]))
            self.assertEqual(outputs[0],outputs[1])
            self.assertEqual(len(outputs[0].splitlines()),5)
            self.assertIn("E:-1:toy.StageFailure:negative",outputs[0])

    def test_wrong_method_or_exception_or_classfile_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,raw=self.fixtures(Path(tmp))
            for args,code in [
                ({"method":"absent","descriptor":"(I)I","exception":"toy/StageFailure"},"EXACT_METHOD_NOT_FOUND"),
                ({"method":"build","descriptor":"(I)I","exception":"toy/Wrong"},"WRONG_CHECKED_EXCEPTION_TYPE"),
            ]:
                with self.assertRaisesRegex(ValueError,code):
                    strip_exact_exception_attribute(raw,**args)
            with self.assertRaisesRegex(ValueError,"NOT_A_JAVA9_CLASSFILE"):
                strip_exact_exception_attribute(b"invalid",method="build",descriptor="(I)I",exception="toy/StageFailure")


if __name__=="__main__":
    unittest.main(verbosity=2)
