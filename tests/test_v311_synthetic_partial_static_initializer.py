"""Synthetic Java9 nested-array <clinit> proof; does not use any game class."""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ORIGINAL = """
package synth;
public final class ArrayRecord {
 public static final int[] A;
 public static final int[][] B;
 public final int value;
 public ArrayRecord(int x) { value=x+7; }
 public int read() { return value; }
 static { A=new int[]{2,4}; B=new int[][]{{1,3,5},{0,6,7,8}}; }
}
"""
PARTIAL = """
package synth;
public final class ArrayRecord {
 public static final int[] A;
 public static final int[][] B;
 public final int value;
 public ArrayRecord() { value=0; } // unmatched constructor: not a full recovery
 public int read() { return value; }
 static { A=new int[]{2,4}; B=new int[][]{{1,3,5},{0,6,7,8}}; }
}
"""
JAVA_PROBE = """
import java.io.*;import java.net.*;import java.util.*;
public class ToyArrays {
 static String snapshot(String path)throws Exception{
  try(URLClassLoader loader=new URLClassLoader(new URL[]{new File(path).toURI().toURL()},
                                              ClassLoader.getPlatformClassLoader())){
   Class<?> c=Class.forName("synth.ArrayRecord",true,loader);
   return Arrays.toString((int[])c.getField("A").get(null))+":"+
          Arrays.deepToString((int[][])c.getField("B").get(null));
  }
 }
 public static void main(String[] args)throws Exception{
  if(!snapshot(args[0]).equals(snapshot(args[1])))
   throw new AssertionError("DIFFERENT_STATIC_ARRAYS");
  System.out.println("SYNTHETIC_STATIC_ARRAYS_MATCH");
 }
}
"""

def run(argv):
    result=subprocess.run(argv,capture_output=True,text=True,timeout=45)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout

def relevant(disasm):
    lines=disasm.splitlines()
    wanted={'public int read();','static {};'}
    selected={}
    for i,line in enumerate(lines):
        name=line.strip()
        if name not in wanted:continue
        if i+2>=len(lines) or not lines[i+1].strip().startswith('descriptor: '):
            raise AssertionError('missing method descriptor')
        if lines[i+2].strip()!='Code:':raise AssertionError('missing Code')
        code=[]
        for row in lines[i+3:]:
            if not row.strip() or row.strip()=='}':break
            match=re.fullmatch(r'\s*(\d+):\s+([a-z][a-z0-9_]*)\s*(.*)',row)
            if not match:raise AssertionError('unknown JVM instruction')
            offset,opcode,operand=match.groups()
            if '#' in operand:
                front,separator,symbol=operand.partition('//')
                if not separator:raise AssertionError('missing symbolic operand')
                operand=re.sub(r'#\d+\b','#CP',front).strip()+' // '+symbol.strip()
            else:operand=' '.join(operand.split())
            code.append((int(offset),opcode,operand))
        selected[name]=(lines[i+1].strip(),code)
    if set(selected)!=wanted:raise AssertionError('missing required methods')
    return selected

@unittest.skipUnless(all(shutil.which(x) for x in ('javac','java','javap')),
                     'requires a Java9-capable JDK')
class SyntheticPartialStaticTests(unittest.TestCase):
    def fixture(self,root,changed=PARTIAL):
        outputs=[]
        for name,source in [('original',ORIGINAL),('partial',changed)]:
            sourcefile=root/name/'synth/ArrayRecord.java'
            sourcefile.parent.mkdir(parents=True)
            sourcefile.write_text(source,encoding='utf-8')
            built=root/name/'classes';built.mkdir()
            cp=root/'empty-cp';cp.mkdir(exist_ok=True)
            sp=root/'empty-sp';sp.mkdir(exist_ok=True)
            run(['javac','--release','9','-proc:none','-g:none',
                 '-classpath',str(cp),'-sourcepath',str(sp),'-d',str(built),
                 str(sourcefile)])
            disasm=run(['javap','-p','-s','-c','-classpath',str(built),
                        'synth.ArrayRecord'])
            outputs.append((built,relevant(disasm)))
        return outputs

    def test_selected_instructions_arrays_match_but_constructor_does_not(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (a,first),(b,second)=self.fixture(root)
            self.assertEqual(first,second)
            self.assertNotEqual((a/'synth/ArrayRecord.class').read_bytes(),
                                (b/'synth/ArrayRecord.class').read_bytes())
            probe=root/'ToyArrays.java'
            probe.write_text(JAVA_PROBE,encoding='utf-8')
            run(['javac','--release','9','-d',str(root),str(probe)])
            self.assertIn('SYNTHETIC_STATIC_ARRAYS_MATCH',
                          run(['java','-cp',str(root),'ToyArrays',str(a),str(b)]))

    def test_changed_nested_array_value_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            (a,first),(b,second)=self.fixture(
                Path(folder),PARTIAL.replace('{0,6,7,8}','{0,6,7,9}'))
            self.assertNotEqual(first['static {};'],second['static {};'])

    def test_truncated_array_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            (a,first),(b,second)=self.fixture(
                Path(folder),PARTIAL.replace('{0,6,7,8}','{0,6,7}'))
            self.assertNotEqual(first['static {};'],second['static {};'])

    def test_altered_accessor_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            (a,first),(b,second)=self.fixture(
                Path(folder),PARTIAL.replace('return value;','return value+1;'))
            self.assertEqual(first['static {};'],second['static {};'])
            self.assertNotEqual(first['public int read();'],second['public int read();'])

if __name__=='__main__':
    unittest.main(verbosity=2)
