"""Synthetic-only Java9 10-position enum and four generated switch-table tests.

All names, Java source and case values are unrelated toy fixtures.
No original v311 binary, original Java or external vendor class is included.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

VALUES=("FLOATING","DOCKED","LEFT","CENTER","RIGHT","LOW_LEFT","LOW_RIGHT","SIDE","EDGE","HINT")
SWITCHES={
    "Alpha":("LEFT","CENTER","RIGHT","LOW_LEFT","LOW_RIGHT","SIDE","EDGE"),
    "Beta":("HINT","DOCKED","FLOATING"),
    "Gamma":("EDGE","SIDE"),
    "Delta":("LOW_LEFT","LOW_RIGHT","LEFT","CENTER","EDGE","RIGHT","SIDE"),
}

def run(argv):
    p=subprocess.run(argv,capture_output=True,text=True,timeout=50)
    if p.returncode:raise AssertionError(p.stderr[-1300:])
    return p.stdout

def compile_fixture(root,mutate=None):
    source=root/"src/synthetic/overlay"
    source.mkdir(parents=True)
    (source/"LayoutPosition.java").write_text(
        "package synthetic.overlay; public enum LayoutPosition { "
        +",".join(VALUES)+"; }\n",encoding="utf-8")
    for name,items in SWITCHES.items():
        cases=["case "+value+": return "+str(i+1)+";" for i,value in enumerate(items)]
        if name==mutate: cases[:2]=list(reversed(cases[:2]))
        body=("package synthetic.overlay; class "+name+
              " { static int translate(LayoutPosition p) { switch(p) {\n"+
              "\n".join(cases)+"\ndefault:return 0; } } }\n")
        (source/(name+".java")).write_text(body,encoding="utf-8")
    out=root/"built"
    out.mkdir()
    run(["javac","--release","9","-proc:none","-g:none",
         "-d",str(out),*[str(p) for p in sorted(source.glob("*.java"))]])
    return out

PROBE="""import java.lang.reflect.*;
public class ToyOverlaySwitchProbe {
 public static void main(String[] ignored)throws Exception {
  Class<?> e=Class.forName("synthetic.overlay.LayoutPosition");
  Object[] values=(Object[])e.getMethod("values").invoke(null);
  for(Object v:values)System.out.println("ENUM:"+((Enum<?>)v).name()+":"+((Enum<?>)v).ordinal());
  for(String owner:new String[]{"Alpha","Beta","Gamma","Delta"}) {
   Class<?> c=Class.forName("synthetic.overlay."+owner+"$1");
   Field f=c.getDeclaredField("$SwitchMap$synthetic$overlay$LayoutPosition");
   f.setAccessible(true);
   int[] map=(int[])f.get(null);
   for(int i=0;i<values.length;i++)System.out.println("MAP:"+owner+":"+i+":"+map[i]);
   System.out.println("SHAPE:"+owner+":"+c.isSynthetic()+":"+c.getDeclaredConstructors().length);
  }
 }
}
"""

@unittest.skipUnless(
    all(shutil.which(x) for x in ("javac","java","javap")),
    "JDK with Java9 compilation support required",
)
class SyntheticOverlaySwitchIsland(unittest.TestCase):
    def test_five_generated_original_shape_candidates_and_fifty_four_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            a=compile_fixture(root/"a")
            b=compile_fixture(root/"b")
            names=["LayoutPosition.class"]+[name+"$1.class" for name in SWITCHES]
            self.assertEqual(len(names),5)
            self.assertEqual(len(list((a/"synthetic/overlay").glob("*.class"))),9)
            for name in names:
                first=(a/"synthetic/overlay"/name).read_bytes()
                second=(b/"synthetic/overlay"/name).read_bytes()
                self.assertEqual(hashlib.sha256(first).digest(),
                                 hashlib.sha256(second).digest())
            probe=root/"ToyOverlaySwitchProbe.java"
            probe.write_text(PROBE,encoding="utf-8")
            run(["javac","--release","9","-d",str(root),str(probe)])
            observed=[]
            for cp in (a,b):
                observed.append(run([
                    "java","-cp",str(root)+os.pathsep+str(cp),
                    "ToyOverlaySwitchProbe",
                ]))
            self.assertEqual(observed[0],observed[1])
            self.assertEqual(len(observed[0].splitlines()),54)
            self.assertIn("SHAPE:Delta:true:0",observed[0])

    def test_reordered_cases_rejected_by_synthetic_jvm_instruction_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            a=compile_fixture(root/"a")
            b=compile_fixture(root/"b",mutate="Alpha")
            self.assertEqual(
                (a/"synthetic/overlay/LayoutPosition.class").read_bytes(),
                (b/"synthetic/overlay/LayoutPosition.class").read_bytes(),
            )
            self.assertNotEqual(
                (a/"synthetic/overlay/Alpha$1.class").read_bytes(),
                (b/"synthetic/overlay/Alpha$1.class").read_bytes(),
            )
            first=run(["javap","-p","-c","-classpath",str(a),
                       "synthetic.overlay.Alpha$1"])
            second=run(["javap","-p","-c","-classpath",str(b),
                        "synthetic.overlay.Alpha$1"])
            self.assertNotEqual(first,second)

if __name__=="__main__":
    unittest.main(verbosity=2)
