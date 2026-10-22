"""Unrelated synthetic Java9 test: whole constructor/clinit exact parity.

This contains no original-client game class, source, data table, or classfile.
"""
from __future__ import annotations
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

STUB = """package rs.synthetic;
// DECLARATION-ONLY PLACEHOLDER: not a recovered original dependency
public final class ToySwitch { public static boolean enabled; }
"""
SOURCE = """package rs.synthetic;
public final class ToyGeometry {
 public static final int[][] CODES;
 public final int[] a, b;
 public final int value;
 public ToyGeometry(int p1,int p2,int p3,int p4,int p5,int p6,int p7,
  int p8,int p9,int p10,int p11,int p12,int p13,int p14,int p15,
  int p16,int p17,int p18,int p19) {
  value=p19;
  int[] shape=CODES[Math.floorMod(p14,3)];
  a=new int[shape.length];b=new int[shape.length];
  for(int i=0;i<shape.length;i++){
   int code=shape[i];int x=p1*32,z=p18*32;
   if(code==0){x+=p13;z+=p4;}
   else if(code==1){x+=(p12+p11)>>1;z+=p17;}
   else{x+=p5;z+=(p6+p8)>>1;}
   a[i]=x;b[i]=z;
  }
 }
 public int[] first(){return a;}
 public int[] optional(){return ToySwitch.enabled ? b : null;}
 static { CODES=new int[][]{{0,1,2},{2,1},{0,2,1,0}}; }
}
"""
PROBE = """import java.io.*;import java.net.*;import java.lang.reflect.*;
import java.util.*;
public class ToyConstructorProbe {
 static String snapshot(Class<?> type,int[] inputs)throws Exception{
  Class<?>[] desc=new Class<?>[19];Arrays.fill(desc,int.class);
  Object[] vals=new Object[19];for(int i=0;i<19;i++)vals[i]=inputs[i];
  Object o=type.getConstructor(desc).newInstance(vals);
  return Arrays.toString((int[])type.getField("a").get(o))+":"+
         Arrays.toString((int[])type.getField("b").get(o))+":"+
         type.getField("value").getInt(o);
 }
 public static void main(String[] args)throws Exception{
  try(URLClassLoader a=new URLClassLoader(new URL[]{new File(args[0]).toURI().toURL()},ClassLoader.getPlatformClassLoader());
      URLClassLoader b=new URLClassLoader(new URL[]{new File(args[1]).toURI().toURL()},ClassLoader.getPlatformClassLoader())){
   Class<?> x=a.loadClass("rs.synthetic.ToyGeometry"),y=b.loadClass("rs.synthetic.ToyGeometry");
   int count=0;
   for(int shape=0;shape<13;shape++)for(int rotation=0;rotation<4;rotation++)for(int variant=0;variant<3;variant++){
    int[] parameters=new int[19];
    for(int i=0;i<19;i++)parameters[i]=variant==0 ? i+2 : variant==1 ? -i*3 : i*5;
    parameters[13]=shape;parameters[6]=rotation;
    if(!snapshot(x,parameters).equals(snapshot(y,parameters)))
     throw new AssertionError("SYNTHETIC_CONSTRUCTOR_BEHAVIOR_MISMATCH");
    count++;
   }
   if(count!=156)throw new AssertionError("SCENARIO_COUNT_MISMATCH");
   System.out.println("SYNTHETIC_JAVA9_FULL_CONSTRUCTOR_PARITY_156_PASS");
  }
 }
}
"""

def run(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=55)
    if p.returncode:raise AssertionError(p.stderr[-1200:])
    return p.stdout

def normalized(disasm):
    result=[]
    for row in disasm.splitlines():
        if row.startswith('Compiled from '):continue
        match=re.fullmatch(r'\s*(\d+):\s+([a-z][a-z0-9_]*)\s*(.*)',row)
        if match:
            offset,op,argument=match.groups()
            result.append(('bytecode',int(offset),op,' '.join(re.sub(r'#\d+\b','#CP',argument).split())))
        elif row.strip():result.append(('declaration',row.strip()))
    return result

@unittest.skipUnless(all(shutil.which(x) for x in ('javac','javap','java')), 'JDK 9+ needed')
class SyntheticFullGeometrySourceTests(unittest.TestCase):
    def fixture(self,root,label,source=SOURCE):
        folder=root/label/'src/rs/synthetic';folder.mkdir(parents=True)
        (folder/'ToySwitch.java').write_text(STUB,encoding='utf-8')
        (folder/'ToyGeometry.java').write_text(source,encoding='utf-8')
        classes=root/label/'classes';classes.mkdir()
        run(['javac','--release','9','-proc:none','-g:none',
             '-classpath',str(root/'empty-cp'),'-sourcepath',str(root/'empty-sp'),
             '-d',str(classes),str(folder/'ToySwitch.java'),str(folder/'ToyGeometry.java')])
        self.assertEqual({p.relative_to(classes).as_posix() for p in classes.rglob('*.class')},
            {'rs/synthetic/ToySwitch.class','rs/synthetic/ToyGeometry.class'})
        self.assertEqual((classes/'rs/synthetic/ToyGeometry.class').read_bytes()[:8],
                         bytes.fromhex('cafebabe00000035'))
        return classes,normalized(run(['javap','-p','-s','-c','-classpath',str(classes),
                                        'rs.synthetic.ToyGeometry']))

    def test_full_method_declarations_instructions_and_constructor_behaviors(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            first,a=self.fixture(root,'first')
            rebuilt,b=self.fixture(root,'rebuilt')
            self.assertEqual(a,b)
            self.assertGreater(sum(row[0]=='bytecode' for row in a),50)
            probe=root/'ToyConstructorProbe.java';probe.write_text(PROBE,encoding='utf-8')
            run(['javac','--release','9','-d',str(root),str(probe)])
            self.assertIn('SYNTHETIC_JAVA9_FULL_CONSTRUCTOR_PARITY_156_PASS',
                run(['java','-cp',str(root),'ToyConstructorProbe',str(first),str(rebuilt)]))
            self.assertIn('DECLARATION-ONLY PLACEHOLDER',STUB)

    def test_changed_constructor_operand_fails_bytecode_parity(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            _,reference=self.fixture(root,'original')
            _,altered=self.fixture(root,'altered',SOURCE.replace('value=p19;','value=p17;'))
            self.assertNotEqual(reference,altered)

    def test_changed_static_nested_array_fails_bytecode_parity(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            _,reference=self.fixture(root,'original')
            _,altered=self.fixture(root,'altered',SOURCE.replace('{2,1}','{2,2}'))
            self.assertNotEqual(reference,altered)

if __name__=='__main__':
    unittest.main(verbosity=2)
